import streamlit as st
from streamlit_option_menu import option_menu
import os
import pandas as pd
import importlib

# --- 1. KONFIGURATION (VIGTIGT: Skal stå øverst) ---
st.set_page_config(page_title="HIF Performance Hub", layout="wide")

# CSS til styling
st.markdown("""
    <style>
        .block-container { padding-top: 2rem !important; }
        [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
        .sidebar-header { font-size: 0.8rem; font-weight: bold; color: #6d6d6d; margin-top: 15px; text-transform: uppercase; }
    </style>
""", unsafe_allow_html=True)

# --- 2. IMPORT AF TOOLS (Siderne) ---
# Vi bruger en stabil metode til at importere dine filer fra /tools mappen
def load_module(name):
    try:
        return importlib.import_module(f"tools.{name}")
    except Exception as e:
        st.sidebar.error(f"Fejl i tools/{name}.py: {e}")
        return None

# Her henter vi alle dine sider manuelt ind
heatmaps = load_module("heatmaps")
shots = load_module("shots")
skudmap = load_module("skudmap")
dataviz = load_module("dataviz")
players = load_module("players")
comparison = load_module("comparison")
stats = load_module("stats")
goalzone = load_module("goalzone")
top5 = load_module("top5")
squad = load_module("squad")
player_goalzone = load_module("player_goalzone")

# --- 3. DATA LOADING ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'HIF-data.xlsx')

@st.cache_data(ttl=900)
def load_full_data():
    try:
        # Læs alle nødvendige ark fra din Excel
        ev = pd.read_excel(DATA_PATH, sheet_name='Eventdata', engine='openpyxl')
        ka = pd.read_excel(DATA_PATH, sheet_name='Kampdata', engine='openpyxl')
        ho = pd.read_excel(DATA_PATH, sheet_name='Hold', engine='openpyxl')
        sp = pd.read_excel(DATA_PATH, sheet_name='Spillere', engine='openpyxl')
        pe = pd.read_excel(DATA_PATH, sheet_name='Playerevents', engine='openpyxl')
        sc = pd.read_excel(DATA_PATH, sheet_name='Playerscouting', engine='openpyxl')
        
        # Merge NAVN på events med det samme
        if 'PLAYER_WYID' in ev.columns and 'PLAYER_WYID' in sp.columns:
            navne_df = sp[['PLAYER_WYID', 'NAVN']].drop_duplicates('PLAYER_WYID')
            ev = ev.merge(navne_df, on='PLAYER_WYID', how='left')
            
        h_map = dict(zip(ho['TEAM_WYID'], ho['Hold']))
        return ev, ka, h_map, sp, pe, sc
    except Exception as e:
        st.error(f"Datafejl: {e}")
        return None, None, {}, None, None, None

# Hent dataen
df_events, kamp, hold_map, spillere, player_events, df_scout = load_full_data()

# Stop appen hvis data ikke kunne indlæses
if df_events is None:
    st.warning("Vent på at Excel-filen indlæses korrekt...")
    st.stop()

# --- 4. SIDEBAR MENU ---
with st.sidebar:
    st.image("https://cdn5.wyscout.com/photos/team/public/2659_120x120.png", width=80)
    
    selected = option_menu(None, ["HOLD", "SPILLERE", "STATISTIK", "SCOUTING"], 
                           icons=["shield", "person", "bar-chart", "search"], 
                           default_index=0)

    selected_sub = None
    if selected == "HOLD":
        st.markdown('<p class="sidebar-header">Holdanalyse</p>', unsafe_allow_html=True)
        selected_sub = st.radio("S_hold", ["Heatmaps", "Shotmaps", "Zoneinddeling", "Afslutninger", "DataViz"], label_visibility="collapsed")
    elif selected == "SPILLERE":
        st.markdown('<p class="sidebar-header">Spilleranalyse</p>', unsafe_allow_html=True)
        selected_sub = st.radio("S_ind", ["Zoneinddeling", "Afslutninger"], label_visibility="collapsed")
    elif selected == "STATISTIK":
        st.markdown('<p class="sidebar-header">Ranglister</p>', unsafe_allow_html=True)
        selected_sub = st.radio("S_stat", ["Spillerstats", "Top 5"], label_visibility="collapsed")
    elif selected == "SCOUTING":
        st.markdown('<p class="sidebar-header">Scoutingværktøjer</p>', unsafe_allow_html=True)
        selected_sub = st.radio("S_scout", ["Hvidovre IF", "Trupsammensætning", "Sammenligning"], label_visibility="collapsed")

# --- 5. ROUTING (Her kaldes de enkelte sider) ---
if selected == "HOLD":
    if selected_sub == "Heatmaps" and heatmaps: heatmaps.vis_side(df_events, 4, hold_map)
    elif selected_sub == "Shotmaps" and skudmap: skudmap.vis_side(df_events, 4, hold_map)
    elif selected_sub == "Zoneinddeling" and goalzone: goalzone.vis_side(df_events, kamp, hold_map)
    elif selected_sub == "Afslutninger" and shots: shots.vis_side(df_events, kamp, hold_map)
    elif selected_sub == "DataViz" and dataviz: dataviz.vis_side(df_events, kamp, hold_map)

elif selected == "SPILLERE":
    if selected_sub == "Zoneinddeling" and player_goalzone: player_goalzone.vis_side(df_events, spillere)
    elif selected_sub == "Afslutninger": st.info("Side under opbygning")

elif selected == "STATISTIK":
    if selected_sub == "Spillerstats" and stats: stats.vis_side(spillere, player_events)
    elif selected_sub == "Top 5" and top5: top5.vis_side(spillere, player_events)

elif selected == "SCOUTING":
    if selected_sub == "Hvidovre IF" and players: players.vis_side(spillere)
    elif selected_sub == "Trupsammensætning" and squad: squad.vis_side(spillere)
    elif selected_sub == "Sammenligning" and comparison: comparison.vis_side(spillere, player_events, df_scout)
