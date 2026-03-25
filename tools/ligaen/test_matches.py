import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    st.title("BETINIA LIGAEN | KAMPE")

    # 1. FORBINDELSE
    conn = _get_snowflake_conn()
    if conn is None:
        st.error("❌ Ingen forbindelse til Snowflake.")
        return

    # KONFIGURATION (Tjek om disse matcher din Snowflake-instans)
    DB = "KLUB_HVIDOVREIF.AXIS"
    # Forsøg at hente uden den specifikke UUID først for at se om der overhovedet er data
    sql_query = f"""
    SELECT 
        MATCH_OPTAUUID, MATCH_DATE_FULL, MATCH_LOCALTIME, WEEK, MATCH_STATUS,
        CONTESTANTHOME_OPTAUUID, CONTESTANTHOME_NAME,
        CONTESTANTAWAY_OPTAUUID, CONTESTANTAWAY_NAME,
        TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE
    FROM {DB}.OPTA_MATCHINFO
    WHERE TOTAL_HOME_SCORE IS NOT NULL -- Sikrer vi kun får kampe med data
    ORDER BY MATCH_DATE_FULL DESC
    LIMIT 100
    """

    try:
        df_matches = conn.query(sql_query)
    except Exception as e:
        st.error(f"⚠️ SQL Fejl: {e}")
        return

    # 2. FEJL-CHECK (Hvis df stadig er tom)
    if df_matches is None or df_matches.empty:
        st.warning("⚠️ Databasen returnerede ingen kampe. Tjek om tabellen 'OPTA_MATCHINFO' indeholder data.")
        return

    # Rens kolonnenavne
    df_matches.columns = [c.upper() for c in df_matches.columns]
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')

    # 3. HOLD-MAPPING LOGIK (Forbedret)
    # Vi laver listen over hold baseret på hvad der rent faktisk findes i dataen, 
    # så selectboxen aldrig er tom
    h_names = df_matches['CONTESTANTHOME_NAME'].unique().tolist()
    a_names = df_matches['CONTESTANTAWAY_NAME'].unique().tolist()
    all_teams_in_data = sorted(list(set(h_names + a_names)))

    # Find Hvidovre index hvis det findes
    hif_idx = 0
    for i, name in enumerate(all_teams_in_data):
        if "Hvidovre" in name:
            hif_idx = i
            break

    # 4. UI FILTRE
    valgt_hold = st.selectbox("Vælg hold", all_teams_in_data, index=hif_idx)

    # Filtrering
    df_team = df_matches[
        (df_matches['CONTESTANTHOME_NAME'] == valgt_hold) | 
        (df_matches['CONTESTANTAWAY_NAME'] == valgt_hold)
    ].copy()

    # 5. STATS BEREGNING
    played = df_team[df_team['MATCH_STATUS'].str.lower().str.contains('play|full|finish|stat', na=False)].copy()
    
    s, u, n = 0, 0, 0
    for _, row in played.iterrows():
        h_s = int(row['TOTAL_HOME_SCORE']) if pd.notnull(row['TOTAL_HOME_SCORE']) else 0
        a_s = int(row['TOTAL_AWAY_SCORE']) if pd.notnull(row['TOTAL_AWAY_SCORE']) else 0
        is_home = row['CONTESTANTHOME_NAME'] == valgt_hold
        
        m_score = h_s if is_home else a_s
        o_score = a_s if is_home else h_s
        
        if m_score > o_score: s += 1
        elif m_score == o_score: u += 1
        else: n += 1

    # CSS
    st.markdown("""
        <style>
        .stat-box { text-align: center; background: #f8f9fa; border-radius: 6px; padding: 10px; border-bottom: 3px solid #df003b; }
        .stat-val { font-weight: 800; font-size: 18px; color: #111; }
        .score-pill { background: #222; color: white; border-radius: 4px; padding: 4px 12px; font-weight: bold; font-size: 18px; }
        </style>
    """, unsafe_allow_html=True)

    cols = st.columns(4)
    cols[0].markdown(f"<div class='stat-box'>Kampe<br><span class='stat-val'>{len(played)}</span></div>", unsafe_allow_html=True)
    cols[1].markdown(f"<div class='stat-box'>Sejre<br><span class='stat-val'>{s}</span></div>", unsafe_allow_html=True)
    cols[2].markdown(f"<div class='stat-box'>Uafgjorte<br><span class='stat-val'>{u}</span></div>", unsafe_allow_html=True)
    cols[3].markdown(f"<div class='stat-box'>Nederlag<br><span class='stat-val'>{n}</span></div>", unsafe_allow_html=True)

    # 6. RESULTAT LISTE
    st.write("### Seneste Resultater")
    for _, row in played.iterrows():
        with st.container(border=True):
            c1, sc, c2 = st.columns([2, 1, 2])
            c1.markdown(f"<div style='text-align:right;'><b>{row['CONTESTANTHOME_NAME']}</b></div>", unsafe_allow_html=True)
            sc.markdown(f"<div style='text-align:center;'><span class='score-pill'>{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}</span></div>", unsafe_allow_html=True)
            c2.markdown(f"<div><b>{row['CONTESTANTAWAY_NAME']}</b></div>", unsafe_allow_html=True)
