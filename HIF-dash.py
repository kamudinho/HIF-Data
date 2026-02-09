import streamlit as st
from streamlit_option_menu import option_menu
import os
import pandas as pd
from tools import (
    heatmaps, shots, skudmap, dataviz, players, 
    comparison, stats, goalzone, top5, squad, player_goalzone
)

# --- 1. KONFIGURATION & CSS ---
st.set_page_config(
    page_title="HIF Performance Hub", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

st.markdown('<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">', unsafe_allow_html=True)

st.markdown("""
    <style>
        .block-container { padding-top: 0rem !important; padding-bottom: 0rem !important; margin-top: -25px !important; }
        [data-testid="stHeader"] { display: none !important; }
        [data-testid="stSidebarNav"] { display: none; }
        [data-testid="stSidebarUserContent"] { padding-top: 0.5rem !important; margin-top: -50px !important; }
        .sidebar-top-container { display: flex; align-items: center; justify-content: center; width: 100%; position: relative; margin-bottom: 10px; }
        .logout-link { color: #d3d3d3 !important; font-size: 22px !important; text-decoration: none !important; position: absolute; left: 5px; }
        .sidebar-logo { width: 70px; }
        [data-testid="stSidebar"] { min-width: 260px; max-width: 300px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. LOGOUT & LOGIN (Forkortet for overblik) ---
if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
if not st.session_state["logged_in"]:
    # ... (Din eksisterende login-kode her)
    st.session_state["logged_in"] = True # Test-line
    st.rerun()

# --- 4. DATA LOADING MED MERGE ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'HIF-data.xlsx')

@st.cache_data
def load_full_data():
    try:
        events = pd.read_excel(DATA_PATH, sheet_name='Eventdata')
        kamp = pd.read_excel(DATA_PATH, sheet_name='Kampdata')
        df_hold = pd.read_excel(DATA_PATH, sheet_name='Hold')
        spillere = pd.read_excel(DATA_PATH, sheet_name='Spillere')
        player_events = pd.read_excel(DATA_PATH, sheet_name='Playerevents')
        df_scout = pd.read_excel(DATA_PATH, sheet_name='Playerscouting')
        
        # KOBLE NAVNE PÅ EVENTS (Vigtigt for Zoneinddeling)
        if 'PLAYER_WYID' in events.columns and 'PLAYER_WYID' in spillere.columns:
            navne_df = spillere[['PLAYER_WYID', 'NAVN']].drop_duplicates('PLAYER_WYID')
            events = events.merge(navne_df, on='PLAYER_WYID', how='left')
            
        hold_map = dict(zip(df_hold['TEAM_WYID'], df_hold['Hold']))
        return events, kamp, hold_map, spillere, player_events, df_scout
    except Exception as e:
        st.error(f"Fejl ved indlæsning: {e}")
        return None, None, {}, None, None, None

df_events, kamp, hold_map, spillere, player_events, df_scout = load_full_data()

# --- 5. SIDEBAR MENU ---
with st.sidebar:
    st.markdown('<div class="sidebar-top-container"><img src="https://cdn5.wyscout.com/photos/team/public/2659_120x120.png" class="sidebar-logo"></div>', unsafe_allow_html=True)
    selected = option_menu(None, ["DATA - HOLD", "DATA - SPILLERE", "STATISTIK", "SCOUTING"], 
                           icons=["shield-shaded", "person-bounding-box", "bar-chart", "search"], default_index=0)
    
    selected_sub = None
    if selected == "DATA - HOLD":
        selected_sub = st.radio("S_hold", ["Heatmaps", "Shotmaps", "Zoneinddeling", "Afslutninger", "DataViz"], label_visibility="collapsed")
    elif selected == "DATA - SPILLERE":
        selected_sub = st.radio("S_ind", ["Zoneinddeling", "Afslutninger"], label_visibility="collapsed")

# --- 6. ROUTING ---
if selected == "DATA - HOLD":
    if selected_sub == "Heatmaps": heatmaps.vis_side(df_events, 4, hold_map)
    elif selected_sub == "Shotmaps": skudmap.vis_side(df_events, 4, hold_map)
    elif selected_sub == "Zoneinddeling": goalzone.vis_side(df_events, kamp, hold_map)
    elif selected_sub == "Afslutninger": shots.vis_side(df_events, kamp, hold_map)
