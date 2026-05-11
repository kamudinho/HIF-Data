import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from mplsoccer import Pitch, VerticalPitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS, COMPETITIONS, TOURNAMENTCALENDAR_NAME
import requests
from PIL import Image
from io import BytesIO

# --- IMPORT FRA DIN MAPPING.PY ---
from data.utils.mapping import (
    OPTA_EVENT_TYPES, 
    OPTA_QUALIFIERS,
    get_action_label
)

# --- 1. KONFIGURATION (DYNAMISK FRA MAPPING.PY) ---
DB = "KLUB_HVIDOVREIF.AXIS"
# Vi bruger nu den specifikke Opta UUID for 1. Division fra din mapping
LIGA_UUID = f"('{COMPETITIONS['1. Division']['COMPETITION_OPTAUUID']}')"
SEASON = TOURNAMENTCALENDAR_NAME  # "2025/2026"

# --- 2. HJÆLPEFUNKTIONER ---
@st.cache_data(ttl=3600)
def get_logo_img(opta_uuid):
    """Henter klublogo fra din TEAMS mapping"""
    if not opta_uuid: return None
    url = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), None)
    if not url: return None
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except: return None

def draw_match_row(date, h_name, h_uuid, score, a_name, a_uuid, res_char):
    bg_color = "#2e7d32" if res_char == "W" else ("#757575" if res_char == "D" else "#c62828")
    cols = st.columns([0.5, 1.2, 0.25, 0.7, 0.25, 1.2, 0.3], vertical_alignment="center")
    flex_style = "display: flex; align-items: center; height: 30px; margin: 0;"

    with cols[0]: st.markdown(f"<div style='{flex_style} font-size:11px; color:#666;'>{date}</div>", unsafe_allow_html=True)
    with cols[1]: st.markdown(f"<div style='{flex_style} justify-content: flex-end; font-size:13px; font-weight:600; text-align:right;'>{h_name[:12]}</div>", unsafe_allow_html=True)
    with cols[2]:
        logo_h = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == h_uuid), "")
        if logo_h: st.image(logo_h, width=18)
    with cols[3]: st.markdown(f"<div style='{flex_style} justify-content: center;'><div style='background:#f0f2f6; border-radius:3px; width: 100%; text-align:center; font-size:12px; font-weight:800; padding:2px 0;'>{score}</div></div>", unsafe_allow_html=True)
    with cols[4]:
        logo_a = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == a_uuid), "")
        if logo_a: st.image(logo_a, width=18)
    with cols[5]: st.markdown(f"<div style='{flex_style} justify-content: flex-start; font-size:13px; font-weight:600; text-align:left;'>{a_name[:12]}</div>", unsafe_allow_html=True)
    with cols[6]: st.markdown(f"<div style='{flex_style} justify-content: center;'><div style='background-color:{bg_color}; color:white; border-radius:3px; text-align:center; font-weight:bold; font-size:11px; padding:2px 0; width:22px;'>{res_char}</div></div>", unsafe_allow_html=True)

def plot_custom_pitch(df, event_ids, title, zone='full', cmap='Reds', logo=None):
    plot_data = df[df['EVENT_TYPEID'].astype(str).isin([str(i) for i in event_ids])].copy()
    pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
    fig, ax = pitch.draw(figsize=(5, 7))
    
    if zone == 'up': 
        ax.set_ylim(0, 55)
        logo_pos, text_y = [0.04, 0.03, 0.08, 0.08], 0.05
    elif zone == 'down': 
        ax.set_ylim(45, 100)
        logo_pos, text_y = [0.04, 0.90, 0.08, 0.08], 0.97
    else: 
        logo_pos, text_y = [0.04, 0.90, 0.08, 0.08], 0.97
        
    if logo:
        ax_l = ax.inset_axes(logo_pos, transform=ax.transAxes); ax_l.imshow(logo); ax_l.axis('off')
    ax.text(0.94, text_y, title, transform=ax.transAxes, fontsize=6, fontweight='bold', ha='right', va='top')
    
    if not plot_data.empty: 
        pitch.kdeplot(plot_data.EVENT_X, plot_data.EVENT_Y, ax=ax, cmap=cmap, fill=True, alpha=0.5, levels=100)
    return fig

