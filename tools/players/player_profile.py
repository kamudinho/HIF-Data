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
from io import BytesIO

# --- IMPORT FRA MAPPING ---
from data.utils.mapping import (
    OPTA_EVENT_TYPES, 
    OPTA_QUALIFIERS,
    get_action_label
)

# --- KONFIGURATION (Fra din gemte info) ---
DB = "KLUB_HVIDOVREIF.AXIS"
SEASONNAME = "2025/2026"
LIGA_IDS = "('335', '328', '329', '43319', '331')"
COMP_MAP = { 335: "Superliga", 328: "NordicBet Liga", 329: "2. division", 43319: "3. division", 331: "Oddset Pokalen", 1305: "U19 Ligaen" }

# --- HJÆLPEFUNKTIONER ---
@st.cache_data(ttl=3600)
def get_logo_img(opta_uuid):
    if not opta_uuid: return None
    uuid_clean = str(opta_uuid).lower().replace('t', '')
    url = next((info['logo'] for name, info in TEAMS.items() if str(info.get('opta_uuid', '')).lower().replace('t','') == uuid_clean), None)
    if not url: return None
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except: return None

def draw_player_info_box(ax, logo, player_name, season, view_name):
    # Baggrundsboks (Hvidovre mørkeblå)
    ax.add_patch(plt.Rectangle((1, 85), 38, 14, color='#003366', alpha=0.9, zorder=10))
    ax.text(12, 95, str(player_name).upper(), color='white', fontsize=10, fontweight='bold', zorder=11)
    ax.text(12, 91, f"{season} | {view_name}", color='white', fontsize=8, alpha=0.8, zorder=11)
    if logo:
        logo_arr = np.array(logo)
        newax = ax.inset_axes([0.02, 0.87, 0.08, 0.1], zorder=12)
        newax.imshow(logo_arr)
        newax.axis('off')

def create_relative_donut(player_val, max_val, label, color="#003366"):
    # Håndtering af None/0 værdier for at undgå fejl
    p_val = player_val if player_val is not None else 0
    m_val = max(max_val if max_val is not None else 1, p_val, 1)
    
    reminder = max(0, m_val - p_val)
    fig = go.Figure(go.Pie(
        values=[p_val, reminder],
        hole=0.7,
        marker_colors=[color, "#EEEEEE"],
        textinfo='none',
        hoverinfo='none'
    ))
    pct = int((p_val / m_val) * 100)
    fig.update_layout(
        showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=130, width=130,
        annotations=[dict(text=f"{p_val}<br><span style='font-size:10px;'>{pct}%</span>", 
                     x=0.5, y=0.5, font_size=16, showarrow=False, font_family="Arial Black")]
    )
    return fig

def vis_side(dp=None):
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 16px !important; text-align: center; font-weight: bold !important; width: 100%; }
        [data-testid="stMetricLabel"] { font-size: 10px !important; text-align: center; width: 100%; }
        .player-header { font-size: 20px; font-weight: bold; margin-bottom: 10px; color: #1E1E1E; }
        </style>
        """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn:
        st.error("Kunne ikke oprette forbindelse til Snowflake.")
        return

    # 1. HENT DATA MED FEJL-CHECK
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
    
    if df_teams_raw is None or df_teams_raw.empty:
        st.warning("Ingen holddata fundet for de valgte ligaer.")
        return

    # Mapping og UI
    mapping_lookup = {str(info['opta_uuid']).lower().replace('t', ''): name for name, info in TEAMS.items() if 'opta_uuid' in info}
    team_map = {mapping_lookup[str(r['CONTESTANTHOME_OPTAUUID']).lower().replace('t','')]: r['CONTESTANTHOME_OPTAUUID'] 
                for _, r in df_teams_raw.iterrows() if str(r['CONTESTANTHOME_OPTAUUID']).lower().replace('t','') in mapping_lookup}

    col_h_hold, col_h_spiller = st.columns(2)
    valgt_hold = col_h_hold.selectbox("Hold", sorted(list(team_map.keys())), key="team_sel")
    valgt_uuid_hold = team_map[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid_hold)

    # 2. SQL QUERY FOR SPILLERE
    sql_all = f"""
        SELECT 
            e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, 
            TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as VISNINGSNAVN, 
            e.PLAYER_OPTAUUID, e.EVENT_OUTCOME as OUTCOME,
            LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
        FROM {DB}.OPTA_EVENTS e
        JOIN (SELECT DISTINCT PLAYER_OPTAUUID, FIRST_NAME, LAST_NAME FROM {DB}.OPTA_PLAYERS) p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
        LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
        WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid_hold}' 
        AND e.EVENT_TIMESTAMP >= '2025-07-01'
        GROUP BY 1, 2, 3, 4, 5, 6
    """
    
    df_all = conn.query(sql_all)
    if df_all is None or df_all.empty:
        st.info("Ingen hændelser fundet for dette hold i den valgte periode.")
        return

    # Rens data
    df_all = df_all.dropna(subset=['VISNINGSNAVN'])
    df_all['Action_Label'] = df_all.apply(get_action_label, axis=1)

    valgt_spiller = col_h_spiller.selectbox("Spiller", sorted(df_all['VISNINGSNAVN'].unique()))
    df_spiller = df_all[df_all['VISNINGSNAVN'] == valgt_spiller].copy()

    # 3. VISNING
    t_profile, t_pitch = st.tabs(["Profil", "Bane"])

    with t_profile:
        col_img, col_stat = st.columns([1, 3])
        if hold_logo: col_img.image(hold_logo, width=100)
        col_stat.markdown(f"<div class='player-header'>{valgt_spiller}</div>", unsafe_allow_html=True)
        
        # Eksempel på donut
        pasninger = len(df_spiller[df_spiller['EVENT_TYPEID'] == 1])
        st.plotly_chart(create_relative_donut(pasninger, 50, "Pasninger"), config={'displayModeBar': False})

    with t_pitch:
        pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
        fig, ax = pitch.draw(figsize=(10, 7))
        draw_player_info_box(ax, hold_logo, valgt_spiller, SEASONNAME, "Sæson Oversigt")
        
        # Plot kun hvis der er koordinater
        df_coords = df_spiller.dropna(subset=['EVENT_X', 'EVENT_Y'])
        if not df_coords.empty:
            pitch.scatter(df_coords.EVENT_X, df_coords.EVENT_Y, ax=ax, color='#003366', alpha=0.5)
        
        st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
