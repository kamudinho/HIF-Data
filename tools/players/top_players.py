import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

def vis_side():
    try:
        conn = _get_snowflake_conn()
    except Exception as e:
        st.error(f"Kunne ikke forbinde til Snowflake: {e}")
        return

    # --- CSS: Samme lækre stil som før ---
    st.markdown("""
        <style>
        .category-header { font-weight: bold; font-size: 1.05rem; padding: 15px 0 5px 0; color: #111; border-bottom: 2px solid #eee; margin-top: 10px; }
        .metric-label { font-size: 0.85rem; color: #444; display: flex; align-items: center; height: 35px; }
        .rank-container { position: relative; background-color: #f0f0f0; height: 32px; width: 100%; border-radius: 4px; overflow: hidden; display: flex; align-items: center; margin-bottom: 2px; }
        .rank-fill { height: 100%; display: flex; align-items: center; padding-left: 8px; font-weight: bold; color: black; font-size: 0.75rem; }
        .player-card { text-align: center; min-height: 110px; }
        .player-img-round { border-radius: 50%; object-fit: cover; border: 2px solid #f0f2f6; background-color: #fff; }
        </style>
    """, unsafe_allow_html=True)

    # 1. HOLDVALG (Tilføjet 'key' for at fjerne din fejl)
    alle_hold = list(TEAMS.keys())
    
    col_sel, _ = st.columns([2, 2])
    with col_sel:
        valgt_navn = st.selectbox(
            "Vælg hold:", 
            alle_hold, 
            index=alle_hold.index("Hvidovre") if "Hvidovre" in alle_hold else 0,
            key="team_selector_physical_top5" # Dette fjerner fejlen!
        )
    
    target_wyid = TEAMS[valgt_navn]["team_wyid"]

    # 2. SQL: Vi holder os til de sikre kolonner (DISTANCE, HSR, SPEED, ACCELS)
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
            PERCENT_RANK() OVER (ORDER BY DIST ASC) as DIST_RANK,
            PERCENT_RANK() OVER (ORDER BY HSR ASC) as HSR_RANK,
            PERCENT_RANK() OVER (ORDER BY SPEED ASC) as SPEED_RANK,
            PERCENT_RANK() OVER (ORDER BY ACCELS ASC) as ACCELS_RANK
        FROM STATS
    ),
    TRUP AS (
        SELECT 
            (TRIM(FIRSTNAME) || ' ' || TRIM(LASTNAME)) as FULL_NAME,
            MAX(IMAGEDATAURL) as IMG
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS
        WHERE CURRENTTEAM_WYID = {target_wyid}
        GROUP BY 1
    )
    SELECT t.IMG, r.*
    FROM TRUP t
    INNER JOIN RANKED r ON (
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
            
            # --- HEADER: SPILLER PROFILER ---
            cols = st.columns([2.5, 1, 1, 1, 1, 1])
            with cols[0]: st.write("")
            
            for i, (_, row) in enumerate(df.iterrows()):
                with cols[i+1]:
                    img_path = row['IMG'] if row['IMG'] and str(row['IMG']) != 'None' else "https://via.placeholder.com/150"
                    short_name = row['PLAYER_NAME'].split()[-1]
                    st.markdown(f"""
                        <div class="player-card">
                            <img src="{img_path}" class="player-img-round" width="65" height="65">
                            <br><b>{short_name}</b>
                        </div>
                    """, unsafe_allow_html=True)

            # --- DEFINER KATEGORIER ---
            kategorier = {
                "Volume Metrics": [("Distance Per 90", "DIST_RANK")],
                "High Intensity Metrics": [("Hi Distance Per 90", "HSR_RANK")],
                "Explosive Metrics": [("Top Speed", "SPEED_RANK"), ("Accelerations", "ACCELS_RANK")]
            }

            # --- RENDER RÆKKER ---
            for kat_navn, metrics in kategorier.items():
                st.markdown(f'<div class="category-header">{kat_navn}</div>', unsafe_allow_html=True)
                
                for label, rank_col in metrics:
                    m_cols = st.columns([2.5, 1, 1, 1, 1, 1])
                    with m_cols[0]:
                        st.markdown(f'<div class="metric-label">{label}</div>', unsafe_allow_html=True)
                    
                    for i, (_, row) in enumerate(df.iterrows()):
                        val = row[rank_col] * 100
                        # Grøn (Top), Gul (Midt), Rød (Bund)
                        color = "#22c55e" if val >= 75 else "#facc15" if val >= 40 else "#fca5a5"
                        
                        with m_cols[i+1]:
                            st.markdown(f"""
                                <div class="rank-container">
                                    <div class="rank-fill" style="width: {max(val, 15)}%; background-color: {color};">
                                        {int(val)}%
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
        else:
            st.info(f"Ingen kampdata fundet for spillere i {valgt_navn} truppen.")

    except Exception as e:
        st.error(f"SQL Fejl: {e}")
