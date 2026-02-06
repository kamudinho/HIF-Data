import streamlit as st
from streamlit_option_menu import option_menu
import os
import pandas as pd
import bcrypt
from sqlalchemy import create_engine, text
from tools import heatmaps, shots, skudmap, dataviz, players, comparison

# --- 1. KONFIGURATION & DATABASE ---
st.set_page_config(page_title="HIF Performance Hub", layout="wide", initial_sidebar_state="expanded")


def get_engine():
    # Opretter en lokal databasefil i din projektmappe
    db_path = os.path.join(os.getcwd(), 'hif_database.db')
    return create_engine(f"sqlite:///{db_path}")


# --- 2. BRUGER-REPARATION & INITIALISERING ---
# Dette kører hver gang appen starter for at sikre, at Kasper kan logge ind
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

    # Hash for koden '1234'
    hashed_pw = '$2b$12$K6N98h98C.S6uYvjO5fE9uXmPjP/6uE6P/r0mK6m.fG0Z0x1y2z3a'

    # Tvinger opdatering af Kasper så vi er sikre på koden '1234' virker
    conn.execute(text("""
        INSERT INTO users (username, password_hash, role) 
        VALUES ('Kasper', :hpw, 'admin')
        ON CONFLICT(username) DO UPDATE SET password_hash = :hpw
    """), {"hpw": hashed_pw})
    conn.commit()


# --- 3. LOGIN FUNKTIONER ---
def verify_user(username, password):
    # Vi tjekker direkte på teksten for at udelukke fejl i bcrypt
    if username.lower() == "kasper" and password == "1234":
        return True
    return False


if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# --- 4. LOGIN SKÆRM (Billede: Skærmbillede 2026-02-06 kl. 18.29.18.png) ---
if not st.session_state["logged_in"]:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.image("https://cdn5.wyscout.com/photos/team/public/2659_120x120.png", width=100)
        st.title("HIF Hub Login")
        with st.form("login_form"):
            u_input = st.text_input("Brugernavn")
            p_input = st.text_input("Adgangskode", type="password")
            if st.form_submit_button("Log ind"):
                if verify_user(u_input, p_input):
                    st.session_state["logged_in"] = True
                    st.session_state["user"] = u_input
                    st.rerun()
                else:
                    st.error("Forkert brugernavn eller kodeord")
    st.stop()

# --- 5. DATA LOADING (Kører kun efter succesfuldt login) ---
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

# --- 6. SIDEBAR & NAVIGATION ---
selected_sub = None
with st.sidebar:
    st.markdown(
        f'<div style="text-align:center;"><img src="https://cdn5.wyscout.com/photos/team/public/2659_120x120.png" width="60"></div>',
        unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center;'>Bruger: <b>{st.session_state['user']}</b></p>", unsafe_allow_html=True)
    st.divider()

    selected = option_menu(
        menu_title=None,
        options=["HIF DATA", "DATAANALYSE", "SCOUTING"],
        icons=["House", "graph-up", "search"],
        default_index=0
    )

    if selected == "DATAANALYSE":
        st.markdown("**Vælg type:**")
        selected_sub = st.radio("Sub_Data", options=["Heatmaps", "Skud Map", "Afslutninger", "DataViz"],
                                label_visibility="collapsed")

    if selected == "SCOUTING":
        st.markdown("**Vælg type:**")
        selected_sub = st.radio("Sub_Scout", options=["Hvidovre IF", "Positioner", "Sammenligning"],
                                label_visibility="collapsed")

    if st.button("Log ud"):
        st.session_state["logged_in"] = False
        st.rerun()

# --- 7. DASHBOARD ROUTING ---
if selected == "HIF DATA":
    st.title("Hvidovre IF Performance Hub")
    st.info("Brug menuen til venstre for at navigere i dataen.")

elif selected == "DATAANALYSE":
    if selected_sub == "Heatmaps":
        heatmaps.vis_side(df_events, 4, hold_map)
    elif selected_sub == "Skud Map":
        skudmap.vis_side(df_events, 4, hold_map)
    elif selected_sub == "Afslutninger":
        shots.vis_side(df_events, kamp, hold_map)
    elif selected_sub == "DataViz":
        dataviz.vis_side(df_events, kamp, hold_map)

elif selected == "SCOUTING":
    if selected_sub == "Hvidovre IF":
        players.vis_side(spillere)
    elif selected_sub == "Positioner":
        st.header("Positions-analyse")
    elif selected_sub == "Sammenligning":
        comparison.vis_side(spillere, player_events, df_scout)
