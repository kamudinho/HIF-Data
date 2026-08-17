import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO
import requests
from PIL import Image
import os
from mplsoccer import Pitch
import io
import base64

# --- DATA OG MAPPING ---
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.utils.mapping import OPTA_EVENT_TYPES, OPTA_QUALIFIERS, get_action_label, is_assist, har_qualifier

# --- SPILLER-KATEGORIER ---
from data.utils.spiller_qualifiers import ACTION_CATEGORIES, POSITION_ACTIONS

# --- GENERELLE UI-HJÆLPERE ---
from utils.helpers import get_logo_img, get_team_color, get_ordinal, draw_player_info_box

# --- IMPORT AF SPILLERE OG SQL ---
from data.sql.liga_spillere import hent_match_og_haendelsesdata

try:
    from data.players import player_mapping
    valgt_player_uuid = st.session_state.get('valgt_player_uuid', getattr(player_mapping, 'valgt_player_uuid', None))
    valgt_spiller = st.session_state.get('valgt_spiller', getattr(player_mapping, 'valgt_spiller', None))
    df_spiller = getattr(player_mapping, 'df_spiller', None)
    hold_logo = getattr(player_mapping, 'hold_logo', None)
    primær_farve = getattr(player_mapping, 'primær_farve', "#df003b")
    valgt_hold = getattr(player_mapping, 'valgt_hold', "Hvidovre")
    conn = getattr(player_mapping, 'conn', None)
    SEASONNAME = getattr(player_mapping, 'SEASONNAME', "2026/2027")
except ImportError:
    st.error("Kunne ikke finde eller indlæse 'player_mapping.py'. Sørg for filen ligger i mappen.")
    st.stop()

# --- POSITIONSDATA ---
_STATIC_PLAYERS = getattr(player_mapping, 'PLAYER_MAPPING', [])
POSITION_MAP = {
    str(p.get('player_optauuid')).strip(): p.get('position', 'Ukendt')
    for p in _STATIC_PLAYERS if p.get('player_optauuid')
}
POSITION_DA = {
    "Goalkeeper": "Målmand",
    "Defender": "Forsvar",
    "Midfielder": "Midtbane",
    "Attacker": "Angriber",
}
POSITION_TO_SPQ = {
    "Goalkeeper": "GK",
    "Defender": "DEF",
    "Midfielder": "MID",
    "Attacker": "FWD",
}

KATEGORIER_DER_KRAEVER_QUALIFIER = {
    "indlaeg",
    "afgoerende_pasninger",
    "keeper_distribution",
    "corner_frispark",
    "blokeringer",
}

ALLE_SPQ_KATEGORIER = sorted({
    key
    for pos_dict in POSITION_ACTIONS.values()
    for side_liste in pos_dict.values()
    for key in side_liste
})


def tilfoej_kategori_kolonner(df_stats: pd.DataFrame, df_events: pd.DataFrame, category_keys) -> pd.DataFrame:
    if df_events is None or df_events.empty:
        for key in category_keys:
            df_stats[key] = 0
        return df_stats

    if 'qual_set' not in df_events.columns:
        df_events = df_events.copy()
        df_events['qual_set'] = df_events['qual_list'].apply(
            lambda ql: frozenset(str(q).strip() for q in ql) if isinstance(ql, list)
            else frozenset(str(q).strip() for q in str(ql).split(','))
        )

    for key in category_keys:
        cat = ACTION_CATEGORIES[key]
        type_mask = df_events['event_typeid'].isin(cat['type_ids'])

        if key in KATEGORIER_DER_KRAEVER_QUALIFIER and cat['qualifier_ids']:
            qual_ids = {str(q) for q in cat['qualifier_ids']}
            delmaengde = df_events.loc[type_mask, 'qual_set']
            qual_match = delmaengde.apply(lambda s: not qual_ids.isdisjoint(s))
            final_mask = pd.Series(False, index=df_events.index)
            final_mask.loc[qual_match.index] = qual_match
        else:
            final_mask = type_mask

        counts = df_events[final_mask].groupby('player_optauuid').size()
        df_stats[key] = counts.reindex(df_stats.index, fill_value=0).astype('Int64')

    return df_stats


