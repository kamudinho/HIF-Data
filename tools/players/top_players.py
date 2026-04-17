import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

def load_player_overrides():
    """Henter manuelle transfers fra CSV."""
    try:
        df_overrides = pd.read_csv("data/player_overrides.csv")
        overrides = {}
        for _, row in df_overrides.iterrows():
            player = row['PLAYER_NAME'].strip()
            team = row['TEAM_NAME'].strip()
            if team in TEAMS:
                overrides[player] = TEAMS[team]["team_wyid"]
        return overrides
    except FileNotFoundError:
        return {}

def vis_side():
    try:
        conn = _get_snowflake_conn()
    except Exception as e:
        st.error(f"Forbindelsesfejl: {e}")
        return

    player_overrides = load_player_overrides()

    # --- CSS for professionelt scouting-look ---
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

    # --- Kontrolpanel ---
    col1, col2 = st.columns([2, 2])
    with col1:
        valgt_navn = st.selectbox("Vælg hold:", list(TEAMS.keys()), key="opta_ss_stable_v1")
        target_id = TEAMS[valgt_navn]["team_wyid"]
    with col2:
        mode = st.radio("Vælg data-visning:", ["Fysiske Data (SS)", "Tekniske Data (Opta)"], horizontal=True)

    # --- SQL Logik Konfiguration ---
    if mode == "Fysiske Data (SS)":
        table = "KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS"
        sql_metrics = """
            AVG(DISTANCE) as M1, AVG(RUNNING) as M2, AVG("HIGH SPEED RUNNING") as M3,
            AVG(SPRINTING) as M4, MAX(TOP_SPEED) as M5, AVG(NO_OF_HIGH_INTENSITY_RUNS) as M6
        """
        date_filter = "WHERE MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'"
        join_key = "PLAYER_NAME"
        metrics_labels = {
            "Volume": [("Total Distance", "M1_RANK"), ("Running Distance", "M2_RANK")],
            "Intensity": [("Hi Distance", "M3_RANK"), ("Sprint Distance", "M4_RANK")],
            "Explosive": [("Top Speed", "M5_RANK"), ("Accelerations", "M6_RANK")]
        }
    else:
        # Forbedret Opta-logik baseret på din verificerede OPTA_EVENTS tabel
        table = "KLUB_HVIDOVREIF.AXIS.OPTA_EVENTS"
        sql_metrics = """
            COUNT(CASE WHEN EVENT_TYPEID = 16 THEN 1 END) as M1, -- Mål
            COUNT(CASE WHEN EVENT_TYPEID = 1 AND EVENT_OUTCOME = 1 THEN 1 END) as M2, -- Succesfulde afleveringer
            COUNT(CASE WHEN EVENT_TYPEID = 15 THEN 1 END) as M3, -- Tacklinger
            COUNT(CASE WHEN EVENT_TYPEID = 12 THEN 1 END) as M4, -- Clearance
            COUNT(CASE WHEN EVENT_TYPEID = 2 THEN 1 END) as M5, -- Offsides
            COUNT(CASE WHEN EVENT_TYPEID = 3 AND EVENT_OUTCOME = 1 THEN 1 END) as M6 -- Driblinger vundet
        """
        date_filter = "" 
        join_key = "PLAYER_OPTAUUID"
        metrics_labels = {
            "Offensivt": [("Mål", "M1_RANK"), ("Vundne Driblinger", "M6_RANK")],
            "Distribution": [("Succesfulde Afleveringer", "M2_RANK"), ("Offsides", "M5_RANK")],
            "Defensivt": [("Tacklinger", "M3_RANK"), ("Clearances", "M4_RANK")]
        }

    # --- Den Store "Double-Check" Query ---
    # Vi bruger QUALIFY ROW_NUMBER() til at sikre, at én person kun optræder én gang
    if mode == "Fysiske Data (SS)":
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
        QUALIFY ROW_NUMBER() OVER (PARTITION BY t.FULL_NAME ORDER BY r.M1 DESC) = 1
        """
    else:
        query = f"""
        WITH PLAYER_SUMS AS (
            SELECT PLAYER_OPTAUUID, {sql_metrics} FROM {table} GROUP BY PLAYER_OPTAUUID
        ),
        LIGA_RANKED AS (
            SELECT p.MATCH_NAME as PLAYER_NAME, p.PLAYER_OPTAUUID, s.*,
                RANK() OVER (ORDER BY s.M1 DESC NULLS LAST) as M1_RANK, RANK() OVER (ORDER BY s.M2 DESC NULLS LAST) as M2_RANK,
                RANK() OVER (ORDER BY s.M3 DESC NULLS LAST) as M3_RANK, RANK() OVER (ORDER BY s.M4 DESC NULLS LAST) as M4_RANK,
                RANK() OVER (ORDER BY s.M5 DESC NULLS LAST) as M5_RANK, RANK() OVER (ORDER BY s.M6 DESC NULLS LAST) as M6_RANK
            FROM KLUB_HVIDOVREIF.AXIS.OPTA_PLAYERS p
            JOIN PLAYER_SUMS s ON p.PLAYER_OPTAUUID = s.PLAYER_OPTAUUID
        ),
        VALGT_TRUP AS (
            SELECT TRIM(FIRSTNAME) as F_NAME, TRIM(LASTNAME) as L_NAME,
                   (TRIM(FIRSTNAME) || ' ' || TRIM(LASTNAME)) as FULL_NAME, MAX(IMAGEDATAURL) as IMG
            FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS WHERE CURRENTTEAM_WYID = {target_id} GROUP BY 1, 2, 3
        )
        SELECT t.IMG, t.FULL_NAME as WYS_NAME, r.* FROM VALGT_TRUP t
        INNER JOIN LIGA_RANKED r ON (
            r.PLAYER_NAME LIKE LEFT(t.F_NAME, 1) || '. ' || t.L_NAME
            OR r.PLAYER_NAME = t.FULL_NAME
            OR (r.PLAYER_NAME LIKE '%' || t.L_NAME || '%' AND r.M2 > 0)
        )
        QUALIFY ROW_NUMBER() OVER (PARTITION BY t.FULL_NAME ORDER BY r.M2 DESC) = 1
        """

    try:
        df = pd.read_sql(query, conn)
        
        if not df.empty:
            if player_overrides:
                df = df[df.apply(lambda row: player_overrides.get(row['WYS_NAME'], target_id) == target_id, axis=1)]
            
            # Sortering: Vis de mest aktive spillere først (M2 er ofte god volumen-indikator)
            df = df.sort_values("M2_RANK").head(5)
            st.write("---")
            
            # --- Render Spiller-kort ---
            cols = st.columns([2.5, 1, 1, 1, 1, 1])
            for i, (_, row) in enumerate(df.iterrows()):
                with cols[i+1]:
                    img = row['IMG'] if row['IMG'] and str(row['IMG']) != 'None' else "https://via.placeholder.com/150"
                    fuldt_navn = row['WYS_NAME']
                    st.markdown(f'<div class="player-card"><img src="{img}" class="player-img-round" width="60" height="60"><br><small><b>{fuldt_navn}</b></small></div>', unsafe_allow_html=True)

            # --- Render Rækker med Ranks ---
            for kat_navn, metrics in metrics_labels.items():
                st.markdown(f'<div class="category-header">{kat_navn}</div>', unsafe_allow_html=True)
                for label, col_name in metrics:
                    m_cols = st.columns([2.5, 1, 1, 1, 1, 1])
                    with m_cols[0]: 
                        st.markdown(f'<div class="metric-label">{label}</div>', unsafe_allow_html=True)
                    
                    for i, (_, row) in enumerate(df.iterrows()):
                        rank_val = int(row[col_name]) if pd.notnull(row[col_name]) else 999
                        # Bar-længde beregning (Rank 1 er top)
                        fill_width = max(15, (1 - (rank_val / 500)) * 100) if rank_val <= 500 else 10
                        color = "#22c55e" if rank_val <= 50 else "#facc15" if rank_val <= 150 else "#fca5a5"
                        
                        with m_cols[i+1]:
                            st.markdown(f"""
                                <div class="rank-container">
                                    <div class="rank-fill" style="width: {fill_width}%; background-color: {color};">
                                        R {rank_val}
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
        else:
            st.info(f"Ingen data fundet for {valgt_navn} i de valgte tabeller.")

    except Exception as e:
        st.error(f"Fejl i data-processering: {e}")

if __name__ == "__main__":
    vis_side()
