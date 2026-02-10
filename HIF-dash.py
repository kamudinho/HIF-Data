import streamlit as st
import streamlit_antd_components as sac
import os
import pandas as pd
import importlib

# --- 1. KONFIGURATION ---
st.set_page_config(page_title="HIF Data Hub", layout="wide")

# CSS til styling (Mindre skrift på underpunkter + overskrifter)
st.markdown("""
    <style>
        .block-container { padding-top: 2rem !important; }
        
        /* Gør underpunkter mindre og sikrer de holder sig på én linje */
        .ant-menu-sub .ant-menu-title-content {
            font-size: 12px !important;
            white-space: nowrap !important;
        }
        
        /* Centrerer logo i sidebaren */
        [data-testid="stSidebar"] img {
            display: block;
            margin-left: auto;
            margin-right: auto;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. LOGIN (Forkortet for overblik - behold din egen version her) ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
# ... (indsæt din egen login logik her) ...

# --- 3. IMPORT AF TOOLS ---
def load_module(name):
    try:
        return importlib.import_module(f"tools.{name}")
    except Exception as e:
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
player_shots = load_module("player_shots")
scout_input = load_module("scout_input")

# --- 4. DATA LOADING (Brug din eksisterende load_full_data funktion) ---
# df_events, kamp, hold_map, spillere, player_events, df_scout = load_full_data()

# --- 5. SIDEBAR MENU ---
with st.sidebar:
    st.markdown(
        """
        <div style="display: flex; justify-content: center; padding-top: 10px; margin-bottom: 20px;">
            <img src="https://cdn5.wyscout.com/photos/team/public/2659_120x120.png" width="100">
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Her tilføjer vi accordion=True for at sikre, at kun én mappe er åben
    selected = sac.menu([
        sac.MenuItem('DASHBOARD', icon='house-fill'),
        sac.MenuItem('HOLD', icon='shield', children=[
            sac.MenuItem('Heatmaps'),
            sac.MenuItem('Shotmaps'),
            sac.MenuItem('Zoneinddeling (Hold)'),
            sac.MenuItem('Afslutninger (Hold)'),
            sac.MenuItem('DataViz'),
        ]),
        sac.MenuItem('SPILLERE', icon='person', children=[
            sac.MenuItem('Zoneinddeling (Spiller)'),
            sac.MenuItem('Afslutninger (Spiller)'),
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
    ], 
    format_func='upper', 
    open_all=False, 
    accordion=True,  # <--- DETTE ER NØGLEN TIL DIN EFFEKT
    index=0)

    st.markdown("---")
    if st.button("Log ud", use_container_width=True):
        st.session_state["logged_in"] = False
        st.rerun()
        
# --- 6. ROUTING ---
if selected == 'DASHBOARD':
    st.title("Hvidovre IF Performance Hub")
    st.write("Vælg et værktøj i menuen til venstre.")

# Hold Analyse
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

# Spiller Analyse
elif selected == "Zoneinddeling (Spiller)":
    player_goalzone.vis_side(df_events, spillere)
elif selected == "Afslutninger (Spiller)":
    player_shots.vis_side(df_events, kamp, hold_map)

# Statistik
elif selected == "Spillerstats":
    stats.vis_side(spillere, player_events)
elif selected == "Top 5":
    top5.vis_side(spillere, player_events)

# Scouting
elif selected == "Hvidovre IF":
    players.vis_side(spillere)
elif selected == "Trupsammensætning":
    squad.vis_side(spillere)
elif selected == "Sammenligning":
    comparison.vis_side(spillere, player_events, df_scout)
elif selected == "Scouting-database":
    scout_input.vis_side(spillere)
