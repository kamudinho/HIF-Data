import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

def load_player_overrides():
    try:
        df_overrides = pd.read_csv("data/player_overrides.csv")
        overrides = {row['PLAYER_NAME'].strip(): TEAMS[row['TEAM_NAME'].strip()]["team_wyid"] 
                     for _, row in df_overrides.iterrows() if row['TEAM_NAME'].strip() in TEAMS}
        return overrides
    except:
        return {}

def vis_side():
    try:
        conn = _get_snowflake_conn()
    except Exception as e:
        st.error(f"Forbindelsesfejl: {e}")
        return

    player_overrides = load_player_overrides()

    # --- CSS ---
    st.markdown("""
        <style>
        .category-header { font-weight: bold; font-size: 1rem; padding: 15px 0 5px 0; color: #111; border-bottom: 2px solid #eee; margin-top: 10px; }
        .metric-label { font-size: 0.8rem; color: #444; display: flex; align-items: center; height: 35px; line-height: 1.1; }
        .rank-container { position: relative; background-color: #f0f0f0; height: 32px; width: 100%; border-radius: 4px; overflow: hidden; display: flex; align-items: center; margin-bottom: 2px; }
        .rank-fill { height: 100%; display: flex; align-items: center; padding-left: 8px; font-weight: bold; color: black; font-size: 0.72rem; white-space: nowrap; min-width: fit-content; }
        .player-card { text-align: center; min-height: 100px; }
        .player-img-round { border-radius: 50%; object-fit: cover; border: 2px solid #f0f2f6; background-color: white; }
        </style>
    """, unsafe_allow_html=True)

    # --- TOP BAR ---
    col1, col2 = st.columns([2, 2])
    with col1:
        valgt_navn = st.selectbox("Vælg hold:", list(TEAMS.keys()), key="final_opta_v8")
        target_id = TEAMS[valgt_navn]["team_wyid"]
    with col2:
        mode = st.radio("Vælg data-visning:", ["Fysiske Data (SS)", "Tekniske Data (Opta)"], horizontal=True)

    # --- SQL LOGIK ---
    if mode == "Fysiske Data (SS)":
        table = "KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS"
        sql_metrics = """
            AVG(DISTANCE) as M1, AVG(RUNNING) as M2, AVG("HIGH SPEED RUNNING") as M3,
            AVG(SPRINTING) as M4, MAX(TOP_SPEED) as M5, AVG(NO_OF_HIGH_INTENSITY_RUNS) as M6
        """
        date_filter = "WHERE MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'"
        metrics_labels = {
            "Volume": [("Total Distance", "M1_RANK"), ("Running Distance", "M2_RANK")],
            "Intensity": [("Hi Distance", "M3_RANK"), ("Sprint Distance", "M4_RANK")],
            "Explosive": [("Top Speed", "M5_RANK"), ("Accelerations", "M6_RANK")]
        }
        main_rank_col = "M1_RANK"
    else:
        # KOMBINERET OPTA QUERY
        sql_metrics = """
            AVG(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_TOTAL END) as M1,
            AVG(CASE WHEN STAT_TYPE = 'goalAssist' THEN STAT_TOTAL END) as M2,
            AVG(CASE WHEN STAT_TYPE = 'totalPass' THEN STAT_TOTAL END) as M3,
            AVG(CASE WHEN STAT_TYPE = 'accuratePass' THEN STAT_TOTAL END) as M4,
            AVG(CASE WHEN STAT_TYPE = 'wonTackle' THEN STAT_TOTAL END) as M5,
            AVG(CASE WHEN STAT_TYPE = 'totalClearance' THEN STAT_TOTAL END) as M6
        """
        table = "KLUB_HVIDOVREIF.AXIS.OPTA_MATCHSTATS"
        date_filter = "" # MatchStats tabellen har ikke altid MATCH_DATE direkte, vi aggregerer alt
        metrics_labels = {
            "Attacking": [("Shots", "M1_RANK"), ("Assists", "M2_RANK")],
            "Passing": [("Total Passes", "M3_RANK"), ("Accurate Passes", "M4_RANK")],
            "Defensive": [("Won Tackles", "M5_RANK"), ("Clearances", "M6_RANK")]
        }
        main_rank_col = "M1_RANK"

    query = f"""
    WITH LIGA_STATS AS (
        SELECT PLAYER_NAME, {sql_metrics} FROM {table} {date_filter} GROUP BY PLAYER_NAME
    ),
    LIGA_RANKED AS (
        SELECT *,
            RANK() OVER (ORDER BY M1 DESC NULLS LAST) as M1_RANK, RANK() OVER (ORDER BY M2 DESC NULLS LAST) as M2_RANK,
            RANK() OVER (ORDER BY M3 DESC NULLS LAST) as M3_RANK, RANK() OVER (ORDER BY M4 DESC NULLS LAST) as M4_RANK,
            RANK() OVER (ORDER BY M5 DESC NULLS LAST) as M5_RANK, RANK() OVER (ORDER BY M6 DESC NULLS LAST) as M6_RANK
        FROM LIGA_STATS
    ),
    VALGT_TRUP AS (
        SELECT (TRIM(FIRSTNAME) || ' ' || TRIM(LASTNAME)) as FULL_NAME, MAX(IMAGEDATAURL) as IMG
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS WHERE CURRENTTEAM_WYID = {target_id} GROUP BY 1
    )
    SELECT t.IMG, t.FULL_NAME as WYS_NAME, r.* FROM VALGT_TRUP t
    INNER JOIN LIGA_RANKED r ON (t.FULL_NAME LIKE '%' || r.PLAYER_NAME || '%' OR r.PLAYER_NAME LIKE '%' || t.FULL_NAME || '%')
    """

    try:
        df = pd.read_sql(query, conn)
        
        if not df.empty:
            if player_overrides:
                df = df[df.apply(lambda row: player_overrides.get(row['WYS_NAME'], target_id) == target_id, axis=1)]
            
            df = df.sort_values(main_rank_col).head(5)
            st.write("---")
            
            # --- RENDER HEADERS ---
            cols = st.columns([2.5, 1, 1, 1, 1, 1])
            for i, (_, row) in enumerate(df.iterrows()):
                with cols[i+1]:
                    img = row['IMG'] if row['IMG'] and str(row['IMG']) != 'None' else "https://via.placeholder.com/150"
                    st.markdown(f'<div class="player-card"><img src="{img}" class="player-img-round" width="60" height="60"><br><small><b>{row["PLAYER_NAME"].split()[-1]}</b></small></div>', unsafe_allow_html=True)

            # --- RENDER METRICS ---
            for kat_navn, metrics in metrics_labels.items():
                st.markdown(f'<div class="category-header">{kat_navn}</div>', unsafe_allow_html=True)
                for label, col_name in metrics:
                    m_cols = st.columns([2.5, 1, 1, 1, 1, 1])
                    with m_cols[0]: st.markdown(f'<div class="metric-label">{label}</div>', unsafe_allow_html=True)
                    for i, (_, row) in enumerate(df.iterrows()):
                        rank_val = int(row[col_name]) if pd.notnull(row[col_name]) else 999
                        fill_width = max(15, (1 - (rank_val / 400)) * 100) if rank_val <= 400 else 10
                        color = "#22c55e" if rank_val <= 30 else "#facc15" if rank_val <= 100 else "#fca5a5"
                        with m_cols[i+1]:
                            st.markdown(f'<div class="rank-container"><div class="rank-fill" style="width: {fill_width}%; background-color: {color};">R {rank_val}</div></div>', unsafe_allow_html=True)
        else:
            st.info("Ingen data fundet for det valgte hold.")
    except Exception as e:
        st.error(f"SQL fejl: {e}")

vis_side()
