import streamlit as st
import pandas as pd
import numpy as np
import re
from data.data_load import _get_snowflake_conn

# --- FORBEDRET KONTRAKT-BEREGNING ---
def beregn_aar(start, slut):
    try:
        s_match = re.search(r'20\d{2}', str(start))
        e_match = re.search(r'20\d{2}', str(slut))
        
        if s_match and e_match:
            s_year = int(s_match.group())
            e_year = int(e_match.group())
            diff = e_year - s_year
            if 0 < diff < 10:
                return f"{slut} ({diff} år)"
    except:
        pass
    return slut

# --- POPUP VINDUE ---
@st.dialog("Alle Transfers - 1. Division", width="large")
def vis_alle_transfers(df):
    df_display = df.copy()
    df_display['Dato'] = pd.to_datetime(df_display['TIMESTAMP']).dt.strftime('%d/%m-%Y')
    df_display['Transfer'] = df_display['SENESTE_KLUB'].fillna('?') + " ➔ " + df_display['KLUB'].fillna('?')
    
    df_display['Kontrakt'] = df_display.apply(
        lambda x: beregn_aar(x['KONTRAKT_START'], x['KONTRAKT_UDLOEB']), axis=1
    )

    cols_to_show = {
        'Dato': 'Dato',
        'NAVN': 'Spiller',
        'POSITION': 'Pos',
        'Transfer': 'Transfer',
        'Kontrakt': 'Kontrakt',
        'KILDE': 'Kilde'
    }
    
    st.dataframe(
        df_display[list(cols_to_show.keys())].rename(columns=cols_to_show),
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Kilde": st.column_config.LinkColumn(
                "Kilde",
                display_text=r"^https?://(?:www\.)?([^/]+)"
            )
        }
    )

def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn: return

    # --- CONFIG ---
    DB = "KLUB_HVIDOVREIF.AXIS"
    LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" 
    HIF_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"   

    # --- DATA LOAD ---
    sql = f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"
    df_matches = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
    if df_matches is None or df_matches.empty: return

    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    hif_id = str(HIF_UUID).strip().lower()
    df_matches['HOME_ID'] = df_matches['CONTESTANTHOME_OPTAUUID'].astype(str).str.strip().str.lower()
    df_matches['AWAY_ID'] = df_matches['CONTESTANTAWAY_OPTAUUID'].astype(str).str.strip().str.lower()
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
    
    hif_m = df_matches[(df_matches['HOME_ID'] == hif_id) | (df_matches['AWAY_ID'] == hif_id)].copy()
    future = hif_m[~hif_m['MATCH_STATUS'].str.upper().str.contains('PLAY|FULL|FINISH|FT', na=False)].sort_values('MATCH_DATE_FULL', ascending=True)

    # --- DASHBOARD LAYOUT ---
    col1, col2, col3 = st.columns([1.2, 1, 1])

    with col1:
        st.caption("##### Næste Modstander")
        with st.container(border=True):
            if not future.empty:
                nk = future.iloc[0]
                er_hjemme = nk['HOME_ID'] == hif_id
                opp_id, opp_name = (nk['AWAY_ID'], nk['CONTESTANTAWAY_NAME']) if er_hjemme else (nk['HOME_ID'], nk['CONTESTANTHOME_NAME'])
                loc, dato, runde = ("H" if er_hjemme else "U"), nk['MATCH_DATE_FULL'].strftime('%d/%m'), int(nk['WEEK'])
                st.markdown(f"<div style='display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px;'><span style='font-size:16px;font-weight:bold;'>{opp_name} ({loc})</span><span style='font-size:11px;color:#666;'>R. {runde} • {dato}</span></div>", unsafe_allow_html=True)
                
                opp_m = df_matches[((df_matches['HOME_ID'] == opp_id) | (df_matches['AWAY_ID'] == opp_id)) & (df_matches['MATCH_STATUS'].str.upper().str.contains('PLAY|FULL|FINISH|FT'))].sort_values('MATCH_DATE_FULL', ascending=False).head(5)
                if not opp_m.empty:
                    m_list = opp_m.iloc[::-1]
                    # Optimeret bredde på legends med gap control
                    f_cols = st.columns(5, gap="small")
                    for i, (_, m) in enumerate(m_list.iterrows()):
                        is_h_opp = m['HOME_ID'] == opp_id
                        h_s, a_s = int(m['TOTAL_HOME_SCORE']), int(m['TOTAL_AWAY_SCORE'])
                        mod_kort = m['CONTESTANTAWAY_NAME'][:3] if is_h_opp else m['CONTESTANTHOME_NAME'][:3]
                        res, col = (("U", "#999") if h_s == a_s else (("V", "#28a745") if (is_h_opp and h_s > a_s) or (not is_h_opp and a_s > h_s) else ("T", "#dc3545")))
                        with f_cols[i]:
                            st.markdown(f"<div style='background:{col};color:white;text-align:center;border-radius:2px;font-weight:bold;font-size:10px;padding:2px;'>{res}</div><div style='text-align:center;font-size:9px;color:#444;margin-top:3px;line-height:1.1;'>{h_s}-{a_s}<br>{mod_kort.upper()}</div>", unsafe_allow_html=True)
            else: st.write("Sæson slut")

    with col2:
        st.caption("##### Transfers")
        with st.container(border=True):
            try:
                df_t_raw = pd.read_csv("data/players/1div_overskrivning.csv")
                df_t = df_t_raw.dropna(subset=['TIMESTAMP']).copy()
                if not df_t.empty:
                    df_t['TS_CLEAN'] = pd.to_datetime(df_t['TIMESTAMP'], errors='coerce')
                    df_t = df_t.sort_values('TS_CLEAN', ascending=False)
                    for _, r in df_t.head(8).iterrows():
                        ts_txt = r['TS_CLEAN'].strftime('%d/%m')
                        pos = f" ({r['POSITION']})" if pd.notnull(r.get('POSITION')) else ""
                        st.markdown(f"<p style='font-size:12px;margin:0;line-height:1.4;'><span style='color:#888;'>{ts_txt}</span> <b>{r['KLUB']}</b>: {r['NAVN']}{pos}</p>", unsafe_allow_html=True)
                    
                    st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
                    if st.button("Se alle transfers", use_container_width=True):
                        vis_alle_transfers(df_t)
                else: st.caption("Afventer data...")
            except: st.caption("Fejl i data")

    with col3:
        st.caption("##### Scouting")
        with st.container(border=True):
            try:
                df_e = pd.read_csv("data/scouting/emneliste.csv").tail(8)
                for _, r in df_e.iterrows():
                    st.markdown(f"<p style='font-size:11px;margin:0;line-height:1.3;'>⭐ <b>{r.get('Navn', 'Ukendt')}</b> ({r.get('Klub', '-')})</p>", unsafe_allow_html=True)
            except: st.caption("Listen er tom")

    st.divider()
