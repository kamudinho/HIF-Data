import streamlit as st
from streamlit_option_menu import option_menu
import os
import pandas as pd

# --- 1. KONFIGURATION ---
st.set_page_config(page_title="HIF Data Hub", layout="wide")

st.markdown("""
    <style>
        .block-container { padding-top: 2rem !important; }
        [data-testid="stSidebar"] img { display: block; margin: 0 auto 10px auto; }
        
        /* Gør hoved-vælgeren (omåde) blå og tydelig */
        .area-header {
            background-color: #003366;
            color: white;
            padding: 10px;
            text-align: center;
            border-radius: 5px;
            font-weight: bold;
            margin-bottom: 15px;
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
                    st.rerun()
    st.stop()

# --- 3. DATA LOADING ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
XLSX_PATH = os.path.join(BASE_DIR, 'HIF-data.xlsx')
PARQUET_PATH = os.path.join(BASE_DIR, 'eventdata.parquet')
SHOT_CSV_PATH = os.path.join(BASE_DIR, 'shotevents.csv')

@st.cache_resource
def load_hif_data():
    try:
        ho = pd.read_excel(XLSX_PATH, sheet_name='Hold')
        sp = pd.read_excel(XLSX_PATH, sheet_name='Spillere')
        ka = pd.read_excel(XLSX_PATH, sheet_name='Kampdata')
        pe = pd.read_excel(XLSX_PATH, sheet_name='Playerevents')
        sc = pd.read_excel(XLSX_PATH, sheet_name='Playerscouting')
        ev = pd.read_parquet(PARQUET_PATH) if os.path.exists(PARQUET_PATH) else None
        if ev is not None:
            ev.columns = [str(c).strip().upper() for c in ev.columns]
            # Shot merge (forenklet her for plads)
            if os.path.exists(SHOT_CSV_PATH):
                sd = pd.read_csv(SHOT_CSV_PATH)
                sd.columns = [str(c).strip().upper() for c in sd.columns]
                ev = ev.merge(sd[['EVENT_WYID', 'SHOTXG', 'SHOTONTARGET']].drop_duplicates('EVENT_WYID'), on='EVENT_WYID', how='left')
        h_map = dict(zip(ho['TEAM_WYID'], ho['Hold']))
        return ev, ka, h_map, sp, pe, sc
    except Exception as e:
        st.error(f"Fejl: {e}")
        return None

if "main_data" not in st.session_state:
    st.session_state["main_data"] = load_hif_data()
df_events, kamp, hold_map, spillere, player_events, df_scout = st.session_state["main_data"]

# --- 4. SIDEBAR NAVIGATION (OPDELT) ---
with st.sidebar:
    st.markdown("<div style='text-align: center;'><img src='https://cdn5.wyscout.com/photos/team/public/2659_120x120.png' width='60'></div>", unsafe_allow_html=True)
    
    # TRIN 1: Vælg Hovedområde
    hoved_omraade = option_menu(
        menu_title=None,
        options=["Dashboard", "Truppen", "Analyse", "Scouting"],
        icons=["house", "people", "graph-up", "search"],
        menu_icon="cast", default_index=0,
        styles={"container": {"background-color": "#f0f2f6"}, "nav-link-selected": {"background-color": "#003366"}}
    )
        
    # TRIN 2: Undermenu baseret på valg 
    if hoved_omraade == "Truppen":
        selected = option_menu(
            menu_title=None,
            options=["Oversigt", "Forecast", "Spillerstats", "Top 5"],
            icons=["list", "shimmer", "bar-chart", "trophy"],
            styles={"nav-link-selected": {"background-color": "#cc0000"}}
        )

    elif hoved_omraade == "Analyse":
        selected = option_menu(
            menu_title=None,
            options=["Zoneinddeling", "Afslutninger", "Heatmaps"],
            icons=["grid", "target", "map"],
            styles={"nav-link-selected": {"background-color": "#cc0000"}}
        )

    elif hoved_omraade == "Scouting":
        selected = option_menu(
            menu_title=None,
            options=["Sammenligning", "Scouting-database"],
            icons=["intersect", "database"],
            styles={"nav-link-selected": {"background-color": "#cc0000"}}
        )

# --- 5. ROUTING ---
if selected == "Dashboard":
    st.title("Hvidovre IF Performance Hub")
    st.success(f"Velkommen, {st.session_state.get('user', 'Træner')}")

elif selected == "Oversigt":
    import tools.players as players
    players.vis_side(spillere)

elif selected == "Forecast":
    import tools.squad as squad
    squad.vis_side(spillere)

elif selected == "Zoneinddeling":
    import tools.player_goalzone as pgz
    pgz.vis_side(df_events, spillere)

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
