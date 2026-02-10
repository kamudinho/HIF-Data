import streamlit as st
import streamlit_antd_components as sac
import os
import pandas as pd
import importlib

# --- 1. KONFIGURATION ---
st.set_page_config(page_title="HIF Data Hub", layout="wide")

# Samlet CSS for at optimere hastighed
st.markdown("""
    <style>
        .block-container { padding-top: 2rem !important; }
        [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
        
        /* Centrerer logo i sidebars */
        [data-testid="stSidebar"] img {
            display: block;
            margin-left: auto;
            margin-right: auto;
        }

        /* Gør underpunkter mindre og fjerner ikoner (via CSS for en sikkerheds skyld) */
        .ant-menu-sub .ant-menu-title-content {
            font-size: 13px !important;
            white-space: nowrap !important;
        }
        
        .ant-menu-submenu-title {
            font-weight: bold !important;
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

# --- 3. DATA LOADING (Cachet) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
XLSX_PATH = os.path.join(BASE_DIR, 'HIF-data.xlsx')

@st.cache_data(ttl=3600, show_spinner="Henter HIF data...")
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

# --- 4. SIDEBAR MENU ---
with st.sidebar:
    st.markdown(
        """
        <div style="display: flex; justify-content: center; padding-top: 10px; margin-bottom: 20px;">
            <img src="https://cdn5.wyscout.com/photos/team/public/2659_120x120.png" width="100">
        </div>
        """,
        unsafe_allow_html=True
    )
    
    selected = sac.menu([
        sac.MenuItem('DASHBOARD', icon='house-fill'),
        sac.MenuItem('HOLD', icon='shield', children=[
            sac.MenuItem('Heatmaps'),
            sac.MenuItem('Shotmaps'),
            sac.MenuItem('Zoneinddeling'),
            sac.MenuItem('Afslutninger'),
            sac.MenuItem('DataViz'),
        ]),
        sac.MenuItem('SPILLERE', icon='person', children=[
            sac.MenuItem('Zoneinddeling'),
            sac.MenuItem('Afslutninger'),
        ]),
        sac.MenuItem('STATISTIK', icon='bar-chart', children=[
            sac.MenuItem('Spillerstats'),
            sac.MenuItem('Top 5'),
        ]),
        sac.MenuItem('SCOUTING', icon='search', children=[
            sac.MenuItem('Hvidovre IF'),
            sac.MenuItem('Trupsammensætning'),
            sac.MenuItem('Sammenligning'),
            sac.MenuItem('Scouting-database'),
        ]),
    ], format_func='upper', key='hif_menu_v2')

# --- 5. ROUTING (LAZY LOADING) ---
# Vi importerer først modulerne herinde for at øge hastigheden på menuen

if selected == 'DASHBOARD':
    st.title("Hvidovre IF Performance Hub")
    st.info(f"Velkommen tilbage. Vælg et modul i menuen til venstre.")

# --- HOLD ---
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

# --- SPILLERE ---
elif selected == 'SPILLERE/Zoneinddeling':
    import tools.player_goalzone as player_goalzone
    player_goalzone.vis_side(df_events, spillere)

elif selected == 'SPILLERE/Afslutninger':
    import tools.player_shots as player_shots
    player_shots.vis_side(df_events, kamp, hold_map)

# --- STATISTIK ---
elif selected == 'Spillerstats':
    import tools.stats as stats
    stats.vis_side(spillere, player_events)

elif selected == 'Top 5':
    import tools.top5 as top5
    top5.vis_side(spillere, player_events)

# --- SCOUTING ---
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
