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

st.markdown("""
    <style>
        /* FJERN STANDARD HEADER OG NAVIGATION */
        [data-testid="stHeader"] { display: none !important; }
        [data-testid="stSidebarNav"] { display: none; }
        
        /* HOVEDINDHOLD HELT OP I TOPPEN */
        .block-container {
            padding-top: 0rem !important;
            margin-top: -30px !important; 
        }

        /* SIDEBAR TOP JUSTERING */
        [data-testid="stSidebarUserContent"] {
            padding-top: 0.5rem !important;
            margin-top: -50px !important; 
        }

        /* STYLING AF IKON-KNAPPER (HUS OG LOGUD) */
        .st-emotion-cache-12fmjuu { /* Specifik Streamlit sidebar kolonne-fix */
            display: flex;
            align-items: center;
        }

        /* FJERNER BOKS OM KNAPPER I TOPPEN AF SIDEBAR */
        div[data-testid="stSidebar"] button[kind="secondary"] {
            background-color: transparent !important;
            border: none !important;
            color: #d3d3d3 !important;
            padding: 0px !important;
            font-size: 20px !important;
            width: 30px !important;
            height: 30px !important;
            box-shadow: none !important;
        }
        
        div[data-testid="stSidebar"] button[kind="secondary"]:hover {
            color: #cc0000 !important;
            transform: scale(1.1);
            background-color: transparent !important;
        }

        /* SIDEBAR LOGO OG LAYOUT */
        .sidebar-logo-container {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            margin-bottom: 10px;
        }

        [data-testid="stSidebar"] { min-width: 260px; max-width: 300px; }
        
        div.row-widget.stRadio > div {
            background-color: #f8f9fb;
            padding: 10px;
            border-radius: 10px;
            border: 1px solid #eceef1;
        }

        .sidebar-header {
            font-size: 0.8rem;
            font-weight: bold;
            color: #6d6d6d;
            margin-top: 15px;
            text-transform: uppercase;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. SESSION STATE INITIALISERING ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "home"

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
    # Top bar med knapper og logo
    t1, t2, t3 = st.columns([0.5, 0.5, 2.5])
    
    with t1:
        if st.button("🏠", help="Hjem"):
            st.session_state["current_page"] = "home"
            st.rerun()
    with t2:
        if st.button("⬅️", help="Log ud"):
            st.session_state["logged_in"] = False
            st.rerun()
    with t3:
        st.markdown('<div style="text-align:right; margin-right:20px;"><img src="https://cdn5.wyscout.com/photos/team/public/2659_120x120.png" width="60"></div>', unsafe_allow_html=True)
    
    st.markdown(f"<p style='text-align:center; margin-top: 10px; margin-bottom: 0px;'>HIF Performance Hub<br><b>{st.session_state['user']}</b></p>", unsafe_allow_html=True)
    st.divider()

    # Menu
    selected = option_menu(
        menu_title=None,
        options=["DATA - HOLD", "DATA - INDIVIDUELT", "STATISTIK", "SCOUTING"],
        icons=["shield-shaded", "person-bounding-box", "bar-chart", "search"],
        default_index=0,
        styles={
            "container": {"padding": "0!important"},
            "nav-link-selected": {"background-color": "#cc0000"},
            "nav-link": {"font-size": "13px", "padding": "8px"}
        }
    )

    # Hvis man klikker i menuen, skifter vi væk fra "home"
    if st.session_state["current_page"] == "home" and any(st.session_state.values()): 
        # Denne logik sikrer at vi kan skifte side
        pass

    selected_sub = None
    if selected == "DATA - HOLD":
        st.markdown('<p class="sidebar-header">Holdanalyse</p>', unsafe_allow_html=True)
        selected_sub = st.radio("S_hold", ["Heatmaps", "Shotmaps", "Målzoner", "Afslutninger", "DataViz"], label_visibility="collapsed")
    elif selected == "DATA - INDIVIDUELT":
        st.markdown('<p class="sidebar-header">Spilleranalyse</p>', unsafe_allow_html=True)
        selected_sub = st.radio("S_ind", ["Spillerzoner", "Afslutninger (Spiller)", "Aktionskort", "Pass Net"], label_visibility="collapsed")
    elif selected == "STATISTIK":
        st.markdown('<p class="sidebar-header">Vælg statistik</p>', unsafe_allow_html=True)
        selected_sub = st.radio("S_stat", ["Spillerstats", "Top 5"], label_visibility="collapsed")
    elif selected == "SCOUTING":
        st.markdown('<p class="sidebar-header">Vælg scouting</p>', unsafe_allow_html=True)
        selected_sub = st.radio("S_scout", ["Hvidovre IF", "Trupsammensætning", "Sammenligning"], label_visibility="collapsed")

# --- 6. ROUTING ---
# Vi tvinger routing til at lytte på om "home" knappen er trykket
if st.session_state["current_page"] == "home":
    st.title("Hvidovre IF Data Hub")
    st.info("Velkommen Kasper. Brug menuen til venstre for at navigere i de forskellige datasektioner.")
    
    # Reset page state når man vælger noget i menuen
    if st.button("Gå til Holdanalyse"): # Eksempel på knap
        st.session_state["current_page"] = "menu"
        st.rerun()

else:
    if selected == "DATA - HOLD":
        if selected_sub == "Heatmaps": heatmaps.vis_side(df_events, 4, hold_map)
        elif selected_sub == "Shotmaps": skudmap.vis_side(df_events, 4, hold_map)
        elif selected_sub == "Målzoner": goalzone.vis_side(df_events, kamp, hold_map)
        elif selected_sub == "Afslutninger": shots.vis_side(df_events, kamp, hold_map)
        elif selected_sub == "DataViz": dataviz.vis_side(df_events, kamp, hold_map)

    elif selected == "DATA - INDIVIDUELT":
        st.title(f"Individuel: {selected_sub}")
        st.info("Sektion under opbygning.")

    elif selected == "STATISTIK":
        if selected_sub == "Spillerstats": stats.vis_side(spillere, player_events)
        elif selected_sub == "Top 5": top5.vis_side(spillere, player_events)

    elif selected == "SCOUTING":
        if selected_sub == "Hvidovre IF": players.vis_side(spillere)
        elif selected_sub == "Trupsammensætning": squad.vis_side(spillere)
        elif selected_sub == "Sammenligning": comparison.vis_side(spillere, player_events, df_scout)

# Trick til at skifte fra Home til Menu:
# Hvis brugeren interagerer med radio-knapperne, skal vi deaktivere "home"
if st.session_state["current_page"] == "home" and selected_sub is not None:
    st.session_state["current_page"] = "menu"
    st.rerun()
