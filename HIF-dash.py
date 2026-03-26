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

# Centraliseret CSS
st.markdown(f"""
    <style>
        .block-container {{ padding-top: 0.5rem !important; }}
        [data-testid="stHeader"] {{ background: rgba(0,0,0,0); }}
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
    # Aggressiv CSS til at tvinge layoutet helt ud til kanten
    st.markdown(f"""
        <style>
            /* Fjern Streamlits standard margin/padding overalt */
            [data-testid="stAppViewContainer"] {{
                padding: 0 !important;
            }}
            [data-testid="stHeader"] {{
                display: none;
            }}
            .main .block-container {{
                padding: 0 !important;
                max-width: 100% !important;
            }}
            
            /* Skab en split-skærm baggrund */
            .stApp {{
                background: linear-gradient(to right, 
                    white 0%, white 50%, 
                    transparent 50%, transparent 100%);
            }}

            /* Den højre side med billedet (Full bleed) */
            [data-testid="stAppViewContainer"]::before {{
                content: "";
                position: fixed;
                right: 0;
                top: 0;
                width: 50%;
                height: 100vh;
                background-image: url('https://www.tv2kosmopol.dk/img/asset/aW1hZ2VzLzIwMjMvMDUvMjgvMjAyMzA1MjctMTUxMTM3LWwtMTkyMHgxNDg1d2UuanBn/20230527-151137-l-1920x1485we.jpg?fm=jpg&w=1920&h=862.92134831461&s=69869f3269bf8ebfa06b2b56bcf20a2e');
                background-size: cover;
                background-position: center;
                z-index: 0;
                
                /* Tilføj opacity her (0.0 er helt væk, 1.0 er fuld synlig) */
                opacity: 0.7; 
            }}
            
            /* Sørg for at login-form lander korrekt til venstre */
            .login-box {{
                max-width: 320px;
                margin-top: 15vh;
                text-align: center;
            }}
            
            /* Fjern rammen om selve formen */
            div[data-testid="stForm"] {{
                border: none !important;
                padding: 0 !important;
            }}
        </style>
    """, unsafe_allow_html=True)

    # Vi bruger kun den venstre kolonne til indhold (da den højre er dækket af CSS-billedet)
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Centrerer indholdet vertikalt
        st.markdown("<br><br><br><br><br><br><br>", unsafe_allow_html=True)
        
        # Vi bruger en række med 3 kolonner [1, 2, 1] for at tvinge indholdet i midten
        left_pad, center_content, right_pad = st.columns([1, 2, 1])
        
        with center_content:
            # Container til logoet for at sikre horisontal centrering
            st.markdown(
                f"""
                <div style="display: flex; justify-content: center; width: 100%;">
                    <img src="{HIF_LOGO_URL}" style="width: 70px;">
                </div>
                """, 
                unsafe_allow_html=True
            )
            
            # Overskrift centreret
            st.markdown("<h2 style='text-align: center; color: #31333F; margin-top: 10px; margin-bottom: 20px;'>HIF Data HUB</h2>", unsafe_allow_html=True)
            
            # Selve formen
            with st.form("login_final"):
                u = st.text_input("BRUGER", placeholder="Brugernavn", label_visibility="collapsed").lower().strip()
                p = st.text_input("KODE", type="password", placeholder="Adgangskode", label_visibility="collapsed")
                submit_button = st.form_submit_button("LOG IND", use_container_width=True)
                
                if submit_button:
                    if u in USER_DB and USER_DB[u]["pass"] == p:
                        st.session_state["logged_in"] = True
                        st.session_state["user"] = u
                        st.rerun()
                    else:
                        st.error("Ugyldig login")
    st.stop()
    
# --- 3. SIDEBAR NAVIGATION ---
with st.sidebar:
    alle_omraader = ["TRUPPEN", "HIF ANALYSE", "BETINIA LIGAEN", "SCOUTING", "ADMIN"]
    user_info = USER_DB.get(st.session_state["user"], {})
    restriktioner = [r.lower().strip() for r in user_info.get("restricted", [])]
    
    synlige_hoved_options = [o for o in alle_omraader if o.lower().strip() not in restriktioner]
    hoved_omraade = option_menu(None, options=synlige_hoved_options, default_index=0)
    
    def filtrer_menu(liste):
        return [o for o in liste if o.lower().strip() not in restriktioner]

    if hoved_omraade == "TRUPPEN":
        sel = option_menu(None, options=filtrer_menu(["Oversigt", "Forecast"]))
    elif hoved_omraade == "HIF ANALYSE":
        sel = option_menu(None, options=["Charts"])
    elif hoved_omraade == "BETINIA LIGAEN":
        sel = option_menu(None, options=filtrer_menu(["Holdoversigt", "Kampe", "Afslutninger - liga", "Fysisk data"]))
    elif hoved_omraade == "SCOUTING":
        sel = option_menu(None, options=filtrer_menu(["Opret emne", "Emnedatabase", "Scoutrapport", "Database", "Sammenligning"]))
    elif hoved_omraade == "ADMIN":
        sel = option_menu(None, options=filtrer_menu(["System Log", "Profil"]))

# --- 4. DATA LOADING & RENDERING ---
render_hif_header(f"{hoved_omraade}  |  {sel.upper()}")

try:
    # SEKTION 1: TRUPPEN (Hurtig CSV-load)
    if hoved_omraade == "TRUPPEN":
        dp_quick = hif_load.get_squad_only()
        if sel == "Oversigt":
            import tools.truppen.players as pl
            pl.vis_side(dp_quick["players"])
        elif sel == "Forecast":
            import tools.truppen.squad as sq
            sq.vis_side(dp_quick["players"])

    # SEKTION 2: SCOUTING (Kræver stadig sin pakke, da den er cross-tabulær)
    elif hoved_omraade == "SCOUTING":
        dp = hif_load.get_scouting_package() 
        if sel == "Scoutrapport":
            import tools.scouting.scout_input as si
            si.vis_side(dp)
        elif sel == "Database":
            import tools.scouting.scout_db as sdb
            sdb.vis_side(dp["scout_reports"], dp["players"], dp["sql_players"], dp["career"])
        elif sel == "Opret emne":
            import tools.scouting.emneliste_input as el
            el.vis_side(dp, st.session_state["user"])
        elif sel == "Emnedatabase":
            import tools.scouting.emne_db as edb
            edb.vis_side(dp)
        elif sel == "Sammenligning":
            import tools.scouting.comparison as comp
            comp.vis_side(dp["players"], None, None, dp["career"], dp["sql_players"], dp["advanced_stats"])

    # SEKTION 3: HIF & LIGA ANALYSE (OPTIMERET: Ingen global load!)
    elif hoved_omraade == "HIF ANALYSE":
        if sel == "Spillerperformance":
            import tools.hifanalyse.player_analysis as pa
            pa.vis_side(dp) # Siden henter selv data
        elif sel == "Afslutninger":
            import tools.hifanalyse.shotmap as sm
            sm.vis_side(dp)
        elif sel == "Assistmap":
            import tools.hifanalyse.assistmap as am
            am.vis_side(dp)

    elif hoved_omraade == "BETINIA LIGAEN":
        if sel == "Modstanderanalyse":
            import tools.ligaen.modstanderanalyse as ma
            ma.vis_side() # Siden henter selv data
        elif sel == "Holdoversigt":
            import tools.ligaen.test_teams as tt
            tt.vis_side()
        elif sel == "Kampe":
            import tools.ligaen.test_matches as tm
            tm.vis_side()
        elif sel == "Charts":
            import tools.ligaen.chart as pc
            pc.vis_side()
        elif sel == "Afslutninger - liga":
            import tools.ligaen.leagueshots as ls
            ls.vis_side()
        elif sel == "Fysisk data":
            import tools.ligaen.fysisk as fd_page
            # Vi sender kun connection med, data hentes lokalt
            fd_page.vis_side(_get_snowflake_conn())

    # SEKTION 4: ADMIN
    elif hoved_omraade == "ADMIN":
        if sel == "System Log":
            import tools.admin_page.admin as admin
            admin.vis_log()
        elif sel == "Profil":
            import tools.admin_page.profil as profil
            profil.vis_side({})

except Exception as e:
    st.error(f"Fejl ved indlæsning af {sel}: {e}")
