import streamlit as st
import pandas as pd
import datetime
from data.utils.team_mapping import TEAMS
from data.data_load import _get_snowflake_conn

def apply_custom_style():
    st.markdown("""
        <style>
            /* Fjern Streamlit standard header */
            [data-testid="stHeaderBlockContainer"] h1 { display: none; }
            [data-testid="stHeader"] { background: rgba(0,0,0,0); }
            
            /* App baggrund */
            .stApp { background-color: #FFFFFF; }
            
            /* Gør kolonnerne mere kompakte */
            [data-testid="stVerticalBlockBorderWrapper"] { 
                min-height: 350px; 
                border-radius: 8px;
                background-color: #ffffff;
            }

            /* Kort-titel styling */
            .card-title {
                color: #1a1a1a;
                font-size: 11px;
                font-weight: 700;
                margin-bottom: 15px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid #f0f0f0;
                padding-bottom: 8px;
            }
            
            .title-date { color: #888; font-weight: 500; text-transform: none; font-size: 11px; }

            /* Statistik tabel i col1 */
            .stats-table {
                width: 100%;
                font-size: 10px;
                border-collapse: collapse;
            }
            .stats-table tr { border-bottom: 1px solid #f9f9f9; }
            .stats-label { color: #666; font-weight: 500; padding: 6px 0; }
            .stats-value { text-align: right; font-weight: 700; color: #111; padding: 6px 0; }

            /* Form-bar (Legends) */
            .form-wrapper {
                display: flex;
                justify-content: space-between;
                gap: 6px;
                width: 100%;
                margin-top: 15px;
            }
            .form-column {
                display: flex;
                flex-direction: column;
                align-items: center;
                flex: 1;
            }
            .res-pill {
                width: 100%;
                border-radius: 3px;
                color: white;
                text-align: center;
                font-size: 9px;
                font-weight: 800;
                padding: 3px 0;
                margin-bottom: 4px;
            }
            .legend-logo { width: 22px; height: 22px; object-fit: contain; }
            
            /* List items (Transfers & Scouting) */
            .list-item {
                font-size: 11px;
                margin-bottom: 8px;
                color: #333;
                line-height: 1.3;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                padding: 2px 0;
            }
            
            /* Knap-styling */
            div.stButton > button {
                font-size: 10px !important;
                padding: 5px 10px !important;
                border-radius: 4px;
            }
        </style>
    """, unsafe_allow_html=True)

# --- Hjælpefunktioner til design ---
def render_card_title(title, date_str=""):
    st.markdown(f"""
        <div class='card-title'>
            <span>{title}</span>
            <span class='title-date'>{date_str}</span>
        </div>
    """, unsafe_allow_html=True)

