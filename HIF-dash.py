import streamlit as st
import os
import pandas as pd

# --- 1. KONFIGURATION ---
st.set_page_config(page_title="HIF Data Hub", layout="wide")

# CSS til styling (Holdes simpel)
st.markdown("""
    <style>
        .block-container { padding-top: 4rem !important; }
        [data-testid="stSidebar"] img { display: block; margin: 0 auto 20px auto; }
        /* Styling af den klassiske radio-menu */
        .stRadio [data-testid="stWidgetLabel"] { display: none; }
        div[data-testid="stSidebarUserContent"] { padding-top: 0rem; }
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

# --- 3. DATA LOADING (PARQUET) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
XLSX_PATH = os.path.join(BASE_DIR, 'HIF-data.xlsx')
PARQUET_PATH = os.path.join(BASE_DIR, 'eventdata.parquet')

@st.cache_resource
def load_hif_data():
    try:
        # Læs Excel
        ho = pd.read_excel(XLSX_PATH, sheet_name='Hold', engine='openpyxl')
        sp = pd.read_excel(XLSX_PATH, sheet_name='Spillere', engine='openpyxl')
        ka = pd.read_excel(XLSX_PATH, sheet_name='Kampdata', engine='openpyxl')
        pe = pd.read_excel(XLSX_PATH, sheet_name='Playerevents', engine='openpyxl')
        sc = pd.read_excel(XLSX_PATH, sheet_name='Playerscouting', engine='openpyxl')

        # Læs Parquet (Lynhurtig)
        if os.path.exists(PARQUET_PATH):
            ev = pd.read_parquet(PARQUET_PATH)
        else:
            st.error("Fandt ikke eventdata.parquet!")
            return None

        # Rens PLAYER_WYID
        for df in [sp, pe, ev]:
            if 'PLAYER_WYID' in df.columns:
                df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()

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

# --- 4. SIDEBAR MENU (KLASSISK & HURTIG) ---
with st.sidebar:
    st.markdown("<div style='text-align: center; padding-top: 10px;'><img src='https://cdn5.wyscout.com/photos/team/public/2659_120x120.png' width='100'></div>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center;'><b>Hvidovre IF Data Hub</b><br>Bruger: {st.session_state['user'].upper()}</p>", unsafe_allow_html=True)
    st.write("---")
    
    # Klassisk Streamlit menu
    menu_options = [
        "Dashboard", 
        "Heatmaps", "Shotmaps", "Zoneinddeling (Hold)", "Afslutninger (Hold)", "DataViz",
        "Zoneinddeling (Spiller)", "Afslutninger (Spiller)",
        "Spillerstats", "Top 5",
        "Hvidovre IF Truppen", "Trupsammensætning", "Sammenligning", "Scouting-database"
    ]
    selected = st.radio("Vælg Modul", menu_options)

# --- 5. ROUTING ---
# Vi importerer alt én gang her for stabilitet
import tools.heatmaps as heatmaps
import tools.skudmap as skudmap
import tools.goalzone as goalzone
import tools.shots as shots
import tools.dataviz as dataviz
import tools.player_goalzone as player_goalzone
import tools.player_shots as player_shots
import tools.stats as stats
import tools.top5 as top5
import tools.players as players
import tools.squad as squad
import tools.comparison as comparison
import tools.scout_input as scout_input

if selected == "Dashboard":
    st.title("Hvidovre IF Performance Hub")
    st.success("Systemet kører nu med standard Streamlit-komponenter for maksimal hastighed.")

elif selected == "Heatmaps":
    heatmaps.vis_side(df_events, 4, hold_map)

elif selected == "Shotmaps":
    skudmap.vis_side(df_events, 4, hold_map)

elif selected == "Zoneinddeling (Hold)":
    goalzone.vis_side(df_events, spillere, hold_map)

elif selected == "Afslutninger (Hold)":
    shots.vis_side(df_events, kamp, hold_map)

elif selected == "DataViz":
    dataviz.vis_side(df_events, kamp, hold_map)

elif selected == "Zoneinddeling (Spiller)":
    player_goalzone.vis_side(df_events, spillere)

elif selected == "Afslutninger (Spiller)":
    player_shots.vis_side(df_events, kamp, hold_map)

elif selected == "Spillerstats":
    stats.vis_side(spillere, player_events)

elif selected == "Top 5":
    top5.vis_side(spillere, player_events)

elif selected == "Hvidovre IF Truppen":
    players.vis_side(spillere)

elif selected == "Trupsammensætning":
    squad.vis_side(spillere)

elif selected == "Sammenligning":
    comparison.vis_side(spillere, player_events, df_scout)

elif selected == "Scouting-database":
    scout_input.vis_side(spillere)
