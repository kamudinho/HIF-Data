import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

def load_player_overrides():
    """Henter din manuelle liste over klubskifter fra en lokal CSV."""
    try:
        # Forventer en CSV med: PLAYER_NAME, CORRECT_TEAM_WYID
        df_overrides = pd.read_csv("data/player_overrides.csv")
        # Lav det til et dictionary for hurtig opslag: { 'Navn': 7490 }
        return dict(zip(df_overrides['PLAYER_NAME'], df_overrides['CORRECT_TEAM_WYID']))
    except FileNotFoundError:
        return {}

def vis_side():
    try:
        conn = _get_snowflake_conn()
    except Exception as e:
        st.error(f"Forbindelsesfejl: {e}")
        return

    # 1. Hent overrides (f.eks. at Kornelius Hansen kun må vises for AaB)
    player_overrides = load_player_overrides()

    # --- CSS ---
    st.markdown("""
        <style>
        .category-header { font-weight: bold; font-size: 1rem; padding: 15px 0 5px 0; color: #111; border-bottom: 2px solid #eee; margin-top: 10px; }
        .metric-label { font-size: 0.8rem; color: #444; display: flex; align-items: center; height: 35px; }
        .rank-container { position: relative; background-color: #f0f0f0; height: 32px; width: 100%; border-radius: 4px; overflow: hidden; display: flex; align-items: center; margin-bottom: 2px; }
        .rank-fill { height: 100%; display: flex; align-items: center; padding-left: 8px; font-weight: bold; color: black; font-size: 0.75rem; white-space: nowrap; }
        .player-card { text-align: center; min-height: 100px; }
        .player-img-round { border-radius: 50%; object-fit: cover; border: 2px solid #f0f2f6; background-color: white; }
        </style>
    """, unsafe_allow_html=True)

    # 2. HOLDVALG
    alle_hold = list(TEAMS.keys())
    col_sel, _ = st.columns([2, 2])
    with col_sel:
        valgt_navn = st.selectbox("Vælg hold:", alle_hold, key="phys_rank_stable_final")
    
    target_wyid = TEAMS[valgt_navn]["team_wyid"]

    # 3. SQL (Henter data for alle potentielle spillere)
    query = f"""
    WITH LIGA_STATS AS (
        SELECT 
            PLAYER_NAME,
            AVG(DISTANCE) as DIST,
            AVG(RUNNING) as RUN_DIST,
            AVG("HIGH SPEED RUNNING") as HSR,
            AVG(SPRINTING) as SPRINT_DIST,
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
    SELECT t.IMG, r.* FROM VALGT_TRUP t
    INNER JOIN LIGA_RANKED r ON (t.FULL_NAME = r.PLAYER_NAME OR r.PLAYER_NAME LIKE '%' || t.FULL_NAME || '%')
    """

    try:
        df = pd.read_sql(query, conn)
        
        # --- 4. OVERRIDE LOGIK: Filtrering baseret på din CSV ---
        if not df.empty and player_overrides:
            # Vi beholder kun spilleren, hvis:
            # a) Han ikke er i override-listen
            # b) Han er i listen, og vi kigger på den rigtige klub
            df = df[df.apply(lambda x: player_overrides.get(x['PLAYER_NAME'], target_wyid) == target_wyid, axis=1)]

        if not df.empty:
            df = df.sort_values("DIST_RANK").head(5) # Vis top 5 efter distance
            st.write("---")
            
            # --- RENDER LOGIK (samme som før) ---
            cols = st.columns([2.5, 1, 1, 1, 1, 1])
            with cols[0]: st.write("")
            for i, (_, row) in enumerate(df.iterrows()):
                with cols[i+1]:
                    img = row['IMG'] if row['IMG'] and str(row['IMG']) != 'None' else "https://via.placeholder.com/150"
                    st.markdown(f'<div class="player-card"><img src="{img}" class="player-img-round" width="60" height="60"><br><small><b>{row["PLAYER_NAME"].split()[-1]}</b></small></div>', unsafe_allow_html=True)

            metrics_map = {
                "Volume Metrics": [("Total Distance", "DIST_RANK"), ("Running Distance", "RUN_DIST_RANK")],
                "High Intensity Metrics": [("Hi Distance", "HSR_RANK"), ("Sprint Distance", "SPRINT_DIST_RANK")],
                "Explosive Metrics": [("Top Speed", "SPEED_RANK"), ("Accelerations", "ACCELS_RANK")]
            }

            for kat_navn, metrics in metrics_map.items():
                st.markdown(f'<div class="category-header">{kat_navn}</div>', unsafe_allow_html=True)
                for label, col_name in metrics:
                    m_cols = st.columns([2.5, 1, 1, 1, 1, 1])
                    with m_cols[0]: st.markdown(f'<div class="metric-label">{label}</div>', unsafe_allow_html=True)
                    for i, (_, row) in enumerate(df.iterrows()):
                        rank_val = int(row[col_name])
                        fill_width = max(25, (1 - (rank_val / 300)) * 100) if rank_val <= 300 else 25
                        color = "#22c55e" if rank_val <= 20 else "#facc15" if rank_val <= 80 else "#fca5a5"
                        with m_cols[i+1]:
                            st.markdown(f'<div class="rank-container"><div class="rank-fill" style="width: {fill_width}%; background-color: {color};">Rank {rank_val}</div></div>', unsafe_allow_html=True)
        else:
            st.info("Ingen spillere fundet.")
    except Exception as e:
        st.error(f"Fejl: {e}")

vis_side()
