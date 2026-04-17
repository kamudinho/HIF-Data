import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

def load_player_overrides():
    """
    Indlæser manuelle transfers fra CSV og mapper klubnavne til WYIDs.
    CSV format: PLAYER_NAME, TEAM_NAME
    """
    try:
        df_overrides = pd.read_csv("data/player_overrides.csv")
        overrides = {}
        for _, row in df_overrides.iterrows():
            spiller = row['PLAYER_NAME'].strip()
            klub_navn = row['TEAM_NAME'].strip()
            
            if klub_navn in TEAMS:
                overrides[spiller] = TEAMS[klub_navn]["team_wyid"]
        return overrides
    except:
        return {}

def vis_side():
    try:
        conn = _get_snowflake_conn()
    except Exception as e:
        st.error(f"Forbindelsesfejl: {e}")
        return

    # 1. Hent manuelle klub-overrides
    player_overrides = load_player_overrides()

    # --- CSS: Professionelt Scouting-look ---
    st.markdown("""
        <style>
        .category-header { font-weight: bold; font-size: 1rem; padding: 15px 0 5px 0; color: #111; border-bottom: 2px solid #eee; margin-top: 10px; }
        .metric-label { font-size: 0.8rem; color: #444; display: flex; align-items: center; height: 35px; line-height: 1.1; }
        .rank-container { position: relative; background-color: #f0f0f0; height: 32px; width: 100%; border-radius: 4px; overflow: hidden; display: flex; align-items: center; margin-bottom: 2px; }
        .rank-fill { 
            height: 100%; display: flex; align-items: center; padding-left: 8px; 
            font-weight: bold; color: black; font-size: 0.72rem; 
            white-space: nowrap; min-width: fit-content;
        }
        .player-card { text-align: center; min-height: 100px; }
        .player-img-round { border-radius: 50%; object-fit: cover; border: 2px solid #f0f2f6; background-color: white; }
        </style>
    """, unsafe_allow_html=True)

    # 2. HOLDVALG
    alle_hold = list(TEAMS.keys())
    col_sel, _ = st.columns([2, 2])
    with col_sel:
        valgt_navn = st.selectbox("Vælg hold:", alle_hold, key="phys_rank_stable_final_v1")
    
    current_target_id = TEAMS[valgt_navn]["team_wyid"]

    # 3. SQL: Fuzzy join og korrekte kolonnenavne (RUNNING, SPRINTING osv.)
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
        WHERE CURRENTTEAM_WYID = {current_target_id}
        GROUP BY 1
    )
    SELECT t.IMG, t.FULL_NAME as WYS_NAME, r.* FROM VALGT_TRUP t
    INNER JOIN LIGA_RANKED r ON (
        t.FULL_NAME LIKE '%' || r.PLAYER_NAME || '%' 
        OR r.PLAYER_NAME LIKE '%' || t.FULL_NAME || '%'
    )
    """

    try:
        df = pd.read_sql(query, conn)
        
        # --- 4. SMART FILTRERING (NAVNE-FUZZY & OVERRIDES) ---
        if not df.empty:
            def matches_manual_transfer(row):
                # Tjek mod navnet i dataen (både fra Wyscout og Second Spectrum)
                data_name_1 = row['WYS_NAME'].lower()
                data_name_2 = row['PLAYER_NAME'].lower()
                
                for override_name, correct_wyid in player_overrides.items():
                    ov_name_lower = override_name.lower()
                    # Hvis override-navnet findes i en af datakilderne
                    if ov_name_lower in data_name_1 or ov_name_lower in data_name_2:
                        return correct_wyid == current_target_id
                return True

            if player_overrides:
                df = df[df.apply(matches_manual_transfer, axis=1)]

            # Sorter efter Distance og tag top 5
            df = df.sort_values("DIST_RANK").head(5)

            st.write("---")
            
            # --- HEADER: SPILLER BILLEDER ---
            cols = st.columns([2.5, 1, 1, 1, 1, 1])
            with cols[0]: st.write("")
            for i, (_, row) in enumerate(df.iterrows()):
                with cols[i+1]:
                    img = row['IMG'] if row['IMG'] and str(row['IMG']) != 'None' else "https://via.placeholder.com/150"
                    efternavn = row['PLAYER_NAME'].split()[-1]
                    st.markdown(f"""
                        <div class="player-card">
                            <img src="{img}" class="player-img-round" width="60" height="60">
                            <br><small><b>{efternavn}</b></small>
                        </div>
                    """, unsafe_allow_html=True)

            # --- DEFINITION AF METRICS ---
            metrics_map = {
                "Volume Metrics": [("Total Distance", "DIST_RANK"), ("Running Distance", "RUN_DIST_RANK")],
                "High Intensity Metrics": [("Hi Distance", "HSR_RANK"), ("Sprint Distance", "SPRINT_DIST_RANK")],
                "Explosive Metrics": [("Top Speed", "SPEED_RANK"), ("Accelerations", "ACCELS_RANK")]
            }

            # --- RENDER RÆKKER ---
            for kat_navn, metrics in metrics_map.items():
                st.markdown(f'<div class="category-header">{kat_navn}</div>', unsafe_allow_html=True)
                for label, col_name in metrics:
                    m_cols = st.columns([2.5, 1, 1, 1, 1, 1])
                    with m_cols[0]:
                        st.markdown(f'<div class="metric-label">{label}</div>', unsafe_allow_html=True)
                    
                    for i, (_, row) in enumerate(df.iterrows()):
                        rank_val = int(row[col_name])
                        # Bar-længde (Rank 1 = bred, Rank 300 = smal)
                        fill_width = max(25, (1 - (rank_val / 300)) * 100) if rank_val <= 300 else 25
                        # Farver
                        color = "#22c55e" if rank_val <= 20 else "#facc15" if rank_val <= 80 else "#fca5a5"
                        
                        with m_cols[i+1]:
                            st.markdown(f"""
                                <div class="rank-container">
                                    <div class="rank-fill" style="width: {fill_width}%; background-color: {color};">
                                        Rank {rank_val}
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
        else:
            st.info(f"Ingen fysiske data fundet for {valgt_navn} i denne periode.")

    except Exception as e:
        st.error(f"Fejl ved indlæsning: {e}")

vis_side()
