import streamlit as st
from streamlit_option_menu import option_menu
import os
import pandas as pd
import requests
import uuid

# --- 1. KONFIGURATION & STYLES ---
st.set_page_config(page_title="HIF Data Hub", layout="wide")

st.markdown("""
    <style>
        header { visibility: visible !important; background: rgba(0,0,0,0) !important; height: 3rem !important; }
        .block-container { padding-top: 0rem !important; margin-top: 2rem !important; padding-bottom: 1rem !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. GITHUB INDSTILLINGER ---
REPO = "Kamudinho/HIF-data"

# --- 3. LOGIN SYSTEM (Uændret) ---
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

# --- 4. DATA LOADING (OPDATERET TIL DATA MAPPE & CSV) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARQUET_PATH = os.path.join(BASE_DIR, 'eventdata.parquet')

@st.cache_resource
def load_hif_data():
    try:
        RAW_URL = f"https://raw.githubusercontent.com/{REPO}/main/data/"
        
        def read_github_csv(file_name):
            url = f"{RAW_URL}{file_name}?nocache={uuid.uuid4()}"
            df = pd.read_csv(url, sep=None, engine='python')
            df.columns = [str(c).strip().upper() for c in df.columns]
            return df

        # Hent Master-filer
        sp = read_github_csv("players.csv")
        ho = read_github_csv("teams.csv")
        sc = read_github_csv("scouting_db.csv")
        
        try:
            pe = read_github_csv("season_stats.csv")
        except:
            pe = pd.DataFrame()

        # Rens ID'er for alle dataframes (vigtigt for integrationen)
        for df in [sp, pe, sc, ho]:
            for col in ['PLAYER_WYID', 'ID', 'TEAM_WYID']:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.split('.').str[0]

        # Hold-mapping
        h_map = dict(zip(ho['TEAM_WYID'], ho['TEAMNAME']))
        
        # Hent event-data (Parquet)
        if os.path.exists(PARQUET_PATH):
            ev = pd.read_parquet(PARQUET_PATH)
            ev.columns = [str(c).strip().upper() for c in ev.columns]
        else:
            ev = pd.DataFrame()

        return ev, pd.DataFrame(), h_map, sp, pe, sc
        
    except Exception as e:
        st.error(f"Fejl ved indlæsning: {e}")
        return pd.DataFrame(), pd.DataFrame(), {}, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

if "main_data" not in st.session_state:
    st.session_state["main_data"] = load_hif_data()

df_events, kamp, hold_map, spillere, player_events, df_scout = st.session_state["main_data"]

# --- 5. SIDEBAR NAVIGATION (Uændret) ---
with st.sidebar:
    hoved_omraade = option_menu(None, options=["Truppen", "Analyse", "Scouting"], icons=["people", "graph-up", "search"], default_index=0)
    
    selected = "Oversigt"
    if hoved_omraade == "Truppen":
        selected = option_menu(None, options=["Oversigt", "Forecast", "Spillerstats", "Top 5"], icons=["people"]*4)
    elif hoved_omraade == "Analyse":
        selected = option_menu(None, options=["Zoneinddeling", "Afslutninger", "Heatmaps"], icons=["graph-up"]*3)
    elif hoved_omraade == "Scouting":
        selected = option_menu(None, options=["Scoutrapport", "Database", "Sammenligning"], icons=["pencil-square", "database", "arrow-left-right"])

# --- 6. ROUTING ---
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
if selected == "Sammenligning":
    import tools.comparison as comp
    comp.vis_side(spillere, player_events, df_scout)
elif selected == "Database":
    import tools.scout_db as sdb
    sdb.vis_side()
elif selected == "Scoutrapport":
    import tools.scout_input as si
    si.vis_side(spillere)