# --- Sektioner ---
def render_col1_next_match(df_matches, hif_id, opta_to_name):
    with st.container(border=True):
        future = df_matches[~df_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].sort_values('MATCH_DATE_FULL')
        if future.empty:
            st.markdown("<div class='card-title'><span>NÆSTE KAMP</span></div>", unsafe_allow_html=True)
            st.caption("Ingen kommende kampe fundet.")
            return

        nk = future.iloc[0]
        opp_id = nk['CONTESTANTAWAY_OPTAUUID'] if str(nk['CONTESTANTHOME_OPTAUUID']).upper() == hif_id else nk['CONTESTANTHOME_OPTAUUID']
        opp_name = opta_to_name.get(str(opp_id).upper(), "Ukendt Modstander")
        
        render_card_title(f"VS. {opp_name.upper()}", nk['MATCH_DATE_FULL'].strftime('%d/%m'))
        
        # Logoer
        c1, c2, c3 = st.columns([1, 0.6, 1])
        c1.image(TEAMS.get("Hvidovre", {}).get("logo", ""), width=42)
        c2.markdown("<div style='text-align:center; padding-top:12px;'><b style='font-size:10px; color:#ccc;'>VS</b></div>", unsafe_allow_html=True)
        c3.image(TEAMS.get(opp_name, {}).get("logo", ""), width=42)
        
        # Stats
        st.markdown(f"""<table class='stats-table' style='margin-top:10px;'>
            <tr><td class='stats-label'>Mål f/i</td><td class='stats-value'>1.4/1.1</td></tr>
            <tr><td class='stats-label'>xG f/i</td><td class='stats-value'>1.5/1.2</td></tr>
        </table>""", unsafe_allow_html=True)
        
        # Form
        st.markdown(f"<div style='font-size:10px; color:#888; font-weight:700; margin-top:14px; text-transform:uppercase;'>Form: {opp_name}</div>", unsafe_allow_html=True)
        opp_m = df_matches[((df_matches['CONTESTANTHOME_OPTAUUID'] == opp_id) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == opp_id)) & (df_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False))].sort_values('MATCH_DATE_FULL', ascending=False).head(5)
        
        if not opp_m.empty:
            f_items = ""
            for _, m in opp_m.iloc[::-1].iterrows():
                is_h = str(m['CONTESTANTHOME_OPTAUUID']).upper() == str(opp_id).upper()
                h_s, a_s = int(m['TOTAL_HOME_SCORE']), int(m['TOTAL_AWAY_SCORE'])
                res_col = "#28a745" if (is_h and h_s > a_s) or (not is_h and a_s > h_s) else ("#6c757d" if h_s == a_s else "#dc3545")
                o_uuid = m['CONTESTANTAWAY_OPTAUUID'] if is_h else m['CONTESTANTHOME_OPTAUUID']
                o_name = opta_to_name.get(str(o_uuid).upper(), "")
                o_logo = TEAMS.get(o_name, {}).get("logo", "")
                logo_html = f"<img src='{o_logo}' class='legend-logo'>" if o_logo else "<div style='width:26px;'></div>"
                f_items += f"<div class='form-column'><div class='res-pill' style='background:{res_col};'>{h_s}-{a_s}</div>{logo_html}</div>"
            st.markdown(f"<div class='form-wrapper'>{f_items}</div>", unsafe_allow_html=True)

def render_col2_transfers():
    with st.container(border=True):
        render_card_title("TRANSFERS")
        try:
            df_t = pd.read_csv("data/players/1div_overskrivning.csv")
            df_t['TS_SORT'] = pd.to_datetime(df_t['TIMESTAMP'], errors='coerce')
            for _, r in df_t.sort_values('TS_SORT', ascending=False).head(7).iterrows():
                d = pd.to_datetime(r['TIMESTAMP']).strftime('%d/%m')
                st.markdown(f"<div class='list-item'>{d}: <b>{r['NAVN']}</b> ({r.get('POSITION', '-')}) ➔ <b>{r['KLUB']}</b></div>", unsafe_allow_html=True)
            if st.button("Se alle transfers", use_container_width=True):
                vis_transfer_dialog(df_t)
        except: st.caption("Kunne ikke indlæse transfers")

def render_col3_scouting():
    with st.container(border=True):
        render_card_title("SCOUTING")
        try:
            df_e = pd.read_csv("data/scouting/emneliste.csv")
            for _, r in df_e.tail(7).iloc[::-1].iterrows():
                st.markdown(f"<div class='list-item'>⭐ {r.get('Navn', 'Ukendt')} ({r.get('Klub', '-')})</div>", unsafe_allow_html=True)
        except: st.caption("Listen er tom")

# --- Hovedfunktion ---
def vis_side(dp=None):
    apply_custom_style()
    conn = _get_snowflake_conn()
    if not conn: return
    
    # Data hentning
    DB, LIGA_UUID, HIF_UUID = "KLUB_HVIDOVREIF.AXIS", "dyjr458hcmrcy87fsabfsy87o", "8GXD9RY2580PU1B1DD5NY9YMY"
    df_matches = conn.query(f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'")
    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1: render_col1_next_match(df_matches, HIF_UUID.strip().upper(), opta_to_name)
    with col2: render_col2_transfers()
    with col3: render_col3_scouting()
