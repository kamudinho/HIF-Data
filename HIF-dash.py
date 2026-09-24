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

# --- 3. STYLING & HOVER-MENU CSS ---
st.markdown("""
    <style>
        .stApp { background-color: #FFFFFF; }
        .block-container {
            padding-top: 0.8rem !important;
            padding-bottom: 2rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
        header { visibility: hidden; }
        [data-testid="stHeaderBlockContainer"] h1 { display: none; }
        .main-header { font-size: 20px; font-weight: 700; color: #1a1a1a; margin-bottom: 5px; }

        /* --- CSS HOVER DROPDOWN MENU --- */
        .navbar-container {
            display: flex;
            align-items: center;
            gap: 20px;
            background-color: #ffffff;
            padding: 10px 0;
            border-bottom: 1px solid #e0e0e0;
            margin-bottom: 20px;
        }
        .dropdown {
            position: relative;
            display: inline-block;
        }
        .dropbtn {
            background-color: transparent;
            color: #1a1a1a;
            padding: 8px 12px;
            font-size: 14px;
            font-weight: 600;
            border: none;
            cursor: pointer;
            border-radius: 4px;
        }
        .dropdown-content {
            display: none;
            position: absolute;
            background-color: #ffffff;
            min-width: 180px;
            box-shadow: 0px 8px 16px rgba(0,0,0,0.1);
            z-index: 100;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
        }
        .dropdown-content a {
            color: #333;
            padding: 10px 14px;
            text-decoration: none;
            display: block;
            font-size: 13px;
        }
        .dropdown-content a:hover {
            background-color: #f1f1f1;
            color: #000;
        }
        /* Viser undermenuen når musen føres over */
        .dropdown:hover .dropdown-content {
            display: block;
        }
        .dropdown:hover .dropbtn {
            background-color: #f8f9fa;
        }
    </style>
""", unsafe_allow_html=True)

# Initialiser session state
if 'menu_hoved' not in st.session_state:
    st.session_state.menu_hoved = "OVERSIGT"
if 'menu_under' not in st.session_state:
    st.session_state.menu_under = "Hovedoversigt"

def main():
    # Vi bruger query_params til at opfange klik fra vores HTML hover-menu
    query_params = st.query_params
    if "m" in query_params:
        st.session_state.menu_hoved = query_params["m"]
    if "s" in query_params:
        st.session_state.menu_under = query_params["s"]

    # --- 4. TOPMENU MED REN CSS HOVER ---
    # Vi designer topmenuen i HTML, så den reagerer øjeblikkeligt på hover
    st.markdown(f"""
        <div class="navbar-container">
            <div style="font-weight: 700; font-size: 16px; margin-right: 20px;">HVIDOVRE IF</div>
            
            <!-- Oversigt -->
            <div class="dropdown">
                <a href="?m=OVERSIGT&s=Hovedoversigt"><button class="dropbtn">Oversigt</button></a>
            </div>

            <!-- Spilleranalyse med Hover Dropdown -->
            <div class="dropdown">
                <button class="dropbtn">Spilleranalyse ▾</button>
                <div class="dropdown-content">
                    <a href="?m=SPILLERANALYSE&s=Spillerprofil">Spillerprofil</a>
                    <a href="?m=SPILLERANALYSE&s=Spilleroversigt">Spilleroversigt</a>
                    <a href="?m=SPILLERANALYSE&s=Målsekvenser">Målsekvenser</a>
                    <a href="?m=SPILLERANALYSE&s=Spilleraktioner">Spilleraktioner</a>
                    <a href="?m=SPILLERANALYSE&s=Spiller-stats">Spiller-stats</a>
                    <a href="?m=SPILLERANALYSE&s=Spiller-profil">Spiller-profil (2)</a>
                </div>
            </div>

            <!-- Kampanalyse med Hover Dropdown -->
            <div class="dropdown">
                <button class="dropbtn">Kampanalyse ▾</button>
                <div class="dropdown-content">
                    <a href="?m=KAMPANALYSE&s=Kampliste">Kampliste</a>
                    <a href="?m=KAMPANALYSE&s=Holdstatistik">Holdstatistik</a>
                    <a href="?m=KAMPANALYSE&s=XG-analyse">XG-analyse</a>
                </div>
            </div>

            <!-- Info til højre -->
            <div style="margin-left: auto; font-size: 11px; color: #666; text-align: right;">
                <b>Sæson:</b> {ACTIVE_SEASON} | <b>Liga:</b> {ACTIVE_COMPETITION}
            </div>
        </div>
    """, unsafe_allow_html=True)

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
