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

# --- SPILLER-KATEGORIER (position -> aktionskategorier, offensiv/defensiv) ---
from data.utils.spiller_qualifiers import ACTION_CATEGORIES, POSITION_ACTIONS

# --- GENERELLE UI-HJÆLPERE ---
from utils.helpers import get_logo_img, get_team_color, get_ordinal, draw_player_info_box

# --- IMPORT AF SPILLERE OG SQL ---
from data.sql.liga_spillere import hent_samlet_spiller_statistik

try:
    from data.players import player_mapping
    valgt_player_uuid = st.session_state.get('valgt_player_uuid', getattr(player_mapping, 'valgt_player_uuid', None))
    valgt_spiller = st.session_state.get('valgt_spiller', getattr(player_mapping, 'valgt_spiller', None))
    df_spiller = getattr(player_mapping, 'df_spiller', None)
    hold_logo = getattr(player_mapping, 'hold_logo', None)
    primær_farve = getattr(player_mapping, 'primær_farve', "#df003b")
    valgt_hold = getattr(player_mapping, 'valgt_hold', "Hvidovre")
    conn = getattr(player_mapping, 'conn', None)
    SEASONNAME = getattr(player_mapping, 'SEASONNAME', "2025/2026")
except ImportError:
    st.error("Kunne ikke finde eller indlæse 'player_mapping.py'. Sørg for filen ligger i mappen.")
    st.stop()

