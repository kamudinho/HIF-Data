import streamlit as st
from streamlit_option_menu import option_menu
import os
import pandas as pd
from sqlalchemy import create_engine, text
from tools import heatmaps, shots, skudmap, dataviz, players, comparison, stats, goalzone, top5, squad

# --- 1. KONFIGURATION & CSS ---
st.set_page_config(
    page_title="HIF Performance Hub", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Bootstrap Icons
st.markdown('<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">', unsafe_allow_html=True)

st.markdown("""
    <style>
        /* 1. FJERN ALT TOMRUM I TOPPEN AF HOVEDINDHOLDET */
        .block-container {
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
            margin-top: -30px !important; /* Trækker indholdet op */
        }

        /* 2. SKJUL STREAMLITS STANDARD HEADER (DEN USYNLIGE BJÆLKE) */
        [data-testid="stHeader"] {
            display: none !important;
        }
        
        /* 3. SIDEBAR NAVIGATION & TOP GAB */
        [data-testid="stSidebarNav"] { display: none; }
        
        [data-testid="stSidebarUserContent"] {
            padding-top: 0.5rem !important;
            margin-top: -50px !important; 
        }

        /* 4. SAMLET CONTAINER TIL LOGO OG IKON */
        .sidebar-top-container {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            position: relative;
            margin-bottom: 10px;
        }

        .logout-link {
            color: #d3d3d3 !important;
            font-size: 22px !important;
            text-decoration: none !important;
            transition: 0.3s;
            cursor: pointer;
            position: absolute;
            left: 5px;
        }
        
        .logout-link:hover {
            color: #cc0000 !important;
        }

        .sidebar-logo {
            width: 70px;
        }

        /* SIDEBAR GENEREL STYLING */
        [data-testid="stSidebar"] { min-width: 260px; max-width: 300px; }
        
        header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 2. LOGOUT LOGIK ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if st.query_params.get("logout") == "true":
    st.session_state["logged_in"] = False
    st.query_params.clear()
    st.rerun()

# --- 3. LOGIN SKÆRM ---
if not st.session_state["logged_in"]:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown('<div style="text-align:center;"><img src="https://cdn5.wyscout.com/photos/team/public/2659_120x120.png" width="120"></div>', unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; color: Gray;'>HIF Hub</h1>", unsafe_allow_html=True)
        with st.form("login_form"):
            u_input = st.text_input("Brugernavn")
            p_input = st.text_input("Adgangskode", type="password")
            if st.form_submit_button("Log ind", use_container_width=True):
                if u_input.lower() == "kasper" and p_input == "1234":
                    st.session_state["logged_in"] = True
                    st.session_state["user"] = u_input
                    st.rerun()
                else:
                    st.error("Fejl i login")
    st.stop()

# --- 4. DATA LOADING ---
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
        hold_map = dict(zip(df_hold['TEAM_WYID'], df_hold['Hold']))
        return events, kamp, hold_map, spillere, player_events, df_scout
    except:
        return None, None, {}, None, None, None

df_events, kamp, hold_map, spillere, player_events, df_scout = load_full_data()

# --- 5. SIDEBAR ---
with st.sidebar:
    # HER ER DEN NYE SAMLEDE TOP
    st.markdown('''
        <div class="sidebar-top-container">
            <a href="/?logout=true" target="_self" class="logout-link" title="Log ud">
                <i class="bi bi-box-arrow-left"></i>
            </a>
            <img src="https://cdn5.wyscout.com/photos/team/public/2659_120x120.png" class="sidebar-logo">
        </div>
    ''', unsafe_allow_html=True)
    
    st.markdown(f"<p style='text-align:center; margin-top: 5px; margin-bottom: 0px;'>HIF Performance Hub<br><b>{st.session_state['user']}</b></p>", unsafe_allow_html=True)
    st.divider()

    selected = option_menu(
        menu_title=None,
        options=["HIF DATA", "DATAANALYSE", "STATISTIK", "SCOUTING"],
        icons=["house", "graph-up", "bar-chart", "search"],
        default_index=0,
        styles={
            "container": {"padding": "0!important"},
            "nav-link-selected": {"background-color": "#cc0000"},
            "nav-link": {"font-size": "13px", "padding": "8px"}
        }
    )

    selected_sub = None
    if selected == "DATAANALYSE":
        st.markdown('<p class="sidebar-header">Vælg analyse</p>', unsafe_allow_html=True)
        selected_sub = st.radio("S1", ["Heatmaps", "Shotmaps", "Målzoner", "Afslutninger", "DataViz"], label_visibility="collapsed")
    elif selected == "STATISTIK":
        st.markdown('<p class="sidebar-header">Vælg statistik</p>', unsafe_allow_html=True)
        selected_sub = st.radio("S2", ["Spillerstats", "Top 5"], label_visibility="collapsed")
    elif selected == "SCOUTING":
        st.markdown('<p class="sidebar-header">Vælg scouting</p>', unsafe_allow_html=True)
        selected_sub = st.radio("S3", ["Hvidovre IF", "Trupsammensætning", "Sammenligning"], label_visibility="collapsed")
        if selected_sub == "Trupsammensætning":
            st.markdown('<p class="sidebar-header">Baneopstilling</p>', unsafe_allow_html=True)
            st.session_state['valgt_formation'] = st.radio("Form", ["3-4-3", "4-3-3", "3-5-2"], label_visibility="collapsed")

# --- 6. ROUTING ---
if selected == "HIF DATA":
    st.title("Hvidovre IF Data Hub")
    st.info("Brug menuen til venstre for at navigere.")
elif selected == "DATAANALYSE":
    if selected_sub == "Heatmaps": heatmaps.vis_side(df_events, 4, hold_map)
    elif selected_sub == "Shotmaps": skudmap.vis_side(df_events, 4, hold_map)
    elif selected_sub == "Målzoner": goalzone.vis_side(df_events, kamp, hold_map)
    elif selected_sub == "Afslutninger": shots.vis_side(df_events, kamp, hold_map)
    elif selected_sub == "DataViz": dataviz.vis_side(df_events, kamp, hold_map)
elif selected == "STATISTIK":
    if selected_sub == "Spillerstats": stats.vis_side(spillere, player_events)
    elif selected_sub == "Top 5": top5.vis_side(spillere, player_events)
elif selected == "SCOUTING":
    if selected_sub == "Hvidovre IF": players.vis_side(spillere)
    elif selected_sub == "Trupsammensætning": squad.vis_side(spillere)
    elif selected_sub == "Sammenligning": comparison.vis_side(spillere, player_events, df_scout)
