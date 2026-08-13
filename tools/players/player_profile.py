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
from data.utils.match_data import classify_take_on
 
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

# Statistik-kategorier vist i "hjul"-grafikkerne på Spillerprofil-fanen
KATEGORI_PER_POSITION = {
    "Goalkeeper": [
        ("PASNINGER", "Pasninger"), ("PASNING %", "Pasningsprocent"),
        ("CLEARINGER", "Clearinger"), ("EROBRINGER", "Erobringer"),
        ("FRISPARK IMOD", "Frispark_imod"), ("GULE KORT", "Gule_kort"),
    ],
    "Defender": [
        ("PASNINGER", "Pasninger"), ("TACKLINGER", "Tacklinger"),
        ("CLEARINGER", "Clearinger"), ("INTERCEPTIONER", "Interceptioner"),
        ("BLOKERINGER", "Blokeringer"), ("EROBRINGER", "Erobringer"),
        ("DEF. DUELLER", "Defensive_Dueller"), ("FRISPARK IMOD", "Frispark_imod"),
    ],
    "Midfielder": [
        ("PASNINGER", "Pasninger"), ("STIKNINGER", "Stikninger"),
        ("CHANCER SKABT", "Chancer_skabt"), ("KEY PASSES", "Key_Passes"),
        ("DRIBLINGER", "Driblinger"), ("EROBRINGER", "Erobringer"),
        ("TACKLINGER", "Tacklinger"), ("INDLÆG", "Indlæg"),
    ],
    "Attacker": [
        ("AFSLUTNINGER", "Afslutninger"), ("MÅL", "Mål"),
        ("CHANCER SKABT", "Chancer_skabt"), ("DRIBLINGER", "Driblinger"),
        ("INDLÆG", "Indlæg"), ("KEY PASSES", "Key_Passes"),
        ("STIKNINGER", "Stikninger"), ("PASNINGER", "Pasninger"),
    ],
}
DEFAULT_KAT_LISTE = [
    ("PASNINGER", "Pasninger"), ("STIKNINGER", "Stikninger"),
    ("AFSLUTNINGER", "Afslutninger"), ("MÅL", "Mål"),
    ("EROBRINGER", "Erobringer"), ("DRIBLINGER", "Driblinger"),
    ("INDLÆG", "Indlæg"), ("CHANCER SKABT", "Chancer_skabt"),
    ("KEY PASSES", "Key_Passes")
]

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
    try:
        csv_path = os.path.join(os.getcwd(), 'data', 'players', '1div_overskrivning.csv')
        df_csv = pd.read_csv(csv_path)
        navne_map = dict(zip(df_csv['PLAYER_OPTAUUID'].astype(str), df_csv['NAVN']))
    except Exception:
        navne_map = {}
 
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

    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
    if df_teams_raw is not None:
        df_teams_raw.columns = df_teams_raw.columns.str.lower()
    else:
        df_teams_raw = pd.DataFrame()

    mapping_lookup = {str(info['opta_uuid']).lower().replace('t', ''): name for name, info in TEAMS.items() if 'opta_uuid' in info}

    team_map = {}
    if not df_teams_raw.empty:
        for _, r in df_teams_raw.iterrows():
            uuid_clean = str(r['contestanthome_optauuid']).lower().replace('t','')
            if uuid_clean in mapping_lookup:
                team_map[mapping_lookup[uuid_clean]] = r['contestanthome_optauuid']

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
        df_all_raw, df_expected, df_db_stats = hent_match_og_haendelsesdata(
            conn, DB, valgt_uuid_hold, LIGA_IDS, navne_map
        )

    if df_all_raw is None:
        df_all_raw = pd.DataFrame()

    if df_all_raw.empty:
        st.warning("Ingen hændelsesdata fundet.")
        st.stop()

    # Behold hele ligaen til sammenligning senere i koden
    df_liga_total = df_all_raw.copy()
    df_liga_total = df_liga_total.dropna(subset=['visningsnavn'])
    df_liga_total['event_timestamp'] = pd.to_datetime(df_liga_total['event_timestamp_str'])
    df_liga_total['qual_list'] = df_liga_total['qualifiers'].fillna('').str.split(',')
    df_liga_total['Pasninger_Total'] = (df_liga_total['event_typeid'] == 1).astype(int)
    df_liga_total['Pasninger_Succes'] = ((df_liga_total['event_typeid'] == 1) & (df_liga_total['outcome'] == 1)).astype(int)

    # Filtrer kun til det valgte hold til dropdown og spillerdata
    if 'hold_optauuid' in df_all_raw.columns:
        df_all = df_all_raw[df_all_raw['hold_optauuid'] == valgt_uuid_hold].copy()
    else:
        df_all = df_all_raw.copy()
 
    df_all = df_all.dropna(subset=['visningsnavn'])
    df_all['event_timestamp'] = pd.to_datetime(df_all['event_timestamp_str'])
    df_all['qual_list'] = df_all['qualifiers'].fillna('').str.split(',')
 
    df_all['Pasninger_Total'] = (df_all['event_typeid'] == 1).astype(int)
    df_all['Pasninger_Succes'] = ((df_all['event_typeid'] == 1) & (df_all['outcome'] == 1)).astype(int)
 
    df_all_temp = df_all.rename(columns={
        'event_x': 'EVENT_X', 'event_y': 'EVENT_Y', 'event_typeid': 'EVENT_TYPEID',
        'visningsnavn': 'VISNINGSNAVN', 'player_optauuid': 'PLAYER_OPTAUUID',
        'outcome': 'OUTCOME', 'qualifiers': 'QUALIFIERS'
    })
    df_all['Action_Label'] = df_all_temp.apply(get_action_label, axis=1)
 
    df_spillere_unikke = df_all[['visningsnavn', 'player_optauuid']].drop_duplicates()
 
    spiller_options = {}
    for _, r in df_spillere_unikke.iterrows():
        navn = r['visningsnavn']
        uuid = r['player_optauuid']
        
        # Hent position på engelsk og map til dansk, fanger også ukendte
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
 
    def count_kamp_qual(df_group, eid, qids):
        return df_group.apply(lambda r: har_qualifier(r['event_typeid'], r.get('qual_list', []), eid, qids), axis=1).sum()
 
    def _get_quals(r):
        ql = r.get('qual_list', [])
        if isinstance(ql, list):
            return [str(q).strip() for q in ql]
        return [str(q).strip() for q in str(ql).split(',')]
 
    # Beregn ligatrup-stats til sammenligning i profiler (hele ligaen)
    event_stats_liga = df_liga_total.groupby(['player_optauuid', 'visningsnavn']).apply(lambda x: pd.Series({
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

    truppen_stats_liga = event_stats_liga.copy()
    truppen_stats_liga['Minutter'] = 0  
    truppen_stats_liga['xG'] = 0.0
    truppen_stats_liga['xA'] = 0.0
    truppen_stats_liga['Mål'] = df_liga_total[df_liga_total['event_typeid'] == 16].groupby('player_optauuid').size().reindex(truppen_stats_liga.index, fill_value=0).astype('Int64')
    truppen_stats_liga['Assists'] = df_liga_total.apply(lambda r: 1 if is_assist(r.get('event_typeid'), r.get('qual_list', [])) else 0, axis=1).groupby(df_liga_total['player_optauuid']).sum().reindex(truppen_stats_liga.index, fill_value=0).astype('Int64')
    truppen_stats_liga['Pasningsprocent'] = ((truppen_stats_liga['Pasninger_Succes'] / truppen_stats_liga['Pasninger']) * 100).where(truppen_stats_liga['Pasninger'] > 0, 0).round(1)
    
    truppen_stats_liga['Position'] = truppen_stats_liga.index.to_series().apply(
        lambda u: POSITION_MAP.get(str(u).strip(), 'Ukendt')
    )

    # Beregn holdets trup-stats direkte
    event_stats_hold = df_all.groupby(['player_optauuid', 'visningsnavn']).apply(lambda x: pd.Series({
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
    })).reset_index().drop_duplicates(subset=['player_optauuid']).set_index('player_optauuid') if not df_all.empty else pd.DataFrame()

    truppen_stats = event_stats_hold.copy() if not event_stats_hold.empty else pd.DataFrame()
    if not truppen_stats.empty:
        truppen_stats['Minutter'] = 0  
        truppen_stats['xG'] = 0.0
        truppen_stats['xA'] = 0.0
        truppen_stats['Mål'] = df_all[df_all['event_typeid'] == 16].groupby('player_optauuid').size().reindex(truppen_stats.index, fill_value=0).astype('Int64')
        truppen_stats['Assists'] = df_all.apply(lambda r: 1 if is_assist(r.get('event_typeid'), r.get('qual_list', [])) else 0, axis=1).groupby(df_all['player_optauuid']).sum().reindex(truppen_stats.index, fill_value=0).astype('Int64')
        truppen_stats['Pasningsprocent'] = ((truppen_stats['Pasninger_Succes'] / truppen_stats['Pasninger']) * 100).where(truppen_stats['Pasninger'] > 0, 0).round(1)
        truppen_stats['Position'] = truppen_stats.index.to_series().apply(
            lambda u: POSITION_MAP.get(str(u).strip(), 'Ukendt')
        )
        for col in ['Kampe', 'Aktioner', 'Gule_kort', 'Roede_kort', 'Indskiftet', 'Udskiftet', 'Pasninger', 'Pasninger_Succes']:
            if col in truppen_stats.columns:
                truppen_stats[col] = truppen_stats[col].fillna(0).astype('Int64')
 
    t_team, t_matches, t_profile, t_pitch, t_phys = st.tabs(["Holdoversigt", "Kampoversigt", "Spillerprofil", "Spilleraktioner", "Fysisk data"])
 
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
 
        if not truppen_stats.empty:
            df_vis_truppen = truppen_stats.reset_index()
            gen_kolonner = ['visningsnavn', 'Kampe', 'Minutter', 'Aktioner', 'Pasninger', 'Pasningsprocent', 'Mål', 'Assists', 'Udskiftet', 'Indskiftet', 'Gule_kort', 'Roede_kort']
            opb_kolonner = ['visningsnavn', 'Aktioner', 'Pasninger', 'Pasningsprocent', 'Key_Passes', 'Stikninger', 'Driblinger', 'Driblinger_Succes', 'Rum_Driblinger_Space']
            off_kolonner = ['visningsnavn', 'Aktioner', 'Afslutninger', 'xG', 'Chancer_skabt', 'Indlæg', 'xA', 'Offensive_Dueller', 'Gennembrud_Overtake', 'Driblinger_Succes']
            def_kolonner = ['visningsnavn', 'Aktioner', 'Erobringer', 'Tacklinger', 'Clearinger', 'Blokeringer', 'Interceptioner', 'Defensive_Dueller', 'Defensive_1v1_Stoppet', 'Frispark_imod']
 
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
                'Driblinger_Ialt': 'Driblinger, ialt', 
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
                event_stats_kamp = df_kamp_events.groupby(['player_optauuid', 'visningsnavn']).apply(lambda x: pd.Series({
                    'Kampe': 1,
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
     
                truppen_stats_kamp_raw = event_stats_kamp.copy()
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
                    'Driblinger_Ialt': 'Driblinger, ialt', 
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
                st.info("Ingen hændelsesdata for denne kamp.")
        else:
            st.warning("Ingen spillede kampe fundet i denne sæson.")
 
    with t_profile:
        if not truppen_stats.empty and valgt_player_uuid in truppen_stats.index:
            if 'Position' not in truppen_stats.columns:
                truppen_stats['Position'] = truppen_stats.index.to_series().apply(
                    lambda u: POSITION_MAP.get(str(u).strip(), 'Ukendt')
                )

            if spiller_position != 'Ukendt':
                sammenligningsgruppe = truppen_stats_liga[truppen_stats_liga['Position'] == spiller_position]
                if sammenligningsgruppe.empty:
                    sammenligningsgruppe = truppen_stats_liga
            else:
                sammenligningsgruppe = truppen_stats_liga

            numeric_cols = sammenligningsgruppe.drop(columns=['visningsnavn', 'Pasningsprocent_Str', 'Position'], errors='ignore')
            ranks = (-numeric_cols).rank(ascending=True, method='min').astype(int)

            try:
                spiller_ranks = ranks.loc[valgt_player_uuid]
                if isinstance(spiller_ranks, pd.DataFrame):
                    spiller_ranks = spiller_ranks.iloc[0]
                s_data = truppen_stats.loc[valgt_player_uuid]
                if isinstance(s_data, pd.DataFrame):
                    s_data = s_data.iloc[0]
            except KeyError:
                st.error(f"Kunne ikke finde stats for spiller: {valgt_spiller}")
                st.stop()

            main_col_left, main_col_right = st.columns([1.3, 4])

            with main_col_left:
                logo_html = ""
                if hold_logo is not None:
                    buffered = io.BytesIO()
                    hold_logo.save(buffered, format="PNG")
                    img_str = base64.b64encode(buffered.getvalue()).decode()
                    logo_html = f'<img src="data:image/png;base64,{img_str}" style="height: 35px; margin-right: 12px;">'

                position_label = POSITION_DA.get(spiller_position, spiller_position)
                st.markdown(f'''<div style="display: flex; align-items: center; margin-bottom: 10px;">{logo_html}<div>
                        <div style="font-size: 18px; font-weight: bold; line-height: 1.2;">{valgt_spiller}</div>
                        <div style="font-size: 12px; color: #888;">{position_label}</div>
                    </div></div>''', unsafe_allow_html=True)
                st.markdown("<hr style='margin: 10px 0; opacity: 0.5;'>", unsafe_allow_html=True)

                st.markdown(f"""
                    <div style="background-color: #f8f9fa; padding: 12px; border-radius: 8px; border: 1px solid #e9ecef;">
                        <h4 style="margin: 0 0 10px 0; font-size: 14px; text-transform: uppercase; font-weight: bold;">Kampdata</h4>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Kampe:</b></span><span>{int(s_data['Kampe'])}</span></div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Minutter:</b></span><span>{int(s_data['Minutter'])}'</span></div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Mål (xG):</b></span><span>{int(s_data['Mål'])} ({round(s_data['xG'], 2)})</span></div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Assists (xA):</b></span><span>{int(s_data['Assists'])} ({round(s_data['xA'], 2)})</span></div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Gule kort:</b></span><span>{int(s_data['Gule_kort'])}</span></div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Røde kort:</b></span><span>{int(s_data['Roede_kort'])}</span></div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Indskiftet:</b></span><span>{int(s_data['Indskiftet'])}</span></div>
                        <div style="display: flex; justify-content: space-between; font-size: 13px;"><span><b>Udskiftet:</b></span><span>{int(s_data['Udskiftet'])}</span></div>
                    </div>
                """, unsafe_allow_html=True)

                st.markdown("<hr style='margin: 15px 0; opacity: 0.5;'>", unsafe_allow_html=True)
                gruppe_navn = POSITION_DA_FLERTAL.get(spiller_position, "spillere")
                st.caption(f"Sammenlignet med alle {gruppe_navn} i ligaen.")

            with main_col_right:
                kat_liste = KATEGORI_PER_POSITION.get(spiller_position, DEFAULT_KAT_LISTE)
                kat_liste = [(label, k_id) for label, k_id in kat_liste if k_id in truppen_stats.columns]

                for i in range(0, len(kat_liste), 4):
                    cols = st.columns(4)
                    for j, (label, k_id) in enumerate(kat_liste[i:i+4]):
                        with cols[j]:
                            st.markdown(f"<p style='text-align:center; font-weight:bold; font-size:12px; margin-bottom:0px;'>{label}</p>", unsafe_allow_html=True)
                            player_val = truppen_stats.loc[valgt_player_uuid, k_id]
                            if isinstance(player_val, pd.Series):
                                player_val = player_val.iloc[0]
                            max_val = sammenligningsgruppe[k_id].max() if k_id in sammenligningsgruppe.columns else 1
                            rank_val = spiller_ranks[k_id] if k_id in spiller_ranks.index else 1
                            fig = create_relative_donut(player_val, max_val, label, get_ordinal(rank_val), color=primær_farve)
                            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"p_{k_id}_{i}_{j}")
        else:
            st.info("Ingen spillerdata tilgængelig.")
     
    # --- 4. SPILLERAKTIONER ---
    with t_pitch:
        descriptions = {
            "Heatmap": "Viser spillerens generelle bevægelsesmønster og intensitet på banen.",
            "Berøringer": "Alle aktioner hvor spilleren har været i kontakt med bolden.",
            "Afslutninger": "Oversigt over alle skudforsøg (Mål = firkant, skud = cirkel).",
            "Defensive aktioner": "Tacklinger, bolderobringer og opsnappede afleveringer.",
            "Offensive pasninger": "Fremadrettede pasninger der lander i sidste tredjedel af banen (grøn = lykkedes, grå = mislykkedes).",
            "Alle aktioner": "Alle aktionstyper vist samtidig, farvekodet efter type (blå = aflevering, rød = dribling, orange = afslutning, grøn = mål, lilla = defensiv aktion)."
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

    with t_phys:
        st.markdown('<div style="font-size: 16px; font-weight: bold; margin-bottom: 10px;">Fysisk Data (Second Spectrum)</div>', unsafe_allow_html=True)
        if valgt_player_uuid and valgt_spiller:
            df_phys_data = get_physical_data(valgt_spiller, valgt_player_uuid, valgt_hold, conn)
            if not df_phys_data.empty:
                st.dataframe(df_phys_data, use_container_width=True, hide_index=True)
            else:
                st.info("Ingen fysisk data tilgængelig for denne spiller.")
        else:
            st.warning("Vælg venligst en spiller for at se fysisk data.")