# --- POSITIONSDATA (fra den statiske spillerliste i data/players/player_mapping.py) ---
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
POSITION_DA_FLERTAL = {
    "Goalkeeper": "målmænd",
    "Defender": "forsvarsspillere",
    "Midfielder": "midtbanespillere",
    "Attacker": "angribere",
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
    """
    Beriger en stats-dataframe (indekseret på player_optauuid) med én kolonne
    pr. aktionskategori fra spiller_qualifiers.ACTION_CATEGORIES.
    """
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
    """
    Tæller fremadrettede pasninger - en pasning der flytter bolden fremad
    (end_x > event_x).
    """
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


def byg_kategori_visning(spq_position: str) -> dict:
    return {
        side: [(ACTION_CATEGORIES[k]["navn"].upper(), k) for k in POSITION_ACTIONS[spq_position][side]]
        for side in ("offensiv", "defensiv")
    }

KATEGORI_PER_POSITION = {
    eng_pos: byg_kategori_visning(spq_pos)
    for eng_pos, spq_pos in POSITION_TO_SPQ.items()
}

for _eng_pos in ("Defender", "Midfielder", "Attacker"):
    KATEGORI_PER_POSITION[_eng_pos]["offensiv"].append(("FREMADRETTEDE PASNINGER", "fremadrettede_pasninger"))

DEFAULT_KAT_LISTE = byg_kategori_visning("MID")
DEFAULT_KAT_LISTE["offensiv"].append(("FREMADRETTEDE PASNINGER", "fremadrettede_pasninger"))

HIDDEN_VIEWS_PER_POSITION = {
    "Goalkeeper": ["Afslutninger", "Offensive pasninger"],
}

AKTIONS_FARVER = [
    ("Aflevering", lambda d: d['event_typeid'] == 1, '#1f77b4', 22, 'o'),
    ("Dribling", lambda d: d['event_typeid'] == 3, '#d62728', 45, 'o'),
    ("Afslutning", lambda d: d['event_typeid'].isin([13, 14, 15]), '#ff7f0e', 70, 'o'),
    ("Mål", lambda d: d['event_typeid'] == 16, '#2ca02c', 130, 's'),
    ("Defensiv aktion", lambda d: d['event_typeid'].isin([5, 7, 8, 12, 49, 55]), '#9467bd', 55, 'o'),
]

# Hent den aktuelle sæson og tilhørende Opta turnering(er) automatisk
SEASONNAME = "2026/2027"  # eller hentet fra session_state / player_mapping
DB = "KLUB_HVIDOVREIF.AXIS"

# Hent Opta UUID for 1. Division (eller de turneringer der hører til sæsonen)
active_leagues = SEASONS.get(SEASONNAME, {})
optauuid_liste = list(active_leagues.values())

# Byg LIGA_IDS-strengen dynamisk i det format Snowflake forventer: ('uuid1', 'uuid2')
if optauuid_liste:
    LIGA_IDS = "('" + "', '".join(optauuid_liste) + "')"
else:
    LIGA_IDS = "('2mb332vncy4450vu14paj8844')"  # Fallback

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


def create_relative_donut(player_val, max_val, label, rank_text, color="#df003b"):
    base_max = max(max_val, player_val, 1)
    reminder = base_max - player_val
    fig = go.Figure(go.Pie(
        values=[player_val, reminder],
        hole=0.7,
        marker_colors=[color, "#eeeeee"],
        textinfo='none',
        hoverinfo='none',
        rotation=0,
        direction='clockwise',
        sort=False
    ))
    fig.update_layout(
        showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=110, width=130,
        annotations=[dict(
            text=f"<b>{player_val}</b><br><span style='font-size:12px; color:{color}; font-weight:bold;'>{rank_text}</span>", 
            x=0.5, y=0.5, font_size=16, showarrow=False, font_family="Arial"
        )]
    )
    return fig


def get_physical_data(player_name, player_opta_uuid, valgt_hold_navn, db_conn):
    efternavn = player_name.split()[-1]
    sql = f"""
        SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE UPPER(PLAYER_NAME) LIKE UPPER('%{efternavn}%')
        AND MATCH_DATE >= '2025-07-01'
    """
    df = db_conn.query(sql)
    if df is not None and not df.empty:
        df.columns = df.columns.str.lower()
        rename_map = {
            'high speed running': 'hsr',
            'sprinting': 'sprinting',
            'top_speed': 'top_speed',
            'no_of_high_intensity_runs': 'hi_runs',
            'distance': 'distance'
        }
        df = df.rename(columns=rename_map, errors='ignore')
        return df
    return pd.DataFrame()


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

    with st.spinner("Henter spillerstatistik..."):
        df_all, df_liga_total, truppen_stats, truppen_stats_liga, df_expected = hent_samlet_spiller_statistik(conn, DB, LIGA_IDS, navne_map)

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

    spiller_position = POSITION_MAP.get(str(valgt_player_uuid).strip(), 'Ukendt') if valgt_player_uuid else 'Ukendt'

    t_team, t_matches = st.tabs(["Holdoversigt", "Kampoversigt"])

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
            
        sql_matches = f"""
            SELECT MATCH_OPTAUUID, MATCH_DATE_FULL, WEEK, MATCH_STATUS, CONTESTANTHOME_OPTAUUID, CONTESTANTHOME_NAME, CONTESTANTAWAY_OPTAUUID, CONTESTANTAWAY_NAME, TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE
            FROM {DB}.OPTA_MATCHINFO
            WHERE TOURNAMENTCALENDAR_NAME = '{SEASONNAME}'
              AND MATCH_STATUS = 'Played'
              AND (CONTESTANTHOME_OPTAUUID = '{valgt_uuid_hold}' OR CONTESTANTAWAY_OPTAUUID = '{valgt_uuid_hold}')
            ORDER BY MATCH_DATE_FULL DESC
        """
        df_matches = conn.query(sql_matches)
        if df_matches is None:
            df_matches = pd.DataFrame()
            
        valgt_kamp_uuid = None
        if not df_matches.empty:
            df_matches.columns = df_matches.columns.str.lower()
            df_matches['match_date_full'] = pd.to_datetime(df_matches['match_date_full'], errors='coerce')
            
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
                # Event stats beregning lokalt for den valgte kamp
                event_stats_kamp = df_kamp_events.groupby(['player_optauuid', 'visningsnavn']).apply(lambda x: pd.Series({
                    'Kampe': 1,
                    'Aktioner': len(x),
                    'Pasninger': (x['event_typeid'] == 1).sum(),
                    'Pasninger_Succes': ((x['event_typeid'] == 1) & (x['outcome'] == 1)).sum(),
                    'Mål': (x['event_typeid'] == 16).sum(),
                    'Assists': x.apply(lambda r: 1 if is_assist(r.get('event_typeid'), r.get('qual_list', [])) else 0, axis=1).sum(),
                    'Afslutninger': x['event_typeid'].isin([13, 14, 15, 16]).sum(),
                    'Tacklinger': (x['event_typeid'] == 7).sum(),
                    'Erobringer': x['event_typeid'].isin([7, 8, 12, 49]).sum(),
                    'Clearinger': (x['event_typeid'] == 12).sum(),
                    'Blokeringer': (x['event_typeid'] == 55).sum(),
                    'Chancer_skabt': x.apply(lambda r: 1 if '210' in str(r.get('qualifiers', '')) else 0, axis=1).sum()
                })).reset_index().drop_duplicates(subset=['player_optauuid']).set_index('player_optauuid')

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
     
                truppen_stats_kamp_kamp = truppen_stats_kamp_raw.copy()
                truppen_stats_kamp_kamp['Pasningsprocent'] = (
                    (truppen_stats_kamp_kamp['Pasninger_Succes'] / truppen_stats_kamp_kamp['Pasninger']) * 100
                ).where(truppen_stats_kamp_kamp['Pasninger'] > 0, 0).round(1)
    
                truppen_stats_kamp_kamp['Position'] = truppen_stats_kamp_kamp.index.to_series().apply(
                    lambda u: POSITION_MAP.get(str(u).strip(), 'Ukendt')
                )
                truppen_stats_kamp_kamp = tilfoej_fremadrettede_pasninger(truppen_stats_kamp_kamp, df_kamp_events)
     
                df_vis_kamp = truppen_stats_kamp_kamp.reset_index()
                
                gen_kolonner = ['visningsnavn', 'Kampe', 'Minutter', 'Aktioner', 'Mål', 'Assists']
                opb_kolonner = ['visningsnavn', 'Pasninger', 'Pasningsprocent', 'fremadrettede_pasninger']
                off_kolonner = ['visningsnavn', 'xG', 'xA', 'Afslutninger', 'Chancer_skabt']
                def_kolonner = ['visningsnavn', 'Tacklinger', 'Erobringer', 'Clearinger', 'Blokeringer']

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
                    'fremadrettede_pasninger': 'Fremad. pasninger',
                    'Chancer_skabt': 'Chancer skabt'
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
                st.info("Ingen hændelsesdata for denne kamp.")
        else:
            st.warning("Ingen spillede kampe fundet i denne sæson.")
