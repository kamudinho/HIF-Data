import os
import sys 
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
from data.data_load import get_data_package, load_snowflake_query
from data.users import get_users

# --- 1. KONFIGURATION ---
st.set_page_config(page_title="HIF Data Hub", layout="wide")

st.markdown("""
    <style>
        .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; }
        header { visibility: hidden; height: 0px; }
        h1, h2, h3 { margin: 0 !important; padding: 0 !important; }
        .custom-header {
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            height: 60px;
            background-color: #cc0000; 
            color: white; 
            border-radius: 8px;
            margin-bottom: 20px;
        }
        /* Styling af tabs så de matcher dit røde HIF tema */
        button[data-baseweb="tab"] { font-size: 14px; }
        button[data-baseweb="tab"][aria-selected="true"] { color: #cc0000 !important; border-bottom-color: #cc0000 !important; }
    </style>
""", unsafe_allow_html=True)

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
    st.markdown("<div style='text-align: center; padding-bottom: 10px;'><img src='https://cdn5.wyscout.com/photos/team/public/2659_120x120.png' width='60'></div>", unsafe_allow_html=True)
    
    alle_omraader = ["TRUPPEN", "HIF ANALYSE", "BETINIA LIGAEN", "SCOUTING", "ADMIN"]
    user_info = USER_DB.get(st.session_state["user"], {})
    restriktioner = user_info.get("restricted", [])
    synlige_options = [o for o in alle_omraader if o not in restriktioner]
    
    hoved_omraade = option_menu(
        None, 
        options=synlige_options, 
        default_index=0,
        styles={
            "nav-link-selected": {"background-color": "#0056a3"},
            "nav-link": {"font-weight": "400"}
        }
    )
    
    st.markdown("---")
    
    sel = ""
    if hoved_omraade == "TRUPPEN":
        sel = option_menu(None, options=["Oversigt", "Forecast", "Spillerstats", "Top 5"], 
                         styles={"nav-link-selected": {"background-color": "#cc0000"}})
    elif hoved_omraade == "HIF ANALYSE":
        sel = option_menu(None, options=["Afslutninger", "Modstanderanalyse", "Scatterplots"], 
                         styles={"nav-link-selected": {"background-color": "#cc0000"}})
    elif hoved_omraade == "BETINIA LIGAEN":
        # Disse navne matcher nu de nye tabs-baserede analyseværktøjer
        sel = option_menu(None, options=["Holdoversigt", "Spillerstats", "Kampe"], 
                         styles={"nav-link-selected": {"background-color": "#cc0000"}})
    elif hoved_omraade == "SCOUTING":
        sel = option_menu(None, options=["Scoutrapport", "Database", "Sammenligning"], 
                         styles={"nav-link-selected": {"background-color": "#cc0000"}})
    elif hoved_omraade == "ADMIN":
        sel = option_menu(None, options=["Brugerstyring", "System Log", "Schema Explorer"], 
                         styles={"nav-link-selected": {"background-color": "#333333"}})

# --- 5. ROUTING LOGIK (OPDATERET) ---
if not sel: 
    sel = "Oversigt"

try:
    # --- TRUPPEN ---
    if hoved_omraade == "TRUPPEN":
        if sel == "Oversigt":
            import tools.players as pl
            pl.vis_side(dp["players"])
        elif sel == "Forecast":
            import tools.squad as sq
            sq.vis_side(dp["players"])
        elif sel == "Spillerstats":
            import tools.stats as st_tool
            st_tool.vis_side(dp["players"], load_snowflake_query("playerstats", dp["comp_filter"], dp["season_filter"]))
        elif sel == "Top 5":
            import tools.top5 as t5
            t5.vis_side(dp["players"], load_snowflake_query("playerstats", dp["comp_filter"], dp["season_filter"]))

    # --- HIF ANALYSE ---
    elif hoved_omraade == "HIF ANALYSE":
        if sel == "Afslutninger":
            import tools.player_shots as ps
            ps.vis_side(dp["players"], dp["hold_map"])
        elif sel == "Modstanderanalyse":
            import tools.modstanderanalyse as ma
            df_matches = load_snowflake_query("team_matches", dp["comp_filter"], dp["season_filter"])
            ma.vis_side(df_matches, dp["hold_map"])
        elif sel == "Scatterplots":
            import tools.scatter as sc
            # RET HER: Fra "team_stats" til "team_stats_full"
            df_scatter = load_snowflake_query("team_stats_full", dp["comp_filter"], dp["season_filter"])
            sc.vis_side(df_scatter)

    # --- BETINIA LIGAEN ---
    elif hoved_omraade == "BETINIA LIGAEN":
        if sel == "Holdoversigt":
            import tools.test.test_teams as tt
            # Vi henter data her for at sikre friskhed, men sender det med
            df_for_teams = load_snowflake_query("team_stats_full", dp["comp_filter"], dp["season_filter"])
            tt.vis_side(df_for_teams)
        
        elif sel == "Spillerstats":
            import tools.test.test_players as tp
            # Vi sender hele dp med, så tp kan læse 'playerstats' og 'players'
            tp.vis_side(dp) 
            
        elif sel == "Kampe":
            import tools.test.test_matches as tm
            # tm.vis_side modtager nu hele dp og håndterer selv sorteringen
            tm.vis_side(dp)
            
    # --- SCOUTING ---
    elif hoved_omraade == "SCOUTING":
        if sel == "Scoutrapport":
            import tools.scout_input as si
            # Her sender vi hele 'dp' med, så si.vis_side kan læse dp["sql_players"]
            si.vis_side(dp) 
        elif sel == "Database":
            import tools.scout_db as sdb
            
            # 1. Hent stats
            df_stats = load_snowflake_query("playerstats", dp["comp_filter"], dp["season_filter"])
            
            # 2. Hent karriere-data (tjekkes om det er i session_state)
            if "player_career_data" not in st.session_state:
                with st.spinner("Henter karrierehistorik..."):
                    st.session_state["player_career_data"] = load_snowflake_query("player_career", dp["comp_filter"], dp["season_filter"])
            
            # 3. Kald modulet - HER SKAL VI BRUGE 'scouting_image' 📸
            sdb.vis_side(
                dp["scouting_image"], # Vi skifter fra dp["scouting"] til dp["scouting_image"]
                dp["players"], 
                df_stats, 
                st.session_state["player_career_data"]
            )
        elif sel == "Sammenligning":
            import tools.comparison as comp
            comp.vis_side(
                dp["players"], 
                load_snowflake_query("playerstats", dp["comp_filter"], dp["season_filter"]), 
                dp["scouting_image"], # Den nye med billeder 🚀
                dp["player_career"],
                dp["season_filter"]
            )
            
    # --- ADMIN ---
    elif hoved_omraade == "ADMIN":
        if sel == "Brugerstyring":
            import tools.admin as adm
            adm.vis_side()
        elif sel == "System Log":
            import tools.admin as adm
            adm.vis_log() 
        elif sel == "Schema Explorer":
            import tools.snowflake_test as stest
            stest.vis_side()

except Exception as e:
    st.error(f"⚠️ Systemfejl på siden '{sel}': {e}")
