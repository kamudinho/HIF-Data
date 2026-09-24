import streamlit as st
import pandas as pd

# --- 1. APP OPSÆTNING ---
st.set_page_config(
    page_title="Hvidovre IF - Match & Performance Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. GLOBALE KONSTANTER & VÆRDIER ---
ACTIVE_SEASON = "2026/2027"
ACTIVE_COMPETITION = "NordicBet Liga"
TEAM_WYID = 7490

# --- 3. GLOBAL STYLING ---
st.markdown("""
    <style>
        .stApp { background-color: #FFFFFF; }
        .main-header { font-size: 24px; font-weight: 700; color: #1a1a1a; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

def main():
    # --- 4. SIDEBAR NAVIGATION ---
    st.sidebar.title("Hvidovre IF")
    st.sidebar.markdown(f"**Sæson:** {ACTIVE_SEASON}")
    st.sidebar.markdown(f"**Turnering:** {ACTIVE_COMPETITION}")
    
    st.sidebar.divider()
    
    valgt_side = st.sidebar.radio(
        "Navigation",
        ["Oversigt (HIF-head)", "Trup & Spillere", "Kampe & Statistik", "Indstillinger"]
    )

    st.sidebar.divider()
    st.sidebar.caption("Data leveret via Snowflake")

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
