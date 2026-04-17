import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS
import time

def vis_side():
    try:
        conn = _get_snowflake_conn()
    except Exception as e:
        st.error(f"Forbindelsesfejl: {e}")
        return

    # --- CSS: Tvinger tekst på én linje og optimerer layout ---
    st.markdown("""
        <style>
        .category-header { font-weight: bold; font-size: 1rem; padding: 15px 0 5px 0; color: #111; border-bottom: 2px solid #eee; margin-top: 10px; }
        .metric-label { font-size: 0.8rem; color: #444; display: flex; align-items: center; height: 35px; line-height: 1.1; }
        .rank-container { position: relative; background-color: #f0f0f0; height: 32px; width: 100%; border-radius: 4px; overflow: hidden; display: flex; align-items: center; margin-bottom: 2px; }
        .rank-fill { 
            height: 100%; 
            display: flex; 
            align-items: center; 
            padding-left: 6px; 
            font-weight: bold; 
            color: black; 
            font-size: 0.72rem; 
            white-space: nowrap; 
            min-width: fit-content;
        }
        .player-card { text-align: center; min-height: 100px; }
        .player-img-round { border-radius: 50%; object-fit: cover; border: 2px solid #f0f2f6; background-color: white; }
        </style>
    """, unsafe_allow_html=True)

    # 1. HOLDVALG - Dynamisk key baseret på tid for at undgå "Duplicate Key" fejl
    alle_hold = list(TEAMS.keys())
    col_sel, _ = st.columns([2, 2])
    with col_sel:
        initial_hold = "Hvidovre" if "Hvidovre" in alle_hold else alle_hold[0]
        valgt_navn = st.selectbox(
            "Vælg hold:", 
            alle_hold, 
            index=alle_hold.index(initial_hold), 
            key=f"phys_rank_selector_{int(time.time() / 100)}" # Skifter hver 100. sekund
        )
    
    target_wyid = TEAMS[valgt_navn]["team_wyid"]

    # 2. SQL: Rettede kolonnenavne med anførselstegn (standard i Second Spectrum)
    # Hvis de stadig fejler, er det fordi de præcise navne i din tabel er anderledes.
    query = f"""
    WITH LIGA_STATS AS (
        SELECT 
            PLAYER_NAME,
            AVG(DISTANCE) as DIST,
            AVG("RUNNING DISTANCE") as RUN_DIST,
            AVG("HIGH SPEED RUNNING") as HSR,
            AVG("SPRINT DISTANCE") as SPRINT_DIST,
            MAX(TOP_SPEED) as SPEED,
            AVG(NO_OF_HIGH_INTENSITY_RUNS) as ACCELS
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'
        GROUP BY PLAYER_NAME
    ),
    LIGA_RANKED AS (
        SELECT *,
            RANK() OVER (ORDER BY DIST DESC) as DIST_RANK,
            RANK() OVER (ORDER BY RUN_DIST DESC) as RUN_DIST_RANK,
            RANK() OVER (ORDER BY HSR DESC) as HSR_RANK,
            RANK() OVER (ORDER BY SPRINT_DIST DESC) as SPRINT_DIST_RANK,
            RANK() OVER (ORDER BY SPEED DESC) as SPEED_RANK,
            RANK() OVER (ORDER BY ACCELS DESC) as ACCELS_RANK
        FROM LIGA_STATS
    ),
    VALGT_TRUP AS (
        SELECT 
            (TRIM(FIRSTNAME) || ' ' || TRIM(LASTNAME)) as FULL_NAME,
            MAX(IMAGEDATAURL) as IMG
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS
        WHERE CURRENTTEAM_WYID = {target_wyid}
        GROUP BY 1
    )
    SELECT t.IMG, r.*
    FROM VALGT_TRUP t
    INNER JOIN LIGA_RANKED r ON (
        t.FULL_NAME = r.PLAYER_NAME 
        OR r.PLAYER_NAME LIKE '%' || t.FULL_NAME || '%'
        OR t.FULL_NAME LIKE '%' || r.PLAYER_NAME || '%'
    )
    ORDER BY r.DIST DESC 
    LIMIT 5
    """

    try:
        df = pd.read_sql(query, conn)
        if not df.empty:
            st.write("---")
            
            # --- HEADER ---
            cols = st.columns([2.5, 1, 1, 1, 1, 1])
            with cols[0]: st.write("")
            for i, (_, row) in enumerate(df.iterrows()):
                with cols[i+1]:
                    img_path = row['IMG'] if row['IMG'] and str(row['IMG']) != 'None' else "https://via.placeholder.com/150"
                    efternavn = row['PLAYER_NAME'].split()[-1]
                    st.markdown(f"""
                        <div class="player-card">
                            <img src="{img_path}" class="player-img-round" width="60" height="60">
                            <br><small><b>{efternavn}</b></small>
                        </div>
                    """, unsafe_allow_html=True)

            # --- KATEGORIER ---
            metrics_map = {
                "Volume Metrics": [
                    ("Distance Per 90", "DIST_RANK"),
                    ("Running Distance Per 90", "RUN_DIST_RANK")
                ],
                "High Intensity Metrics": [
                    ("Hi Distance Per 90", "HSR_RANK"),
                    ("Sprint Distance Per 90", "SPRINT_DIST_RANK")
                ],
                "Explosive Metrics": [
                    ("Top Speed", "SPEED_RANK"),
                    ("Accelerations", "ACCELS_RANK")
                ]
            }

            for kat_navn, metrics in metrics_map.items():
                st.markdown(f'<div class="category-header">{kat_navn}</div>', unsafe_allow_html=True)
                for label, col_name in metrics:
                    m_cols = st.columns([2.5, 1, 1, 1, 1, 1])
                    with m_cols[0]:
                        st.markdown(f'<div class="metric-label">{label}</div>', unsafe_allow_html=True)
                    
                    for i, (_, row) in enumerate(df.iterrows()):
                        rank_val = int(row[col_name])
                        fill_width = max(20, (1 - (rank_val / 300)) * 100) if rank_val <= 300 else 20
                        
                        if rank_val <= 20: color = "#22c55e"
                        elif rank_val <= 80: color = "#facc15"
                        else: color = "#fca5a5"
                        
                        with m_cols[i+1]:
                            st.markdown(f"""
                                <div class="rank-container">
                                    <div class="rank-fill" style="width: {fill_width}%; background-color: {color};">
                                        Rank {rank_val}
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
        else:
            st.info("Ingen match fundet.")
    except Exception as e:
        st.error(f"SQL eller Datafejl: {e}")

vis_side()
