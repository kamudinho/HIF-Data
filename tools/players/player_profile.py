import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from mplsoccer import Pitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS, COMPETITIONS, COMPETITION_NAME, TOURNAMENTCALENDAR_NAME
import requests
from PIL import Image
from io import BytesIO

# --- IMPORT FRA MAPPING ---
from data.utils.mapping import get_action_label

# --- KONFIGURATION (Hentet direkte fra team_mapping.py) ---
DB = "KLUB_HVIDOVREIF.AXIS"
# Vi henter den specifikke OPTA UUID for den valgte turnering (f.eks. 1. Division)
CURRENT_COMP_UUID = COMPETITIONS[COMPETITION_NAME]["COMPETITION_OPTAUUID"]
SEASONNAME = TOURNAMENTCALENDAR_NAME 

def get_logo_img(url):
    if not url: return None
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except: return None

def draw_player_info_box(ax, logo, player_name, season, view_name):
    ax.add_patch(plt.Rectangle((1, 85), 38, 14, color='#003366', alpha=0.9, zorder=10))
    ax.text(12, 95, str(player_name).upper(), color='white', fontsize=10, fontweight='bold', zorder=11)
    ax.text(12, 91, f"{season} | {view_name}", color='white', fontsize=8, alpha=0.8, zorder=11)
    if logo:
        logo_arr = np.array(logo)
        newax = ax.inset_axes([0.02, 0.87, 0.08, 0.1], zorder=12)
        newax.imshow(logo_arr)
        newax.axis('off')

def vis_side():
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 16px !important; font-weight: bold !important; }
        .player-header { font-size: 22px; font-weight: bold; margin-bottom: 10px; }
        </style>
        """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn: return

    # 1. HOLDVALG (Filtreret via din TEAMS mapping baseret på liga)
    hold_muligheder = [name for name, info in TEAMS.items() if info["league"] == COMPETITION_NAME]
    
    col_h_hold, col_h_spiller = st.columns(2)
    valgt_hold_navn = col_h_hold.selectbox("Hold", sorted(hold_muligheder))
    
    # Hent OPTA data for det valgte hold fra din mapping
    hold_info = TEAMS[valgt_hold_navn]
    valgt_hold_uuid = hold_info["opta_uuid"]
    hold_logo_url = hold_info["logo"]
    hold_logo = get_logo_img(hold_logo_url)

    # 2. HENT SPILLERE FRA OPTA_EVENTS (Bruger kun OPTA UUIDs)
    sql_all = f"""
        SELECT 
            e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, 
            TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as VISNINGSNAVN, 
            e.PLAYER_OPTAUUID, e.EVENT_OUTCOME as OUTCOME,
            LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
        FROM {DB}.OPTA_EVENTS e
        JOIN (SELECT DISTINCT PLAYER_OPTAUUID, FIRST_NAME, LAST_NAME FROM {DB}.OPTA_PLAYERS) p 
            ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
        LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
        WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_hold_uuid}' 
        AND e.EVENT_TIMESTAMP >= '2025-07-01'
        GROUP BY 1, 2, 3, 4, 5, 6
    """
    
    df_all = conn.query(sql_all)
    if df_all is None or df_all.empty:
        st.warning(f"Ingen data fundet for {valgt_hold_navn} i Snowflake.")
        return

    df_all = df_all.dropna(subset=['VISNINGSNAVN'])
    
    valgt_spiller = col_h_spiller.selectbox("Spiller", sorted(df_all['VISNINGSNAVN'].unique()))
    df_spiller = df_all[df_all['VISNINGSNAVN'] == valgt_spiller].copy()

    # 3. VISNING
    t_profile, t_pitch = st.tabs(["Spillerprofil", "Aktioner"])

    with t_profile:
        st.markdown(f'<div class="player-header">{valgt_spiller}</div>', unsafe_allow_html=True)
        if hold_logo: st.image(hold_logo, width=80)
        st.write(f"Klub: {valgt_hold_navn} | Sæson: {SEASONNAME}")

    with t_pitch:
        pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
        fig, ax = pitch.draw(figsize=(10, 7))
        draw_player_info_box(ax, hold_logo, valgt_spiller, SEASONNAME, "Aktioner")
        
        df_coords = df_spiller.dropna(subset=['EVENT_X', 'EVENT_Y'])
        if not df_coords.empty:
            pitch.kdeplot(df_coords.EVENT_X, df_coords.EVENT_Y, ax=ax, cmap='Reds', fill=True, alpha=0.5)
        
        st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
