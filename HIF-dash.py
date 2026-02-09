import streamlit as st
from streamlit_option_menu import option_menu
import os
import pandas as pd
from sqlalchemy import create_engine, text
from tools import heatmaps, shots, skudmap, dataviz, players, comparison, stats, goalzone, top5, squad

# --- 1. KONFIGURATION & CSS ---
st.set_page_config(
    page_title="HIF Performance Hub", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Indlæser Bootstrap Icons via CDN
st.markdown('<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">', unsafe_allow_html=True)

st.markdown("""
    <style>
        /* RYGER INDHOLDET HELT OP I TOPPEN */
        [data-testid="stSidebarNav"] { display: none; }
        [data-testid="stSidebarUserContent"] {
            padding-top: 0.5rem !important;
            margin-top: -50px !important; 
        }

        /* BOOTSTRAP ICON LOGOUT STYLING */
        .logout-wrapper {
            display: flex;
            align-items: center;
            justify-content: flex-start;
            height: 70px; /* Samme højde som logoet for alignment */
        }
        
        .logout-link {
            color: #d3d3d3 !important;
            font-size: 24px !important;
            text-decoration: none !important;
            transition: 0.3s;
            cursor: pointer;
            margin-left: 10px;
        }
        
        .logout-link:hover {
            color: #cc0000 !important;
            transform: scale(1.1);
        }

        /* SIDEBAR GENEREL STYLING */
        [data-testid="stSidebar"] { min-width: 260px; max-width: 300px; }
        div.row-widget.stRadio > div {
            background-color: #f8f9fb;
            padding: 10px;
            border-radius: 10px;
            border: 1px solid #eceef1;
        }
        .sidebar-header {
            font-size: 0.8rem;
            font-weight: bold;
            color: #6d6d6d;
            margin-top: 10px;
            text-transform: uppercase;
        }
        header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- LOGIN LOGIK (Håndterer logout via URL param) ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# Tjek om brugeren lige har trykket på logout-linket
if st.query_params.get("logout") == "true":
    st.session_state["logged_in"] = False
    st.query_params.clear()
    st.rerun()

if not st.session_state["logged_in"]:
    # ... (Din eksisterende login form her)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown('<div style="text-align:center;"><img src="https://cdn5.wyscout.com/photos/team/public/2659_120x120.png" width="120"></div>', unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; color: Gray;'>HIF Hub</h1>", unsafe_allow_html=True)
        with st.form("login_form"):
            u_input = st.text_input("Brugernavn")
            p_input = st.text_input("Adgangskode", type="password")
            if st.form_submit_button("Log ind", use_container_width=True):
                if u_input.lower() == "kasper" and p_input == "1234":
                    st.session_state["logged_in"] = True
                    st.session_state["user"] = u_input
                    st.rerun()
    st.stop()

# --- 4. DATA LOADING (Antages indlæst korrekt fra din tools-fil) ---
# (df_events, kamp, hold_map, spillere, player_events, df_scout = load_full_data() osv.)

# --- 5. SIDEBAR NAVIGATION ---
with st.sidebar:
    # Top-sektion: Her bruger vi rent HTML til ikonet og logoet
    # Vi bruger 'st.columns' til at skabe strukturen, men HTML indeni for at undgå boks-effekten
    side_top_col1, side_top_col2 = st.columns([1, 4])
    
    with side_top_col1:
        # Ægte Bootstrap Icon uden Streamlit-knap ramme
        st.markdown('''
            <div class="logout-wrapper">
                <a href="/?logout=true" target="_self" class="logout-link" title="Log ud">
                    <i class="bi bi-box-arrow-left"></i>
                </a>
            </div>
        ''', unsafe_allow_html=True)
            
    with side_top_col2:
        st.markdown('<div style="text-align:center;"><img src="https://cdn5.wyscout.com/photos/team/public/2659_120x120.png" width="70"></div>', unsafe_allow_html=True)
    
    st.markdown(f"<p style='text-align:center; margin-top: 5px; margin-bottom: 0px;'>HIF Performance Hub<br><b>{st.session_state['user']}</b></p>", unsafe_allow_html=True)
    st.divider()

    # --- MENUVALG ---
    selected = option_menu(
        menu_title=None,
        options=["HIF DATA", "DATAANALYSE", "STATISTIK", "SCOUTING"],
        icons=["house", "graph-up", "bar-chart", "search"],
        default_index=0,
        styles={
            "container": {"padding": "0!important"},
            "nav-link-selected": {"background-color": "#cc0000"},
            "nav-link": {"font-size": "13px", "padding": "8px"}
        }
    )
    # ... (Resten af din routing logik)
