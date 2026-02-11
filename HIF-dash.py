import streamlit as st
from streamlit_option_menu import option_menu
import os
import pandas as pd

# --- 1. KONFIGURATION ---
st.set_page_config(page_title="HIF Data Hub", layout="wide")

st.markdown("""
    <style>
        .block-container { 
            padding-top: 3rem !important; 
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
        [data-testid="stSidebar"] img { display: block; margin: 0 auto 20px auto; }
        .nav-link { font-size: 14px !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. LOGIN SYSTEM ---
USER_DB = {"kasper": "1234", "ceo": "2650", "mr": "2650", "kd": "2650", "cg": "2650"}

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user" not in st.session_state:
    st.session_state["user"] = ""

if not st.session_state["logged_in"]:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<br><br><div style='text-align: center;'><img src='https://cdn5.wyscout.com/photos/team/public/2659_120x120.png' width='120'></div>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center;'>HIF Performance Hub</h3>", unsafe_allow_html=True)
        with st.form("login_form"):
            user_input = st.text_input("Brugernavn").lower().strip()
            pw = st.text_input("Adgangskode", type="password")
            if st.form_submit_button("Log ind", use_container_width=True):
                if user_input in USER_DB and USER_DB[user_input] == pw:
                    st.session_state["logged_in"] = True
                    st.session_state["user"] = user_input
                    st.rerun()
                else:
                    st.error("Ugyldigt brugernavn eller kode")
    st.stop()

# --- 3. DATA LOADING ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
XLSX_PATH = os.path.join(BASE_DIR, 'HIF-data.xlsx')
PARQUET_PATH = os.path.join(BASE_DIR, 'eventdata.parquet')
SHOT_CSV_PATH = os.path.join(BASE_DIR, 'shotevents.csv')

@st.cache_resource
def load_hif_data():
    try:
        ho = pd.read_excel(XLSX_PATH, sheet_name='Hold', engine='openpyxl')
        sp = pd.read_excel(XLSX_PATH, sheet_name='Spillere', engine='openpyxl')
        ka = pd.read_excel(XLSX_PATH, sheet_name='Kampdata', engine='openpyxl')
        pe = pd.read_excel(XLSX_PATH, sheet_name='Playerevents', engine='openpyxl')
        sc = pd.read_excel(XLSX_PATH, sheet_name='Playerscouting', engine='openpyxl')

        if os.path.exists(PARQUET_PATH):
            ev = pd.read_parquet(PARQUET_PATH)
            ev.columns = [str(c).strip().upper() for c in ev.columns]
        else:
            return None

        # --- MERGE SHOT DETAILS ---
        if os.path.exists(SHOT_CSV_PATH):
            shot_details = pd.read_csv(SHOT_CSV_PATH)
            shot_details.columns = [str(c).strip().upper() for c in shot_details.columns]
            
            # Vask ID'er så de matcher (vigtigt for merge)
            for d in [ev, shot_details]:
                if 'EVENT_WYID' in d.columns:
                    d['EVENT_WYID'] = d['EVENT_WYID'].astype(str).str.split('.').str[0].str.strip()
            
            if 'EVENT_WYID' in ev.columns and 'EVENT_WYID' in shot_details.columns:
                shot_details = shot_details.drop_duplicates(subset=['EVENT_WYID'])
                cols = ['EVENT_WYID', 'SHOTISGOAL', 'SHOTONTARGET', 'SHOTXG']
                existing_cols = [c for c in cols if c in shot_details.columns]
                ev = ev.merge(shot_details[existing_cols], on='EVENT_WYID', how='left')

        # Standardiser PLAYER_WYID
        for d in [sp, pe, ev]:
            if 'PLAYER_WYID' in d.columns:
                d['PLAYER_WYID'] = d['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()

        h_map = dict(zip(ho['TEAM_WYID'], ho['Hold']))
        godkendte_ids = ho['TEAM_WYID'].unique()
        ev = ev[ev['TEAM_WYID'].isin(godkendte_ids)]
        
        navne = sp[['PLAYER_WYID', 'NAVN']].drop_duplicates('PLAYER_WYID')
        ev = ev.merge(navne, on='PLAYER_WYID', how='left').rename(columns={'NAVN': 'PLAYER_NAME'})
            
        return ev, ka, h_map, sp, pe, sc
    except Exception as e:
        st.error(f"Kritisk fejl: {e}")
        return None

if "main_data" not in st.session_state:
    st.session_state["main_data"] = load_hif_data()

df_events, kamp, hold_map, spillere, player_events, df_scout = st.session_state["main_data"]

# --- 4. SIDEBAR MENU ---
with st.sidebar:
    st.markdown("<div style='text-align: center; margin-top: -50px;'><img src='https://cdn5.wyscout.com/photos/team/public/2659_120x120.png' width='60'></div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; font-size: 10px; margin-bottom: 5px;'>HIF DATA HUB</p>", unsafe_allow_html=True)
    
    selected = option_menu(
        menu_title=None,
        options=[
            "Dashboard",  "Truppen", "Forecast", 
            "Spillerstats", "Top 5",
            "Zoneinddeling - hold", "Afslutninger - hold",
            "Zoneinddeling - spillere", "Afslutninger - spillere",  "DataViz",
           "Heatmaps", "Shotmaps", "Sammenligning", "Scouting-database"
        ],
        icons=[
            'house', 'MAP', 'MAP', 
            'MAP-3x3', 'MAP', 'MAP-up',
            'person-MAP-box', 'MAP-badge',
            'MAP-chart', 'MAP',
            'MAP', 'MAP-3', 'MAP', 'MAP'
        ],
        menu_icon="cast", default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "#fafafa"},
            "icon": {"color": "#cc0000", "font-size": "14px"}, 
            "nav-link": {"font-size": "13px", "text-align": "left", "padding": "5px 10px"},
            "nav-link-selected": {"background-color": "#cc0000"},
        }
    )

# --- 5. ROUTING ---
if selected == "Dashboard":
    st.title("Hvidovre IF Performance Hub")
    st.success(f"Velkommen tilbage, {st.session_state['user'].upper()}")

elif selected == "Truppen":
    import tools.players as players
    players.vis_side(spillere)

elif selected == "Forecast":
    import tools.squad as squad
    squad.vis_side(spillere)

elif selected == "Zoneinddeling - hold":
    import tools.goalzone as goalzone
    goalzone.vis_side(df_events, spillere, hold_map)

elif selected == "Afslutninger - hold":
    import tools.shots as shots
    shots.vis_side(df_events, kamp, hold_map)

elif selected == "DataViz":
    import tools.dataviz as dataviz
    dataviz.vis_side(df_events, kamp, hold_map)

elif selected == "Zoneinddeling - spillere":
    import tools.player_goalzone as player_goalzone
    player_goalzone.vis_side(df_events, spillere)

elif selected == "Afslutninger - spillere":
    import tools.player_shots as player_shots
    player_shots.vis_side(df_events, spillere, hold_map)

elif selected == "Spillerstats":
    import tools.stats as stats
    stats.vis_side(spillere, player_events)

elif selected == "Top 5":
    import tools.top5 as top5
    top5.vis_side(spillere, player_events)

elif selected == "Heatmaps":
    import tools.heatmaps as heatmaps
    heatmaps.vis_side(df_events, 4, hold_map)

elif selected == "Shotmaps":
    import tools.skudmap as skudmap
    skudmap.vis_side(df_events, 4, hold_map)

elif selected == "Sammenligning":
    import tools.comparison as comparison
    comparison.vis_side(spillere, player_events, df_scout)

elif selected == "Scouting-database":
    import tools.scout_input as scout_input
    scout_input.vis_side(spillere)
