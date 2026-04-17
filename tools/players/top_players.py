import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

def vis_side():
    conn = _get_snowflake_conn()

    # --- CSS for at matche stilen præcis ---
    st.markdown("""
        <style>
        .category-header { font-weight: bold; font-size: 1.1rem; padding: 20px 0 10px 0; color: #111; border-bottom: 2px solid #eee; }
        .metric-label { font-size: 0.9rem; color: #444; display: flex; align-items: center; height: 35px; }
        .rank-container { position: relative; background-color: #f0f0f0; height: 30px; width: 100%; border-radius: 3px; overflow: hidden; display: flex; align-items: center; margin-bottom: 2px; }
        .rank-fill { height: 100%; display: flex; align-items: center; padding-left: 8px; font-weight: bold; color: black; font-size: 0.75rem; }
        .player-card { text-align: center; min-height: 120px; }
        .player-img-round { border-radius: 50%; object-fit: cover; border: 2px solid #eee; }
        </style>
    """, unsafe_allow_html=True)

    # 1. HOLDVALG
    alle_hold = list(TEAMS.keys())
    valgt_navn = st.selectbox("Vælg hold:", alle_hold, index=alle_hold.index("Hvidovre") if "Hvidovre" in alle_hold else 0)
    target_wyid = TEAMS[valgt_navn]["team_wyid"]

    # 2. SQL: Nu med alle de rigtige labels fra billedet
    query = f"""
    WITH STATS AS (
        SELECT 
            PLAYER_NAME,
            AVG(DISTANCE) as DIST,
            AVG(RUNNING_DISTANCE) as RUN_DIST,
            AVG("HIGH SPEED RUNNING") as HSR,
            AVG(SPRINT_DISTANCE) as SPRINT_DIST,
            MAX(TOP_SPEED) as SPEED,
            AVG(NO_OF_HIGH_INTENSITY_RUNS) as ACCELS
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'
        GROUP BY PLAYER_NAME
    ),
    RANKED AS (
        SELECT *,
            1 - PERCENT_RANK() OVER (ORDER BY DIST DESC) as DIST_RANK,
            1 - PERCENT_RANK() OVER (ORDER BY RUN_DIST DESC) as RUN_DIST_RANK,
            1 - PERCENT_RANK() OVER (ORDER BY HSR DESC) as HSR_RANK,
            1 - PERCENT_RANK() OVER (ORDER BY SPRINT_DIST DESC) as SPRINT_DIST_RANK,
            1 - PERCENT_RANK() OVER (ORDER BY SPEED DESC) as SPEED_RANK,
            1 - PERCENT_RANK() OVER (ORDER BY ACCELS DESC) as ACCELS_RANK
        FROM STATS
    ),
    TRUP AS (
        -- Vi grupperer her for at undgå at Smed optræder flere gange
        SELECT 
            (FIRSTNAME || ' ' || LASTNAME) as FULL_NAME,
            MAX(IMAGEDATAURL) as IMG
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS
        WHERE CURRENTTEAM_WYID = {target_wyid}
        GROUP BY 1
    )
    SELECT t.*, r.*
    FROM TRUP t
    INNER JOIN RANKED r ON (t.FULL_NAME = r.PLAYER_NAME OR t.FULL_NAME LIKE '%' || r.PLAYER_NAME || '%')
    ORDER BY r.DIST DESC 
    LIMIT 5
    """

    try:
        df = pd.read_sql(query, conn)
        
        if not df.empty:
            # --- TOP: SPILLER PROFILER ---
            cols = st.columns([2.5, 1, 1, 1, 1, 1])
            with cols[0]: st.write("")
            
            for i, (_, row) in enumerate(df.iterrows()):
                with cols[i+1]:
                    img = row['IMG'] if row['IMG'] else "https://via.placeholder.com/150"
                    st.markdown(f"""
                        <div class="player-card">
                            <img src="{img}" class="player-img-round" width="65" height="65">
                            <br><b>{row['FULL_NAME'].split()[-1]}</b>
                        </div>
                    """, unsafe_allow_html=True)

            # --- DEFINER KATEGORIER OG METRICS ---
            kategorier = {
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

            # --- RENDER TABEL ---
            for kat_navn, metrics in kategorier.items():
                st.markdown(f'<div class="category-header">{kat_navn}</div>', unsafe_allow_html=True)
                
                for label, rank_col in metrics:
                    m_cols = st.columns([2.5, 1, 1, 1, 1, 1])
                    with m_cols[0]:
                        st.markdown(f'<div class="metric-label">{label}</div>', unsafe_allow_html=True)
                    
                    for i, (_, row) in enumerate(df.iterrows()):
                        val = row[rank_col] * 100
                        # Farve-logik: Grøn for top, rød for bund (ligesom billedet)
                        color = "#22c55e" if val > 75 else "#86efac" if val > 50 else "#fca5a5"
                        
                        with m_cols[i+1]:
                            st.markdown(f"""
                                <div class="rank-container">
                                    <div class="rank-fill" style="width: {max(val, 15)}%; background-color: {color};">
                                        {int(val)}%
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
        else:
            st.warning("Ingen match fundet for truppen.")
            
    except Exception as e:
        st.error(f"SQL Fejl: {e}")

vis_side()
