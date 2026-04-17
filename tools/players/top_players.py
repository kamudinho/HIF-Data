import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

def vis_side():
    conn = _get_snowflake_conn()

    # --- 1. HOLDVALG ---
    alle_hold = list(TEAMS.keys())
    valgt_navn = st.selectbox("Vælg hold:", alle_hold)
    target_wyid = TEAMS[valgt_navn]["team_wyid"]

    st.write(f"### Data-inspektion for {valgt_navn}")
    
    # Opret Tabs til at vise de forskellige trin i processen
    tab1, tab2, tab3 = st.tabs(["📋 Trup (Wyscout/Opta)", "🏃 SS Fysisk Data", "🏆 Endelig Top 5"])

    # --- TAB 1: TRUP QUERY ---
    with tab1:
        st.markdown("**Formål:** Henter alle navne-varianter og billeder for at sikre match.")
        trup_sql = f"""
        SELECT 
            (TRIM(w.FIRSTNAME) || ' ' || TRIM(w.LASTNAME)) as FULL_NAME,
            w.SHORTNAME,
            o.MATCH_NAME as OPTA_MATCH_NAME,
            w.PLAYER_WYID,
            w.IMAGEDATAURL
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS w
        LEFT JOIN KLUB_HVIDOVREIF.AXIS.OPTA_PLAYERS o ON w.PLAYER_WYID = o.PLAYER_WYID
        WHERE w.CURRENTTEAM_WYID = {target_wyid}
        """
        df_trup = pd.read_sql(trup_sql, conn)
        st.dataframe(df_trup, use_container_width=True)

    # --- TAB 2: SS QUERY ---
    with tab2:
        st.markdown("**Formål:** Viser gennemsnitlig data fra Second Spectrum for ALLE spillere i ligaen.")
        ss_sql = """
        SELECT 
            PLAYER_NAME,
            AVG(DISTANCE) as DIST, 
            AVG("HIGH SPEED RUNNING") as HSR, 
            MAX(TOP_SPEED) as SPEED
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'
        GROUP BY PLAYER_NAME
        """
        df_ss = pd.read_sql(ss_sql, conn)
        st.dataframe(df_ss, use_container_width=True)

    # --- TAB 3: JOINED QUERY (RESULTATET) ---
    with tab3:
        st.markdown("**Formål:** Det endelige resultat hvor vi kobler truppen med fysisk data.")
        # Her bruger vi din store kombinerede query
        final_sql = f"""
        WITH HVI_TRUP AS ({trup_sql}),
             SS_PHYSICAL AS ({ss_sql})
        SELECT 
            w.FULL_NAME,
            s.*,
            COALESCE(w.IMAGEDATAURL, 'https://via.placeholder.com/150') as FINAL_IMAGE_URL
        FROM HVI_TRUP w
        INNER JOIN SS_PHYSICAL s ON (
            s.PLAYER_NAME = w.FULL_NAME 
            OR s.PLAYER_NAME = w.SHORTNAME
            OR s.PLAYER_NAME = w.OPTA_MATCH_NAME
            OR w.FULL_NAME LIKE '%' || s.PLAYER_NAME || '%'
            OR s.PLAYER_NAME LIKE '%' || w.SHORTNAME || '%'
        )
        ORDER BY s.DIST DESC 
        LIMIT 5
        """
        df_final = pd.read_sql(final_sql, conn)
        
        # Vis de visuelle bars (din eksisterende visning)
        for _, row in df_final.iterrows():
            col1, col2 = st.columns([1, 4])
            with col1:
                st.image(row['FINAL_IMAGE_URL'], width=60)
            with col2:
                st.write(f"**{row['FULL_NAME']}**")
                st.progress(min(row['DIST']/12000, 1.0)) # Eksempel bar
                st.caption(f"{row['DIST']:.0f}m | {row['SPEED']} km/t")
