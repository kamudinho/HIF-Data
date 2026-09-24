import streamlit as st
import pandas as pd

# --- 1. APP OPSÆTNING ---
st.set_page_config(
    page_title="Hvidovre IF - Match & Performance Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. GLOBALE KONSTANTER ---
ACTIVE_SEASON = "2026/2027"
ACTIVE_COMPETITION = "NordicBet Liga"
TEAM_WYID = 7490

# --- 3. STYLING (FJERNER STANDARD TOP-PADDING OG GØR DEN REN) ---
st.markdown("""
    <style>
        /* Fjerner Streamlits standard top-margin og padding, så alt rykkes helt op */
        .stApp { background-color: #FFFFFF; }
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
        /* Skjul standard Streamlit header elementer */
        [data-testid="stHeaderBlockContainer"] h1 { display: none; }
        header { visibility: hidden; }
        
        .main-header { font-size: 22px; font-weight: 700; color: #1a1a1a; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

def main():
    # --- 4. TOPMENU / NAVIGATION (HELT OPPE I TOPPEN) ---
    col1, col2 = st.columns([3, 1])
    
    with col1:
        valgt_side = st.radio(
            "Navigation",
            ["Oversigt (HIF-head)", "Trup & Spillere", "Kampe & Statistik", "Indstillinger"],
            horizontal=True,
            label_visibility="collapsed"
        )
        
    with col2:
        st.markdown(
            f"<div style='text-align: right; font-size: 12px; color: #666; padding-top: 5px;'>"
            f"<b>Sæson:</b> {ACTIVE_SEASON} | <b>Turnering:</b> {ACTIVE_COMPETITION}"
            f"</div>", 
            unsafe_allow_html=True
        )

    st.divider()

    # --- 5. RUTEVALG (ROUTER) ---
    if "Oversigt" in valgt_side:
        st.markdown('<div class="main-header">Hovedoversigt</div>', unsafe_allow_html=True)
        try:
            from HIF_head import vis_side
            vis_side()
        except ImportError:
            st.warning("Kunne ikke finde 'HIF_head.py'. Sørg for filen ligger i mappen.")

    elif "Trup" in valgt_side:
        st.markdown('<div class="main-header">Trupoversigt</div>', unsafe_allow_html=True)
        st.info("Truppens sider under opbygning...")

    elif "Kampe" in valgt_side:
        st.markdown('<div class="main-header">Kampoversigt & Statistik</div>', unsafe_allow_html=True)
        st.info("Kampmoduler under opbygning...")

    elif "Indstillinger" in valgt_side:
        st.markdown('<div class="main-header">App Indstillinger</div>', unsafe_allow_html=True)
        st.write(f"Aktivt Hold ID: {TEAM_WYID}")
        st.write(f"Aktiv Sæson: {ACTIVE_SEASON}")

if __name__ == "__main__":
    main()
