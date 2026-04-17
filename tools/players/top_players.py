import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

def vis_side():
    conn = _get_snowflake_conn()

    # --- CSS: Samme styling som før ---
    st.markdown("""
        <style>
        .metric-label { font-weight: bold; font-size: 0.9rem; color: #333; display: flex; align-items: center; height: 40px; }
        .rank-container { position: relative; background-color: #eee; height: 35px; width: 100%; border-radius: 4px; overflow: hidden; display: flex; align-items: center; margin-bottom: 2px; }
        .rank-fill { height: 100%; display: flex; align-items: center; padding-left: 8px; font-weight: bold; color: black; font-size: 0.8rem; }
        .player-header { text-align: center; padding-bottom: 10px; min-height: 110px; }
        .player-img-round { border-radius: 50%; object-fit: cover; border: 2px solid #f0f2f6; }
        </style>
    """, unsafe_allow_html=True)

    # 1. HOLDVALG
    alle_hold = list(TEAMS.keys())
    valgt_navn = st.selectbox("Vælg hold:", alle_hold, index=alle_hold.index("Hvidovre") if "Hvidovre" in alle_hold else 0)
    target_wyid = TEAMS[valgt_navn]["team_wyid"]

    # 2. SQL: Optimeret til at undgå duplikater
    query = f"""
    WITH STATS AS (
        -- Hent gennemsnit for ALLE spillere i ligaen først
        SELECT 
            PLAYER_NAME,
            AVG(DISTANCE) as DIST,
            AVG("HIGH SPEED RUNNING") as HSR,
            MAX(TOP_SPEED) as SPEED,
            AVG(NO_OF_HIGH_INTENSITY_RUNS) as ACCELS
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'
        GROUP BY PLAYER_NAME
    ),
    RANKED AS (
        -- Beregn percentil for hele ligaen
        SELECT *,
            PERCENT_RANK() OVER (ORDER BY DIST DESC) as DIST_PR,
            PERCENT_RANK() OVER (ORDER BY HSR DESC) as HSR_PR,
            PERCENT_RANK() OVER (ORDER BY SPEED DESC) as SPEED_PR,
            PERCENT_RANK() OVER (ORDER BY ACCELS DESC) as ACCELS_PR
        FROM STATS
    ),
    TRUP AS (
        -- Hent din specifikke trup (DISTINCT sikrer én række pr. spiller)
        SELECT DISTINCT
            (FIRSTNAME || ' ' || LASTNAME) as FULL_NAME, 
            SHORTNAME, 
            MAX(IMAGEDATAURL) OVER (PARTITION BY PLAYER_WYID) as IMG
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS
        WHERE CURRENTTEAM_WYID = {target_wyid}
    )
    -- Join og tag de 5 bedste fra det valgte hold
    SELECT DISTINCT
        t.FULL_NAME,
        r.DIST, r.HSR, r.SPEED, r.ACCELS,
        r.DIST_PR, r.HSR_PR, r.SPEED_PR, r.ACCELS_PR,
        t.IMG
    FROM TRUP t
    INNER JOIN RANKED r ON (
        r.PLAYER_NAME = t.FULL_NAME 
        OR r.PLAYER_NAME = t.SHORTNAME
        OR t.FULL_NAME LIKE '%' || r.PLAYER_NAME || '%'
    )
    ORDER BY r.DIST DESC 
    LIMIT 5
    """

    try:
        df = pd.read_sql(query, conn)
        
        # Hvis Smed stadig driller, fjerner vi duplikater i Pandas for en sikkerheds skyld
        df = df.drop_duplicates(subset=['FULL_NAME'])

        if not df.empty:
            st.write("---")
            
            # --- HEADER ---
            cols = st.columns([2, 1, 1, 1, 1, 1])
            with cols[0]: st.write("")
            
            for i, (_, row) in enumerate(df.iterrows()):
                with cols[i+1]:
                    img_url = row['IMG'] if row['IMG'] and str(row['IMG']) != 'None' else "https://via.placeholder.com/150"
                    # Vis kun efternavn for at spare plads
                    efternavn = row['FULL_NAME'].split()[-1]
                    st.markdown(f"""
                        <div class="player-header">
                            <img src="{img_url}" class="player-img-round" width="65" height="65">
                            <br><small><b>{efternavn}</b></small>
                        </div>
                    """, unsafe_allow_html=True)

            # --- METRIC RÆKKER ---
            metrics = [
                ("Total Distance", "DIST_PR"),
                ("High Speed Running", "HSR_PR"),
                ("Top Speed", "SPEED_PR"),
                ("Accelerations", "ACCELS_PR")
            ]

            for label, pr_col in metrics:
                m_cols = st.columns([2, 1, 1, 1, 1, 1])
                with m_cols[0]:
                    st.markdown(f'<div class="metric-label">{label}</div>', unsafe_allow_html=True)
                
                for i, (_, row) in enumerate(df.iterrows()):
                    # Vi beregner rank (0% - 100%)
                    val_pct = (1 - row[pr_col]) * 100
                    
                    # Farve-skala (Grøn til Rød)
                    if val_pct >= 80: color = "#22c55e" # Stærk grøn
                    elif val_pct >= 50: color = "#86efac" # Lys grøn
                    else: color = "#fca5a5" # Rødlig
                    
                    with m_cols[i+1]:
                        st.markdown(f"""
                            <div class="rank-container">
                                <div class="rank-fill" style="width: {max(val_pct, 15)}%; background-color: {color};">
                                    {int(val_pct)}%
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
        else:
            st.info("Ingen match fundet mellem trup og fysiske data.")

    except Exception as e:
        st.error(f"Fejl ved datahentning: {e}")
