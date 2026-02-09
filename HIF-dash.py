import streamlit as st
from streamlit_option_menu import option_menu
import os
import pandas as pd
import importlib

# --- 1. KONFIGURATION ---
st.set_page_config(page_title="HIF Performance Hub", layout="wide")

# CSS til styling og generel oprydning
st.markdown("""
    <style>
        .block-container { padding-top: 2rem !important; }
        [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
        .sidebar-header { font-size: 0.8rem; font-weight: bold; color: #6d6d6d; margin-top: 15px; text-transform: uppercase; }
        
        /* Fjern standard Streamlit padding i sidebaren for bedre logo-kontrol */
        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. LOGIN SYSTEM ---
USER_DB = {"kasper": "1234", "ceo": "2650", "mr": "2650", "kd": "2650", "cg": "2650"}

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    # Centreret login boks
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        # Centreret logo på login-skærm
        st.markdown(
            """
            <div style="display: flex; justify-content: center; margin-bottom: 20px;">
                <img src="https://cdn5.wyscout.com/photos/team/public/2659_120x120.png" width="120">
            </div>
            """,
            unsafe_allow_html=True
        )
        
        st.markdown("<h3 style='text-align: center;'>HIF Performance Hub</h3>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            user = st.text_input("Brugernavn").lower().strip()
            pw = st.text_input("Adgangskode", type="password")
            submit = st.form_submit_button("Log ind", use_container_width=True)
            
            if submit:
                if user in USER_DB and USER_DB[user] == pw:
                    st.session_state["logged_in"] = True
                    st.rerun()
                else:
                    st.error("Ugyldigt brugernavn eller kode")
    st.stop()

# --- 3. IMPORT AF TOOLS (MODULER) ---
def load_module(name):
    try:
        return importlib.import_module(f"tools.{name}")
    except Exception as e:
        return None

# Load alle analyse-moduler
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

# --- 4. DATA LOADING ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'HIF-data.xlsx')

@st.cache_data(ttl=3600, show_spinner="Opdaterer HIF data...")
def load_full_data():
    try:
        # Læs alle ark fra Excel filen
        ev = pd.read_excel(DATA_PATH, sheet_name='Eventdata', engine='openpyxl')
        ka = pd.read_excel(DATA_PATH, sheet_name='Kampdata', engine='openpyxl')
        ho = pd.read_excel(DATA_PATH, sheet_name='Hold', engine='openpyxl')
        sp = pd.read_excel(DATA_PATH, sheet_name='Spillere', engine='openpyxl')
        pe = pd.read_excel(DATA_PATH, sheet_name='Playerevents', engine='openpyxl')
        sc = pd.read_excel(DATA_PATH, sheet_name='Playerscouting', engine='openpyxl')
        
        # Merge spillernavne ind på eventdata med det samme
        if 'PLAYER_WYID' in ev.columns and 'PLAYER_WYID' in sp.columns:
            navne_df = sp[['PLAYER_WYID', 'NAVN']].drop_duplicates('PLAYER_WYID')
            ev = ev.merge(navne_df, on='PLAYER_WYID', how='left')
            
        h_map = dict(zip(ho['TEAM_WYID'], ho['Hold']))
        return ev, ka, h_map, sp, pe, sc
    except Exception as e:
        st.error(f"Kritisk fejl ved indlæsning af data: {e}")
        return None, None, {}, None, None, None

df_events, kamp, hold_map, spillere, player_events, df_scout = load_full_data()

# --- 5. SIDEBAR MENU (i HIF-dash.py) ---
with st.sidebar:
    st.markdown("""<div style="display: flex; justify-content: center;"><img src="..." width="100"></div>""", unsafe_allow_html=True)
    
    selected = option_menu(None, ["HOLD", "SPILLERE", "STATISTIK", "SCOUTING"], ...)

    selected_sub = None
    if selected == "HOLD":
        st.markdown('<p class="sidebar-header">Holdanalyse</p>', unsafe_allow_html=True)
        selected_sub = st.radio("S_hold", ["Heatmaps", "Shotmaps", "Zoneinddeling", "Afslutninger", "DataViz"], label_visibility="collapsed")
    
    # --- HER INDSÆTTER DU FORMATIONSVÆLGEREN HVIS VI ER PÅ SCOUTING/TRUP ---
    elif selected == "SCOUTING":
        st.markdown('<p class="sidebar-header">Scoutingværktøjer</p>', unsafe_allow_html=True)
        selected_sub = st.radio("S_scout", ["Hvidovre IF", "Trupsammensætning", "Sammenligning"], label_visibility="collapsed")
        
        # Hvis vi har valgt truppen, så vis formationsvælgeren her!
        if selected_sub == "Trupsammensætning":
            st.markdown("---")
            st.markdown('<p class="sidebar-header">Taktik</p>', unsafe_allow_html=True)
            # Vi gemmer valget i session_state, så squad.py kan læse det
            st.selectbox("Vælg formation:", ["3-4-3", "4-3-3", "3-5-2"], key="formation_valg")

    st.markdown("---") # Denne linje adskiller menuen fra log ud
    if st.button("Log ud", use_container_width=True):
        st.session_state["logged_in"] = False
        st.rerun()

# --- 6. ROUTING (VISNING AF SIDER) ---
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
