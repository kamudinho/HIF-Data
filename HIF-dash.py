import streamlit as st
from streamlit_option_menu import option_menu
import os
import pandas as pd
import importlib

# --- 1. KONFIGURATION & CSS ---
st.set_page_config(
    page_title="HIF Performance Hub", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Dynamisk import for at undgå KeyError hvis en fil mangler på Github
def safe_import(module_name):
    try:
        return importlib.import_module(f"tools.{module_name}")
    except Exception as e:
        st.error(f"Fejl ved indlæsning af tools.{module_name}: {e}")
        return None

heatmaps = safe_import("heatmaps")
shots = safe_import("shots")
skudmap = safe_import("skudmap")
dataviz = safe_import("dataviz")
players = safe_import("players")
comparison = safe_import("comparison")
stats = safe_import("stats")
goalzone = safe_import("goalzone")
top5 = safe_import("top5")
squad = safe_import("squad")
player_goalzone = safe_import("player_goalzone")

st.markdown('<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">', unsafe_allow_html=True)

st.markdown("""
    <style>
        .block-container { padding-top: 2rem !important; padding-bottom: 0rem !important; }
        [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
        [data-testid="stSidebarNav"] { display: none; }
        [data-testid="stSidebarUserContent"] { padding-top: 0.5rem !important; margin-top: -30px !important; }
        .sidebar-top-container { display: flex; align-items: center; justify-content: center; width: 100%; position: relative; margin-bottom: 10px; }
        .logout-link { color: #d3d3d3 !important; font-size: 22px !important; text-decoration: none !important; position: absolute; left: 5px; }
        .sidebar-logo { width: 70px; }
        .sidebar-header { font-size: 0.8rem; font-weight: bold; color: #6d6d6d; margin-top: 15px; text-transform: uppercase; }
    </style>
""", unsafe_allow_html=True)

# --- 2. LOGIN LOGIK (OPDATERET TIL 2026) ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown('<div style="text-align:center;"><img src="https://cdn5.wyscout.com/photos/team/public/2659_120x120.png" width="120"></div>', unsafe_allow_html=True)
        with st.form("login_form"):
            u_input = st.text_input("Brugernavn")
            p_input = st.text_input("Adgangskode", type="password")
            # RETTET: use_container_width -> width='stretch'
            if st.form_submit_button("Log ind", width='stretch'):
                if u_input.lower() == "kasper" and p_input == "1234":
                    st.session_state["logged_in"] = True
                    st.rerun()
                else:
                    st.error("Fejl i login")
    st.stop()

# --- 4. DATA LOADING ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'HIF-data.xlsx')

@st.cache_data(ttl=900) # Opdaterer hver 15. min
def load_full_data():
    try:
        events = pd.read_excel(DATA_PATH, sheet_name='Eventdata')
        kamp = pd.read_excel(DATA_PATH, sheet_name='Kampdata')
        df_hold = pd.read_excel(DATA_PATH, sheet_name='Hold')
        spillere = pd.read_excel(DATA_PATH, sheet_name='Spillere')
        player_events = pd.read_excel(DATA_PATH, sheet_name='Playerevents')
        df_scout = pd.read_excel(DATA_PATH, sheet_name='Playerscouting')
        
        if 'PLAYER_WYID' in events.columns and 'PLAYER_WYID' in spillere.columns:
            navne_df = spillere[['PLAYER_WYID', 'NAVN']].drop_duplicates('PLAYER_WYID')
            events = events.merge(navne_df, on='PLAYER_WYID', how='left')
            
        hold_map = dict(zip(df_hold['TEAM_WYID'], df_hold['Hold']))
        return events, kamp, hold_map, spillere, player_events, df_scout
    except Exception as e:
        st.error(f"Datafejl: {e}")
        return None, None, {}, None, None, None

df_events, kamp, hold_map, spillere, player_events, df_scout = load_full_data()

# --- 5. SIDEBAR ---
with st.sidebar:
    st.markdown('''
        <div class="sidebar-top-container">
            <a href="/?logout=true" target="_self" class="logout-link"><i class="bi bi-box-arrow-left"></i></a>
            <img src="https://cdn5.wyscout.com/photos/team/public/2659_120x120.png" class="sidebar-logo">
        </div>
    ''', unsafe_allow_html=True)
    
    selected = option_menu(None, ["DATA - HOLD", "DATA - SPILLERE", "STATISTIK", "SCOUTING"], 
                           icons=["shield-shaded", "person-bounding-box", "bar-chart", "search"], default_index=0)

    selected_sub = None
    if selected == "DATA - HOLD":
        selected_sub = st.radio("S_hold", ["Heatmaps", "Shotmaps", "Zoneinddeling", "Afslutninger", "DataViz"], label_visibility="collapsed")
    elif selected == "DATA - SPILLERE":
        selected_sub = st.radio("S_ind", ["Zoneinddeling", "Afslutninger"], label_visibility="collapsed")

# --- 6. ROUTING ---
if selected == "DATA - HOLD":
    if selected_sub == "Heatmaps" and heatmaps: heatmaps.vis_side(df_events, 4, hold_map)
    elif selected_sub == "Shotmaps" and skudmap: skudmap.vis_side(df_events, 4, hold_map)
    elif selected_sub == "Zoneinddeling" and goalzone: goalzone.vis_side(df_events, kamp, hold_map)
    elif selected_sub == "Afslutninger" and shots: shots.vis_side(df_events, kamp, hold_map)
    elif selected_sub == "DataViz" and dataviz: dataviz.vis_side(df_events, kamp, hold_map)

elif selected == "DATA - SPILLERE":
    if selected_sub == "Zoneinddeling" and player_goalzone:
        player_goalzone.vis_side(df_events, spillere)
