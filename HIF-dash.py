import os
import sys
import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd

# Sikr at vi kan finde vores egne moduler
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.data_load import get_data_package, load_snowflake_query
from data.users import get_users

# --- 1. KONFIGURATION ---
HIF_LOGO_URL = "https://cdn5.wyscout.com/photos/team/public/2659_120x120.png"

st.set_page_config(
    page_title="HIF Data Hub", 
    layout="wide", 
    page_icon=HIF_LOGO_URL
)

st.markdown(f"""
    <style>
        .block-container {{ padding-top: 1rem !important; padding-bottom: 0rem !important; }}
        header {{ visibility: hidden; height: 0px; }}
        .custom-header {{
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            height: 60px;
            background-color: #cc0000; 
            color: white; 
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        button[data-baseweb="tab"] {{ font-size: 14px; }}
        button[data-baseweb="tab"][aria-selected="true"] {{ color: #cc0000 !important; border-bottom-color: #cc0000 !important; }}
    </style>
""", unsafe_allow_html=True)

# --- 2. LOGIN SYSTEM ---
USER_DB = get_users()
if "logged_in" not in st.session_state: 
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown(f"<div style='text-align: center;'><img src='{HIF_LOGO_URL}' width='120'></div>", unsafe_allow_html=True)
        with st.form("login"):
            u = st.text_input("BRUGER").lower().strip()
            p = st.text_input("KODE", type="password")
            if st.form_submit_button("LOG IND"):
                if u in USER_DB and USER_DB[u]["pass"] == p:
                    st.session_state["logged_in"] = True
                    st.session_state["user"] = u
                    st.session_state["role"] = USER_DB[u]["role"] 
                    st.rerun()
                else:
                    st.error("Ugyldig bruger eller kode")
    st.stop()

# --- 3. DATA LOADING ---
if "dp" not in st.session_state:
    with st.spinner("Henter systemdata..."):
        st.session_state["dp"] = get_data_package()

dp = st.session_state["dp"]

# --- 4. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.markdown(f"<div style='text-align: center; padding-bottom: 10px;'><img src='{HIF_LOGO_URL}' width='60'></div>", unsafe_allow_html=True)
    
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
        sel = option_menu(None, options=["Holdoversigt", "Spillerstats", "Kampe"], 
                         styles={"nav-link-selected": {"background-color": "#cc0000"}})
    elif hoved_omraade == "SCOUTING":
        sel = option_menu(None, options=["Scoutrapport", "Database", "Sammenligning"], 
                         styles={"nav-link-selected": {"background-color": "#cc0000"}})
    elif hoved_omraade == "ADMIN":
        sel = option_menu(None, options=["Rå Data Explorer", "Brugerstyring", "System Log"], 
                         styles={"nav-link-selected": {"background-color": "#333333"}})

# --- 5. ROUTING LOGIK ---
if not sel: 
    sel = "Oversigt"

try:
    # --- TRUPPEN SEKTION ---
    if hoved_omraade == "TRUPPEN":
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

    # --- HIF ANALYSE SEKTION ---
    elif hoved_omraade == "HIF ANALYSE":
        if sel == "Afslutninger":
            import tools.player_shots as ps
            ps.vis_side(dp)
        elif sel == "Modstanderanalyse":
            import tools.modstanderanalyse as ma
            ma.vis_side(dp["opta_matches"], dp["logo_map"])
        elif sel == "Scatterplots":
            import tools.scatter as sc
            sc.vis_side(dp["team_stats_full"])

    # --- BETINIA LIGAEN SEKTION ---
    elif hoved_omraade == "BETINIA LIGAEN":
        if sel == "Holdoversigt":
            import tools.test.test_teams as tt
            tt.vis_side(dp)
        elif sel == "Spillerstats":
            import tools.test.test_players as tp
            tp.vis_side(dp["players"], dp["playerstats"])
        elif sel == "Kampe":
            import tools.test.test_matches as tm
            tm.vis_side(dp)

    # --- SCOUTING SEKTION ---
    elif hoved_omraade == "SCOUTING":
        if sel == "Scoutrapport":
            import tools.scout_input as si
            si.vis_side(dp)
        elif sel == "Database":
            import tools.scout_db as sdb
            sdb.vis_side(dp.get("scouting_image"), dp["players"], dp["playerstats"], dp["player_career"])
        elif sel == "Sammenligning":
            import tools.comparison as comp
            comp.vis_side(dp["players"], dp["playerstats"], dp.get("scouting_image"), dp["player_career"], dp.get("season_filter"))

    # --- ADMIN SEKTION ---
    elif hoved_omraade == "ADMIN":
        if sel == "Rå Data Explorer":
            st.title("🛰️ Rå Data Explorer")
            st.write("### Opta Matches", dp["opta_matches"].head(50))
            st.write("### Opta Stats", dp.get("opta_raw_stats", pd.DataFrame()).head(50))
        elif sel == "Brugerstyring":
            import tools.admin as adm
            adm.vis_side()
        elif sel == "System Log":
            import tools.admin as adm
            adm.vis_log()

except Exception as e:
    st.error(f"Kunne ikke indlæse siden '{sel}': {e}")
