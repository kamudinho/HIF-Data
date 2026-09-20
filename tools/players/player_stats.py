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
    SEASONNAME = getattr(player_mapping, 'SEASONNAME', "2025/2026")
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

DB = "KLUB_HVIDOVREIF.AXIS"
TEAM_WYID = 7490
COMPETITION_WYID = (328,)
LIGA_IDS = "('2mb332vncy4450vu14paj8844', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '335', '328', '329', '43319', '331')"


@st.cache_data(ttl=600, show_spinner="Indlæser spillerliste...")
def hent_navne_map() -> dict:
    navne_map = {}
    try:
        for p in _STATIC_PLAYERS:
            uuid = str(p.get('player_optauuid', '')).strip()
            navn = p.get('navn') or p.get('visningsnavn') or p.get('name')
            if uuid and navn:
                navne_map[uuid] = navn
    except Exception:
        pass

    try:
        csv_path = os.path.join(os.getcwd(), 'data', 'players', '1div_overskrivning.csv')
        if os.path.exists(csv_path):
            df_csv = pd.read_csv(csv_path)
            for _, r in df_csv.iterrows():
                navne_map[str(r['PLAYER_OPTAUUID']).strip()] = r['NAVN']
    except Exception:
        pass
    return navne_map


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


@st.cache_data(ttl=300, show_spinner="Henter data fra Snowflake...")
def hent_data_fra_sql(_conn, valgt_uuid_hold: str, navne_map: dict):
    df_events, df_stats_hold, df_stats_liga = hent_match_og_haendelsesdata(
        _conn, DB, valgt_uuid_hold, LIGA_IDS, navne_map
    )
    return df_events, df_stats_hold, df_stats_liga


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

    with st.spinner("Henter spillere og statistik..."):
        df_events, truppen_stats, truppen_stats_liga = hent_data_fra_sql(conn, valgt_uuid_hold, navne_map)

    if df_events is None or df_events.empty:
        st.warning("Ingen hændelsesdata fundet.")
        st.stop()

    df_spillere_unikke = df_events[['visningsnavn', 'player_optauuid']].drop_duplicates()

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
    df_spiller = df_events[df_events['player_optauuid'] == valgt_player_uuid].copy() if valgt_player_uuid else pd.DataFrame()

    t_team, t_matches = st.tabs(["Holdoversigt", "Kampoversigt"])

    # Fælleskolonner til visning
    gen_kolonner = ['visningsnavn', 'Kampe', 'Minutter', 'Aktioner', 'Pasninger', 'Pasningsprocent', 'Mål', 'Assists', 'Udskiftet', 'Indskiftet', 'Gule_kort', 'Roede_kort']
    opb_kolonner = ['visningsnavn', 'Aktioner', 'Pasninger', 'Pasningsprocent', 'Key_Passes', 'fremadrettede_pasninger', 'Stikninger', 'Driblinger', 'Driblinger_Succes', 'Rum_Driblinger_Space']
    off_kolonner = ['visningsnavn', 'Aktioner', 'Afslutninger', 'xG', 'Chancer_skabt', 'Indlæg', 'xA', 'Offensive_Dueller', 'Gennembrud_Overtake', 'Driblinger_Succes']
    def_kolonner = ['visningsnavn', 'Aktioner', 'Erobringer', 'Tacklinger', 'Clearinger', 'Blokeringer', 'Interceptioner', 'Defensive_Dueller', 'Defensive_1v1_Stoppet', 'Frispark_imod']

    renaming_dict = {
        'visningsnavn': 'Spiller',
        'Pasningsprocent': 'Pasning (%)',
        'Gule_kort': 'Gule kort',
        'Roede_kort': 'Røde kort',
        'Chancer_skabt': 'Chancer skabt',
        'Key_Passes': 'Key Passes',
        'Frispark_imod': 'Frispark',
        'fremadrettede_pasninger': 'Fremad. pasninger',
        'Driblinger_Ialt': 'Driblinger, ialt', 
        'Driblinger_Succes': 'Driblinger (Succes)', 
        'Gennembrud_Overtake': 'Gennembrud, 1v1', 
        'Rum_Driblinger_Space': 'Driblinger, 1v1', 
        'Offensive_Dueller': 'Off. dueller',
        'Defensive_Dueller': 'Def. dueller', 
        'Defensive_1v1_Stoppet': 'Def. 1v1'
    }

    # --- HOLDOVERSIGT ---
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
            df_vis_truppen = truppen_stats.reset_index() if 'player_optauuid' in truppen_stats.index.names or truppen_stats.index.name == 'player_optauuid' else truppen_stats
            
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

            df_visning = df_visning.rename(columns=renaming_dict)

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

    # --- KAMPOVERSIGT ---
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
            match_col_in_all = next((col for col in ['match_optauuid', 'match_id'] if col in df_events.columns), None)
            df_kamp_events = df_events[df_events[match_col_in_all].astype(str) == valgt_kamp_uuid].copy() if match_col_in_all else pd.DataFrame()
            
            if not df_kamp_events.empty:
                # Filtrér eller genberegn kampstatistik direkte fra de indlæste events for den valgte kamp
                # Alternativt kan du udvide liga_spillere.py til at returnere per-kamp-statistik på samme måde som hold-statistikken.
                # Her filtrerer vi blot events for den valgte kamp.
                st.info(f"Viser kampdata forvalgt kamp. (Hændelser fundet: {len(df_kamp_events)})")
            else:
                st.warning("Ingen hændelsesdata for denne kamp.")
        else:
            st.warning("Ingen spillede kampe fundet i denne sæson.")
