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

# --- 2. DYNAMISK IMPORT (FEJLSIKKER) ---
def get_tool(name):
    try:
        return importlib.import_module(f"tools.{name}")
    except Exception as e:
        return None

# Hent alle moduler
heatmaps = get_tool("heatmaps")
shots = get_tool("shots")
skudmap = get_tool("skudmap")
dataviz = get_tool("dataviz")
players = get_tool("players")
comparison = get_tool("comparison")
stats = get_tool("stats")
goalzone = get_tool("goalzone")
top5 = get_tool("top5")
squad = get_tool("squad")
player_goalzone = get_tool("player_goalzone")

# --- 3. LOGIN LOGIK ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if st.query_params.get("logout") == "true":
    st.session_state["logged_in"] = False
    st.query_params.clear()
    st.rerun()

if not st.session_state["logged_in"]:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown('<div style="text-align:center;"><img src="https://cdn5.wyscout.com/photos/team/public/2659_120x120.png" width="120"></div>', unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center;'>HIF Hub</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            u_input = st.text_input("Brugernavn")
            p_input = st.text_input("Adgangskode", type="password")
            if st.form_submit_button("Log ind", width="stretch"):
                if u_input.lower() == "kasper" and p_input == "1234":
                    st.session_state["logged_in"] = True
                    st.rerun()
                else:
                    st.error("Fejl i login")
    st.stop()

# --- 4. DATA LOADING (15 MIN CACHE + ROBUST TJEK) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'HIF-data.xlsx')

@st.cache_data(ttl=900)
def load_data():
    try:
        if not os.path.exists(DATA_PATH):
            return None, None, {}, None, None, None
            
        # Brug openpyxl engine for .xlsx stabilitet
        ev = pd.read_excel(DATA_PATH, sheet_name='Eventdata', engine='openpyxl')
        ka = pd.read_excel(DATA_PATH, sheet_name='Kampdata', engine='openpyxl')
        ho = pd.read_excel(DATA_PATH, sheet_name='Hold', engine='openpyxl')
        sp = pd.read_excel(DATA_PATH, sheet_name='Spillere', engine='openpyxl')
        pe = pd.read_excel(DATA_PATH, sheet_name='Playerevents', engine='openpyxl')
        sc = pd.read_excel(DATA_PATH, sheet_name='Playerscouting', engine='openpyxl')
        
        if 'PLAYER_WYID' in ev.columns and 'PLAYER_WYID' in sp.columns:
            names = sp[['PLAYER_WYID', 'NAVN']].drop_duplicates('PLAYER_WYID')
            ev = ev.merge(names, on='PLAYER_WYID', how='left')
            
        h_map = dict(zip(ho['TEAM_WYID'], ho['Hold']))
        return ev, ka, h_map, sp, pe, sc
    except Exception as e:
        st.error(f"Excel-fejl: {e}")
        return None, None, {}, None, None, None

# Hent data og stop hvis Excel fejler
df_events, kamp, hold_map, spillere, player_events, df_scout = load_data()

if df_events is None:
    st.warning("⚠️ Kunne ikke læse data. Sørg for at 'HIF-data.xlsx' er en gyldig Excel-fil og er uploadet til GitHub.")
    st.stop()

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
        st.markdown('<p class="sidebar-header">Holdanalyse</p>', unsafe_allow_html=True)
        selected_sub = st.radio("S_hold", ["Heatmaps", "Shotmaps", "Zoneinddeling", "Afslutninger", "DataViz"], label_visibility="collapsed")
    elif selected == "DATA - SPILLERE":
        st.markdown('<p class="sidebar-header">Spilleranalyse</p>', unsafe_allow_html=True)
        selected_sub = st.radio("S_ind", ["Zoneinddeling", "Afslutninger"], label_visibility="collapsed")
    elif selected == "STATISTIK":
        st.markdown('<p class="sidebar-header">Vælg statistik</p>', unsafe_allow_html=True)
        selected_sub = st.radio("S_stat", ["Spillerstats", "Top 5"], label_visibility="collapsed")
    elif selected == "SCOUTING":
        st.markdown('<p class="sidebar-header">Vælg scouting</p>', unsafe_allow_html=True)
        selected_sub = st.radio("S_scout", ["Hvidovre IF", "Trupsammensætning", "Sammenligning"], label_visibility="collapsed")

# --- 6. ROUTING ---
if selected == "DATA - HOLD":
    if selected_sub == "Heatmaps" and heatmaps: heatmaps.vis_side(df_events, 4, hold_map)
    elif selected_sub == "Shotmaps" and skudmap: skudmap.vis_side(df_events, 4, hold_map)
    elif selected_sub == "Zoneinddeling" and goalzone: goalzone.vis_side(df_events, kamp, hold_map)
    elif selected_sub == "Afslutninger" and shots: shots.vis_side(df_events, kamp, hold_map)
    elif selected_sub == "DataViz" and dataviz: dataviz.vis_side(df_events, kamp, hold_map)

elif selected == "DATA - SPILLERE":
    if selected_sub == "Zoneinddeling" and player_goalzone: player_goalzone.vis_side(df_events, spillere)
    elif selected_sub == "Afslutninger": st.info("Under udvikling")

elif selected == "STATISTIK":
    if selected_sub == "Spillerstats" and stats: stats.vis_side(spillere, player_events)
    elif selected_sub == "Top 5" and top5: top5.vis_side(spillere, player_events)

elif selected == "SCOUTING":
    if selected_sub == "Hvidovre IF" and players: players.vis_side(spillere)
    elif selected_sub == "Trupsammensætning" and squad: squad.vis_side(spillere)
    elif selected_sub == "Sammenligning" and comparison: comparison.vis_side(spillere, player_events, df_scout)
