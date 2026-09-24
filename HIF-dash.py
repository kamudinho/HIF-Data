import streamlit as st
import pandas as pd

# --- 1. APP OPSÆTNING ---
st.set_page_config(
    page_title="Hvidovre IF - Match & Performance Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed" # Minimerer sidebaren, da vi bruger topmenu
)

# --- 2. GLOBALE KONSTANTER & VÆRDIER ---
ACTIVE_SEASON = "2026/2027"
ACTIVE_COMPETITION = "NordicBet Liga"
TEAM_WYID = 7490

# --- 3. GLOBAL STYLING ---
st.markdown("""
    <style>
        .stApp { background-color: #FFFFFF; }
        .main-header { font-size: 22px; font-weight: 700; color: #1a1a1a; margin-bottom: 10px; }
        /* Gør radio-knapper mere vandrette og pæne øverst */
        div[data-testid="stHorizontalBlock"] { align-items: center; }
    </style>
""", unsafe_allow_html=True)

def main():
    # --- 4. TOPMENU & INFO ---
    top_col1, top_col2 = st.columns([3, 1])
    
    with top_col1:
        # Vandret navigation
        valgt_side = st.radio(
            "Navigation",
            ["Oversigt (HIF-head)", "Trup & Spillere", "Kampe & Statistik", "Indstillinger"],
            horizontal=True,
            label_visibility="collapsed"
        )
        
    with top_col2:
        st.markdown(f"<div style='text-align: right; font-size: 13px; color: #666;'><b>Sæson:</b> {ACTIVE_SEASON} | <b>Turnering:</b> {ACTIVE_COMPETITION}</div>", unsafe_allow_html=True)

    st.divider()

    # --- 5. RUTEVALG (ROUTER) ---
    if "Oversigt" in valgt_side:
        st.markdown('<div class="main-header">Hovedoversigt</div>', unsafe_allow_html=True)
        try:
            from HIF_head import vis_side
            vis_side()
        except ImportError:
            st.error("Kunne ikke indhente 'HIF_head.py'. Sørg for filen ligger i mappen.")

    elif "Trup" in valgt_side:
        st.markdown('<div class="main-header">Trupoversigt</div>', unsafe_allow_html=True)
        st.info("Truppens sider under opbygning fra scratch...")

    elif "Kampe" in valgt_side:
        st.markdown('<div class="main-header">Kampoversigt & Statistik</div>', unsafe_allow_html=True)
        st.info("Kampmoduler under opbygning fra scratch...")

    elif "Indstillinger" in valgt_side:
        st.markdown('<div class="main-header">App Indstillinger</div>', unsafe_allow_html=True)
        st.write(f"Aktivt Hold ID (WyScout): {TEAM_WYID}")
        st.write(f"Aktiv Sæson: {ACTIVE_SEASON}")

if __name__ == "__main__":
    main()
