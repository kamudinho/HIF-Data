import streamlit as st
import streamlit_antd_components as sac
import os
import pandas as pd
import importlib

# --- 1. KONFIGURATION ---
st.set_page_config(page_title="HIF Data Hub", layout="wide")

# Samlet optimeret CSS
st.markdown("""
    <style>
        .block-container { padding-top: 2rem !important; }
        [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
        [data-testid="stSidebar"] img { display: block; margin: 0 auto 20px auto; }
        
        /* Gør undermenuer mindre og skarpere */
        .ant-menu-sub .ant-menu-title-content {
            font-size: 13px !important;
            white-space: nowrap !important;
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
        st.markdown("<br><br><div style='text-align: center;'><img src='https://cdn5.wyscout.com/photos/team/public/2659_120x120.png' width='120'></div>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center;'>HIF Performance Hub</h3>", unsafe_allow_html=True)
        with st.form("login_form"):
            user = st.text_input("Brugernavn").lower().strip()
            pw = st.text_input("Adgangskode", type="password")
            if st.form_submit_button("Log ind", use_container_width=True):
                if user in USER_DB and USER_DB[user] == pw:
                    st.session_state["logged_in"] = True
                    st.rerun()
                else:
                    st.error("Ugyldigt brugernavn eller kode")
    st.stop()

# --- 3. DATA LOADING (TURBO OPTIMERET) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR.endswith('tools'):
    BASE_DIR = os.path.dirname(BASE_DIR)

XLSX_PATH = os.path.join(BASE_DIR, 'HIF-data.xlsx')
CSV_PATH = os.path.join(BASE_DIR, 'eventdata.csv')
PARQUET_PATH = os.path.join(BASE_DIR, 'eventdata.parquet')

@st.cache_data(ttl=3600, show_spinner="Turbo-indlæser data...")
def load_full_data():
    try:
        # Læs Excel ark (altid fra Excel)
        ho = pd.read_excel(XLSX_PATH, sheet_name='Hold', engine='openpyxl')
        sp = pd.read_excel(XLSX_PATH, sheet_name='Spillere', engine='openpyxl')
        ka = pd.read_excel(XLSX_PATH, sheet_name='Kampdata', engine='openpyxl')
        pe = pd.read_excel(XLSX_PATH, sheet_name='Playerevents', engine='openpyxl')
        sc = pd.read_excel(XLSX_PATH, sheet_name='Playerscouting', engine='openpyxl')

        # DATA ENGINE: Prøv at læse Parquet først, ellers læs CSV og konverter
        if os.path.exists(PARQUET_PATH):
            ev = pd.read_parquet(PARQUET_PATH)
        elif os.path.exists(CSV_PATH):
            # Læs CSV hurtigt med C-engine og faste typer
            ev = pd.read_csv(CSV_PATH, low_memory=False, engine='c', dtype={'PLAYER_WYID': str})
            # Gem som Parquet til næste gang
            ev.to_parquet(PARQUET_PATH, index=False)
        else:
            st.error("Ingen eventdata fundet!")
            return None, None, {}, None, None, None

        # Rens PLAYER_WYID (kun hvis nødvendigt efter Parquet load)
        for df in [sp, pe, ev]:
            if 'PLAYER_WYID' in df.columns:
                df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()

        godkendte_hold_ids = ho['TEAM_WYID'].unique()
        h_map = dict(zip(ho['TEAM_WYID'], ho['Hold']))

        # Filtrer events og tilføj navne
        ev = ev[ev['TEAM_WYID'].isin(godkendte_hold_ids)]
        if 'PLAYER_NAME' not in ev.columns:
            navne_df = sp[['PLAYER_WYID', 'NAVN']].drop_duplicates('PLAYER_WYID')
            ev = ev.merge(navne_df, on='PLAYER_WYID', how='left').rename(columns={'NAVN': 'PLAYER_NAME'})
            
        return ev, ka, h_map, sp, pe, sc
    except Exception as e:
        st.error(f"Kritisk fejl: {e}")
        return None, None, {}, None, None, None

df_events, kamp, hold_map, spillere, player_events, df_scout = load_full_data()

if df_events is None:
    st.stop()

# --- 4. SIDEBAR MENU ---
with st.sidebar:
    st.markdown("<div style='text-align: center; padding-top: 10px;'><img src='https://cdn5.wyscout.com/photos/team/public/2659_120x120.png' width='100'></div>", unsafe_allow_html=True)
    
    selected = sac.menu([
        sac.MenuItem('DASHBOARD', icon='house-fill'),
        sac.MenuItem('HOLD', icon='shield', children=[
            sac.MenuItem('Heatmaps'), sac.MenuItem('Shotmaps'), 
            sac.MenuItem('Zoneinddeling'), sac.MenuItem('Afslutninger'), sac.MenuItem('DataViz'),
        ]),
        sac.MenuItem('SPILLERE', icon='person', children=[
            sac.MenuItem('Zoneinddeling'), sac.MenuItem('Afslutninger'),
        ]),
        sac.MenuItem('STATISTIK', icon='bar-chart', children=[
            sac.MenuItem('Spillerstats'), sac.MenuItem('Top 5'),
        ]),
        sac.MenuItem('SCOUTING', icon='search', children=[
            sac.MenuItem('Hvidovre IF'), sac.MenuItem('Trupsammensætning'), 
            sac.MenuItem('Sammenligning'), sac.MenuItem('Scouting-database'),
        ]),
    ], format_func='upper', key='hif_menu_v3')

# --- 5. ROUTING (LAZY LOADING) ---
if selected == 'DASHBOARD':
    st.title("Hvidovre IF Performance Hub")
    st.write(f"Data er nu optimeret via Parquet-format for maksimal hastighed.")

elif selected == 'Heatmaps':
    import tools.heatmaps as heatmaps
    heatmaps.vis_side(df_events, 4, hold_map)

elif selected == 'Shotmaps':
    import tools.skudmap as skudmap
    skudmap.vis_side(df_events, 4, hold_map)

elif selected == 'HOLD/Zoneinddeling':
    import tools.goalzone as goalzone
    goalzone.vis_side(df_events, spillere, hold_map)

elif selected == 'HOLD/Afslutninger':
    import tools.shots as shots
    shots.vis_side(df_events, kamp, hold_map)

elif selected == 'DataViz':
    import tools.dataviz as dataviz
    dataviz.vis_side(df_events, kamp, hold_map)

elif selected == 'SPILLERE/Zoneinddeling':
    import tools.player_goalzone as player_goalzone
    player_goalzone.vis_side(df_events, spillere)

elif selected == 'SPILLERE/Afslutninger':
    import tools.player_shots as player_shots
    player_shots.vis_side(df_events, kamp, hold_map)

elif selected == 'Spillerstats':
    import tools.stats as stats
    stats.vis_side(spillere, player_events)

elif selected == 'Top 5':
    import tools.top5 as top5
    top5.vis_side(spillere, player_events)

elif selected == 'Hvidovre IF':
    import tools.players as players
    players.vis_side(spillere)

elif selected == 'Trupsammensætning':
    import tools.squad as squad
    squad.vis_side(spillere)

elif selected == 'Sammenligning':
    import tools.comparison as comparison
    comparison.vis_side(spillere, player_events, df_scout)

elif selected == 'Scouting-database':
    import tools.scout_input as scout_input
    scout_input.vis_side(spillere)
