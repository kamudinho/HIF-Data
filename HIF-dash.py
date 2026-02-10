import streamlit as st
from streamlit_option_menu import option_menu
import streamlit_antd_components as sac
import os
import pandas as pd
import importlib
import uuid

# --- 1. KONFIGURATION ---
st.set_page_config(page_title="HIF Data Hub", layout="wide")

# CSS til styling
st.markdown("""
    <style>
        .block-container { padding-top: 2rem !important; }
        [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
        
        /* Centrerer logo i sidebaren */
        [data-testid="stSidebar"] img {
            display: block;
            margin-left: auto;
            margin-right: auto;
        }
        
        /* Styling af Ant Design Menu */
        .nav-link-text { font-weight: 500; }
    </style>
""", unsafe_allow_html=True)

# --- 2. LOGIN SYSTEM ---
USER_DB = {"kasper": "1234", "ceo": "2650", "mr": "2650", "kd": "2650", "cg": "2650"}

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="display: flex; justify-content: center; margin-bottom: 20px;">
                <img src="https://cdn5.wyscout.com/photos/team/public/2659_120x120.png" width="120">
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("<h3 style='text-align: center;'>HIF Performance Hub</h3>", unsafe_allow_html=True)
        with st.form("login_form"):
            user = st.text_input("Brugernavn").lower().strip()
            pw = st.text_input("Adgangskode", type="password")
            submit = st.form_submit_button("Log ind", use_container_width=True)
            if submit:
                if user in USER_DB and USER_DB[user] == pw:
                    st.session_state["logged_in"] = True
                    st.rerun()
                else:
                    st.error("Ugyldigt brugernavn eller kode")
    st.stop()

# --- 3. IMPORT AF TOOLS ---
def load_module(name):
    try:
        return importlib.import_module(f"tools.{name}")
    except Exception as e:
        st.error(f"Fejl ved indlæsning af {name}: {e}")
        return None

# Load moduler
heatmaps = load_module("heatmaps")
shots = load_module("shots")
skudmap = load_module("skudmap")
dataviz = load_module("dataviz")
players = load_module("players")
comparison = load_module("comparison")
stats = load_module("stats")
goalzone = load_module("goalzone")
top5 = load_module("top5")
squad = load_module("squad")
player_goalzone = load_module("player_goalzone")
player_shots = load_module("player_shots")
scout_input = load_module("scout_input")

# --- 4. DATA LOADING ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
XLSX_PATH = os.path.join(BASE_DIR, 'HIF-data.xlsx')

