#HIF-dash.py
import os
import sys
import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd

# Sikr at vi kan finde vores egne moduler
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# NYE IMPORTS (Splitte data-loads)
import data.HIF_load as hif_load
from data.data_load import _get_snowflake_conn, parse_xg, load_local_players
import data.analyse_load as analyse_load
from data.users import get_users

# --- 1. KONFIGURATION & BRANDING ---
HIF_LOGO_URL = "https://cdn5.wyscout.com/photos/team/public/2659_120x120.png"
HIF_ROD = "#df003b"
HIF_GULD = "#b8860b"

st.set_page_config(
    page_title="HIF Dataanalyse",
    layout="wide",
    page_icon=HIF_LOGO_URL
)

# Centraliseret CSS
st.markdown(f"""
    <style>
        .block-container {{ padding-top: 0.5rem !important; padding-bottom: 0rem !important; }}
        header {{ visibility: hidden; height: 0px; }}
        .hif-header-container {{
            background-color: {HIF_ROD};
            height: 50px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 4px;
            margin-bottom: 15px;
            width: 100%;
            border-bottom: 3px solid {HIF_GULD};
        }}
        .hif-header-text {{
            color: white !important;
            margin: 0 !important;
            text-transform: uppercase;
            letter-spacing: 2px;
            font-size: 1.1rem;
            font-weight: 600;
            font-family: sans-serif;
            line-height: 50px;
        }}
        button[data-baseweb="tab"] {{ font-size: 14px; font-weight: 600; }}
        button[data-baseweb="tab"][aria-selected="true"] {{ 
            color: {HIF_ROD} !important; 
            border-bottom-color: {HIF_ROD} !important; 
        }}
        section[data-testid="stSidebar"] {{ background-color: #f8f9fa; }}
    </style>
""", unsafe_allow_html=True)

def render_hif_header(titel):
    """Genererer den ensartede røde top-bar"""
    st.markdown(f"""
        <div class="hif-header-container">
            <p class="hif-header-text">{titel}</p>
        </div>
    """, unsafe_allow_html=True)

# --- 2. LOGIN SYSTEM ---
USER_DB = get_users()
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown(f"<div style='text-align: center; padding-top: 50px;'><img src='{HIF_LOGO_URL}' width='150'></div>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center;'>HIF DATA HUB</h3>", unsafe_allow_html=True)
        with st.form("login"):
            u = st.text_input("BRUGER").lower().strip()
            p = st.text_input("KODE", type="password")
            if st.form_submit_button("LOG IND", use_container_width=True):
                if u in USER_DB and USER_DB[u]["pass"] == p:
                    st.session_state["logged_in"] = True
                    st.session_state["user"] = u
                    st.session_state["role"] = USER_DB[u]["role"]
                    st.rerun()
                else:
                    st.error("Ugyldig bruger eller kode")
    st.stop()

# --- 3. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.markdown(f"<div style='text-align: center; padding-bottom: 10px;'><img src='{HIF_LOGO_URL}' width='30'></div>", unsafe_allow_html=True)
    
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
        sel = option_menu(None, options=["Oversigt", "Forecast"],
                         styles={"nav-link-selected": {"background-color": HIF_ROD}})
    elif hoved_omraade == "HIF ANALYSE":
        sel = option_menu(None, options=["Spillerperformance", "Afslutninger", "Assistmap", "Modstanderanalyse", "Sekvenser"], # Tilføj denne
                     styles={"nav-link-selected": {"background-color": HIF_ROD}})
    elif hoved_omraade == "BETINIA LIGAEN":
        sel = option_menu(None, options=["Holdoversigt", "Kampe", "Charts", "Afslutninger - liga", "Fysisk data"],
                         styles={"nav-link-selected": {"background-color": HIF_ROD}})
    elif hoved_omraade == "SCOUTING":
        sel = option_menu(None, 
                         options=["Scoutrapport", "Database", "Sammenligning"],
                         styles={"nav-link-selected": {"background-color": HIF_ROD}})
    elif hoved_omraade == "ADMIN":
        sel = option_menu(None, options=["System Log"],
                         styles={"nav-link-selected": {"background-color": "#333333"}})

