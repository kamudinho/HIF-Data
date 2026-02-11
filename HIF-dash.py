import streamlit as st
from streamlit_option_menu import option_menu
import os
import pandas as pd

# --- 1. KONFIGURATION ---
st.set_page_config(page_title="HIF Data Hub", layout="wide")

st.markdown("""
    <style>
        /* 1. Fjern luft i toppen af selve appen */
        .block-container {
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
        }
        
        /* 2. Fjern det skjulte mellemrum over menuen/logoet */
        header {
            visibility: hidden;
            height: 0px;
        }

        /* 3. Gør headeren synlig igen, men fjern dens baggrundsstøj */
        header {
            visibility: visible !important;
            background: rgba(0,0,0,0) !important;
        }

        /* 4. Gør afstanden mellem widgets mindre på alle sider */
        [data-testid="stVerticalBlock"] {
            gap: 0.5rem !important;
        }

        /* 5. Fix for at selectboxes og radiobuttons ikke tager for meget plads */
        div[data-testid="stSelectbox"], div[data-testid="stRadio"] {
            margin-bottom: -10px !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. LOGIN SYSTEM ---
USER_DB = {"kasper": "1234", "ceo": "2650", "mr": "2650", "kd": "2650", "cg": "2650"}
if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
if not st.session_state["logged_in"]:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<br><br><div style='text-align: center;'><img src='https://cdn5.wyscout.com/photos/team/public/2659_120x120.png' width='120'></div>", unsafe_allow_html=True)
        with st.form("login"):
            u = st.text_input("Bruger").lower().strip()
            p = st.text_input("Kode", type="password")
            if st.form_submit_button("Log ind", use_container_width=True):
                if u in USER_DB and USER_DB[u] == p:
                    st.session_state["logged_in"] = True
                    st.session_state["user"] = u
                    st.rerun()
                else: st.error("Ugyldig kode")
    st.stop()

# --- 3. DATA LOADING ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
XLSX_PATH = os.path.join(BASE_DIR, 'HIF-data.xlsx')
PARQUET_PATH = os.path.join(BASE_DIR, 'eventdata.parquet')

@st.cache_resource
def load_hif_data():
    try:
        ho = pd.read_excel(XLSX_PATH, sheet_name='Hold')
        sp = pd.read_excel(XLSX_PATH, sheet_name='Spillere')
        ka = pd.read_excel(XLSX_PATH, sheet_name='Kampdata')
        pe = pd.read_excel(XLSX_PATH, sheet_name='Playerevents')
        sc = pd.read_excel(XLSX_PATH, sheet_name='Playerscouting')
        
        if os.path.exists(PARQUET_PATH):
            ev = pd.read_parquet(PARQUET_PATH)
            ev.columns = [str(c).strip().upper() for c in ev.columns]
        else:
            ev = pd.DataFrame()
        
        h_map = dict(zip(ho['TEAM_WYID'], ho['Hold']))
        return ev, ka, h_map, sp, pe, sc
    except Exception as e:
        st.error(f"Fejl: {e}")
        return pd.DataFrame(), pd.DataFrame(), {}, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

if "main_data" not in st.session_state:
    st.session_state["main_data"] = load_hif_data()
df_events, kamp, hold_map, spillere, player_events, df_scout = st.session_state["main_data"]

# --- 4. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.markdown("<div style='text-align: center;'><img src='https://cdn5.wyscout.com/photos/team/public/2659_120x120.png' width='60'></div>", unsafe_allow_html=True)
    
    hoved_omraade = option_menu(
        menu_title=None,
        options=["Truppen", "Analyse", "Scouting"],
        icons=["people", "graph-up", "search"],
        menu_icon="cast", default_index=0,
        styles={"container": {"background-color": "#f0f2f6"}, "nav-link-selected": {"background-color": "#003366"}}
    )
        
    if hoved_omraade == "Truppen":
        selected = option_menu(
            menu_title=None,
            options=["Oversigt", "Forecast", "Spillerstats", "Top 5"],
            icons=["people", "people", "people", "people"], # Dine valgte ikoner
            styles={"nav-link-selected": {"background-color": "#cc0000"}}
        )
    elif hoved_omraade == "Analyse":
        selected = option_menu(
            menu_title=None,
            options=["Zoneinddeling", "Afslutninger", "Heatmaps"],
            icons=["graph-up", "graph-up", "graph-up"], # Dine valgte ikoner
            styles={"nav-link-selected": {"background-color": "#cc0000"}}
        )
    elif hoved_omraade == "Scouting":
        selected = option_menu(
            menu_title=None,
            options=["Scouting-database", "Sammenligning"],
            icons=["search", "search"], # Dine valgte ikoner
            styles={"nav-link-selected": {"background-color": "#cc0000"}}
        )

# --- 5. ROUTING ---
if selected == "Oversigt":
    import tools.players as players
    players.vis_side(spillere)
elif selected == "Forecast":
    import tools.squad as squad
    squad.vis_side(spillere)
elif selected == "Spillerstats":
    import tools.stats as stats
    stats.vis_side(spillere, player_events)
elif selected == "Top 5":
    import tools.top5 as top5
    top5.vis_side(spillere, player_events)
elif selected == "Zoneinddeling":
    import tools.player_goalzone as pgz
    pgz.vis_side(df_events, spillere, hold_map)
elif selected == "Afslutninger":
    import tools.player_shots as ps
    ps.vis_side(df_events, spillere, hold_map)
elif selected == "Heatmaps":
    import tools.heatmaps as hm
    hm.vis_side(df_events, 4, hold_map)
elif selected == "Sammenligning":
    import tools.comparison as comp
    comp.vis_side(spillere, player_events, df_scout)
elif selected == "Scouting-database":
    import tools.scout_input as si
    si.vis_side(spillere)
