import streamlit as st
import pandas as pd
import datetime
from data.utils.team_mapping import TEAMS
from data.data_load import _get_snowflake_conn
from data.sql.opta_queries import get_opta_queries

@st.dialog("Alle Transfers", width="large")
def vis_transfer_dialog(df):
    if df.empty:
        st.write("Ingen data fundet.")
        return
    df_display = df.copy()
    df_display.columns = [str(c).upper().strip() for c in df_display.columns]
    df_display['TS_SORT'] = pd.to_datetime(df_display['TIMESTAMP'], errors='coerce')
    df_display = df_display.sort_values('TS_SORT', ascending=False)
    df_display['Dato'] = df_display['TS_SORT'].dt.strftime('%d/%m-%Y')
    pos_col = 'POSITION' if 'POSITION' in df_display.columns else 'POS'
    df_display['Spiller'] = df_display['NAVN'] + " (" + df_display.get(pos_col, '-').fillna('-') + ")"
    df_display['Skifte'] = df_display['SENESTE_KLUB'].fillna('?') + " ➔ " + df_display['KLUB'].fillna('?')
    st.dataframe(df_display[['Dato', 'Spiller', 'Skifte', 'KILDE']], hide_index=True, use_container_width=True)

def apply_custom_style():
    st.markdown("""
        <style>
            [data-testid="stHeaderBlockContainer"] h1 { display: none; }
            .stApp { background-color: #FFFFFF; }
            .card-title { color: #1a1a1a; font-size: 11px; font-weight: 700; margin-bottom: 12px; text-transform: uppercase; border-bottom: 1px solid #f0f0f0; padding-bottom: 6px; display: flex; justify-content: space-between; }
            .form-wrapper { display: flex; justify-content: space-between; gap: 4px; width: 100%; margin-top: 12px; }
            .res-pill { width: 100%; border-radius: 4px; color: white; text-align: center; font-size: 9px; font-weight: 800; padding: 2px 0; }
            .list-item { font-size: 10px; margin-bottom: 6px; color: #333; display: grid; grid-template-columns: 1fr auto auto auto; align-items: center; gap: 4px; width: 100%; }
        </style>
    """, unsafe_allow_html=True)

def vis_side():
    apply_custom_style()
    conn = _get_snowflake_conn()
    if not conn: return
    
    HIF_UUID = "8GXD9RY2580PU1B1DD5NY9YMY"
    queries = get_opta_queries(liga_f="NordicBet Liga", saeson_f="2025/2026", hif_only=True)
    
    df_matches = conn.query(queries["opta_team_stats"])
    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    
    # Datarens for at undgå NaN-fejl
    for col in ['TOTAL_HOME_SCORE', 'TOTAL_AWAY_SCORE']:
        if col in df_matches.columns:
            df_matches[col] = pd.to_numeric(df_matches[col], errors='coerce').fillna(0).astype(int)
            
    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}

    col1, col2, col3 = st.columns(3)
    
    with col1:
        with st.container(border=True):
            future = df_matches[~df_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]
            if not future.empty:
                nk = future.iloc[0]
                opp_id = nk['CONTESTANTAWAY_OPTAUUID'] if str(nk['CONTESTANTHOME_OPTAUUID']).upper() == HIF_UUID else nk['CONTESTANTHOME_OPTAUUID']
                opp_name = opta_to_name.get(str(opp_id).upper(), "Ukendt")
                st.markdown(f"<div class='card-title'>NÆSTE KAMP vs. {opp_name.upper()}</div>", unsafe_allow_html=True)
                
                f_items = ""
                for _, m in df_matches.head(5).iloc[::-1].iterrows():
                    is_h = str(m['CONTESTANTHOME_OPTAUUID']).upper() == HIF_UUID
                    h_s, a_s = int(m['TOTAL_HOME_SCORE']), int(m['TOTAL_AWAY_SCORE'])
                    res_col = "#28a745" if (is_h and h_s > a_s) or (not is_h and a_s > h_s) else ("#6c757d" if h_s == a_s else "#dc3545")
                    f_items += f"<div style='flex:1;'><div class='res-pill' style='background:{res_col};'>{h_s}-{a_s}</div></div>"
                st.markdown(f"<div class='form-wrapper'>{f_items}</div>", unsafe_allow_html=True)

    with col2:
        with st.container(border=True):
            st.markdown('<div class="card-title">TRANSFERS</div>', unsafe_allow_html=True)
            df_t = pd.read_csv("data/players/1div_overskrivning.csv")
            for _, r in df_t.sort_values('TIMESTAMP', ascending=False).head(5).iterrows():
                st.markdown(f"<div class='list-item'><span>{r['NAVN']}</span><span>{r['KLUB']}</span></div>", unsafe_allow_html=True)
            if st.button("Se alle", key="transfers_btn"): vis_transfer_dialog(df_t)

    with col3:
        with st.container(border=True):
            st.markdown('<div class="card-title">SCOUTING</div>', unsafe_allow_html=True)
