import streamlit as st
from streamlit_option_menu import option_menu
import os
import pandas as pd
from tools import heatmaps, shots, skudmaps, dataviz, players, comparison

# --- 1. KONFIGURATION ---
st.set_page_config(page_title="HIF Performance Hub", layout="wide", initial_sidebar_state="expanded")

# --- 2. LOGIN FUNKTIONER ---
def verify_user(username, password):
    # Case-insensitive tjek for brugernavn, men præcist tjek for adgangskode
    if username.lower() == "data" and password == "Data":
        return True
    return False

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# --- 3. LOGIN SKÆRM ---
if not st.session_state["logged_in"]:
    # Skaber luft og centrerer formen
    col1, col2, col3 = st.columns([1, 1.2, 1])
    
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        
        # Centreret Logo
        st.markdown(
            """
            <div style="display: flex; justify-content: center;">
                <img src="https://cdn5.wyscout.com/photos/team/public/2659_120x120.png" width="120">
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        # Centreret Titel
        st.markdown(
            "<h1 style='text-align: center; color: gray; margin-bottom: 20px;'>HIF Hub Login</h1>", 
            unsafe_allow_html=True
        )

        with st.form("login_form"):
            u_input = st.text_input("Brugernavn")
            p_input = st.text_input("Adgangskode", type="password")
            
            # Centreret knap
            btn_col1, btn_col2, btn_col3 = st.columns([1, 2, 1])
            with btn_col2:
                submit_button = st.form_submit_button("Log ind", use_container_width=True)
            
            if submit_button:
                if verify_user(u_input, p_input):
                    st.session_state["logged_in"] = True
                    st.session_state["user"] = u_input
                    st.rerun()
                else:
                    st.error("❌ Forkert brugernavn eller kodeord")
                    
    st.stop()

# --- 4. DATA LOADING (Kører kun efter login) ---
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
    except Exception as e:
        st.error(f"Fejl ved indlæsning af Excel-data: {e}")
        return None, None, {}, None, None, None

df_events, kamp, hold_map, spillere, player_events, df_scout = load_full_data()

# --- 5. SIDEBAR & NAVIGATION ---
selected_sub = None
with st.sidebar:
    # Centreret logo i sidebaren
    st.markdown(
        """
        <div style="display: flex; justify-content: center; margin-bottom: 10px;">
            <img src="https://cdn5.wyscout.com/photos/team/public/2659_120x120.png" width="70">
        </div>
        """, 
        unsafe_allow_html=True
    )
    st.markdown(f"<p style='text-align:center;'>Bruger: <b>{st.session_state['user']}</b></p>", unsafe_allow_html=True)
    st.divider()

    selected = option_menu(
        menu_title=None,
        options=["HIF DATA", "DATAANALYSE", "SCOUTING"],
        icons=["house", "graph-up", "search"],
        default_index=0
    )

    if selected == "DATAANALYSE":
        st.markdown("**Vælg type:**")
        selected_sub = st.radio("Sub_Data", options=["Heatmaps", "Skudmaps", "Afslutninger", "DataViz"], label_visibility="collapsed")

    if selected == "SCOUTING":
        st.markdown("**Vælg type:**")
        selected_sub = st.radio("Sub_Scout", options=["Hvidovre IF", "Sammenligning"], label_visibility="collapsed")

    st.divider()
    if st.button("Log ud"):
        st.session_state["logged_in"] = False
        st.rerun()

# --- 6. DASHBOARD ROUTING ---
if selected == "HIF DATA":
    st.title("Hvidovre IF Performance Hub")
    st.info("Velkommen tilbage! Brug menuen til venstre for at navigere i dataen.")

elif selected == "DATAANALYSE":
    if selected_sub == "Heatmaps":
        heatmaps.vis_side(df_events, 4, hold_map)
    elif selected_sub == "Skudmaps":
        skudmaps.vis_side(df_events, 4, hold_map)
    elif selected_sub == "Afslutninger":
        shots.vis_side(df_events, kamp, hold_map)
    elif selected_sub == "DataViz":
        dataviz.vis_side(df_events, kamp, hold_map)

elif selected == "SCOUTING":
    if selected_sub == "Hvidovre IF":
        players.vis_side(spillere)
    elif selected_sub == "Sammenligning":
        comparison.vis_side(spillere, player_events, df_scout)
