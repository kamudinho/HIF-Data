import streamlit as st
import pandas as pd

# Importér din nye trup-side
try:
    from pages.modstanderanalyse import vis_side
except ImportError:
    vis_trup_side = None

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

# --- 3. STYLING ---
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
        div[data-testid="column"] button {
            width: 100%;
            border-radius: 4px;
            font-weight: 500;
        }
        .main-header { font-size: 22px; font-weight: 700; color: #1a1a1a; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

if 'valgt_side' not in st.session_state:
    st.session_state.valgt_side = "Oversigt"

def main():
    # --- 4. TOPMENU ---
    col1, col2, col3, col4 = st.columns([1.2, 1.2, 1.5, 2.1])
    
    with col1:
        if st.button("Oversigt", use_container_width=True):
            st.session_state.valgt_side = "Oversigt"
    with col2:
        if st.button("Modstanderanalyse", use_container_width=True):
            st.session_state.valgt_side = "Modstanderanalyse"
    with col3:
        if st.button("Kampe & Statistik", use_container_width=True):
            st.session_state.valgt_side = "Kampe"
            
    with col4:
        st.markdown(
            f"<div style='text-align: right; font-size: 11px; color: #666; padding-top: 8px;'>"
            f"<b>Team ID:</b> {TEAM_WYID} | <b>Sæson:</b> {ACTIVE_SEASON}"
            f"</div>", 
            unsafe_allow_html=True
        )

    st.divider()

    # --- 5. RUTEVALG (ROUTER) ---
    if st.session_state.valgt_side == "Oversigt":
        try:
            from HIF_head import vis_side
            vis_side()
        except ImportError:
            st.warning("Kunne ikke finde 'HIF_head.py'. Sørg for filen ligger i mappen.")

    elif st.session_state.valgt_side == "Trup":
        if vis_trup_side:
            vis_trup_side(TEAM_WYID, ACTIVE_SEASON)
        else:
            st.error("Kunne ikke indlæse 'pages/trup.py'.")

    elif st.session_state.valgt_side == "Kampe":
        st.markdown('<div class="main-header">Kampoversigt & Statistik</div>', unsafe_allow_html=True)
        st.info("Kampmoduler under opbygning...")

if __name__ == "__main__":
    main()
