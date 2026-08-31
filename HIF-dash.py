import os
import sys
import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd

# Sikr at vi kan finde vores egne moduler
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# IMPORTS
import data.hif_load as hif_load
from data.data_load import _get_snowflake_conn
from data.users import get_users

# --- 1. KONFIGURATION & BRANDING ---
HIF_LOGO_URL = "https://cdn5.wyscout.com/photos/team/public/2659_120x120.png"
HIF_ROD = "#df003b"

st.set_page_config(
    page_title="HIF Data Hub",
    layout="wide",
    page_icon=HIF_LOGO_URL,
    initial_sidebar_state="auto"
)

# Centraliseret CSS
st.markdown(f"""
    <style>
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        
        /* Gør headeren synlig så sidebarknappen dukker op, men gør den helt transparent */
        header {{visibility: visible !important; background: transparent !important;}}
        [data-testid="stHeader"] {{background-color: transparent !important;}}
        [data-testid="stDecoration"] {{display: none;}}
        
        .block-container {{ padding-top: 1.5rem !important; }}
    </style>
""", unsafe_allow_html=True)

def render_hif_header(titel):
    st.markdown(f'''
        <div style="background-color: {HIF_ROD} !important; background: {HIF_ROD} !important; height: 50px; display: flex; align-items: center; justify-content: center; border-radius: 4px; margin-bottom: 15px; width: 100%;">
            <p style="color: white !important; text-transform: uppercase; letter-spacing: 2px; font-weight: 600; margin: 0;">{titel}</p>
        </div>
    ''', unsafe_allow_html=True)

# --- 2. LOGIN SYSTEM ---
USER_DB = get_users()
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    st.markdown(f"""
        <style>
            [data-testid="stAppViewContainer"] {{ padding: 0 !important; }}
            [data-testid="stHeader"] {{ display: none; }}
            .stApp {{ background: linear-gradient(to right, white 35%, transparent 35%); }}
            [data-testid="stAppViewContainer"]::before {{
                content: ""; position: fixed; right: 0; top: 0; width: 65%; height: 100vh;
                background-image: url('https://static1.squarespace.com/static/573c1b7d01dbae9b52cd0936/573d6bdc37013bcc611eefd5/6477a814a3929d7ab0fa3006/1685610754298/GettyImages-1252722215.jpg?format=1500w');
                background-size: cover; background-position: left; opacity: 0.7; 
            }}
        </style>
    """, unsafe_allow_html=True)
    
    col_left, col_right = st.columns([35, 65])
    
    with col_left:
        st.markdown("<br><br><br><br><br>", unsafe_allow_html=True)
        
        _, center, _ = st.columns([0.8, 2.4, 0.8])
        with center:
            st.markdown(f'<div style="display: flex; justify-content: center;"><img src="{HIF_LOGO_URL}" style="width: 70px;"></div>', unsafe_allow_html=True)
            st.markdown("<h2 style='text-align: center;'>HIF Data HUB</h2>", unsafe_allow_html=True)
            with st.form("login"):
                u = st.text_input("BRUGER", placeholder="Brugernavn", label_visibility="collapsed").lower().strip()
                p = st.text_input("KODE", type="password", placeholder="Adgangskode", label_visibility="collapsed")
                if st.form_submit_button("LOG IND", use_container_width=True):
                    if u in USER_DB and USER_DB[u]["pass"] == p:
                        st.session_state["logged_in"] = True
                        st.session_state["user"] = u

                        # --- LOGNING: login ---
                        try:
                            import tools.admin_page.admin as admin
                            admin.save_action_log(u, "Login", "HIF Data Hub")
                        except Exception as log_e:
                            st.warning(f"Login lykkedes, men kunne ikke skrive til log: {log_e}")

                        st.rerun()
                    else: st.error("Ugyldig login")
    st.stop()

