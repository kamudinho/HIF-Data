import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from mplsoccer import Pitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS
import requests
from PIL import Image
import io
import base64
from io import BytesIO
import os

# --- IMPORT FRA MAPPING ---
from data.utils.mapping import (
    OPTA_EVENT_TYPES, 
    OPTA_QUALIFIERS,
    get_action_label
)

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '335', '328', '329', '43319', '331')"
CURRENT_SEASON = "2025/2026"

# --- HJÆLPEFUNKTIONER ---
@st.cache_data(ttl=3600)
def get_logo_img(opta_uuid):
    if not opta_uuid: 
        return None
    uuid_clean = str(opta_uuid).lower().replace('t', '')
    url = next((info['logo'] for name, info in TEAMS.items() if str(info.get('opta_uuid', '')).lower().replace('t','') == uuid_clean), None)
    if not url: 
        return None
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except: 
        return None

def har_qualifier(row_events, row_quals, event_id, qual_ids):
    try:
        if str(row_events) != str(event_id):
            return False
        ql = row_quals if isinstance(row_quals, list) else str(row_quals).split(',')
        row_quals_set = {str(q).strip() for q in ql}
        if isinstance(qual_ids, list):
            target_quals = {str(q).strip() for q in qual_ids}
            return len(row_quals_set.intersection(target_quals)) > 0
        else:
            return str(qual_ids).strip() in row_quals_set
    except:
        return False

def get_ordinal(n):
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

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
            text=f"<b>{player_val}</b><br><span style='font-size:12px; color:#df003b; font-weight:bold;'>{rank_text}</span>", 
            x=0.5, y=0.5, font_size=16, showarrow=False, font_family="Arial"
        )]
    )
    return fig

def draw_player_info_box(ax, team_logo, player_name, season_str, category_str):
    if team_logo:
        ax_l = ax.inset_axes([0.02, 0.88, 0.07, 0.07], transform=ax.transAxes)
        ax_l.imshow(team_logo)
        ax_l.axis('off')
    ax.text(0.10, 0.92, str(player_name).upper(), transform=ax.transAxes, 
            fontsize=10, fontweight='bold', color='black', va='center')
    ax.text(0.10, 0.89, f"{season_str} | {category_str}", transform=ax.transAxes, 
            fontsize=8, color='#666666', va='center')

def vis_side(dp=None):
    # --- 1. INDLÆS NAVNE-OVERSKRIVNING (Mapper OPTA_UUID -> NAVN) ---
    try:
        csv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'players', '1div_overskrivning.csv')
        df_navne_csv = pd.read_csv(csv_path)
        # Vi bruger PLAYER_OPTAUUID som nøgle, da det er det, vi har i Snowflake
        navne_map = dict(zip(df_navne_csv['PLAYER_OPTAUUID'].astype(str), df_navne_csv['NAVN']))
    except:
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

    # --- 2. HOLDVALG ---
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
    if df_teams_raw is not None:
        df_teams_raw.columns = df_teams_raw.columns.str.lower()
        
    mapping_lookup = {str(info['opta_uuid']).lower().replace('t', ''): name for name, info in TEAMS.items() if 'opta_uuid' in info}
    team_map = {}
    if df_teams_raw is not None:
        for _, r in df_teams_raw.iterrows():
            uuid_clean = str(r['contestanthome_optauuid']).lower().replace('t','')
            if uuid_clean in mapping_lookup:
                team_map[mapping_lookup[uuid_clean]] = r['contestanthome_optauuid']

    col_spacer_top, col_h_hold, col_h_spiller = st.columns([2, 1.2, 1.2])
    valgt_hold = col_h_hold.selectbox("Hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid_hold = team_map[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid_hold)

    # --- 3. HENT DATA ---
    with st.spinner("Henter spillerdata..."):
        sql_events = f"""
            SELECT 
                e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, 
                TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as DB_NAVN, 
                e.PLAYER_OPTAUUID, e.EVENT_OUTCOME as OUTCOME,
                TO_CHAR(e.EVENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS') as EVENT_TIMESTAMP_STR,
                LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
            FROM {DB}.OPTA_EVENTS e
            JOIN (SELECT DISTINCT PLAYER_OPTAUUID, FIRST_NAME, LAST_NAME FROM {DB}.OPTA_PLAYERS WHERE FIRST_NAME IS NOT NULL) p 
                ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
            WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid_hold}' 
            AND e.EVENT_TIMESTAMP >= '2025-07-01'
            GROUP BY 1, 2, 3, 4, 5, 6, 7
        """
        df_all = conn.query(sql_events)
        if df_all is not None:
            df_all.columns = df_all.columns.str.lower()
            
            # --- NAVNE-MAPPING LOGIK ---
            # Vi tjekker PLAYER_OPTAUUID mod din CSV-fil
            def get_clean_name(row):
                p_uuid = str(row['player_optauuid'])
                return navne_map.get(p_uuid, row['db_navn'])
            
            df_all['visningsnavn'] = df_all.apply(get_clean_name, axis=1)

        # SQL for xG/xA og Stats (forbliver de samme)
        sql_expected = f"SELECT PLAYER_OPTAUUID, MAX(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_VALUE ELSE 0 END) AS xg, MAX(CASE WHEN STAT_TYPE = 'expectedAssists' THEN STAT_VALUE ELSE 0 END) AS xa, MAX(CASE WHEN STAT_TYPE = 'minsPlayed' THEN STAT_VALUE ELSE 0 END) AS minutes, COUNT(DISTINCT MATCH_ID) as kampe FROM {DB}.OPTA_MATCHEXPECTEDGOALS WHERE CONTESTANT_OPTAUUID = '{valgt_uuid_hold}' AND MATCH_STATUS = 'Played' GROUP BY PLAYER_OPTAUUID"
        df_expected = conn.query(sql_expected)
        if df_expected is not None: df_expected.columns = df_expected.columns.str.lower()

    if df_all is None or df_all.empty:
        st.warning("Ingen hændelsesdata fundet.")
        return

    # Forberedelse til UI
    df_all['qual_list'] = df_all['qualifiers'].fillna('').str.split(',')
    df_all_temp = df_all.rename(columns={'event_x':'EVENT_X','event_y':'EVENT_Y','event_typeid':'EVENT_TYPEID','visningsnavn':'VISNINGSNAVN','player_optauuid':'PLAYER_OPTAUUID','outcome':'OUTCOME','qualifiers':'QUALIFIERS'})
    df_all['Action_Label'] = df_all_temp.apply(get_action_label, axis=1)

    # Dropdown menu
    df_spillere_unikke = df_all[['visningsnavn', 'player_optauuid']].drop_duplicates()
    spiller_options = {r['visningsnavn']: r['player_optauuid'] for _, r in df_spillere_unikke.iterrows()}
    valgt_label = col_h_spiller.selectbox("Spiller", sorted(list(spiller_options.keys())), label_visibility="collapsed")
    valgt_player_uuid = spiller_options[valgt_label]

    # Tabs og visning
    t_profile, t_pitch = st.tabs(["Spillerprofil", "Aktioner"])

    with t_profile:
        # Her beregnes stats og vises donuts som i din oprindelige kode
        st.subheader(f"Profil: {valgt_label}")
        # ... (Resten af din donut og profil logik herfra)

    with t_pitch:
        visning = st.selectbox("Visning", ["Heatmap", "Berøringer", "Afslutninger"], label_visibility="collapsed")
        pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
        fig, ax = pitch.draw(figsize=(10, 7))
        draw_player_info_box(ax, hold_logo, valgt_label, CURRENT_SEASON, visning)
        # Plotting logik...
        st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
