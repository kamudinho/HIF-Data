import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
from data.data_load import get_data_package, load_snowflake_query 
from data.users import get_users

st.set_page_config(page_title="HIF Data Hub", layout="wide")

# --- LOGIN ---
USER_DB = get_users()
if "logged_in" not in st.session_state: 
    st.session_state["logged_in"] = False
    st.session_state["user"] = None

if not st.session_state["logged_in"]:
    # ... (behold din login-boks kode her) ...
    st.stop()

# --- DATA LOADING ---
if "data_package" not in st.session_state:
    with st.spinner("Lynhurtig opstart..."):
        st.session_state["data_package"] = get_data_package()

dp = st.session_state["data_package"]

# --- SIDEBAR ---
with st.sidebar:
    user_info = USER_DB.get(st.session_state["user"], {})
    hoved_options = user_info.get("access", ["TRUPPEN", "ANALYSE", "SCOUTING"])
    hoved_omraade = option_menu(None, options=hoved_options, default_index=0)
    
    if hoved_omraade == "TRUPPEN":
        sel = option_menu(None, options=["Oversigt", "Forecast", "Spillerstats"])
    elif hoved_omraade == "ANALYSE":
        sel = option_menu(None, options=["Afslutninger", "Modstanderanalyse", "Scatterplots"])
    elif hoved_omraade == "SCOUTING":
        sel = option_menu(None, options=["Scoutrapport", "Database", "Sammenligning"])

# --- 5. ROUTING LOGIK (Fuld liste genindsat) ---
if not sel:
    sel = "Oversigt"

try:
    # --- TRUPPEN ---
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

    # --- ANALYSE ---
    elif sel == "Afslutninger":
        import tools.player_shots as ps
        ps.vis_side(None, dp["players"], dp["hold_map"]) # Lazy loading
    elif sel == "Modstanderanalyse":
        import tools.modstanderanalyse as ma
        ma.vis_side(dp["team_matches"], dp["hold_map"], None) # Lazy loading
    elif sel == "Scatterplots":
        import tools.scatter as sc
        sc.vis_side(dp["team_scatter"])

    # --- SCOUTING ---
    elif sel == "Scoutrapport":
        import tools.scout_input as si
        si.vis_side(dp)
    elif sel == "Database":
        import tools.scout_db as sdb
        sdb.vis_side(dp["scouting"], dp["players"], dp["playerstats"], None) # Lazy loading
    elif sel == "Sammenligning":
        import tools.comparison as comp
        # Vi sender None til player_seasons, så siden selv henter historik on-demand
        comp.vis_side(dp["players"], dp["playerstats"], dp["scouting"], None, dp["season_filter"])

    # --- ADMIN ---
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
