import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    # --- 1. DIN SQL LOGIK (Fra test_matches.py) ---
    conn = _get_snowflake_conn()
    if not conn: return

    DB = "KLUB_HVIDOVREIF.AXIS"
    LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" 
    HIF_UUID = "DYJR458HCMRCY87FSABFSY87O" # Vi tvinger den til HIF

    # ... (Indsæt din fulde WITH MatchBase, StatsPivot, XGPivot query her) ...
    # Vi gemmer plads, men brug præcis den SQL du sendte før.
    
    with st.spinner("Opdaterer dashboard..."):
        df_matches = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)

    if df_matches is None or df_matches.empty:
        st.warning("Ingen data fundet i Snowflake.")
        return

    # --- 2. DATA PREP (Uændret fra din kode) ---
    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
    df_matches['TOTAL_HOME_SCORE'] = pd.to_numeric(df_matches['TOTAL_HOME_SCORE'], errors='coerce').fillna(0)
    df_matches['TOTAL_AWAY_SCORE'] = pd.to_numeric(df_matches['TOTAL_AWAY_SCORE'], errors='coerce').fillna(0)
    
    for col in ['CONTESTANTHOME_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID']:
        df_matches[col] = df_matches[col].astype(str).str.strip().str.upper()

    # --- 3. AUTOMATISK FILTRERING FOR HVIDOVRE ---
    # Vi dropper selectboxen og finder HIF kampe med det samme
    hif_matches = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == HIF_UUID) | 
                             (df_matches['CONTESTANTAWAY_OPTAUUID'] == HIF_UUID)].copy()

    played_p = hif_matches[hif_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].sort_values('MATCH_DATE_FULL', ascending=False)
    future = hif_matches[~hif_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].sort_values('MATCH_DATE_FULL', ascending=True)

    # Beregn S, U, N (Præcis din logik)
    summary = {"K": len(played_p), "S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0}
    for _, m in played_p.iterrows():
        is_h = m['CONTESTANTHOME_OPTAUUID'] == HIF_UUID
        h_s, a_s = int(m['TOTAL_HOME_SCORE']), int(m['TOTAL_AWAY_SCORE'])
        summary["M+"] += h_s if is_h else a_s
        summary["M-"] += a_s if is_h else h_s
        if h_s == a_s: summary["U"] += 1
        elif (is_h and h_s > a_s) or (not is_h and a_s > h_s): summary["S"] += 1
        else: summary["N"] += 1

    # --- 4. DASHBOARD LAYOUT ---
    st.markdown("### HIF Dashboard")
    
    c1, c2, c3 = st.columns(3)
    
    # BOX 1: Næste kamp (Hentet dynamisk fra din 'future' variabel)
    with c1:
        st.caption("##### Næste Kamp")
        with st.container(border=True):
            if not future.empty:
                nk = future.iloc[0]
                er_hjemme = nk['CONTESTANTHOME_OPTAUUID'] == HIF_UUID
                modstander = nk['CONTESTANTAWAY_NAME'] if er_hjemme else nk['CONTESTANTHOME_NAME']
                st.markdown(f"**{modstander}** ({'H' if er_hjemme else 'U'})")
                st.caption(f"Runde {int(nk['WEEK'])} | {nk['MATCH_DATE_FULL'].strftime('%d. %b')}")
            else:
                st.write("Ingen kommende kampe")

    # BOX 2: Form (De 5 seneste resultater)
    with c2:
        st.caption("##### Form (Seneste 5)")
        with st.container(border=True):
            if not played_p.empty:
                f_cols = st.columns(5)
                # Vi tager de 5 nyeste og viser dem
                for i, (_, m) in enumerate(played_p.head(5).iloc[::-1].iterrows()):
                    is_h = m['CONTESTANTHOME_OPTAUUID'] == HIF_UUID
                    h_s, a_s = int(m['TOTAL_HOME_SCORE']), int(m['TOTAL_AWAY_SCORE'])
                    if h_s == a_s: res, col = "U", "#999"
                    elif (is_h and h_s > a_s) or (not is_h and a_s > h_s): res, col = "V", "#28a745"
                    else: res, col = "T", "#dc3545"
                    
                    f_cols[i].markdown(f"<div style='background:{col}; color:white; text-align:center; border-radius:3px; font-weight:bold; font-size:12px;'>{res}</div>", unsafe_allow_html=True)
            else:
                st.write("Ingen data")

    # BOX 3: Sæson Status (Dine S-U-N beregninger)
    with c3:
        st.caption("##### Sæson Status")
        with st.container(border=True):
            st.markdown(f"**{summary['S']}**V - **{summary['U']}**U - **{summary['N']}**T")
            st.caption(f"Mål: {summary['M+']} - {summary['M-']} ({summary['M+']-summary['M-']})")

    # --- 5. DIN STAT-BOX LOGIK (De 6 bokse i bunden) ---
    st.markdown("---")
    st.caption("##### Holdets Snit (Sæson)")
    
    avg_cols = st.columns(6)
    avg_map = [
        ("POSS", "POSS %", 1, "%"), ("XG", "xG", 2, ""), 
        ("XGNP", "xGnp", 2, ""), ("BIG_CHANCES", "STORE CHANCER", 1, ""), 
        ("PASSES", "PASSES", 0, ""), ("FORWARD_PASSES", "FREMADRETTEDE", 0, "")
    ]

    for i, (key, label, dec, suffix) in enumerate(avg_map):
        vals = []
        for _, m in played_p.iterrows():
            pref = "HOME_" if m['CONTESTANTHOME_OPTAUUID'] == HIF_UUID else "AWAY_"
            vals.append(pd.to_numeric(m.get(f"{pref}{key}"), errors='coerce'))
        
        avg_val = np.nanmean(vals) if vals else 0
        fmt = f"{avg_val:.{dec}f}{suffix}" if dec > 0 else f"{int(round(avg_val))}{suffix}"
        
        with avg_cols[i]:
            st.markdown(f"<div class='stat-box'><div class='stat-label'>{label}</div><div class='stat-val'>{fmt}</div></div>", unsafe_allow_html=True)
