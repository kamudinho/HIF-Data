import os
import sys
import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd

# Sikr at vi kan finde vores egne moduler
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# IMPORTS
import data.HIF_load as hif_load
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

# Centraliseret CSS (Renset for UTF-8 fejl og dobbelt tags)
st.markdown(f"""
    <style>
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header {{visibility: hidden;}} 
        
        .block-container {{ padding-top: 0.5rem !important; }}
        [data-testid="stSidebarUserContent"] {{ padding-top: 0.5rem !important; }}
        [data-testid="stSidebarNav"] {{ display: none; }}
        
        /* Top-ikoner styling */
        .stButton > button {{
            border: none !important;
            background-color: transparent !important;
            color: #31333F !important;
            font-size: 22px !important;
            padding: -10px !important;
            width: 100% !important;
        }}
        .stButton > button:hover {{
            color: {HIF_ROD} !important;
        }}
        
        /* Indrammet undermenu */
        .sub-nav-container {{
            border: 1px solid #ddd !important;
            border-radius: 8px !important;
            padding: 4px !important;
            margin-top: 20px !important;
        }}

        .hif-header-container {{
            background-color: {HIF_ROD};
            height: 50px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 4px;
            margin-bottom: 15px;
        }}
        .hif-header-text {{
            color: white !important;
            text-transform: uppercase;
            letter-spacing: 2px;
            font-weight: 600;
            margin: 0;
        }}
    </style>
""", unsafe_allow_html=True)

def render_hif_header(titel):
    st.markdown(f'<div class="hif-header-container"><p class="hif-header-text">{titel}</p></div>', unsafe_allow_html=True)

# --- 2. LOGIN SYSTEM ---
USER_DB = get_users()
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    st.markdown(f"""
        <style>
            [data-testid="stAppViewContainer"] {{ padding: 0 !important; }}
            [data-testid="stHeader"] {{ display: none; }}
            .stApp {{ background: linear-gradient(to right, white 50%, transparent 50%); }}
            [data-testid="stAppViewContainer"]::before {{
                content: ""; position: fixed; right: 0; top: 0; width: 50%; height: 100vh;
                background-image: url('https://www.tv2kosmopol.dk/img/asset/aW1hZ2VzLzIwMjMvMDUvMjgvMjAyMzA1MjctMTUxMTM3LWwtMTkyMHgxNDg1d2UuanBn/20230527-151137-l-1920x1485we.jpg?fm=jpg&w=1920&h=862.92134831461&s=69869f3269bf8ebfa06b2b56bcf20a2e');
                background-size: cover; background-position: center; opacity: 0.7; 
            }}
        </style>
    """, unsafe_allow_html=True)
    
    col1, _ = st.columns([1, 1])
    with col1:
        st.markdown("<br><br><br><br><br><br>", unsafe_allow_html=True)
        _, center, _ = st.columns([1, 2, 1])
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
                        st.rerun()
                    else: st.error("Ugyldig login")
    st.stop()

