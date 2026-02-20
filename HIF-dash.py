# HIF-dash.py
import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
from data.data_load import get_data_package, load_snowflake_query 
from data.users import get_users

# --- 1. KONFIGURATION ---
st.set_page_config(page_title="HIF Data Hub", layout="wide")

# --- 2. LOGIN SYSTEM ---
USER_DB = get_users()
if "logged_in" not in st.session_state: 
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("login"):
            u = st.text_input("BRUGER").lower().strip()
            p = st.text_input("KODE", type="password")
            if st.form_submit_button("LOG IND", width="stretch"):
                if u in USER_DB and USER_DB[u]["pass"] == p:
                    st.session_state["logged_in"] = True
                    st.session_state["user"] = u
                    st.rerun()
    st.stop()

# --- 3. DATA LOADING ---
if "data_package" not in st.session_state:
    st.session_state["data_package"] = get_data_package()

dp = st.session_state["data_package"]

# --- 4. SIDEBAR NAVIGATION ---
with st.sidebar:
    user_info = USER_DB.get(st.session_state["user"], {})
    hoved_options = user_info.get("access", ["TRUPPEN", "ANALYSE", "SCOUTING", "ADMIN"])
    
    hoved_omraade = option_menu(
        menu_title=None, 
        options=hoved_options, 
        default_index=0,
        styles={"nav-link-selected": {"background-color": "#003366"}}
    )    
    
    # Undermenuer
    if hoved_omraade == "TRUPPEN":
        sel = option_menu(None, options=["Oversigt", "Forecast", "Spillerstats", "Top 5"], default_index=0)
    elif hoved_omraade == "ANALYSE":
        sel = option_menu(None, options=["Afslutninger", "Modstanderanalyse", "Scatterplots"], default_index=0)
    elif hoved_omraade == "SCOUTING":
        sel = option_menu(None, options=["Scoutrapport", "Database", "Sammenligning"], default_index=0)
    elif hoved_omraade == "ADMIN":
        sel = option_menu(None, options=["Brugerstyring", "System Log", "Schema Explorer"], default_index=0)
    else:
        sel = "Oversigt"

# --- 5. ROUTING LOGIK ---
try:
    # TRUPPEN
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

    # ANALYSE
    elif sel == "Afslutninger":
        import tools.player_shots as ps
        ps.vis_side(None, dp["players"], dp["hold_map"])
    elif sel == "Modstanderanalyse":
        import tools.modstanderanalyse as ma
        ma.vis_side(dp["team_matches"], dp["hold_map"], None)
    elif sel == "Scatterplots":
        import tools.scatter as sc
        sc.vis_side(dp["team_scatter"])

    # SCOUTING
    elif sel == "Scoutrapport":
        import tools.scout_input as si
        si.vis_side(dp)
    elif sel == "Database":
        import tools.scout_db as sdb
        sdb.vis_side(dp["scouting"], dp["players"], dp["playerstats"], None)
    elif sel == "Sammenligning":
        import tools.comparison as comp
        comp.vis_side(dp["players"], dp["playerstats"], dp["scouting"], None, dp["season_filter"])

    # ADMIN (Her er de!)
    elif sel == "Brugerstyring":
        import tools.admin as adm
        adm.vis_side()
    elif sel == "System Log":
        import tools.admin as adm
        adm.vis_log() 
    elif sel == "Schema Explorer":
        import tools.snowflake_test as stest
        stest.vis_side()

except Exception as e:
    st.error(f"Fejl ved indlæsning af siden '{sel}': {e}")
