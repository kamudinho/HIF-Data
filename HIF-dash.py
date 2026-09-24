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

# --- 3. STYLING OG ENSARTEDE KNAPPER ---
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

        /* Tvinger alle knapper inde i popover/menuer til at have fast størrelse og venstrestillet tekst */
        div[data-testid="stPopover"] button {
            width: 100% !important;
            text-align: left !important;
            justify-content: flex-start !important;
            border-radius: 4px !important;
            font-size: 13px !important;
            padding: 6px 10px !important;
            margin-bottom: 2px !important;
        }
    </style>
""", unsafe_allow_html=True)

# Initialiser session state
if 'menu_hoved' not in st.session_state:
    st.session_state.menu_hoved = "Forside"
if 'menu_under' not in st.session_state:
    st.session_state.menu_under = "Hovedoversigt"

def main():
    # --- 4. TOPMENU MED STABIL DROPDOWN (POPOVER) ---
    col1, col2, col3, col4 = st.columns([1.2, 1.5, 1.5, 2])
    
    with col1:
        if st.button("Oversigt", use_container_width=True):
            st.session_state.menu_hoved = "Forside"
            st.session_state.menu_under = "Hovedoversigt"
            st.rerun()

    # Spilleranalyse (eksempel med mange punkter)
    with col2:
        with st.popover("Spilleranalyse ▾", use_container_width=True):
            if st.button("Spillerprofil", use_container_width=True):
                st.session_state.menu_hoved = "SPILLERANALYSE"
                st.session_state.menu_under = "Spillerprofil"
                st.rerun()
            if st.button("Spilleroversigt", use_container_width=True):
                st.session_state.menu_hoved = "SPILLERANALYSE"
                st.session_state.menu_under = "Spilleroversigt"
                st.rerun()
            if st.button("Målsekvenser", use_container_width=True):
                st.session_state.menu_hoved = "SPILLERANALYSE"
                st.session_state.menu_under = "Målsekvenser"
                st.rerun()
            if st.button("Spilleraktioner", use_container_width=True):
                st.session_state.menu_hoved = "SPILLERANALYSE"
                st.session_state.menu_under = "Spilleraktioner"
                st.rerun()
            if st.button("Spiller-stats", use_container_width=True):
                st.session_state.menu_hoved = "SPILLERANALYSE"
                st.session_state.menu_under = "Spiller-stats"
                st.rerun()
            if st.button("Spiller-profil (2)", use_container_width=True):
                st.session_state.menu_hoved = "SPILLERANALYSE"
                st.session_state.menu_under = "Spiller-profil"
                st.rerun()

    # Kampanalyse (eksempel med færre punkter - de vil nu have præcis samme stil/bredde)
    with col3:
        with st.popover("Kampanalyse ▾", use_container_width=True):
            if st.button("Kampliste", use_container_width=True):
                st.session_state.menu_hoved = "KAMPANALYSE"
                st.session_state.menu_under = "Kampliste"
                st.rerun()
            if st.button("Holdstatistik", use_container_width=True):
                st.session_state.menu_hoved = "KAMPANALYSE"
                st.session_state.menu_under = "Holdstatistik"
                st.rerun()

    with col4:
        st.markdown(
            f"<div style='text-align: right; font-size: 11px; color: #666; padding-top: 8px;'>"
            f"<b>Sæson:</b> {ACTIVE_SEASON} | <b>Liga:</b> {ACTIVE_COMPETITION}"
            f"</div>", 
            unsafe_allow_html=True
        )

    st.divider()

    # Hent aktuelle værdier fra state
    m = st.session_state.menu_hoved
    s = st.session_state.menu_under

    # --- 5. RUTEVALG (ROUTER) ---
    try:
        if m == "OVERSIGT":
            st.markdown(f'<div class="main-header">Hovedoversigt</div>', unsafe_allow_html=True)
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
        st.error(f"Kunne ikke indhente modulet for '{s}'. Tjek at filstien findes. Detaljer: {e}")
    except Exception as e:
        st.error(f"Der opstod en fejl under indlæsning af siden: {e}")

if __name__ == "__main__":
    main()