def tilfoej_fremadrettede_pasninger(df_stats: pd.DataFrame, df_events: pd.DataFrame) -> pd.DataFrame:
    if df_events is None or df_events.empty or 'end_x' not in df_events.columns:
        df_stats['fremadrettede_pasninger'] = 0
        return df_stats

    mask = (
        (df_events['event_typeid'] == 1)
        & df_events['end_x'].notna()
        & (df_events['end_x'] > df_events['event_x'])
    )
    counts = df_events[mask].groupby('player_optauuid').size()
    df_stats['fremadrettede_pasninger'] = counts.reindex(df_stats.index, fill_value=0).astype('Int64')
    return df_stats


DB = "KLUB_HVIDOVREIF.AXIS"
SEASONNAME = "2026/2027"
TEAM_WYID = 7490
COMPETITION_WYID = (328,)
LIGA_IDS = "('2mb332vncy4450vu14paj8844', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '335', '328', '329', '43319', '331')"

def _get_quals(r):
    ql = r.get('qual_list', [])
    if isinstance(ql, list):
        return [str(q).strip() for q in ql]
    return [str(q).strip() for q in str(ql).split(',')]


def count_kamp_qual(df_group, eid, qids):
    return df_group.apply(lambda r: har_qualifier(r['event_typeid'], r.get('qual_list', []), eid, qids), axis=1).sum()


def _byg_event_stats(df_events: pd.DataFrame) -> pd.DataFrame:
    return df_events.groupby(['player_optauuid', 'visningsnavn']).apply(lambda x: pd.Series({
        'Kampe': x['match_optauuid'].nunique() if 'match_optauuid' in x.columns else 1,
        'Aktioner': len(x),
        'Gule_kort': count_kamp_qual(x, 17, 31),
        'Roede_kort': count_kamp_qual(x, 17, 33),
        'Indskiftet': (x['event_typeid'] == 19).sum(),
        'Udskiftet': (x['event_typeid'] == 18).sum(),
        'Pasninger': x['Pasninger_Total'].sum() if 'Pasninger_Total' in x.columns else 0,
        'Pasninger_Succes': x['Pasninger_Succes'].sum() if 'Pasninger_Succes' in x.columns else 0,
        'Stikninger': count_kamp_qual(x, 1, 4),
        'Indlæg': count_kamp_qual(x, 1, [2, 155]),
        'Afslutninger': x['event_typeid'].isin([13, 14, 15, 16]).sum(),
        'Erobringer': x['event_typeid'].isin([7, 8, 12, 49]).sum(),
        'Driblinger': (x['event_typeid'] == 3).sum(),
        'Driblinger_Succes': x.apply(lambda r: 1 if str(r['event_typeid']) == "3" and "211" not in _get_quals(r) else 0, axis=1).sum(),
        'Gennembrud_Overtake': x.apply(lambda r: 1 if str(r['event_typeid']) == "3" and "465" in _get_quals(r) else 0, axis=1).sum(),
        'Rum_Driblinger_Space': x.apply(lambda r: 1 if str(r['event_typeid']) == "3" and "464" in _get_quals(r) else 0, axis=1).sum(),
        'Offensive_Dueller': x.apply(lambda r: 1 if "286" in _get_quals(r) else 0, axis=1).sum(),
        'Defensive_Dueller': x.apply(lambda r: 1 if "285" in _get_quals(r) else 0, axis=1).sum(),
        'Defensive_1v1_Stoppet': x.apply(lambda r: 1 if "467" in _get_quals(r) else 0, axis=1).sum(),
        'Chancer_skabt': x.apply(lambda r: 1 if '210' in _get_quals(r) else 0, axis=1).sum(),
        'Key_Passes': x.apply(lambda r: 1 if '210' in _get_quals(r) else 0, axis=1).sum(),
        'Tacklinger': (x['event_typeid'] == 7).sum(),
        'Clearinger': (x['event_typeid'] == 12).sum(),
        'Blokeringer': (x['event_typeid'] == 55).sum(),
        'Interceptioner': (x['event_typeid'] == 5).sum(),
        'Frispark_imod': (x['event_typeid'] == 4).sum()
    })).reset_index().drop_duplicates(subset=['player_optauuid']).set_index('player_optauuid')