if not sel:
    sel = "Oversigt"

# --- 4. DATA LOADING & RENDERING ---
render_hif_header(f"{hoved_omraade}  |  {sel.upper()}")

try:
    # SEKTION A: TRUPPEN & SCOUTING (HIF_load - Primært CSV/Wyscout)
    if hoved_omraade in ["TRUPPEN", "SCOUTING"]:
        dp = hif_load.get_scouting_package()
        
        if hoved_omraade == "TRUPPEN":
            # Sørg for at vi sender dp["players"] (din players.csv) ind
            if sel == "Oversigt":
                import tools.truppen.players as pl
                # Her skal vi sikre os, at vi sender DataFrame'en
                pl.vis_side(dp["players"]) 
                
            elif sel == "Forecast":
                import tools.truppen.squad as sq
                # Her skal vi også sende DataFrame'en
                sq.vis_side(dp["players"])
                    
        elif hoved_omraade == "SCOUTING":
            if sel == "Scoutrapport":
                import tools.scouting.scout_input as si
                si.vis_side(dp)
            elif sel == "Database":
                import tools.scouting.scout_db as sdb
                # Vi sender dp["scout_reports"] som det første argument
                sdb.scouting.vis_side(
                    dp["scout_reports"], 
                    dp["players"], 
                    dp["sql_players"], 
                    dp["career"]
                )
            elif sel == "Sammenligning":
                import tools.scouting.comparison as comp
                # Nu sender vi de rigtige data-pakker med:
                comp.vis_side(
                    dp["players"],      # df_spillere
                    None,               # d1 (ikke brugt pt)
                    None,               # d2 (ikke brugt pt)
                    dp["career"],       # career_df
                    dp["sql_players"],   # HER ER BILLEDERNE! (d3)
                    dp["advanced_stats"]
                )

    # SEKTION B: ANALYSE & LIGA (Analyse_load - Primært OPTA)
    elif hoved_omraade in ["HIF ANALYSE", "BETINIA LIGAEN"]:
        # Vi definerer hif_only her: True hvis vi er i analyse, False hvis vi er i ligaen
        is_hif_mode = (hoved_omraade == "HIF ANALYSE")
        dp = analyse_load.get_analysis_package(hif_only=is_hif_mode)
        
        # Gem i session state så tools kan tilgå det
        st.session_state["dp"] = dp
        
        # I din rendering-sektion i main.py:
        if hoved_omraade == "HIF ANALYSE":
            if sel == "Afslutninger":
                import tools.hifanalyse.shotmap as sm
                sm.vis_side(dp)
            elif sel == "Spillerperformance": # Tilføj denne blok
                import tools.hifanalyse.player_analysis as pa
                pa.vis_side(dp)
            elif sel == "Assistmap": # Tilføj denne blok
                import tools.hifanalyse.assistmap as am
                am.vis_side(dp)
            elif sel == "Modstanderanalyse": # Tilføj denne blok
                import tools.hifanalyse.modstanderanalyse as ma
                ma.vis_side(dp)
        
        elif hoved_omraade == "BETINIA LIGAEN":
            if sel == "Holdoversigt":
                import tools.ligaen.test_teams as tt
                tt.vis_side(dp)
            elif sel == "Kampe":
                import tools.ligaen.test_matches as tm
                tm.vis_side(dp)
            elif sel == "Charts":
                import tools.ligaen.chart as pc
                pc.vis_side(dp)
            elif sel == "Afslutninger - liga":
                import tools.ligaen.leagueshots as ls
                ls.vis_side(dp)
            elif sel == "Fysisk data - liga":
                import tools.ligaen.fysisk as fd
                fd.vis_side(dp, run_query)

    elif hoved_omraade == "ADMIN":
        st.info("Systemet kører i modulariseret tilstand.")

except Exception as e:
    st.error(f"Fejl ved indlæsning af {sel}: {e}")
