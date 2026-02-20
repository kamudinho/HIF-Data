import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
from data.data_load import get_data_package, load_snowflake_query 
from data.users import get_users

# --- 1. KONFIGURATION ---
st.set_page_config(page_title="HIF Data Hub", layout="wide")

# (Her kan du indsætte dine CSS styles hvis du ønsker det)

# --- 2. LOGIN SYSTEM ---
USER_DB = get_users()
if "logged_in" not in st.session_state: 
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<div style='text-align: center;'><img src='https://cdn5.wyscout.com/photos/team/public/2659_120x120.png' width='120'></div>", unsafe_allow_html=True)
        with st.form("login"):
            u = st.text_input("BRUGER").lower().strip()
            p = st.text_input("KODE", type="password")
            if st.form_submit_button("LOG IND", width="stretch"):
                if u in USER_DB and USER_DB[u]["pass"] == p:
                    st.session_state["logged_in"] = True
                    st.session_state["user"] = u
                    # FIX: Gem rollen så Admin-siden kan se hvem du er
                    st.session_state["role"] = USER_DB[u]["role"] 
                    st.rerun()
                else:
                    st.error("Ugyldig bruger eller kode")
    st.stop()

# --- 3. DATA LOADING ---
if "data_package" not in st.session_state:
    with st.spinner("Henter systemdata..."):
        st.session_state["data_package"] = get_data_package()

dp = st.session_state["data_package"]

# --- 4. SIDEBAR NAVIGATION ---
with st.sidebar:
    user_info = USER_DB.get(st.session_state["user"], {})
    hoved_options = user_info.get("access", ["TRUPPEN", "ANALYSE", "SCOUTING", "ADMIN"])
    
    hoved_omraade = option_menu(None, options=hoved_options, default_index=0)
    
    sel = ""
    if hoved_omraade == "TRUPPEN":
        sel = option_menu(None, options=["Oversigt", "Forecast", "Spillerstats", "Top 5"], styles={"nav-link-selected": {"background-color": "#cc0000"}})
    elif hoved_omraade == "ANALYSE":
        sel = option_menu(None, options=["Afslutninger", "Modstanderanalyse", "Scatterplots"], styles={"nav-link-selected": {"background-color": "#cc0000"}})
    elif hoved_omraade == "SCOUTING":
        sel = option_menu(None, options=["Scoutrapport", "Database", "Sammenligning"], styles={"nav-link-selected": {"background-color": "#cc0000"}})
    elif hoved_omraade == "ADMIN":
        sel = option_menu(None, options=["Brugerstyring", "System Log", "Schema Explorer"], styles={"nav-link-selected": {"background-color": "#333333"}})

# --- 5. ROUTING LOGIK ---
if not sel: sel = "Oversigt"

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
        comp.vis_side(dp["players"], dp["playerstats"], dp["scouting"], None, dp.get("season_filter"))

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
    st.error(f"⚠️ Kunne ikke indlæse siden '{sel}': {e}")
