import streamlit as st
import pandas as pd
import os
import io
import base64

# --- DATA OG MAPPING ---
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS
from data.utils.mapping import is_assist, har_qualifier, get_action_label
from data.utils.spiller_qualifiers import ACTION_CATEGORIES, POSITION_ACTIONS

# --- GENERELLE UI-HJÆLPERE ---
from utils.helpers import get_logo_img, get_team_color

# --- IMPORT AF SQL ---
from data.sql.liga_spillere import hent_match_og_haendelsesdata

try:
    from data.players import player_mapping
    _STATIC_PLAYERS = getattr(player_mapping, 'PLAYER_MAPPING', [])
except ImportError:
    _STATIC_PLAYERS = []

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

DB = "KLUB_HVIDOVREIF.AXIS"
SEASONNAME = "2026/2027"
TEAM_WYID = 7490
COMPETITION_WYID = (328,)
COMP_MAP = {
    335: "Superliga",
    328: "NordicBet Liga",
    329: "2. division",
    43319: "3. division",
    331: "Oddset Pokalen",
    1305: "U19 Ligaen"
}
LIGA_IDS = "('2mb332vncy4450vu14paj8844', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '335', '328', '329', '43319', '331')"

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


def _get_quals(r):
    ql = r.get('qual_list', [])
    if isinstance(ql, list):
        return [str(q).strip() for q in ql]
    return [str(q).strip() for q in str(ql).split(',')]


def count_kamp_qual(df_group, eid, qids):
    return df_group.apply(lambda r: har_qualifier(r['event_typeid'], r.get('qual_list', []), eid, qids), axis=1).sum()


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


def _forbered_events(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=['visningsnavn']).copy()
    df['event_timestamp'] = pd.to_datetime(df['event_timestamp_str'], errors='coerce')
    df['qual_list'] = df['qualifiers'].fillna('').str.split(',')
    df['Pasninger_Total'] = (df['event_typeid'] == 1).astype(int)
    df['Pasninger_Succes'] = ((df['event_typeid'] == 1) & (df['outcome'] == 1)).astype(int)
    return df


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


@st.cache_data(ttl=600, show_spinner=False)
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


@st.cache_data(ttl=300, show_spinner=False)
def hent_kampliste(_conn, valgt_uuid_hold: str, seasonname: str) -> pd.DataFrame:
    sql_matches = f"""
        SELECT MATCH_OPTAUUID, MATCH_DATE_FULL, WEEK, MATCH_STATUS, CONTESTANTHOME_OPTAUUID, CONTESTANTHOME_NAME, CONTESTANTAWAY_OPTAUUID, CONTESTANTAWAY_NAME, TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE
        FROM {DB}.OPTA_MATCHINFO
        WHERE TOURNAMENTCALENDAR_NAME = '{seasonname}'
          AND MATCH_STATUS = 'Played'
          AND (CONTESTANTHOME_OPTAUUID = '{valgt_uuid_hold}' OR CONTESTANTAWAY_OPTAUUID = '{valgt_uuid_hold}')
        ORDER BY MATCH_DATE_FULL DESC
    """
    df_matches = _conn.query(sql_matches)
    if df_matches is None:
        return pd.DataFrame()
    df_matches.columns = df_matches.columns.str.lower()
    df_matches['match_date_full'] = pd.to_datetime(df_matches['match_date_full'], errors='coerce')
    return df_matches


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


