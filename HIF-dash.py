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
        .main-header { font-size: 20px; font-weight: 700; color: #1a1a1a; margin-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# Initialiser session state til menuen
if 'menu_hoved' not in st.session_state:
    st.session_state.menu_hoved = "OVERSIGT"
if 'menu_under' not in st.session_state:
    st.session_state.menu_under = "Hovedoversigt"

def main():
    # --- 4. TOPMENU (NIVEAU 1: HOVEDKATEGORI) ---
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1.5])
    
    with col1:
        if st.button("Oversigt", use_container_width=True):
            st.session_state.menu_hoved = "OVERSIGT"
            st.session_state.menu_under = "Hovedoversigt"
    with col2:
        if st.button("Spilleranalyse", use_container_width=True):
            st.session_state.menu_hoved = "SPILLERANALYSE"
            st.session_state.menu_under = "Spillerprofil" # Standardvalg i undermenuen
    with col3:
        if st.button("Kampanalyse", use_container_width=True):
            st.session_state.menu_hoved = "KAMPANALYSE"
            st.session_state.menu_under = "Kampliste"
            
    with col4:
        st.markdown(
            f"<div style='text-align: right; font-size: 11px; color: #666; padding-top: 6px;'>"
            f"<b>Sæson:</b> {ACTIVE_SEASON} | <b>Liga:</b> {ACTIVE_COMPETITION}"
            f"</div>", 
            unsafe_allow_html=True
        )

    # --- 4.2 UNDERMENU (NIVEAU 2: BASERET PÅ HOVEDKATEGORI) ---
    m = st.session_state.menu_hoved
    
    if m == "SPILLERANALYSE":
        under_valg = ["Spillerprofil", "Spilleroversigt", "Målsekvenser", "Spilleraktioner", "Spiller-stats", "Spiller-profil"]
        st.session_state.menu_under = st.selectbox("Vælg analyse", under_valg, label_visibility="collapsed")
    elif m == "KAMPANALYSE":
        under_valg = ["Kampliste", "Holdstatistik", "XG-analyse"]
        st.session_state.menu_under = st.selectbox("Vælg analyse", under_valg, label_visibility="collapsed")
    else:
        st.session_state.menu_under = "Hovedoversigt"

    st.divider()

    # --- 5. RUTEVALG (ROUTER MED DIN STRUKTUR) ---
    s = st.session_state.menu_under

    try:
        if m == "OVERSIGT":
            st.markdown('<div class="main-header">Hovedoversigt</div>', unsafe_allow_html=True)
            from HIF_head import vis_side
            vis_side()

        elif m == "SPILLERANALYSE":
            st.markdown(f'<div class="main-header">Spilleranalyse: {s}</div>', unsafe_allow_html=True)
            
            if s == "Spillerprofil":
                import tools.players.player_profile as pp
                pp.vis_side()
            elif s == "Spilleroversigt":
                import tools.players.player_rank as pr
                pr.vis_side()
            elif s == "Målsekvenser":
                import tools.hifanalyse.sequences as ms
                ms.vis_side()
            elif s == "Spilleraktioner":
                import tools.players.player_actions as pa
                pa.vis_side()
            elif s == "Spiller-stats":
                import tools.players.player_stats as ps
                ps.vis_side()
            elif s == "Spiller-profil":
                import tools.players.player_profile2 as pp2
                pp2.vis_side()

        elif m == "KAMPANALYSE":
            st.markdown(f'<div class="main-header">Kampanalyse: {s}</div>', unsafe_allow_html=True)
            st.info(f"Modul for {s} er under opbygning...")

    except ImportError as e:
        st.error(f"Kunne ikke indhente modulet for '{s}'. Tjek at mappen og filstien findes. Detaljer: {e}")
    except Exception as e:
        st.error(f"Der opstod en fejl under indlæsning af siden: {e}")

if __name__ == "__main__":
    main()
