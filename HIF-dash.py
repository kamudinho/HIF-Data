import streamlit as st
from streamlit_option_menu import option_menu
import os
import pandas as pd
from data.data_load import load_all_data
from data.users import get_users

# --- 1. KONFIGURATION & STYLES ---
st.set_page_config(page_title="HIF Data Hub", layout="wide")

st.markdown("""
    <style>
        header { visibility: visible !important; background: rgba(0,0,0,0) !important; height: 3rem !important; }
        .block-container { padding-top: 0rem !important; margin-top: 2rem !important; padding-bottom: 1rem !important; }
        [data-testid="stVerticalBlock"] { gap: 0.5rem !important; }
        /* Fjern Streamlit ikoner og støj for et rent look */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 2. LOGIN SYSTEM ---
USER_DB = get_users()
if "logged_in" not in st.session_state: 
    st.session_state["logged_in"] = False
    st.session_state["user"] = None

if not st.session_state["logged_in"]:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<br><br><div style='text-align: center;'><img src='https://cdn5.wyscout.com/photos/team/public/2659_120x120.png' width='120'></div>", unsafe_allow_html=True)
        with st.form("login"):
            u = st.text_input("BRUGER").lower().strip()
            p = st.text_input("KODE", type="password")
            if st.form_submit_button("LOG IND", use_container_width=True):
                if u in USER_DB and USER_DB[u] == p:
                    st.session_state["logged_in"] = True
                    st.session_state["user"] = u
                    st.rerun()
                else: 
                    st.error("Ugyldig bruger eller kode")
    st.stop()

# --- 3. DATA LOADING ---
if "data_package" not in st.session_state:
    with st.spinner("Henter systemdata..."):
        # Henter alt fra Snowflake og GitHub via din data_load.py
        st.session_state["data_package"] = load_all_data()

dp = st.session_state["data_package"]

# --- 4. SIDEBAR NAVIGATION (INGEN IKONER) ---
with st.sidebar:
    st.markdown(f"<p style='text-align: center; font-size: 11px; letter-spacing: 1px;'>BRUGER: {st.session_state['user'].upper()}</p>", unsafe_allow_html=True)
    st.markdown("<div style='text-align: center; padding-bottom: 20px;'><img src='https://cdn5.wyscout.com/photos/team/public/2659_120x120.png' width='80'></div>", unsafe_allow_html=True)
    
    # Hovedkategorier
    hoved_options = ["TRUPPEN", "ANALYSE", "SCOUTING"]
    if st.session_state["user"] == "kasper":
        hoved_options.append("ADMIN")

    hoved_omraade = option_menu(
        menu_title=None,
        options=hoved_options,
        icons=None, # Ikoner fjernet
        menu_icon=None,
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "#fafafa"},
            "nav-link": {"font-size": "14px", "text-align": "left", "margin": "0px", "text-transform": "uppercase"},
            "nav-link-selected": {"background-color": "#003366"},
        }
    )    
    
    selected = "OVERSIGT" 
    if hoved_omraade == "TRUPPEN":
        selected = option_menu(None, options=["Oversigt", "Forecast", "Spillerstats", "Top 5"], icons=None, styles={"nav-link-selected": {"background-color": "#cc0000"}})
    elif hoved_omraade == "ANALYSE":
        selected = option_menu(None, options=["Zoneinddeling", "Afslutninger", "Heatmaps", "Modstanderanalyse"], icons=None, styles={"nav-link-selected": {"background-color": "#cc0000"}})
    elif hoved_omraade == "SCOUTING":
        selected = option_menu(None, options=["Scoutrapport", "Database", "Sammenligning"], icons=None, styles={"nav-link-selected": {"background-color": "#cc0000"}})
    elif hoved_omraade == "ADMIN":
        selected = "Brugerstyring"

# --- 5. ROUTING ---
if selected == "Oversigt":
    import tools.players as players
    players.vis_side(dp["players"])

elif selected == "Spillerstats":
    import tools.stats as stats
    stats.vis_side(dp["players"], dp["season_stats"])

elif selected == "Modstanderanalyse":
    import tools.modstanderanalyse as ma
    # Her sender vi shotevents og hold_map direkte fra din pakke
    ma.vis_side(dp["shotevents"], dp["hold_map"])

elif selected == "Brugerstyring":
    import tools.admin as admin
    admin.vis_side()

# Tilføj her de øvrige elif statements for dine tools (Heatmaps, Database, etc.)
# Husk altid at sende dp["relevante_data"] med som argument!
