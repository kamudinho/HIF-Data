import streamlit as st
from streamlit_option_menu import option_menu
import os
import pandas as pd
import importlib

# --- 1. KONFIGURATION ---
st.set_page_config(page_title="HIF Performance", layout="wide")

# CSS for et rent look og synlig menu
st.markdown("""
    <style>
        .block-container { padding-top: 2rem !important; }
        [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
        [data-testid="stSidebarNav"] { display: none; }
    </style>
""", unsafe_allow_html=True)

# Dynamisk og fejlsikker import
def get_tool(name):
    try:
        module = importlib.import_module(f"tools.{name}")
        return module
    except Exception as e:
        # Vi viser fejlen i en lille boks, så vi ved HVILKEN fil der driller
        st.sidebar.error(f"Fejl i tools/{name}.py: {str(e)}")
        return None

# Importér alle værktøjer
heatmaps = get_tool("heatmaps")
shots = get_tool("shots")
skudmap = get_tool("skudmap")
dataviz = get_tool("dataviz")
players = get_tool("players")  # HUSK: Skift til "hif_players" hvis du omdøber filen
goalzone = get_tool("goalzone")
player_goalzone = get_tool("player_goalzone")

# --- 2. DATA LOADING (15 min cache) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'HIF-data1.xlsx')

@st.cache_data(ttl=900)
def load_data():
    try:
        # Læs alle ark
        ev = pd.read_excel(DATA_PATH, sheet_name='Eventdata')
        sp = pd.read_excel(DATA_PATH, sheet_name='Spillere')
        ka = pd.read_excel(DATA_PATH, sheet_name='Kampdata')
        ho = pd.read_excel(DATA_PATH, sheet_name='Hold')
        
        # Merge navne med det samme
        if 'PLAYER_WYID' in ev.columns and 'PLAYER_WYID' in sp.columns:
            names = sp[['PLAYER_WYID', 'NAVN']].drop_duplicates('PLAYER_WYID')
            ev = ev.merge(names, on='PLAYER_WYID', how='left')
            
        h_map = dict(zip(ho['TEAM_WYID'], ho['Hold']))
        return ev, ka, h_map, sp
    except Exception as e:
        st.error(f"Excel-fejl: {e}")
        return None, None, {}, None

df_events, kamp, hold_map, spillere = load_data()

# --- 3. SIDEBAR & MENU ---
with st.sidebar:
    st.image("https://cdn5.wyscout.com/photos/team/public/2659_120x120.png", width=100)
    selected = option_menu(None, ["HOLD", "SPILLERE"], 
                           icons=["shield", "person"], default_index=0)
    
    if selected == "HOLD":
        sub = st.radio("Vælg:", ["Heatmaps", "Shotmaps", "Zoneinddeling", "Afslutninger"], label_visibility="collapsed")
    else:
        sub = st.radio("Vælg:", ["Zoneinddeling", "Spillerliste"], label_visibility="collapsed")

# --- 4. ROUTING (KUN VIS HVIS MODUL ER FUNDET) ---
if selected == "HOLD":
    if sub == "Heatmaps" and heatmaps: heatmaps.vis_side(df_events, 4, hold_map)
    elif sub == "Shotmaps" and skudmap: skudmap.vis_side(df_events, 4, hold_map)
    elif sub == "Zoneinddeling" and goalzone: goalzone.vis_side(df_events, kamp, hold_map)
    elif sub == "Afslutninger" and shots: shots.vis_side(df_events, kamp, hold_map)
else:
    if sub == "Zoneinddeling" and player_goalzone: player_goalzone.vis_side(df_events, spillere)
    elif sub == "Spillerliste" and players: players.vis_side(spillere)