@st.cache_data(ttl=3600, show_spinner="Opdaterer HIF data...")
def load_full_data():
    try:
        ho = pd.read_excel(XLSX_PATH, sheet_name='Hold', engine='openpyxl')
        sp = pd.read_excel(XLSX_PATH, sheet_name='Spillere', engine='openpyxl')
        ka = pd.read_excel(XLSX_PATH, sheet_name='Kampdata', engine='openpyxl')
        pe = pd.read_excel(XLSX_PATH, sheet_name='Playerevents', engine='openpyxl')
        sc = pd.read_excel(XLSX_PATH, sheet_name='Playerscouting', engine='openpyxl')
        
        for df_tmp in [sp, pe]:
            if 'PLAYER_WYID' in df_tmp.columns:
                df_tmp['PLAYER_WYID'] = df_tmp['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()

        godkendte_hold_ids = ho['TEAM_WYID'].unique()
        h_map = dict(zip(ho['TEAM_WYID'], ho['Hold']))

        ev = None
        possible_names = ['eventdata.csv', 'Eventdata.csv', 'EventData.csv', 'EVENTDATA.csv']
        found_path = next((os.path.join(BASE_DIR, n) for n in possible_names if os.path.exists(os.path.join(BASE_DIR, n))), None)
        
        if found_path:
            ev = pd.read_csv(found_path, low_memory=False)
            if len(ev.columns) < 2:
                ev = pd.read_csv(found_path, sep=';', low_memory=False)
            
            if 'PLAYER_WYID' in ev.columns:
                ev['PLAYER_WYID'] = ev['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
        
        if ev is not None:
            ev = ev[ev['TEAM_WYID'].isin(godkendte_hold_ids)]
            if 'PLAYER_WYID' in ev.columns and 'PLAYER_WYID' in sp.columns:
                navne_df = sp[['PLAYER_WYID', 'NAVN']].drop_duplicates('PLAYER_WYID')
                ev = ev.merge(navne_df, on='PLAYER_WYID', how='left')
                ev = ev.rename(columns={'NAVN': 'PLAYER_NAME'})
            
        return ev, ka, h_map, sp, pe, sc
    except Exception as e:
        st.error(f"Kritisk datafejl: {e}")
        return None, None, {}, None, None, None

df_events, kamp, hold_map, spillere, player_events, df_scout = load_full_data()

if df_events is None:
    st.stop()

# --- 5. SIDEBAR MENU (Ant Design for Collapsible effect) ---
with st.sidebar:
    st.markdown(
        """
        <div style="display: flex; justify-content: center; padding-top: 10px; margin-bottom: 20px;">
            <img src="https://cdn5.wyscout.com/photos/team/public/2659_120x120.png" width="100">
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Ny hierarkisk menu
    selected = sac.menu([
        sac.MenuItem('DASHBOARD', icon='house-fill'),
        sac.MenuItem('HOLD', icon='shield', children=[
            sac.MenuItem('Heatmaps', icon='fire'),
            sac.MenuItem('Shotmaps', icon='target'),
            sac.MenuItem('Zoneinddeling (Hold)', icon='grid-3x3'),
            sac.MenuItem('Afslutninger (Hold)', icon='fullscreen-exit'),
            sac.MenuItem('DataViz', icon='graph-up'),
        ]),
        sac.MenuItem('SPILLERE', icon='person', children=[
            sac.MenuItem('Zoneinddeling (Spiller)', icon='grid'),
            sac.MenuItem('Afslutninger (Spiller)', icon='bullseye'),
        ]),
        sac.MenuItem('STATISTIK', icon='bar-chart', children=[
            sac.MenuItem('Spillerstats', icon='list-ol'),
            sac.MenuItem('Top 5', icon='trophy'),
        ]),
        sac.MenuItem('SCOUTING', icon='search', children=[
            sac.MenuItem('Hvidovre IF', icon='shield-check'),
            sac.MenuItem('Trupsammensætning', icon='people'),
            sac.MenuItem('Sammenligning', icon='arrow-left-right'),
            sac.MenuItem('Scouting-database', icon='database-fill-add'),
        ]),
    ], format_func='upper', open_all=False, index=0)

    st.markdown("---")
    if st.button("Log ud", use_container_width=True):
        st.session_state["logged_in"] = False
        st.rerun()

# --- 6. ROUTING (Baseret på menuvalg) ---

# Dashboard
if selected == 'DASHBOARD':
    st.title("Hvidovre IF Performance Hub")
    st.write(f"Velkommen, {user.capitalize()}. Vælg et værktøj i menuen til venstre.")

# Hold Analyse
elif selected == "Heatmaps" and heatmaps:
    heatmaps.vis_side(df_events, 4, hold_map)
elif selected == "Shotmaps" and skudmap:
    skudmap.vis_side(df_events, 4, hold_map)
elif selected == "Zoneinddeling (Hold)" and goalzone:
    goalzone.vis_side(df_events, spillere, hold_map)
elif selected == "Afslutninger (Hold)" and shots:
    shots.vis_side(df_events, kamp, hold_map)
elif selected == "DataViz" and dataviz:
    dataviz.vis_side(df_events, kamp, hold_map)

# Spiller Analyse
elif selected == "Zoneinddeling (Spiller)" and player_goalzone:
    player_goalzone.vis_side(df_events, spillere)
elif selected == "Afslutninger (Spiller)" and player_shots:
    player_shots.vis_side(df_events, kamp, hold_map)

# Statistik
elif selected == "Spillerstats" and stats:
    stats.vis_side(spillere, player_events)
elif selected == "Top 5" and top5:
    top5.vis_side(spillere, player_events)

# Scouting
elif selected == "Hvidovre IF" and players:
    players.vis_side(spillere)
elif selected == "Trupsammensætning" and squad:
    squad.vis_side(spillere)
elif selected == "Sammenligning" and comparison:
    comparison.vis_side(spillere, player_events, df_scout)
elif selected == "Scouting-database" and scout_input:
    scout_input.vis_side(spillere)
