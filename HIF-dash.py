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
    
    # 1. Alle hovedområder (Rækkefølgen i menuen)
    alle_omraader = ["TRUPPEN", "HIF ANALYSE", "BETINIA LIGAEN", "SCOUTING", "ADMIN"]
    
    # 2. Hent brugerens restriktioner (hvis ingen findes, er listen tom = alt synligt)
    user_info = USER_DB.get(st.session_state["user"], {})
    restriktioner = user_info.get("restricted", [])
    
    # 3. Byg menuen ved at fjerne de låste områder
    synlige_options = [o for o in alle_omraader if o not in restriktioner]
    
    # 4. Hovedmenu (Uden ikoner, så de rene pile/linjer bevares)
    hoved_omraade = option_menu(
        None, 
        options=synlige_options, 
        default_index=0,
        styles={
            "nav-link-selected": {"background-color": "#0056a3"},
            "nav-link": {"font-weight": "400"} # Holder teksten ren
        }
    )
    
    st.markdown("---")
    
    # 5. Undermenuer (Præcis som du har dem nu)
    sel = ""
    if hoved_omraade == "TRUPPEN":
        sel = option_menu(None, options=["Oversigt", "Forecast", "Spillerstats", "Top 5"], 
                         styles={"nav-link-selected": {"background-color": "#cc0000"}})
    elif hoved_omraade == "HIF ANALYSE":
        sel = option_menu(None, options=["Afslutninger", "Modstanderanalyse", "Scatterplots"], 
                         styles={"nav-link-selected": {"background-color": "#cc0000"}})
    elif hoved_omraade == "BETINIA LIGAEN":
        # Opdateret med dine nye test-sider
        sel = option_menu(None, options=["Test Kampe", "Test Spillerstats", "Test Holdoversigt"], 
                         styles={"nav-link-selected": {"background-color": "#cc0000"}})
    elif hoved_omraade == "SCOUTING":
        sel = option_menu(None, options=["Scoutrapport", "Database", "Sammenligning"], 
                         styles={"nav-link-selected": {"background-color": "#cc0000"}})
    elif hoved_omraade == "ADMIN":
        sel = option_menu(None, options=["Brugerstyring", "System Log", "Schema Explorer"], 
                         styles={"nav-link-selected": {"background-color": "#333333"}})

# --- 5. ROUTING LOGIK ---
if not sel: 
    sel = "Oversigt"

# Funktion til sikker hentning af Snowflake data uden at crashe siden
def safe_load_stats():
    if dp.get("playerstats") is None:
        try:
            # Vi tjekker om vi overhovedet har filtrene klar før vi kalder Snowflake
            comp_f = dp.get("comp_filter", [])
            seas_f = dp.get("season_filter", [])
            
            with st.spinner("Henter live stats fra Snowflake..."):
                dp["playerstats"] = load_snowflake_query("playerstats", comp_f, seas_f)
        except Exception as e:
            st.warning("⚠️ Snowflake stats kunne ikke hentes. Viser kun lokale data (CSV).")
            dp["playerstats"] = pd.DataFrame() # Fortsæt med tom dataframe

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
            safe_load_stats()
            import tools.stats as st_tool
            st_tool.vis_side(dp["players"], dp["playerstats"])
        elif sel == "Top 5":
            safe_load_stats()
            import tools.top5 as t5
            t5.vis_side(dp["players"], dp["playerstats"])

    # --- HIF ANALYSE ---
    elif hoved_omraade == "HIF ANALYSE":
        # Her kan du tilføje safe_load_stats() hvis de skal bruge Snowflake-data
        if sel == "Afslutninger":
            import tools.player_shots as ps
            ps.vis_side(dp) # Linker til din analyse-fil
        elif sel == "Modstanderanalyse":
            import tools.modstanderanalyse as ma
            ma.vis_side(dp) # Linker til din modstander-fil
        elif sel == "Scatterplots":
            safe_load_stats()
            import tools.scatters as sc
            sc.vis_side(dp["playerstats"])

    # --- BETINIA LIGAEN ---
    elif hoved_omraade == "BETINIA LIGAEN":
        if sel == "Test Kampe":
            import tools.test.test_matches as tm
            # Vi antager her at du har en funktion i filen der hedder vis_side()
            tm.vis_side() 
            
        elif sel == "Test Spillerstats":
            import tools.test.test_players as tp
            tp.vis_side()
            
        elif sel == "Test Holdoversigt":
            import tools.test.test_teams as tt
            tt.vis_side()

    # --- SCOUTING ---
    elif hoved_omraade == "SCOUTING":
        if sel == "Scoutrapport":
            import tools.scout_input as si
            si.vis_side(dp)
        elif sel == "Database":
            safe_load_stats()
            import tools.scout_db as sdb
            sdb.vis_side(dp["scouting"], dp["players"], dp["playerstats"], None)
        elif sel == "Sammenligning":
            safe_load_stats()
            import tools.comparison as comp
            comp.vis_side(dp["players"], dp["playerstats"], dp["scouting"], None, dp["season_filter"])

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
    st.info("Dette skyldes ofte manglende filer i 'tools' mappen eller Snowflake-rettigheder.")