# --- 3. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.markdown("""
        <style>
            /* Fjerner scrollbar og tvinger layout */
            [data-testid="stSidebarUserContent"] {
                padding-top: 1rem !important;
                overflow: hidden !important; 
                display: flex;
                flex-direction: column;
                height: 98vh; 
            }
            .nav-wrapper { flex-grow: 1; }
            .custom-hr {
                margin: 5px 0px !important;
                opacity: 0.2;
                border: 0;
                border-top: 1px solid #31333F;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="nav-wrapper">', unsafe_allow_html=True)

    menu_style = {
        "container": {"padding": "0!important", "background-color": "transparent"},
        "nav-link": {"font-size": "14px", "text-align": "left", "margin": "0px", "color": "#31333F", "border-radius": "4px"},
        "nav-link-selected": {"background-color": HIF_ROD, "color": "white"}
    }

    # HOVEDMENU
    alle_omraader = ["HVIDOVRE IF", "HOLDANALYSE", "SPILLERANALYSE", "FYSISK DATA", "SCOUTING", "TILPASNING", "TESTSIDE", "ADMIN"]
    user_info = USER_DB.get(st.session_state["user"], {})
    restriktioner = [r.lower().strip() for r in user_info.get("restricted", [])]
    synlige_hoved_options = [o for o in alle_omraader if o.lower().strip() not in restriktioner]
    
    if "main_menu_selection" not in st.session_state:
        st.session_state["main_menu_selection"] = synlige_hoved_options[0]

    hoved_omraade = option_menu(
        None, options=synlige_hoved_options, 
        icons=["play-fill"] * len(synlige_hoved_options), 
        default_index=synlige_hoved_options.index(st.session_state["main_menu_selection"]),
        key="main_menu_widget", styles=menu_style
    )
    st.session_state["main_menu_selection"] = hoved_omraade

    st.markdown('<hr class="custom-hr">', unsafe_allow_html=True)

    # UNDERMENU LOGIK
    menu_map = {
        "HVIDOVRE IF": ["Forside"],
        "HOLDANALYSE": ["Modstanderanalyse", "Ligaoversigt", "Kampoversigt", "Kampudvikling", "Afslutninger", "Målsekvenser", "Grafer"],
        "SPILLERANALYSE": ["Spilleraktioner", "Spiller-stats", "Spiller-profil", "Spilleroversigt", "Spillerprofil"],
        "FYSISK DATA": ["Fysisk data"],
        "SCOUTING": ["Scoutrapport", "Database", "Emnedatabase", "Sammenligning", "Transfers", "Top10-scouting"],
        "TILPASNING": ["Spillerdata", "Spiller-score", "Standardsituationer", "Model"],
        "TESTSIDE": ["Performance", "Winning Performance", "1. Div-tilpasning", "Charts", "Oversigt", "Forecast"],
        "ADMIN": ["System Log", "Profil", "Datakatalog", "Konklusion", "Fysisk profil", "Hold: Fysisk profil", "Intern analyse", "Top 5: Spillere", "Ordbog"]
    }
    
    aktuel_undermenu = [o for o in menu_map.get(hoved_omraade, ["Forside"]) if o.lower().strip() not in restriktioner]
    
    # SIKKERHEDSTJEK: Undgå ValueError ved skift af hovedmenu
    if "sub_menu_selection" not in st.session_state or st.session_state["sub_menu_selection"] not in aktuel_undermenu:
        u_index = 0
    else:
        u_index = aktuel_undermenu.index(st.session_state["sub_menu_selection"])

    sel = option_menu(
        None, options=aktuel_undermenu,
        icons=["play-fill"] * len(aktuel_undermenu),
        default_index=u_index,
        key=f"sub_menu_{hoved_omraade}", 
        styles=menu_style
    )
    st.session_state["sub_menu_selection"] = sel

    # --- LOGNING: faneskift ---
    _nuvaerende_fane = f"{hoved_omraade} -> {sel}"
    if st.session_state.get("_forrige_fane") != _nuvaerende_fane:
        try:
            import tools.admin_page.admin as admin
            admin.save_action_log(st.session_state["user"], "Skiftede fane", _nuvaerende_fane)
        except Exception as log_e:
            st.warning(f"Kunne ikke skrive faneskift til log: {log_e}")
        st.session_state["_forrige_fane"] = _nuvaerende_fane

    st.markdown('</div>', unsafe_allow_html=True) 

    # BUND-SEKTION
    st.markdown('<hr class="custom-hr">', unsafe_allow_html=True)
    if st.button("Ryd cache", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- 4. DATA LOADING & RENDERING ---
render_hif_header(f"{st.session_state['main_menu_selection']}  |  {st.session_state['sub_menu_selection'].upper()}")

try:
    s = st.session_state["sub_menu_selection"]
    m = st.session_state["main_menu_selection"]

    if m == "HVIDOVRE IF":
        if s == "Forside":
            import HIF_head as fh
            fh.vis_side()
        else:
            dp_quick = hif_load.get_squad_only()
            if s == "Oversigt":
                import tools.truppen.players as pl
                pl.vis_side(dp_quick["players"])
            elif s == "Forecast":
                import tools.truppen.squad as sq
                sq.vis_side(dp_quick["players"])

    elif m == "SCOUTING":
        dp = hif_load.get_scouting_package()
        if s == "Scoutrapport":
            import tools.scouting.scout_input as si
            si.vis_side(dp)
        elif s == "Database":
            import tools.scouting.scout_db as sdb
            sdb.vis_side(dp["scout_reports"], dp["players"], dp["sql_players"], dp["career"])
        elif s == "Emnedatabase":
            import tools.scouting.emne_db as edb
            edb.vis_side()
        elif s == "Sammenligning":
            import tools.scouting.sammenligning as comp
            comp.vis_side(dp["players"], None, dp["wyscout_players"], dp["career"], dp["sql_players"], dp["advanced_stats"], dp.get("primaer_positioner"))
        elif s == "Top10-scouting":
            import tools.scouting.top10_scouting as t10
            t10.vis_side(dp.get("advanced_stats"), dp.get("primaer_positioner"))
        elif s == "Transfers":
            import tools.scouting.transfer_input as t_input
            t_input.vis_side()

    elif m == "SPILLERANALYSE":
        if s == "Spillerprofil":
            import tools.players.player_profile as pp
            pp.vis_side()
        elif s == "Spilleroversigt":
            import tools.players.player_rank as pr
            pr.vis_side()
        elif s == "Målsekvenser":
            import tools.hifanalyse.sequences as ms
            ms.vis_side()
        elif s == "Spilleraktioner":
            import tools.players.player_actions as pa
            pa.vis_side()
        elif s == "Spiller-stats":
            import tools.players.player_stats as ps
            ps.vis_side()
        elif s == "Spiller-profil":
            import tools.players.player_profile2 as pp2
            pp2.vis_side()

    elif m == "FYSISK DATA":
        if s == "Charts":
            import tools.ligaen.chart as pc
            pc.vis_side()
        elif s == "Fysisk data":
            import tools.ligaen.fysisk as fd_page
            fd_page.vis_side(_get_snowflake_conn())


    elif m == "HOLDANALYSE":
        if s == "Ligaoversigt":
            import tools.ligaen.test_teams as tt
            tt.vis_side()
        elif s == "Kampoversigt":
            import tools.ligaen.test_matches as tm
            tm.vis_side()
        elif s == "Afslutninger":
            import tools.ligaen.leagueshots as ls
            ls.vis_side()
        elif s == "Modstanderanalyse":
            import tools.ligaen.modstanderanalyse as ma
            ma.vis_side()
        elif s == "Grafer":
            import tools.ligaen.dataviz as dviz
            dviz.vis_side()
        elif s == "Målsekvenser":
            import tools.ligaen.sequences as ms
            ms.vis_side()
        elif s == "Kampudvikling":
            import tools.ligaen.kampudvikling as ku
            ku.vis_side()

    elif m == "TILPASNING":
        if s == "Spillerdata":
            import tools.tilpasning.spiller_tilpasning as tilpasning
            tilpasning.vis_side()
        elif s == "Spiller-score":
            import tools.players.player_score as pscore
            pscore.vis_side()
        elif s == "Standardsituationer":
            import tools.standarder.setpieces as std
            std.vis_side()

    elif m == "TESTSIDE":
        if s == "1. Div-tilpasning":
            import tools.tilpasning.div_tilpasning as div
            div.vis_side()
        elif s == "Grafer":
            import tools.ligaen.dataviz as dviz
            dviz.vis_side()
        elif s == "Winning Performance":
            import tools.analyse.winning_performance as wp
            wp.vis_side()
        elif s == "Performance":
            import tools.analyse.baseline_performance as bp
            bp.vis_side()
        elif s == "Model":
            import tools.ligaen.model as xg
            xg.vis_side()

    elif m == "ADMIN":
        if s == "System Log":
            import tools.admin_page.admin as admin
            admin.vis_log()
        elif s == "Profil":
            import tools.admin_page.profil as profil
            profil.vis_side({})
        elif s == "Konklusion":
            import tools.analyse.konklusion as kon
            kon.vis_side()
        elif s == "Datakatalog":
            import tools.admin_page.data_katalog as dk
            dk.vis_side(hif_load._get_snowflake_conn())
        elif s == "Fysisk profil":
            import tools.players.fysisk_player as fp
            fp.vis_side()
        elif s == "Hold: Fysisk profil":
            import tools.ligaen.hold_fysisk as hf
            hf.vis_side()
        elif s == "Intern analyse":
            import tools.admin_page.intern_modstanderanalyse as im
            im.vis_side()
        elif s == "Top 5: Spillere":
            import tools.players.top_players as tp
            tp.vis_side()
        elif s == "Ordbog":
            import utils.ordbog as ob
            ob.vis_side()

except Exception as e:
    st.error(f"Fejl ved indlæsning: {e}")