# --- 3. SIDEBAR NAVIGATION ---
with st.sidebar:
    # Tvinger indholdet helt op i toppen og definerer linje-stilen
    st.markdown("""
        <style>
            /* Fjern luft i toppen af sidebaren */
            [data-testid="stSidebarUserContent"] { padding-top: 0.5rem !important; }
            
            /* Juster margin på den vandrette linje */
            .custom-hr {
                margin-top: 5px !important;
                margin-bottom: 5px !important;
                opacity: 0.2;
                border: 0;
                border-top: 1px solid #31333F;
            }
        </style>
        <div style="margin-top: -40px;"></div>
    """, unsafe_allow_html=True)

    # --- TOP IKONER (🏠 & 🔄) ---
    icon_col1, icon_col2, icon_col3, icon_col4 = st.columns([1.5, 1, 1, 1.5])
    with icon_col2:
        if st.button("🏠", help="Gå til Forsiden"):
            st.session_state["main_menu_selection"] = "HVIDOVRE IF"
            st.session_state["sub_menu_selection"] = "Forside"
            st.rerun()
    with icon_col3:
        if st.button("🔄", help="Ryd cache"):
            st.cache_data.clear()
            st.rerun()

    # Den tætte linje under top-ikonerne
    st.markdown('<hr class="custom-hr">', unsafe_allow_html=True)

    # --- STYLE DEFINITION FOR MENUER ---
    menu_style = {
        "container": {"padding": "0!important", "background-color": "transparent"},
        "nav-link": {
            "font-size": "14px", 
            "text-align": "left", 
            "margin": "0px", 
            "color": "#31333F",
            "border-radius": "4px"
        },
        "nav-link-selected": {"background-color": HIF_ROD, "color": "white"}
    }

    # --- HOVEDMENU ---
    alle_omraader = ["HVIDOVRE IF", "HOLDANALYSE", "SPILLERANALYSE", "SCOUTING", "TILPASNING", "TESTSIDE", "ADMIN"]
    user_info = USER_DB.get(st.session_state["user"], {})
    restriktioner = [r.lower().strip() for r in user_info.get("restricted", [])]
    synlige_hoved_options = [o for o in alle_omraader if o.lower().strip() not in restriktioner]
    
    if "main_menu_selection" not in st.session_state:
        st.session_state["main_menu_selection"] = synlige_hoved_options[0]

    hoved_omraade = option_menu(
        None, 
        options=synlige_hoved_options, 
        icons=["play-fill"] * len(synlige_hoved_options), 
        default_index=synlige_hoved_options.index(st.session_state["main_menu_selection"]),
        key="main_menu_widget",
        styles=menu_style
    )
    st.session_state["main_menu_selection"] = hoved_omraade

    # Den tætte linje mellem de to menuer
    st.markdown('<hr class="custom-hr">', unsafe_allow_html=True)

    # --- UNDERMENU LOGIK ---
    menu_map = {
        "HVIDOVRE IF": ["Forside", "Oversigt", "Forecast"],
        "HOLDANALYSE": ["Modstanderanalyse", "Ligaoversigt", "Kampoversigt", "Afslutninger", "Fysisk data"],
        "SPILLERANALYSE": ["Spillerprofil", "Charts"],
        "SCOUTING": ["Scoutrapport", "Database", "Emnedatabase", "Sammenligning", "Transfers"],
        "TILPASNING": ["Spillerdata", "Spiller-score", "Standardsituationer"],
        "TESTSIDE": ["1. Div-tilpasning", "Grafer"],
        "ADMIN": ["System Log", "Profil", "Datakatalog", "Konklusion", "Fysisk profil", "Hold: Fysisk profil", "Intern analyse", "Top 5: Spillere", "Ordbog"]
    }

    aktuel_undermenu = [o for o in menu_map.get(hoved_omraade, ["Forside"]) if o.lower().strip() not in restriktioner]
    
    if "sub_menu_selection" not in st.session_state or st.session_state["sub_menu_selection"] not in aktuel_undermenu:
        st.session_state["sub_menu_selection"] = aktuel_undermenu[0]

    # Selve undermenuen
    sel = option_menu(
        None, 
        options=aktuel_undermenu,
        icons=["play-fill"] * len(aktuel_undermenu),
        default_index=aktuel_undermenu.index(st.session_state["sub_menu_selection"]),
        key="sub_menu_widget",
        styles=menu_style
    )
    st.session_state["sub_menu_selection"] = sel

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
            import tools.scouting.comparison as comp
            comp.vis_side(dp["players"], None, None, dp["career"], dp["sql_players"], dp["advanced_stats"])
        elif s == "Transfers":
            import tools.scouting.transfer_input as t_input
            t_input.vis_side()

    elif m == "SPILLERANALYSE":
        if s == "Charts":
            import tools.ligaen.chart as pc
            pc.vis_side()
        elif s == "Spillerprofil":
            import tools.players.player_profile as pp
            pp.vis_side()

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
        elif s == "Fysisk data":
            import tools.ligaen.fysisk as fd_page
            fd_page.vis_side(_get_snowflake_conn())
        elif s == "Modstanderanalyse":
            import tools.ligaen.modstanderanalyse as ma
            ma.vis_side()

    elif m == "TILPASNING":
        if s == "Spillerdata":
            import tools.tilpasning.spiller_tilpasning as tilpasning
            tilpasning.vis_side()
        elif s == "Spiller-score":
            import tools.players.player_score as pscore
            pscore.vis_side()
        elif s == "Standardsituationer":
            import tools.standarder.std_analyse as std
            std.vis_side()

    elif m == "TESTSIDE":
        if s == "1. Div-tilpasning":
            import tools.tilpasning.div_tilpasning as div
            div.vis_side()
        elif s == "Grafer":
            import tools.ligaen.dataviz as dviz
            dviz.vis_side()

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