# --- 3. HOVEDFUNKTION ---
def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn: return

    # --- 1. DYNAMISK HOLDVALG BASERET PÅ 1. DIVISION ---
    # Vi henter kun hold der findes i din TEAMS mapping under 1. Division
    nbl_teams = {name: info['opta_uuid'] for name, info in TEAMS.items() if info.get('league') == "1. Division"}
    
    col_hold, col_spacer = st.columns([1, 3.5])
    valgt_hold = col_hold.selectbox("Vælg hold", sorted(list(nbl_teams.keys())), index=0)
    valgt_uuid = nbl_teams[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid)

    with st.spinner("Henter data for 1. Division..."):
        # SQL: Kun 1. Division og nuværende sæson
        sql_res = f"""
            SELECT MATCH_LOCALDATE, CONTESTANTHOME_NAME, CONTESTANTAWAY_NAME, 
                    TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE, CONTESTANTHOME_OPTAUUID, 
                    CONTESTANTAWAY_OPTAUUID, MATCH_OPTAUUID 
            FROM {DB}.OPTA_MATCHINFO 
            WHERE (CONTESTANTHOME_OPTAUUID = '{valgt_uuid}' OR CONTESTANTAWAY_OPTAUUID = '{valgt_uuid}') 
            AND TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_UUID}
            AND TOURNAMENTCALENDAR_NAME = '{SEASON}'
            AND (MATCH_STATUS ILIKE '%Played%' OR MATCH_STATUS ILIKE '%Full%' OR MATCH_STATUS ILIKE '%Finish%') 
            ORDER BY MATCH_LOCALDATE DESC LIMIT 10
        """
        df_res = conn.query(sql_res)
        
        if df_res is None or df_res.empty:
            st.warning(f"Ingen kampdata fundet for {valgt_hold} i sæson {SEASON}.")
            return

        match_ids = tuple(df_res['MATCH_OPTAUUID'].tolist())
        m_ids_str = f"('{match_ids[0]}')" if len(match_ids) == 1 else str(match_ids)

        # --- SQL: EVENTS ---
        sql_all_h = f"""
            SELECT e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, 
                   TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME, 
                   e.MATCH_OPTAUUID, e.EVENT_TIMESTAMP, e.EVENT_OUTCOME as OUTCOME,
                   LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
            FROM {DB}.OPTA_EVENTS e
            JOIN (SELECT DISTINCT PLAYER_OPTAUUID, FIRST_NAME, LAST_NAME FROM {DB}.OPTA_PLAYERS) p 
                ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
            LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' 
            AND e.MATCH_OPTAUUID IN {m_ids_str}
            GROUP BY 1, 2, 3, 4, 5, 6, 7
        """
        df_all_h = conn.query(sql_all_h)

        # --- SQL: MÅL-SEKVENSER ---
        sql_seq = f"""
            SELECT e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, 
                   TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME, 
                   e.EVENT_TIMESTAMP, e.MATCH_OPTAUUID,
                   m.MATCH_LOCALDATE, m.CONTESTANTHOME_NAME, m.CONTESTANTAWAY_NAME, 
                   m.TOTAL_HOME_SCORE, m.TOTAL_AWAY_SCORE,
                   e.EVENT_TIMEMIN as GOAL_MIN,
                   LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
            FROM {DB}.OPTA_EVENTS e
            JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
            JOIN {DB}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
            WHERE e.MATCH_OPTAUUID IN {m_ids_str}
            AND e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}'
            AND e.EVENT_TYPEID = 16
            GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12
        """
        df_goals = conn.query(sql_seq)

    # --- HERFRA STARTER TABS (Ligesom din originale kode) ---
    # ... Resten af din logik for OVERSIGT, MED BOLDEN, osv.
    st.success(f"Data indlæst for {valgt_hold} i 1. Division ({SEASON})")