def _agger_expected(df_expected: pd.DataFrame, hold_optauuid: str = None) -> pd.DataFrame:
    if df_expected is None or df_expected.empty:
        return pd.DataFrame(columns=['xg', 'xa', 'minutes'])
    df = df_expected.copy()
    if hold_optauuid is not None and 'hold_optauuid' in df.columns:
        df = df[df['hold_optauuid'] == hold_optauuid]
    for col in ('xg', 'xa', 'minutes'):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0
    if 'player_optauuid' not in df.columns or df.empty:
        return pd.DataFrame(columns=['xg', 'xa', 'minutes'])
    return df.groupby('player_optauuid')[['xg', 'xa', 'minutes']].sum()


def _forbered_events(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=['visningsnavn']).copy()
    df['event_timestamp'] = pd.to_datetime(df['event_timestamp_str'])
    df['qual_list'] = df['qualifiers'].fillna('').str.split(',')
    df['Pasninger_Total'] = (df['event_typeid'] == 1).astype(int)
    df['Pasninger_Succes'] = ((df['event_typeid'] == 1) & (df['outcome'] == 1)).astype(int)
    return df


@st.cache_data(ttl=600, show_spinner="Indlæser spillerliste...")
def hent_navne_map() -> dict:
    try:
        csv_path = os.path.join(os.getcwd(), 'data', 'players', '1div_overskrivning.csv')
        df_csv = pd.read_csv(csv_path)
        return dict(zip(df_csv['PLAYER_OPTAUUID'].astype(str), df_csv['NAVN']))
    except Exception:
        return {}


@st.cache_data(ttl=1800, show_spinner=False)
def hent_holdliste(_conn) -> dict:
    df_teams_raw = _conn.query(
        f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID "
        f"FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}"
    )
    if df_teams_raw is not None:
        df_teams_raw.columns = df_teams_raw.columns.str.lower()
    else:
        df_teams_raw = pd.DataFrame()

    mapping_lookup = {
        str(info['opta_uuid']).lower().replace('t', ''): name
        for name, info in TEAMS.items() if 'opta_uuid' in info
    }

    team_map = {}
    if not df_teams_raw.empty:
        for _, r in df_teams_raw.iterrows():
            uuid_clean = str(r['contestanthome_optauuid']).lower().replace('t', '')
            if uuid_clean in mapping_lookup:
                team_map[mapping_lookup[uuid_clean]] = r['contestanthome_optauuid']
    return team_map


