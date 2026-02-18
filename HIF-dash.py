#HIF-dash.py
import streamlit as st
from streamlit_option_menu import option_menu
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
            if st.form_submit_button("LOG IND", width="stretch"):
                # Rettelse: Tjekker specifikt ['pass'] nøglen
                if u in USER_DB and USER_DB[u]["pass"] == p:
                    st.session_state["logged_in"] = True
                    st.session_state["user"] = u
                    st.rerun()
                else: 
                    st.error("Ugyldig bruger eller kode")
    st.stop()

# --- 3. DATA LOADING ---
if "data_package" not in st.session_state:
    with st.spinner("Henter systemdata..."):
        st.session_state["data_package"] = load_all_data()

# VIGTIGT: dp skal defineres UDEN FOR if-blokken
dp = st.session_state["data_package"]

# --- 4. SIDEBAR NAVIGATION ---
with st.sidebar:
    curr_user = st.session_state["user"]
    user_info = USER_DB.get(curr_user, {})
    
    st.markdown(f"<p style='text-align: center; font-size: 11px; letter-spacing: 1px;'>BRUGER: {curr_user.upper()} ({user_info.get('role', 'User')})</p>", unsafe_allow_html=True)
    st.markdown("<div style='text-align: center; padding-bottom: 20px;'><img src='https://cdn5.wyscout.com/photos/team/public/2659_120x120.png' width='80'></div>", unsafe_allow_html=True)
    
    # Henter adgang fra users.py
    hoved_options = user_info.get("access", ["TRUPPEN", "ANALYSE", "SCOUTING"])

    hoved_omraade = option_menu(
        menu_title=None, options=hoved_options, icons=None, menu_icon=None, default_index=0,
        styles={"container": {"background-color": "#fafafa"}, "nav-link-selected": {"background-color": "#003366"}}
    )    
    
    sel = "" 
    if hoved_omraade == "TRUPPEN":
        sel = option_menu(None, options=["Oversigt", "Forecast", "Spillerstats", "Top 5"], icons=None, styles={"nav-link-selected": {"background-color": "#cc0000"}})
    elif hoved_omraade == "ANALYSE":
        sel = option_menu(None, options=["Afslutninger", "Modstanderanalyse"], icons=None, styles={"nav-link-selected": {"background-color": "#cc0000"}})
    elif hoved_omraade == "SCOUTING":
        sel = option_menu(None, options=["Scoutrapport", "Database", "Sammenligning"], icons=None, styles={"nav-link-selected": {"background-color": "#cc0000"}})
    elif hoved_omraade == "ADMIN":
        sel = option_menu(None, options=["Brugerstyring", "Schema Explorer"], icons=None, styles={"nav-link-selected": {"background-color": "#333333"}})

# --- 5. ROUTING LOGIK ---
if not sel:
    sel = "Oversigt"

# Fejlsikret routing
try:
    if sel == "Oversigt":
        import tools.players as pl
        pl.vis_side(dp["players"])
    elif sel == "Forecast":
        import tools.squad as sq
        sq.vis_side(dp["players"])
    elif sel == "Spillerstats":
        import tools.stats as st_tool
        st_tool.vis_side(dp["players"], dp["playerstats"])
    elif sel == "Top 5":
        import tools.top5 as t5
        t5.vis_side(dp["players"], dp["playerstats"])
    elif sel == "Afslutninger":
        import tools.player_shots as ps
        ps.vis_side(dp["shotevents"], dp["players"], dp["hold_map"])
    elif sel == "Modstanderanalyse":
        import tools.modstanderanalyse as ma
        ma.vis_side(dp["team_matches"], dp["hold_map"], dp["events"])
    elif sel == "Database":
        import tools.scout_db as sdb
        import importlib
        importlib.reload(sdb) 
        sdb.vis_side(dp["scouting"], dp["players"], dp["playerstats"], dp["player_career"])
    elif sel == "Scoutrapport":
        import tools.scout_input as si
        si.vis_side(dp)
    elif sel == "Sammenligning":
        import tools.comparison as comp
        comp.vis_side(
        spillere=dp["players"], 
        player_events=dp["playerstats"], 
        df_scout=dp["scouting"])
    elif sel == "Brugerstyring":
        import tools.admin as adm
        adm.vis_side()
    elif sel == "Schema Explorer":
        import tools.snowflake_test as stest
        stest.vis_side()
except Exception as e:
    st.error(f"Fejl ved indlæsning af siden '{sel}': {e}")
