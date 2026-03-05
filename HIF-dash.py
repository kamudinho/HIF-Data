import os
import sys
import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd

# Sikr at vi kan finde vores egne moduler
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.data_load import get_data_package, load_snowflake_query
from data.users import get_users

# --- 1. KONFIGURATION & BRANDING ---
HIF_LOGO_URL = "https://cdn5.wyscout.com/photos/team/public/2659_120x120.png"
HIF_ROD = "#df003b"
HIF_GULD = "#b8860b"

st.set_page_config(
    page_title="HIF Data Hub",
    layout="wide",
    page_icon=HIF_LOGO_URL
)

# Centraliseret CSS for hele appen
st.markdown(f"""
    <style>
        /* Fjern standard Streamlit padding og header */
        .block-container {{ padding-top: 0.5rem !important; padding-bottom: 0rem !important; }}
        header {{ visibility: hidden; height: 0px; }}
        
        /* FAST CENTRAL BRANDING CONTAINER */
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

        /* Styling af Tabs */
        button[data-baseweb="tab"] {{ font-size: 14px; font-weight: 600; }}
        button[data-baseweb="tab"][aria-selected="true"] {{ 
            color: {HIF_ROD} !important; 
            border-bottom-color: {HIF_ROD} !important; 
        }}
        
        /* Sidebar justeringer */
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

# --- 3. DATA LOADING ---
if "dp" not in st.session_state:
    with st.spinner("Henter systemdata..."):
        try:
            # Hent den rensede pakke
            data_pkg = get_data_package()
            st.session_state["dp"] = data_pkg
        except Exception as e:
            st.error(f"❌ Kritisk fejl ved indlæsning af datapakke: {e}")
            st.stop()

dp = st.session_state["dp"]

# --- 4. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.markdown(f"<div style='text-align: center; padding-bottom: 10px;'><img src='{HIF_LOGO_URL}' width='80'></div>", unsafe_allow_html=True)
    
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
        sel = option_menu(None, options=["Afslutninger"],
                         styles={"nav-link-selected": {"background-color": HIF_ROD}})
    elif hoved_omraade == "BETINIA LIGAEN":
        sel = option_menu(None, options=["Holdoversigt", "Kampe"],
                         styles={"nav-link-selected": {"background-color": HIF_ROD}})
    elif hoved_omraade == "SCOUTING":
        sel = option_menu(None, options=[],
                         styles={"nav-link-selected": {"background-color": HIF_ROD}})
    elif hoved_omraade == "ADMIN":
        sel = option_menu(None, options=["Rå Data Explorer", "Assist Data Explorer", "Brugerstyring", "System Log"],
                         styles={"nav-link-selected": {"background-color": "#333333"}})

# --- 5. RENDERING AF HEADER & INDHOLD ---
if not sel:
    sel = "Oversigt"

# Her tegnes den centrale header automatisk
render_hif_header(f"{hoved_omraade}  |  {sel.upper()}")

try:
    if hoved_omraade == "TRUPPEN":
        if sel == "Oversigt":
            import tools.players as pl
            pl.vis_side(dp["players"])
        elif sel == "Forecast":
            import tools.squad as sq
            sq.vis_side(dp["players"])

    elif hoved_omraade == "HIF ANALYSE":
        if sel == "Afslutninger":
            import tools.shotmap as sm
            sm.vis_side(dp)
        elif sel == "Modstanderanalyse":
            import tools.modstanderanalyse as ma
            ma.vis_side(dp["opta_matches"], dp["logo_map"])
        elif sel == "Scatterplots":
            import tools.scatter as sc
            sc.vis_side(dp["team_stats_full"])

    elif hoved_omraade == "BETINIA LIGAEN":
        if sel == "Holdoversigt":
            import tools.test.test_teams as tt
            tt.vis_side(dp)
        elif sel == "Kampe":
            import tools.test.test_matches as tm
            tm.vis_side(dp)

    elif hoved_omraade == "SCOUTING":
        if sel == "Scoutrapport":
            import tools.scout_input as si
            si.vis_side(dp) # Denne er OK, da den tager hele pakken
        elif sel == "Database":
            import tools.scout_db as sdb
            # RETTET HER: Vi henter data fra de rigtige under-nøgler
            sdb.vis_side(
                dp.get("scouting_image"), 
                dp["players"], 
                dp["opta"]["player_stats"], # I stedet for dp["playerstats"]
                dp["wyscout"]["career"]     # I stedet for dp["player_career"]
            )
        elif sel == "Sammenligning":
            import tools.comparison as comp
            # RETTET HER:
            comp.vis_side(
                dp["players"], 
                dp["opta"]["player_stats"], 
                dp.get("scouting_image"), 
                dp["wyscout"]["career"], 
                dp.get("season_filter"))
            
    elif hoved_omraade == "ADMIN":
        if sel == "Rå Data Explorer":
            st.write("### Opta Matches", dp.get("opta", {}).get("matches", pd.DataFrame()).head(50))
        
        # --- NY SEKTION HER ---
        elif sel == "Assist Data Explorer":
            st.markdown("### 🎯 Opta Assist Query Validering")
            df_a = dp.get("assists", pd.DataFrame())
            
            if df_a.empty:
                st.warning("Ingen assist-data fundet i datapakken.")
            else:
                st.write(f"Viser alle {len(df_a)} registrerede assists:")
                # Vi sorterer efter seneste hændelser øverst
                st.dataframe(
                    df_a.sort_values("EVENT_TIMESTAMP", ascending=False),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "EVENT_TIMESTAMP": st.column_config.DatetimeColumn("Tidspunkt", format="D. MMM, HH:mm"),
                        "PASS_START_X": "Start X",
                        "PASS_START_Y": "Start Y",
                        "SHOT_X": "Slut X",
                        "SHOT_Y": "Slut Y",
                        "SCORER": "Målscorer",
                        "ASSIST_PLAYER": "Assist"
                    }
                )
        # -----------------------

        elif sel == "Brugerstyring":
            import tools.admin as adm
            adm.vis_side()
        elif sel == "System Log":
            import tools.admin as adm
            adm.vis_log()

except Exception as e:
    st.error(f"Fejl ved indlæsning af {sel}: {e}")