@st.cache_data(ttl=300, show_spinner="Behandler spiller- og holddata...")
def byg_spiller_og_holdstats(_conn, valgt_uuid_hold: str, navne_map: dict):
    df_all_raw, df_expected, df_db_stats = hent_match_og_haendelsesdata(
        _conn, DB, valgt_uuid_hold, LIGA_IDS, navne_map
    )
    if df_all_raw is None:
        df_all_raw = pd.DataFrame()
    if df_all_raw.empty:
        tom = pd.DataFrame()
        return tom, tom, tom, tom, tom

    expected_liga = _agger_expected(df_expected)
    expected_hold = _agger_expected(df_expected, hold_optauuid=valgt_uuid_hold)

    df_liga_total = _forbered_events(df_all_raw)

    if 'hold_optauuid' in df_all_raw.columns:
        df_all = df_all_raw[df_all_raw['hold_optauuid'] == valgt_uuid_hold].copy()
    else:
        df_all = df_all_raw.copy()
    df_all = _forbered_events(df_all)

    df_all_temp = df_all.rename(columns={
        'event_x': 'EVENT_X', 'event_y': 'EVENT_Y', 'event_typeid': 'EVENT_TYPEID',
        'visningsnavn': 'VISNINGSNAVN', 'player_optauuid': 'PLAYER_OPTAUUID',
        'outcome': 'OUTCOME', 'qualifiers': 'QUALIFIERS'
    })
    df_all['Action_Label'] = df_all_temp.apply(get_action_label, axis=1)

    event_stats_liga = _byg_event_stats(df_liga_total)
    truppen_stats_liga = event_stats_liga.copy()
    truppen_stats_liga['Minutter'] = expected_liga['minutes'].reindex(truppen_stats_liga.index, fill_value=0).round(0).astype('Int64')
    truppen_stats_liga['xG'] = expected_liga['xg'].reindex(truppen_stats_liga.index, fill_value=0).round(2)
    truppen_stats_liga['xA'] = expected_liga['xa'].reindex(truppen_stats_liga.index, fill_value=0).round(2)
    truppen_stats_liga['Mål'] = df_liga_total[df_liga_total['event_typeid'] == 16].groupby('player_optauuid').size().reindex(truppen_stats_liga.index, fill_value=0).astype('Int64')
    truppen_stats_liga['Assists'] = df_liga_total.apply(lambda r: 1 if is_assist(r.get('event_typeid'), r.get('qual_list', [])) else 0, axis=1).groupby(df_liga_total['player_optauuid']).sum().reindex(truppen_stats_liga.index, fill_value=0).astype('Int64')
    truppen_stats_liga['Pasningsprocent'] = ((truppen_stats_liga['Pasninger_Succes'] / truppen_stats_liga['Pasninger']) * 100).where(truppen_stats_liga['Pasninger'] > 0, 0).round(1)
    truppen_stats_liga['Position'] = truppen_stats_liga.index.to_series().apply(lambda u: POSITION_MAP.get(str(u).strip(), 'Ukendt'))
    truppen_stats_liga = tilfoej_kategori_kolonner(truppen_stats_liga, df_liga_total, ALLE_SPQ_KATEGORIER)
    truppen_stats_liga = tilfoej_fremadrettede_pasninger(truppen_stats_liga, df_liga_total)

    if df_all.empty:
        truppen_stats = pd.DataFrame()
    else:
        event_stats_hold = _byg_event_stats(df_all)
        truppen_stats = event_stats_hold.copy()
        truppen_stats['Minutter'] = expected_hold['minutes'].reindex(truppen_stats.index, fill_value=0).round(0).astype('Int64')
        truppen_stats['xG'] = expected_hold['xg'].reindex(truppen_stats.index, fill_value=0).round(2)
        truppen_stats['xA'] = expected_hold['xa'].reindex(truppen_stats.index, fill_value=0).round(2)
        truppen_stats['Mål'] = df_all[df_all['event_typeid'] == 16].groupby('player_optauuid').size().reindex(truppen_stats.index, fill_value=0).astype('Int64')
        truppen_stats['Assists'] = df_all.apply(lambda r: 1 if is_assist(r.get('event_typeid'), r.get('qual_list', [])) else 0, axis=1).groupby(df_all['player_optauuid']).sum().reindex(truppen_stats.index, fill_value=0).astype('Int64')
        truppen_stats['Pasningsprocent'] = ((truppen_stats['Pasninger_Succes'] / truppen_stats['Pasninger']) * 100).where(truppen_stats['Pasninger'] > 0, 0).round(1)
        truppen_stats['Position'] = truppen_stats.index.to_series().apply(lambda u: POSITION_MAP.get(str(u).strip(), 'Ukendt'))
        for col in ['Kampe', 'Aktioner', 'Gule_kort', 'Roede_kort', 'Indskiftet', 'Udskiftet', 'Pasninger', 'Pasninger_Succes']:
            if col in truppen_stats.columns:
                truppen_stats[col] = truppen_stats[col].fillna(0).astype('Int64')
        truppen_stats = tilfoej_kategori_kolonner(truppen_stats, df_all, ALLE_SPQ_KATEGORIER)
        truppen_stats = tilfoej_fremadrettede_pasninger(truppen_stats, df_all)

    if df_expected is None:
        df_expected = pd.DataFrame()
    elif not df_expected.empty:
        df_expected = df_expected.copy()
        for col in ('xg', 'xa', 'minutes'):
            if col in df_expected.columns:
                df_expected[col] = pd.to_numeric(df_expected[col], errors='coerce').fillna(0)

    return df_all, df_liga_total, truppen_stats, truppen_stats_liga, df_expected


