import streamlit as st
import pandas as pd

# --- 1. APP OPSÆTNING ---
st.set_page_config(
    page_title="Hvidovre IF - Match & Performance Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. GLOBALE KONSTANTER ---
ACTIVE_SEASON = "2025/2026"
ACTIVE_COMPETITION = "NordicBet Liga"
TEAM_WYID = 7490
COMP_MAP = {
    335: "Superliga",
    328: "NordicBet Liga",
    329: "2. division",
    43319: "3. division",
    331: "Oddset Pokalen",
    1305: "U19 Ligaen"
}

# --- 3. STYLING (FJERNER TOP-PADDING OG GØR DET RENT) ---
st.markdown("""
    <style>
        .stApp { background-color: #FFFFFF; }
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
        header { visibility: hidden; }
        [data-testid="stHeaderBlockContainer"] h1 { display: none; }
        
        /* Gør knapperne mere strømlinede i topmenuen */
        div[data-testid="column"] button {
            width: 100%;
            border-radius: 4px;
            font-weight: 500;
        }
        .main-header { font-size: 22px; font-weight: 700; color: #1a1a1a; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# Initialiser session state til side-navigation hvis den ikke findes
if 'valgt_side' not in st.session_state:
    st.session_state.valgt_side = "Oversigt"

def main():
    # --- 4. TOPMENU MED RIGTIGE KNAPPER OG DROPDOWNS ---
    # Vi opdeler topmenuen i kolonner: Sider + Dropdown-menuer til højre
    col1, col2, col3, col4, col5 = st.columns([1.2, 1.2, 1.5, 1.5, 1.5])
    
    with col1:
        if st.button("Oversigt", use_container_width=True):
            st.session_state.valgt_side = "Oversigt"
    with col2:
        if st.button("Trup", use_container_width=True):
            st.session_state.valgt_side = "Trup"
    with col3:
        if st.button("Kampe & Statistik", use_container_width=True):
            st.session_state.valgt_side = "Kampe"
            
    # Eksempel på en rigtig dropdown-knap (Popover) i topmenuen til turneringer/sæson
    with col4:
        with st.popover("Turnering & Sæson", use_container_width=True):
            st.markdown("<b>Aktiv Sæson:</b> " + ACTIVE_SEASON, unsafe_allow_html=True)
            valgt_comp = st.selectbox(
                "Vælg Turnering",
                options=list(COMP_MAP.keys()),
                format_func=lambda x: COMP_MAP[x],
                index=list(COMP_MAP.keys()).index(328) # Standard NordicBet Liga
            )
            st.write(f"Valgt ID: {valgt_comp}")

    with col5:
        st.markdown(
            f"<div style='text-align: right; font-size: 11px; color: #666; padding-top: 8px;'>"
            f"<b>Team ID:</b> {TEAM_WYID}<br><b>Sæson:</b> {ACTIVE_SEASON}"
            f"</div>", 
            unsafe_allow_html=True
        )

    st.divider()

    # --- 5. RUTEVALG (ROUTER) BASERET PÅ SESSION STATE ---
    if st.session_state.valgt_side == "Oversigt":
        st.markdown('<div class="main-header">Hovedoversigt</div>', unsafe_allow_html=True)
        try:
            from HIF_head import vis_side
            vis_side()
        except ImportError:
            st.warning("Kunne ikke finde 'HIF_head.py'. Sørg for filen ligger i mappen.")

    elif st.session_state.valgt_side == "Trup":
        st.markdown('<div class="main-header">Trupoversigt</div>', unsafe_allow_html=True)
        st.info("Truppens sider under opbygning...")

    elif st.session_state.valgt_side == "Kampe":
        st.markdown('<div class="main-header">Kampoversigt & Statistik</div>', unsafe_allow_html=True)
        st.info("Kampmoduler under opbygning...")

if __name__ == "__main__":
    main()
