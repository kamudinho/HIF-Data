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

# --- 3. DATA LOADING (FORBEDRET TIL MULTILINE CSV) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
XLSX_PATH = os.path.join(BASE_DIR, 'HIF-data.xlsx')
PARQUET_PATH = os.path.join(BASE_DIR, 'eventdata.parquet')
SHOT_CSV_PATH = os.path.join(BASE_DIR, 'shotevents.csv')

@st.cache_resource
def load_hif_data():
    try:
        # Excel data
        ho = pd.read_excel(XLSX_PATH, sheet_name='Hold', engine='openpyxl')
        sp = pd.read_excel(XLSX_PATH, sheet_name='Spillere', engine='openpyxl')
        ka = pd.read_excel(XLSX_PATH, sheet_name='Kampdata', engine='openpyxl')
        pe = pd.read_excel(XLSX_PATH, sheet_name='Playerevents', engine='openpyxl')
        sc = pd.read_excel(XLSX_PATH, sheet_name='Playerscouting', engine='openpyxl')

        # Parquet data (Main events)
        if os.path.exists(PARQUET_PATH):
            ev = pd.read_parquet(PARQUET_PATH)
            ev.columns = [str(c).strip().upper() for c in ev.columns]
        else:
            st.error("Fandt ikke eventdata.parquet!")
            return None

        # --- SPECIALISERET CSV INDLÆSNING TIL MULTILINE/TAGS ---
        if os.path.exists(SHOT_CSV_PATH):
            # Vi bruger engine='python' og specielle citat-indstillinger 
            # for at håndtere ["goal", "opportunity"] listerne korrekt.
            shot_details = pd.read_csv(
                SHOT_CSV_PATH, 
                quotechar='"',          # Håndterer felter med " "
                on_bad_lines='skip',    # Skipper knækkede linjer der ikke kan læses
                engine='python',
                skipinitialspace=True
            )
            shot_details.columns = [str(c).strip().upper() for c in shot_details.columns]
            
            # Sørg for at ID'er er strenge og uden decimaler
            keys = ['EVENT_WYID', 'MATCH_WYID']
            for k in keys:
                if k in ev.columns:
                    ev[k] = ev[k].astype(str).str.split('.').str[0].str.strip()
                if k in shot_details.columns:
                    shot_details[k] = shot_details[k].astype(str).str.split('.').str[0].str.strip()

            # Merge kun hvis nøgler findes
            if all(k in ev.columns for k in keys) and all(k in shot_details.columns for k in keys):
                shot_details = shot_details.drop_duplicates(subset=keys)
                cols_to_add = keys + ['SHOTISGOAL', 'SHOTONTARGET', 'SHOTXG']
                existing_cols = [c for c in cols_to_add if c in shot_details.columns]
                
                ev = ev.merge(shot_details[existing_cols], on=keys, how='left')
            else:
                st.warning("Merge fejlede: Tjek kolonnenavne i shotevents.csv")

        # Standardisering af PLAYER_WYID
        for d in [sp, pe, ev]:
            if 'PLAYER_WYID' in d.columns:
                d['PLAYER_WYID'] = d['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()

        h_map = dict(zip(ho['TEAM_WYID'], ho['Hold']))
        godkendte_ids = ho['TEAM_WYID'].unique()
        ev = ev[ev['TEAM_WYID'].isin(godkendte_ids)]
        
        # Navne-merge
        navne = sp[['PLAYER_WYID', 'NAVN']].drop_duplicates('PLAYER_WYID')
        ev = ev.merge(navne, on='PLAYER_WYID', how='left').rename(columns={'NAVN': 'PLAYER_NAME'})
            
        return ev, ka, h_map, sp, pe, sc
    except Exception as e:
        st.error(f"Kritisk fejl ved data-indlæsning: {e}")
        return None

if "main_data" not in st.session_state:
    st.session_state["main_data"] = load_hif_data()

# Udpakning af data
df_events, kamp, hold_map, spillere, player_events, df_scout = st.session_state["main_data"]

# --- 4. SIDEBAR MENU ---
with st.sidebar:
    st.markdown("<div style='text-align: center; margin-top: -50px;'><img src='https://cdn5.wyscout.com/photos/team/public/2659_120x120.png' width='60'></div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; font-size: 10px; margin-bottom: 5px;'>HIF DATA HUB</p>", unsafe_allow_html=True)
    
    selected = option_menu(
        menu_title=None,
        options=[
            "Dashboard", "Heatmaps", "Shotmaps", 
            "Zoneinddeling", "Afslutninger", "DataViz",
            "Spiller Zoneinddeling", "Spiller Afslutninger",
            "Spillerstats", "Top 5",
            "Hvidovre IF Truppen", "Trupsammensætning", "Sammenligning", "Scouting-database"
        ],
        icons=[
            'house', 'map', 'target', 
            'grid-3x3', 'lightning', 'graph-up',
            'person-bounding-box', 'person-badge',
            'bar-chart', 'trophy',
            'people', 'diagram-3', 'intersect', 'search'
        ],
        menu_icon="cast", 
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "#fafafa"},
            "icon": {"color": "#cc0000", "font-size": "14px"}, 
            "nav-link": {"font-size": "13px", "text-align": "left", "padding": "5px 10px"},
            "nav-link-selected": {"background-color": "#cc0000"},
        }
    )

# --- 5. ROUTING ---
# (Din eksisterende routing herunder...)
if selected == "Dashboard":
    st.title("Hvidovre IF Performance Hub")
    st.success(f"Velkommen tilbage, {st.session_state['user'].upper()}")

elif selected == "Heatmaps":
    import tools.heatmaps as heatmaps
    heatmaps.vis_side(df_events, 4, hold_map)

elif selected == "Shotmaps":
    import tools.skudmap as skudmap
    skudmap.vis_side(df_events, 4, hold_map)

elif selected == "Zoneinddeling":
    import tools.goalzone as goalzone
    goalzone.vis_side(df_events, spillere, hold_map)

elif selected == "Afslutninger":
    import tools.shots as shots
    shots.vis_side(df_events, kamp, hold_map)

elif selected == "DataViz":
    import tools.dataviz as dataviz
    dataviz.vis_side(df_events, kamp, hold_map)

elif selected == "Spiller Zoneinddeling":
    import tools.player_goalzone as player_goalzone
    player_goalzone.vis_side(df_events, spillere)

elif selected == "Spiller Afslutninger":
    import tools.player_shots as player_shots
    player_shots.vis_side(df_events, spillere, hold_map)

elif selected == "Spillerstats":
    import tools.stats as stats
    stats.vis_side(spillere, player_events)

elif selected == "Top 5":
    import tools.top5 as top5
    top5.vis_side(spillere, player_events)

elif selected == "Hvidovre IF Truppen":
    import tools.players as players
    players.vis_side(spillere)

elif selected == "Trupsammensætning":
    import tools.squad as squad
    squad.vis_side(spillere)

elif selected == "Sammenligning":
    import tools.comparison as comparison
    comparison.vis_side(spillere, player_events, df_scout)

elif selected == "Scouting-database":
    import tools.scout_input as scout_input
    scout_input.vis_side(spillere)