def vis_side(dp=None):
    navne_map = hent_navne_map()

    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 16px !important; text-align: center; font-weight: bold !important; width: 100%; }
        [data-testid="stMetricLabel"] { font-size: 10px !important; text-align: center; width: 100%; }
        [data-testid="stMetric"] { display: flex; flex-direction: column; align-items: center; }
        .player-header { font-size: 18px; font-weight: bold; margin-bottom: 10px; color: #1E1E1E; }
        </style>
        """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn: 
        return

    team_map = hent_holdliste(conn)

    col_spacer_top, col_h_hold, col_h_spiller = st.columns([2, 1.2, 1.2])

    default_team_idx = 0
    team_names = sorted(list(team_map.keys()))
    for idx, name in enumerate(team_names):
        if "hvidovre" in name.lower():
            default_team_idx = idx
            break

    valgt_hold = col_h_hold.selectbox("Hold", team_names if team_names else ["Hvidovre"], index=default_team_idx if team_names else 0, label_visibility="collapsed")
    valgt_uuid_hold = team_map.get(valgt_hold, "t7490")
    hold_logo = get_logo_img(valgt_uuid_hold)
    primær_farve = get_team_color(valgt_hold, "primary", "#df003b")

    with st.spinner("Henter spillere..."):
        df_all, df_liga_total, truppen_stats, truppen_stats_liga, df_expected = byg_spiller_og_holdstats(conn, valgt_uuid_hold, navne_map)

    if df_all.empty:
        st.warning("Ingen hændelsesdata fundet.")
        st.stop()

    df_spillere_unikke = df_all[['visningsnavn', 'player_optauuid']].drop_duplicates()

    spiller_options = {}
    for _, r in df_spillere_unikke.iterrows():
        navn = r['visningsnavn']
        uuid = r['player_optauuid']
        eng_pos = POSITION_MAP.get(str(uuid).strip(), 'Ukendt')
        da_pos = POSITION_DA.get(eng_pos, eng_pos)
        visnings_label = f"{navn} ({da_pos})"
        spiller_options[visnings_label] = uuid

    spiller_liste = sorted(list(spiller_options.keys()))
    valgt_label = col_h_spiller.selectbox("Spiller", spiller_liste if spiller_liste else [""], label_visibility="collapsed")

    valgt_player_uuid = spiller_options.get(valgt_label, None)
    valgt_spiller = valgt_label.split(" (")[0] if valgt_label else ""
    df_spiller = df_all[df_all['player_optauuid'] == valgt_player_uuid].copy() if valgt_player_uuid else pd.DataFrame()

    spiller_position = POSITION_MAP.get(str(valgt_player_uuid).strip(), 'Ukendt')

    # KUN t_pitch (Baneoversigt)
    t_pitch = st.container()

    with t_pitch:
        descriptions = {
            "Heatmap": "Viser spillerens generelle bevægelsesmønster og intensitet på banen.",
            "Berøringer": "Alle aktioner hvor spilleren har været i kontakt med bolden.",
            "Afslutninger": "Oversigt over alle skudforsøg (Mål = firkant, skud = cirkel).",
            "Defensive aktioner": "Tacklinger, bolderobringer og opsnappede afleveringer.",
            "Offensive pasninger": "Fremadrettede pasninger til sidste tredjedel (grøn = succes, grå = % succes).",
            "Alle aktioner": "Alle aktionstyper (blå = aflevering, rød = dribling, orange = afslutning, grøn = mål, lilla = defensiv aktion)."
        }
        touch_ids = [1, 3, 7, 10, 11, 12, 13, 14, 15, 16, 42, 44, 49, 50, 51, 54, 61, 73]
        df_filtreret = df_spiller[~df_spiller['Action_Label'].isin(['Pasning', 'Indkast'])]

        akt_stats = pd.DataFrame()
        if not df_filtreret.empty:
            akt_stats = df_filtreret.groupby('Action_Label').agg(Total=('outcome', 'count'), Succes=('outcome', 'sum')).sort_values('Total', ascending=False)

        c_stats_side, c_buffer, c_pitch_side = st.columns([1, 0.05, 2.2])

        with c_stats_side:
            logo_html = ""
            if hold_logo is not None:
                buffered = io.BytesIO()
                hold_logo.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                logo_html = f'<img src="data:image/png;base64,{img_str}" style="height: 35px; margin-right: 12px; object-fit: contain;">'

            st.markdown(f"""
                <div style="display: flex; align-items: center; margin-bottom: 10px;">
                    {logo_html}
                    <div class="player-header" style="margin: 0; line-height: 1.2; font-size: 18px; font-weight: bold;">
                        {valgt_spiller}
                    </div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown("<hr style='margin: 15px 0; opacity: 0.5;'>", unsafe_allow_html=True)
            total_akt = len(df_spiller)
            pas_df = df_spiller[df_spiller['event_typeid'] == 1]
            pas_count = len(pas_df)
            pas_acc = (pas_df['outcome'].sum() / pas_count * 100) if pas_count > 0 else 0

            chancer_skabt = akt_stats[akt_stats.index.str.contains("Key Pass|assist|Stor chance", case=False, na=False)]['Total'].sum() if not akt_stats.empty else 0
            shots_count = len(df_spiller[df_spiller['event_typeid'].isin([13, 14, 15, 16])])
            cross_count = len(df_spiller[df_spiller['qual_list'].apply(lambda x: "2" in x if isinstance(x, list) else False)])
            erob_count = len(df_spiller[df_spiller['event_typeid'].isin([49])])
            touch_count = len(df_spiller[df_spiller['event_typeid'].isin(touch_ids)])
            drib_count = len(df_spiller[df_spiller['event_typeid'].isin([3])])
            regains_count = len(df_spiller[df_spiller['event_typeid'].isin([7, 8, 12, 49])])
            boldtab_count = len(df_spiller[df_spiller['event_typeid'].isin([50, 51])])
            def_count = len(df_spiller[df_spiller['event_typeid'].isin([7, 8])])
            if 'end_x' in df_spiller.columns:
                fremad_count = len(df_spiller[
                    (df_spiller['event_typeid'] == 1)
                    & df_spiller['end_x'].notna()
                    & (df_spiller['end_x'] > df_spiller['event_x'])
                ])
            else:
                fremad_count = 0

            m_r1 = st.columns(4)
            m_r1[0].metric("Aktioner", total_akt)
            m_r1[1].metric("Berøringer", touch_count)
            m_r1[2].metric("Pasninger", pas_count)
            m_r1[3].metric("Pasning %", f"{int(pas_acc)}%")

            m_r2 = st.columns(4)
            m_r2[0].metric("Driblinger", drib_count)
            m_r2[1].metric("Skud", shots_count)
            m_r2[2].metric("Chancer", int(chancer_skabt))
            m_r2[3].metric("Indlæg", cross_count)

            m_r3 = st.columns(4)
            m_r3[0].metric("Def. 1v1", def_count)
            m_r3[1].metric("Regains", regains_count)
            m_r3[2].metric("Erobringer", erob_count)
            m_r3[3].metric("Boldtab", boldtab_count)

            m_r4 = st.columns(4)
            m_r4[0].metric("Fremad. pasn.", fremad_count)

            st.markdown("<hr style='margin: 15px 0; opacity: 0.5;'>", unsafe_allow_html=True)
            st.caption("**Top 10: Aktioner**")
            if not akt_stats.empty:
                bare_antal = ['Erobring', 'Clearing', 'Boldtab', 'Frispark vundet', 'Blokeret skud', 'Interception']
                for akt, row in akt_stats.head(10).iterrows():
                    total, succes = int(row['Total']), int(row['Succes'])
                    stats_html = f"<b>{total}</b>" if akt in bare_antal else f"{succes}/{total} <b>({int(succes/total*100)}%)</b>"
                    st.markdown(f'<div style="display:flex; justify-content:space-between; font-size:11px; border-bottom:0.5px solid #eee; padding:5px 0;"><span>{akt}</span><span style="font-family:monospace;">{stats_html}</span></div>', unsafe_allow_html=True)

        with c_pitch_side:
            c_side_spacer, c_desc_col, c_menu_col = st.columns([0.2, 2.0, 1.0])

            skjulte_visninger = HIDDEN_VIEWS_PER_POSITION.get(spiller_position, [])
            descriptions_visning = {k: v for k, v in descriptions.items() if k not in skjulte_visninger}

            with c_menu_col:
                visning = st.selectbox(
                    "Visning",
                    list(descriptions_visning.keys()),
                    key=f"pitch_view_sel_{valgt_player_uuid}",
                    label_visibility="collapsed"
                )
            with c_desc_col:
                st.markdown(f'<div style="text-align: right; margin-top: 8px; line-height: 1.2;"><span style="color: #666; font-size: 0.85rem;">{descriptions_visning.get(visning)}</span></div>', unsafe_allow_html=True)

            pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
            fig, ax = pitch.draw(figsize=(10, 7))
            draw_player_info_box(ax, hold_logo, valgt_spiller, SEASONNAME, visning)

            df_plot = df_spiller.dropna(subset=['event_x', 'event_y'])
            if not df_plot.empty:
                if visning == "Heatmap":
                    pitch.kdeplot(df_plot.event_x, df_plot.event_y, ax=ax, cmap='Blues', fill=True, alpha=0.6, levels=50)
                elif visning == "Berøringer":
                    d = df_plot[df_plot['event_typeid'].isin(touch_ids)]
                    ax.scatter(d.event_x, d.event_y, color=primær_farve, s=40, edgecolors='white', alpha=0.5)
                elif visning == "Afslutninger":
                    d = df_plot[df_plot['event_typeid'].isin([13, 14, 15, 16])]
                    goals = d[d['event_typeid'] == 16]
                    misses = d[d['event_typeid'].isin([13, 14, 15])]
                    ax.scatter(misses.event_x, misses.event_y, color='grey', s=60, edgecolors='black', alpha=0.6)
                    ax.scatter(goals.event_x, goals.event_y, color=primær_farve, s=120, marker='s', edgecolors='black', zorder=5)
                elif visning == "Defensive aktioner":
                    d = df_plot[df_plot['event_typeid'].isin([5, 7, 8, 12, 49, 55])]
                    ax.scatter(d.event_x, d.event_y, color='orange', s=100, edgecolors='white')
                elif visning == "Alle aktioner":
                    noget_vist = False
                    for label, mask_fn, color, size, marker in AKTIONS_FARVER:
                        d = df_plot[mask_fn(df_plot)]
                        if not d.empty:
                            noget_vist = True
                            ax.scatter(
                                d.event_x, d.event_y, color=color, s=size,
                                edgecolors='white', alpha=0.75, label=label,
                                marker=marker, zorder=3
                            )
                    if noget_vist:
                        ax.legend(
                            loc='upper center', bbox_to_anchor=(0.5, -0.03),
                            ncol=len(AKTIONS_FARVER), fontsize=7, frameon=False
                        )
                elif visning == "Offensive pasninger":
                    if 'end_x' not in df_plot.columns or 'end_y' not in df_plot.columns:
                        st.info(
                            "Denne visning kræver pasningens slutkoordinater (end_x/end_y), "
                            "som ikke findes i de hentede data lige nu."
                        )
                    else:
                        d = df_plot[
                            (df_plot['event_typeid'] == 1) &
                            (df_plot['end_x'] > 66.7) &
                            (df_plot['end_x'] > df_plot['event_x'])
                        ].dropna(subset=['end_x', 'end_y'])

                        succes = d[d['outcome'] == 1]
                        fejl = d[d['outcome'] != 1]

                        if not fejl.empty:
                            pitch.arrows(
                                fejl.event_x, fejl.event_y, fejl.end_x, fejl.end_y,
                                ax=ax, color='#bdbdbd', width=0.7, headwidth=2, headlength=3, alpha=0.6, zorder=2
                            )
                        if not succes.empty:
                            pitch.arrows(
                                succes.event_x, succes.event_y, succes.end_x, succes.end_y,
                                ax=ax, color='green', width=1.3, headwidth=3, headlength=4, alpha=0.85, zorder=3
                            )

                        ax.scatter(d.event_x, d.event_y, color='green', s=20, edgecolors='white', alpha=0.6, zorder=4)

            st.pyplot(fig, use_container_width=True)
