import streamlit as st
from streamlit_option_menu import option_menu
import os
import pandas as pd
import importlib

# --- 1. KONFIGURATION ---
st.set_page_config(page_title="HIF Performance Hub", layout="wide")

# CSS til styling: Centrerer logo og rydder op i margins
st.markdown("""
    <style>
        .block-container { padding-top: 2rem !important; }
        [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
        .sidebar-header { font-size: 0.8rem; font-weight: bold; color: #6d6d6d; margin-top: 15px; text-transform: uppercase; }
        
        /* Centrerer logo i sidebaren */
        [data-testid="stSidebar"] img {
            display: block;
            margin-left: auto;
            margin-right: auto;
        }
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
        # Centreret logo på login-skærm
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
    except:
        return None

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

# --- 4. DATA LOADING (Smart Version) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
XLSX_PATH = os.path.join(BASE_DIR, 'HIF-data.xlsx')

@st.cache_data(ttl=3600, show_spinner="Henter data...")
def load_full_data():
    try:
        # 1. Hent Excel-arkene
        ka = pd.read_excel(XLSX_PATH, sheet_name='Kampdata', engine='openpyxl')
        ho = pd.read_excel(XLSX_PATH, sheet_name='Hold', engine='openpyxl')
        sp = pd.read_excel(XLSX_PATH, sheet_name='Spillere', engine='openpyxl')
        pe = pd.read_excel(XLSX_PATH, sheet_name='Playerevents', engine='openpyxl')
        sc = pd.read_excel(XLSX_PATH, sheet_name='Playerscouting', engine='openpyxl')
        
        # 2. Hent Eventdata (Smart CSV-søgning)
        ev = None
        # Liste over mulige filnavne (Linux er case-sensitive!)
        possible_names = ['eventdata.csv', 'Eventdata.csv', 'EventData.csv', 'EVENTDATA.csv']
        
        found_path = None
        for name in possible_names:
            path = os.path.join(BASE_DIR, name)
            if os.path.exists(path):
                found_path = path
                break
        
        if found_path:
            # Prøv at indlæse med komma, hvis det fejler så semikolon
            try:
                ev = pd.read_csv(found_path, sep=',', low_memory=False)
                if len(ev.columns) < 2: # Hvis alt ligger i én kolonne, prøv semikolon
                    ev = pd.read_csv(found_path, sep=';', low_memory=False)
            except Exception as e:
                st.error(f"Fejl ved læsning af CSV: {e}")
                return None, None, {}, None, None, None
        else:
            # DEBUG INFO: Hvis filen stadig ikke findes, vis hvad der ligger i mappen
            files_in_dir = os.listdir(BASE_DIR)
            st.error(f"Kunne ikke finde eventdata.csv. Filer i mappen: {files_in_dir}")
            return None, None, {}, None, None, None

        # 3. Data Merge
        if ev is not None and 'PLAYER_WYID' in ev.columns and 'PLAYER_WYID' in sp.columns:
            navne_df = sp[['PLAYER_WYID', 'NAVN']].drop_duplicates('PLAYER_WYID')
            ev = ev.merge(navne_df, on='PLAYER_WYID', how='left')
            
        h_map = dict(zip(ho['TEAM_WYID'], ho['Hold']))
        
        return ev, ka, h_map, sp, pe, sc

    except Exception as e:
        st.error(f"Kritisk fejl ved indlæsning: {e}")
        return None, None, {}, None, None, None

df_events, kamp, hold_map, spillere, player_events, df_scout = load_full_data()

# SIKKERHEDS-CHECK: Stop hvis data ikke blev indlæst
if df_events is None:
    st.warning("Data kunne ikke indlæses. Tjek fejlbeskeden ovenfor.")
    st.stop()

# --- 5. SIDEBAR MENU ---
with st.sidebar:
    st.markdown(
        """
        <div style="display: flex; justify-content: center; padding-top: 10px;">
            <img src="https://cdn5.wyscout.com/photos/team/public/2659_120x120.png" width="100">
        </div>
        """,
        unsafe_allow_html=True
    )
    
    selected = option_menu(
        menu_title=None, 
        options=["HOLD", "SPILLERE", "STATISTIK", "SCOUTING"], 
        icons=["shield", "person", "bar-chart", "search"], 
        default_index=0
    )

    selected_sub = None
    if selected == "HOLD":
        st.markdown('<p class="sidebar-header">Holdanalyse</p>', unsafe_allow_html=True)
        selected_sub = st.radio("S_hold", ["Heatmaps", "Shotmaps", "Zoneinddeling", "Afslutninger", "DataViz"], label_visibility="collapsed")
    elif selected == "SPILLERE":
        st.markdown('<p class="sidebar-header">Spilleranalyse</p>', unsafe_allow_html=True)
        selected_sub = st.radio("S_ind", ["Zoneinddeling", "Afslutninger"], label_visibility="collapsed")
    elif selected == "STATISTIK":
        st.markdown('<p class="sidebar-header">Ranglister</p>', unsafe_allow_html=True)
        selected_sub = st.radio("S_stat", ["Spillerstats", "Top 5"], label_visibility="collapsed")
    elif selected == "SCOUTING":
        st.markdown('<p class="sidebar-header">Scoutingværktøjer</p>', unsafe_allow_html=True)
        selected_sub = st.radio("S_scout", ["Hvidovre IF", "Trupsammensætning", "Sammenligning"], label_visibility="collapsed")
        
        if selected_sub == "Trupsammensætning":
            st.markdown("---")
            st.selectbox("Vælg formation:", ["3-4-3", "4-3-3", "3-5-2"], key="formation_valg")

    st.markdown("---")
    if st.button("Log ud", use_container_width=True):
        st.session_state["logged_in"] = False
        st.rerun()

# --- 6. ROUTING ---
if selected == "HOLD":
    if selected_sub == "Heatmaps" and heatmaps: heatmaps.vis_side(df_events, 4, hold_map)
    elif selected_sub == "Shotmaps" and skudmap: skudmap.vis_side(df_events, 4, hold_map)
    elif selected_sub == "Zoneinddeling" and goalzone: goalzone.vis_side(df_events, kamp, hold_map)
    elif selected_sub == "Afslutninger" and shots: shots.vis_side(df_events, kamp, hold_map)
    elif selected_sub == "DataViz" and dataviz: dataviz.vis_side(df_events, kamp, hold_map)

elif selected == "SPILLERE":
    if selected_sub == "Zoneinddeling" and player_goalzone: player_goalzone.vis_side(df_events, spillere)
    elif selected_sub == "Afslutninger": st.info("Side under opbygning")

elif selected == "STATISTIK":
    if selected_sub == "Spillerstats" and stats: stats.vis_side(spillere, player_events)
    elif selected_sub == "Top 5" and top5: top5.vis_side(spillere, player_events)

elif selected == "SCOUTING":
    if selected_sub == "Hvidovre IF" and players: players.vis_side(spillere)
    elif selected_sub == "Trupsammensætning" and squad: squad.vis_side(spillere)
    elif selected_sub == "Sammenligning" and comparison: comparison.vis_side(spillere, player_events, df_scout)
