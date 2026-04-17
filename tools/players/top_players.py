import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

def vis_side():
    conn = _get_snowflake_conn()

    # --- CSS: Finpudsning af celler og barer ---
    st.markdown("""
        <style>
        .metric-label {
            font-weight: bold;
            font-size: 1rem;
            color: #333;
            display: flex;
            align-items: center;
            height: 40px;
        }
        .rank-container {
            position: relative;
            background-color: #eee; /* Baggrund på tom bar */
            height: 40px;
            width: 100%;
            border-radius: 4px;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: flex-start;
            margin-bottom: 2px;
        }
        .rank-fill {
            height: 100%;
            display: flex;
            align-items: center;
            padding-left: 10px;
            font-weight: bold;
            color: black;
            white-space: nowrap;
        }
        .player-header {
            text-align: center;
            padding-bottom: 10px;
        }
        .player-img-round {
            border-radius: 50%;
            object-fit: cover;
            border: 2px solid #f0f2f6;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- 1. HOLDVALG ---
    alle_hold = list(TEAMS.keys())
    valgt_navn = st.selectbox("Vælg hold:", alle_hold, index=alle_hold.index("Hvidovre") if "Hvidovre" in alle_hold else 0)
    target_wyid = TEAMS[valgt_navn]["team_wyid"]

    # --- 2. SQL ---
    query = f"""
    WITH STATS AS (
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
        SELECT *,
            PERCENT_RANK() OVER (ORDER BY DIST DESC) as DIST_PR,
            PERCENT_RANK() OVER (ORDER BY HSR DESC) as HSR_PR,
            PERCENT_RANK() OVER (ORDER BY SPEED DESC) as SPEED_PR,
            PERCENT_RANK() OVER (ORDER BY ACCELS DESC) as ACCELS_PR
        FROM STATS
    ),
    TRUP AS (
        SELECT (FIRSTNAME || ' ' || LASTNAME) as FULL_NAME, SHORTNAME, IMAGEDATAURL
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS
        WHERE CURRENTTEAM_WYID = {target_wyid}
    )
    SELECT r.*, t.IMAGEDATAURL 
    FROM RANKED r
    JOIN TRUP t ON (r.PLAYER_NAME = t.FULL_NAME OR r.PLAYER_NAME = t.SHORTNAME)
    ORDER BY r.DIST DESC LIMIT 5
    """

    try:
        df = pd.read_sql(query, conn)
        if not df.empty:
            
            # --- HEADER: Spillerbilleder ---
            cols = st.columns([2, 1, 1, 1, 1, 1])
            with cols[0]: st.write("") # Plads til labels
            
            for i, (_, row) in enumerate(df.iterrows()):
                with cols[i+1]:
                    img = row['IMAGEDATAURL'] if row['IMAGEDATAURL'] else "https://via.placeholder.com/150"
                    st.markdown(f"""
                        <div class="player-header">
                            <img src="{img}" class="player-img-round" width="70">
                            <br><b>{row['PLAYER_NAME'].split()[-1]}</b>
                        </div>
                    """, unsafe_allow_html=True)

            # --- RÆKKER: Metrics ---
            # Liste over (Navn, Procent-kolonne, Farve-skala)
            metrics_to_show = [
                ("Distance Per 90", "DIST_PR"),
                ("Hi Distance Per 90", "HSR_PR"),
                ("Top Speed", "SPEED_PR"),
                ("Accelerations", "ACCELS_PR")
            ]

            for label, pr_col in metrics_to_show:
                st.write("") # Padding
                m_cols = st.columns([2, 1, 1, 1, 1, 1])
                
                with m_cols[0]:
                    st.markdown(f'<div class="metric-label">{label}</div>', unsafe_allow_html=True)
                
                for i, (_, row) in enumerate(df.iterrows()):
                    # Vi inverterer pr_col (da PERCENT_RANK 0 er bedst i SQL)
                    val_pct = (1 - row[pr_col]) * 100
                    
                    # Dynamisk farve (Stærk grøn for top, lysere for midt, rødlig for bund)
                    color = "#00ff00" if val_pct > 80 else "#90ee90" if val_pct > 50 else "#ffcccb"
                    
                    with m_cols[i+1]:
                        st.markdown(f"""
                            <div class="rank-container">
                                <div class="rank-fill" style="width: {val_pct}%; background-color: {color};">
                                    {int(val_pct)}%
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
        else:
            st.warning("Ingen spillere fundet for det valgte hold.")
    except Exception as e:
        st.error(f"Der opstod en fejl: {e}")

vis_side()