def vis_side():
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
    col_spacer_top, col_h_hold = st.columns([3.2, 1.2])

    default_team_idx = 0
    team_names = sorted(list(team_map.keys()))
    for idx, name in enumerate(team_names):
        if "hvidovre" in name.lower():
            default_team_idx = idx
            break

    valgt_hold = col_h_hold.selectbox(
        "Hold", team_names if team_names else ["Hvidovre"],
        index=default_team_idx if team_names else 0,
        label_visibility="collapsed", key="global_hold_select"
    )
    valgt_uuid_hold = team_map.get(valgt_hold, "t7490")
    hold_logo = get_logo_img(valgt_uuid_hold)

    with st.spinner("Henter trup- og kampdata..."):
        df_all, df_liga_total, truppen_stats, truppen_stats_liga, df_expected = byg_spiller_og_holdstats(conn, valgt_uuid_hold, navne_map)

    if df_all.empty:
        st.warning("Ingen hændelsesdata fundet.")
        return

    t_team, t_matches = st.tabs(["Holdoversigt", "Kampoversigt"])

    with t_team:
        col_t_title, col_t_btn = st.columns([2.7, 1.3])
        with col_t_title:
            logo_html = ""
            if hold_logo is not None:
                buffered = io.BytesIO()
                hold_logo.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                logo_html = f'<img src="data:image/png;base64,{img_str}" style="height: 26px; margin-right: 10px; object-fit: contain;">'
            st.markdown(f'<div style="display: flex; align-items: center; padding-top: 20px;">{logo_html}<span style="font-size: 16px; font-weight: bold; line-height: 1;">{valgt_hold.upper()}</span></div>', unsafe_allow_html=True)

        with col_t_btn:
            st.markdown('<div style="display: flex; justify-content: flex-end;">', unsafe_allow_html=True)
            kategori_valg = st.segmented_control(
                "Visningskategori",
                options=["Generelt", "Opbygning", "Offensiv", "Defensiv"],
                default="Generelt",
                key="team_kategori_control",
                label_visibility="collapsed"
            )
            st.markdown('</div>', unsafe_allow_html=True)

        gen_kolonner = ['visningsnavn', 'Kampe', 'Minutter', 'Aktioner', 'Pasninger', 'Pasningsprocent', 'Mål', 'Assists', 'Udskiftet', 'Indskiftet', 'Gule_kort', 'Roede_kort']
        opb_kolonner = ['visningsnavn', 'Aktioner', 'Pasninger', 'Pasningsprocent', 'Key_Passes', 'fremadrettede_pasninger', 'Stikninger', 'Driblinger', 'Driblinger_Succes', 'Rum_Driblinger_Space']
        off_kolonner = ['visningsnavn', 'Aktioner', 'Afslutninger', 'xG', 'Chancer_skabt', 'Indlæg', 'xA', 'Offensive_Dueller', 'Gennembrud_Overtake', 'Driblinger_Succes']
        def_kolonner = ['visningsnavn', 'Aktioner', 'Erobringer', 'Tacklinger', 'Clearinger', 'Blokeringer', 'Interceptioner', 'Defensive_Dueller', 'Defensive_1v1_Stoppet', 'Frispark_imod']

        if not truppen_stats.empty:
            df_vis_truppen = truppen_stats.reset_index()

            if kategori_valg == "Generelt":
                eksisterende_kolonner = [k for k in gen_kolonner if k in df_vis_truppen.columns]
            elif kategori_valg == "Opbygning":
                eksisterende_kolonner = [k for k in opb_kolonner if k in df_vis_truppen.columns]
            elif kategori_valg == "Offensiv":
                eksisterende_kolonner = [k for k in off_kolonner if k in df_vis_truppen.columns]
            elif kategori_valg == "Defensiv":
                eksisterende_kolonner = [k for k in def_kolonner if k in df_vis_truppen.columns]
            else:
                eksisterende_kolonner = [k for k in df_vis_truppen.columns if k != 'player_optauuid']

            df_visning = df_vis_truppen[eksisterende_kolonner].copy()
            if 'Aktioner' in df_visning.columns:
                df_visning = df_visning.sort_values(by='Aktioner', ascending=False)

            df_visning = df_visning.rename(columns={
                'visningsnavn': 'Spiller',
                'Pasningsprocent': 'Pasning (%)',
                'Gule_kort': 'Gule kort',
                'Roede_kort': 'Røde kort',
                'Chancer_skabt': 'Chancer skabt',
                'Key_Passes': 'Key Passes',
                'Frispark_imod': 'Frispark',
                'fremadrettede_pasninger': 'Fremad. pasninger',
                'Driblinger_Succes': 'Driblinger (Succes)',
                'Gennembrud_Overtake': 'Gennembrud, 1v1',
                'Rum_Driblinger_Space': 'Driblinger, 1v1',
                'Offensive_Dueller': 'Off. dueller',
                'Defensive_Dueller': 'Def. dueller',
                'Defensive_1v1_Stoppet': 'Def. 1v1'
            })

            beregnet_hoejde = int(len(df_visning) * 38 + 45)
            st.dataframe(
                df_visning,
                use_container_width=True,
                hide_index=True,
                height=beregnet_hoejde,
                column_config={"Pasning (%)": st.column_config.NumberColumn("Pasning (%)", format="%.1f%%")}
            )
        else:
            st.info("Ingen trup-data tilgængelig endnu.")

    with t_matches:
        col_t_title, col_t_matches, col_t_btn = st.columns([1.3, 2.0, 1.7], vertical_alignment="center")
        with col_t_title:
            logo_html = ""
            if hold_logo is not None:
                buffered = io.BytesIO()
                hold_logo.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                logo_html = f'<img src="data:image/png;base64,{img_str}" style="height: 26px; margin-right: 10px; object-fit: contain;">'
            st.markdown(f'<div style="display: flex; align-items: center;">{logo_html}<span style="font-size: 16px; font-weight: bold; line-height: 1;">KAMPOVERSIGT</span></div>', unsafe_allow_html=True)

        df_matches = hent_kampliste(conn, valgt_uuid_hold, SEASONNAME)

        valgt_kamp_uuid = None
        if not df_matches.empty:
            kamp_options = {}
            for _, r in df_matches.iterrows():
                er_hjemme = str(r['contestanthome_optauuid']) == str(valgt_uuid_hold)
                modstander = r['contestantaway_name'] if er_hjemme else r['contestanthome_name']
                hjemme_maal = int(r['total_home_score']) if pd.notna(r['total_home_score']) else 0
                ude_maal = int(r['total_away_score']) if pd.notna(r['total_away_score']) else 0
                hold_maal = hjemme_maal if er_hjemme else ude_maal
                mod_maal = ude_maal if er_hjemme else hjemme_maal
                label = f"Kamp {r['week']}: vs. {modstander} ({hold_maal}-{mod_maal})"
                kamp_options[label] = str(r['match_optauuid'])

            with col_t_matches:
                valgt_kamp_label = st.selectbox("Vælg kamp", list(kamp_options.keys()), key="valgt_kamp_dropdown", label_visibility="collapsed")
                valgt_kamp_uuid = kamp_options[valgt_kamp_label]

        with col_t_btn:
            st.markdown('<div style="display: flex; justify-content: flex-end;">', unsafe_allow_html=True)
            kategori_valg_kamp = st.segmented_control(
                "Visningskategori Kamp",
                options=["Generelt", "Opbygning", "Offensiv", "Defensiv"],
                default="Generelt",
                key="match_kategori_control",
                label_visibility="collapsed"
            )
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

        if not df_matches.empty and valgt_kamp_uuid:
            match_col_in_all = next((col for col in ['match_optauuid', 'match_id'] if col in df_all.columns), None)
            df_kamp_events = df_all[df_all[match_col_in_all].astype(str) == valgt_kamp_uuid].copy() if match_col_in_all else pd.DataFrame()

            if not df_kamp_events.empty:
                event_stats_kamp = _byg_event_stats(df_kamp_events)
                truppen_stats_kamp_raw = event_stats_kamp.copy()

                expected_agg_kamp = pd.DataFrame(columns=['xg', 'xa', 'minutes'])
                if df_expected is not None and not df_expected.empty and 'match_optauuid' in df_expected.columns:
                    df_expected_kamp = df_expected[df_expected['match_optauuid'].astype(str) == str(valgt_kamp_uuid)]
                    if not df_expected_kamp.empty:
                        expected_agg_kamp = df_expected_kamp.groupby('player_optauuid')[['xg', 'xa', 'minutes']].sum()

                if not expected_agg_kamp.empty:
                    truppen_stats_kamp_raw['Minutter'] = expected_agg_kamp['minutes'].reindex(truppen_stats_kamp_raw.index, fill_value=0).round(0).astype('Int64')
                    truppen_stats_kamp_raw['xG'] = expected_agg_kamp['xg'].reindex(truppen_stats_kamp_raw.index, fill_value=0).round(2)
                    truppen_stats_kamp_raw['xA'] = expected_agg_kamp['xa'].reindex(truppen_stats_kamp_raw.index, fill_value=0).round(2)
                else:
                    truppen_stats_kamp_raw['Minutter'] = 0
                    truppen_stats_kamp_raw['xG'] = 0.0
                    truppen_stats_kamp_raw['xA'] = 0.0

                truppen_stats_kamp_raw['Mål'] = df_kamp_events[df_kamp_events['event_typeid'] == 16].groupby('player_optauuid').size().reindex(truppen_stats_kamp_raw.index, fill_value=0).astype('Int64')
                truppen_stats_kamp_raw['Assists'] = df_kamp_events.apply(lambda r: 1 if is_assist(r.get('event_typeid'), r.get('qual_list', [])) else 0, axis=1).groupby(df_kamp_events['player_optauuid']).sum().reindex(truppen_stats_kamp_raw.index, fill_value=0).astype('Int64')

                truppen_stats_kamp_kamp = truppen_stats_kamp_raw.copy()
                truppen_stats_kamp_kamp['Pasningsprocent'] = (
                    (truppen_stats_kamp_kamp['Pasninger_Succes'] / truppen_stats_kamp_kamp['Pasninger']) * 100
                ).where(truppen_stats_kamp_kamp['Pasninger'] > 0, 0).round(1)

                truppen_stats_kamp_kamp['Position'] = truppen_stats_kamp_kamp.index.to_series().apply(
                    lambda u: POSITION_MAP.get(str(u).strip(), 'Ukendt')
                )
                truppen_stats_kamp_kamp = tilfoej_fremadrettede_pasninger(truppen_stats_kamp_kamp, df_kamp_events)

                df_vis_kamp = truppen_stats_kamp_kamp.reset_index()

                if kategori_valg_kamp == "Generelt":
                    eksisterende_kolonner_kamp = [k for k in gen_kolonner if k in df_vis_kamp.columns]
                elif kategori_valg_kamp == "Opbygning":
                    eksisterende_kolonner_kamp = [k for k in opb_kolonner if k in df_vis_kamp.columns]
                elif kategori_valg_kamp == "Offensiv":
                    eksisterende_kolonner_kamp = [k for k in off_kolonner if k in df_vis_kamp.columns]
                elif kategori_valg_kamp == "Defensiv":
                    eksisterende_kolonner_kamp = [k for k in def_kolonner if k in df_vis_kamp.columns]
                else:
                    eksisterende_kolonner_kamp = [k for k in df_vis_kamp.columns if k != 'player_optauuid']

                df_visning_kamp = df_vis_kamp[eksisterende_kolonner_kamp].copy()
                if 'Aktioner' in df_visning_kamp.columns:
                    df_visning_kamp = df_visning_kamp.sort_values(by='Aktioner', ascending=False)

                df_visning_kamp = df_visning_kamp.rename(columns={
                    'visningsnavn': 'Spiller',
                    'Pasningsprocent': 'Pasning (%)',
                    'Gule_kort': 'Gule kort',
                    'Roede_kort': 'Røde kort',
                    'Chancer_skabt': 'Chancer skabt',
                    'Key_Passes': 'Key Passes',
                    'Frispark_imod': 'Frispark',
                    'fremadrettede_pasninger': 'Fremad. pasninger',
                    'Driblinger_Succes': 'Driblinger (Succes)',
                    'Gennembrud_Overtake': 'Gennembrud, 1v1',
                    'Rum_Driblinger_Space': 'Driblinger, 1v1',
                    'Offensive_Dueller': 'Off. dueller',
                    'Defensive_Dueller': 'Def. dueller',
                    'Defensive_1v1_Stoppet': 'Def. 1v1'
                })

                beregnet_hoejde_kamp = int(len(df_visning_kamp) * 38 + 45)
                st.dataframe(
                    df_visning_kamp,
                    use_container_width=True,
                    hide_index=True,
                    height=beregnet_hoejde_kamp,
                    column_config={"Pasning (%)": st.column_config.NumberColumn("Pasning (%)", format="%.1f%%")}
                )
            else:
                st.info("Ingen hændelsesdata fundet for denne kamp.")
        else:
            st.info("Ingen kampe tilgængelige.")


if __name__ == "__main__":
    vis_side()
