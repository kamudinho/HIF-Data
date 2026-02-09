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

# Custom CSS til at forbedre layout på tværs af opløsninger
st.markdown("""
    <style>
        /* Sidebar bredde og styling */
        [data-testid="stSidebar"] {
            min-width: 260px;
            max-width: 320px;
        }
        /* Gør radio-buttons mere lækre og responsive */
        div.row-widget.stRadio > div {
            background-color: #f8f9fb;
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #eceef1;
        }
        /* Justering af overskrifter i sidebaren */
        .sidebar-header {
            font-size: 0.85rem;
            font-weight: bold;
            color: #6d6d6d;
            margin-top: 15px;
            margin-bottom: 5px;
            text-transform: uppercase;
        }
    </style>
""", unsafe_allow_html=True)

def get_engine():
    db_path = os.path.join(os.getcwd(), 'hif_database.db')
    return create_engine(f"sqlite:///{db_path}")

# --- 2. INITIALISERING AF DATABASE ---
engine = get_engine()
with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            username TEXT UNIQUE, 
            password_hash TEXT, 
            role TEXT
        )
    """))
    # Kasper login setup (Hashed pw for '1234')
    hashed_pw = '$2b$12$K6N98h98C.S6uYvjO5fE9uXmPjP/6uE6P/r0mK6m.fG0Z0x1y2z3a'
    conn.execute(text("""
        INSERT INTO users (username, password_hash, role) 
        VALUES ('Kasper', :hpw, 'admin')
        ON CONFLICT(username) DO UPDATE SET password_hash = :hpw
    """), {"hpw": hashed_pw})
    conn.commit()

# --- 3. LOGIN LOGIK ---
def verify_user(username, password):
    return username.lower() == "kasper" and password == "1234"

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

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
                if verify_user(u_input, p_input):
                    st.session_state["logged_in"] = True
                    st.session_state["user"] = u_input
                    st.rerun()
                else:
                    st.error("Forkert brugernavn eller kodeord")
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
    except Exception as e:
        st.error(f"Excel-fejl: {e}")
        return None, None, {}, None, None, None

df_events, kamp, hold_map, spillere, player_events, df_scout = load_full_data()

# --- 5. SIDEBAR NAVIGATION ---
selected_sub = None
with st.sidebar:
    st.markdown('<div style="text-align:center; padding-bottom:10px;"><img src="https://cdn5.wyscout.com/photos/team/public/2659_120x120.png" width="80"></div>', unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center;'>HIF Performance Hub<br><b>{st.session_state['user']}</b></p>", unsafe_allow_html=True)
    st.divider()

    selected = option_menu(
        menu_title=None,
        options=["HIF DATA", "DATAANALYSE", "STATISTIK", "SCOUTING"],
        icons=["house", "graph-up", "bar-chart", "search"],
        default_index=0,
        styles={
            "nav-link-selected": {"background-color": "#cc0000"},
            "nav-link": {"font-size": "14px"}
        }
    )

    # Sub-menuer
    st.markdown('<p class="sidebar-header">Menuvalg</p>', unsafe_allow_html=True)
    
    if selected == "DATAANALYSE":
        selected_sub = st.radio("Sub", ["Heatmaps", "Shotmaps", "Målzoner", "Afslutninger", "DataViz"], label_visibility="collapsed")
    
    elif selected == "STATISTIK":
        selected_sub = st.radio("Sub", ["Spillerstats", "Top 5"], label_visibility="collapsed")
    
    elif selected == "SCOUTING":
        selected_sub = st.radio("Sub", ["Hvidovre IF", "Trupsammensætning", "Sammenligning"], label_visibility="collapsed")
        
        # Formation dukker kun op her, hvis Trupsammensætning er valgt
        if selected_sub == "Trupsammensætning":
            st.markdown('<p class="sidebar-header">Baneopstilling</p>', unsafe_allow_html=True)
            st.session_state['valgt_formation'] = st.radio("Form", ["3-4-3", "4-3-3", "3-5-2"], label_visibility="collapsed")

    st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
    if st.button("Log ud", use_container_width=True):
        st.session_state["logged_in"] = False
        st.rerun()

# --- 6. ROUTING ---
if selected == "HIF DATA":
    st.title("Hvidovre IF Data Hub")
    st.info("Velkommen til HIF Performance Hub. Vælg en kategori i menuen til venstre for at se data.")

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
