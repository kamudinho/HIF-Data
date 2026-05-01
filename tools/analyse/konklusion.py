import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, COMPETITIONS, COMPETITION_NAME, TOURNAMENTCALENDAR_NAME
from data.data_load import _get_snowflake_conn

def vis_side(dp=None):
    # --- 1. KONFIGURATION (Fra din mapping-fil) ---
    # Vi henter Opta UUID for 1. Division direkte fra din ordbog
    LIGA_UUID = COMPETITIONS[COMPETITION_NAME]["COMPETITION_OPTAUUID"]

    conn = _get_snowflake_conn()
    if not conn:
        st.error("Kunne ikke forbinde til Snowflake.")
        return

    DB = "KLUB_HVIDOVREIF.AXIS"

    # SQL er rettet til kun at bruge TOURNAMENTCALENDAR_OPTAUUID for at undgå 'SEASONNAME' fejl
    sql = f"""
        WITH MatchBase AS (
            SELECT 
                MATCH_OPTAUUID, 
                MATCH_DATE_FULL, 
                CONTESTANTHOME_OPTAUUID, 
                CONTESTANTAWAY_OPTAUUID,
                TOTAL_HOME_SCORE, 
                TOTAL_AWAY_SCORE, 
                MATCH_STATUS
            FROM {DB}.OPTA_MATCHINFO
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        ),
        StatsPivot AS (
            SELECT 
                MATCH_OPTAUUID, 
                CONTESTANT_OPTAUUID,
                MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL END) AS POSSESSION,
                SUM(CASE WHEN STAT_TYPE = 'totalPass' THEN STAT_TOTAL ELSE 0 END) AS PASSES,
                SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_TOTAL ELSE 0 END) AS SHOTS,
                SUM(CASE WHEN STAT_TYPE = 'touchesInOppBox' THEN STAT_TOTAL ELSE 0 END) AS TOUCHES_IN_BOX
            FROM {DB}.OPTA_MATCHSTATS
            GROUP BY 1, 2
        ),
        XGPivot AS (
            SELECT 
                MATCH_ID, 
                CONTESTANT_OPTAUUID,
                SUM(CASE WHEN STAT_TYPE IN ('expectedGoals', 'expectedGoal') THEN STAT_VALUE ELSE 0 END) AS XG
            FROM {DB}.OPTA_MATCHEXPECTEDGOALS
            GROUP BY 1, 2
        )
        SELECT 
            b.*,
            h.POSSESSION AS HOME_POSS, h.TOUCHES_IN_BOX AS HOME_TOUCHES, hx.XG AS HOME_XG,
            h.PASSES AS HOME_PASSES, h.SHOTS AS HOME_SHOTS,
            a.POSSESSION AS AWAY_POSS, a.TOUCHES_IN_BOX AS AWAY_TOUCHES, ax.XG AS AWAY_XG,
            a.PASSES AS AWAY_PASSES, a.SHOTS AS AWAY_SHOTS
        FROM MatchBase b
        LEFT JOIN StatsPivot h ON b.MATCH_OPTAUUID = h.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = h.CONTESTANT_OPTAUUID
        LEFT JOIN StatsPivot a ON b.MATCH_OPTAUUID = a.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = a.CONTESTANT_OPTAUUID
        LEFT JOIN XGPivot hx ON b.MATCH_OPTAUUID = hx.MATCH_ID AND b.CONTESTANTHOME_OPTAUUID = hx.CONTESTANT_OPTAUUID
        LEFT JOIN XGPivot ax ON b.MATCH_OPTAUUID = ax.MATCH_ID AND b.CONTESTANTAWAY_OPTAUUID = ax.CONTESTANT_OPTAUUID
    """

    with st.spinner("Henter Opta data..."):
        try:
            df_matches = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
        except Exception as e:
            st.error(f"Fejl ved hentning af data: {e}")
            return

    if df_matches is None or df_matches.empty:
        st.warning(f"Ingen data fundet for {COMPETITION_NAME} med UUID {LIGA_UUID}.")
        return

    # --- 2. DATA PREP ---
    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    
    # Filtrer hold baseret på den valgte liga
    liga_hold = {n: i for n, i in TEAMS.items() if i.get("league") == COMPETITION_NAME}
    h_list = sorted(liga_hold.keys())

    # --- 3. UI ---
    st.markdown("## Performance Analyse (Opta)")
    
    col_titel, col_drop = st.columns([3, 1])
    with col_drop:
        hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0
        valgt_hold = st.selectbox("Vælg hold:", h_list, index=hif_idx)
        valgt_uuid = liga_hold[valgt_hold].get("opta_uuid")

    # Filtrer spillede kampe for det valgte hold ved hjælp af Opta UUID
    team_df = df_matches[
        ((df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)) &
        (df_matches['TOTAL_HOME_SCORE'].notnull())
    ].copy()

    if team_df.empty:
        st.info(f"Ingen spillede kampe fundet for {valgt_hold} (UUID: {valgt_uuid}).")
        return

    # --- 4. BEREGNINGER ---
    def get_val(row, base_col):
        pref = "HOME_" if row['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else "AWAY_"
        val = row.get(f"{pref}{base_col}")
        return float(val) if pd.notnull(val) else 0.0

    # Beregn gennemsnit for det valgte hold
    goals_list = []
    for _, r in team_df.iterrows():
        g = r['TOTAL_HOME_SCORE'] if r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else r['TOTAL_AWAY_SCORE']
        goals_list.append(float(g))
    
    avg_goals = np.mean(goals_list)
    avg_xg = team_df.apply(lambda r: get_val(r, 'XG'), axis=1).mean()
    avg_poss = team_df.apply(lambda r: get_val(r, 'POSS'), axis=1).mean()
    avg_shots = team_df.apply(lambda r: get_val(r, 'SHOTS'), axis=1).mean()
    avg_touches = team_df.apply(lambda r: get_val(r, 'TOUCHES'), axis=1).mean()

    # --- 5. VISNING ---
    r1c1, r1c2 = st.columns(2)
    with r1c1:
        with st.container(border=True):
            st.markdown(f"**Mål vs xG ({valgt_hold})**")
            st.metric("Mål snit", f"{avg_goals:.2f}")
            st.metric("xG snit", f"{avg_xg:.2f}", delta=f"{avg_goals - avg_xg:.2f}")

    with r1c2:
        with st.container(border=True):
            st.markdown(f"**Produktion i feltet**")
            st.write(f"Afslutninger: **{avg_shots:.1f}**")
            st.write(f"Berøringer i feltet: **{avg_touches:.1f}**")
            st.write(f"Boldbesiddelse: **{avg_poss:.1f}%**")
