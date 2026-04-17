import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

def vis_side():
    try:
        conn = _get_snowflake_conn()
    except Exception as e:
        st.error(f"Forbindelsesfejl: {e}")
        return

    # --- CSS: Justeret til Rank-visning ---
    st.markdown("""
        <style>
        .category-header { font-weight: bold; font-size: 1.1rem; padding: 20px 0 10px 0; color: #111; border-bottom: 2px solid #eee; }
        .metric-label { font-size: 0.9rem; color: #444; display: flex; align-items: center; height: 35px; }
        .rank-container { position: relative; background-color: #f0f0f0; height: 32px; width: 100%; border-radius: 4px; overflow: hidden; display: flex; align-items: center; margin-bottom: 2px; }
        .rank-fill { height: 100%; display: flex; align-items: center; padding-left: 8px; font-weight: bold; color: black; font-size: 0.8rem; }
        .player-card { text-align: center; min-height: 120px; }
        .player-img-round { border-radius: 50%; object-fit: cover; border: 2px solid #f0f2f6; background-color: white; }
        </style>
    """, unsafe_allow_html=True)

    alle_hold = list(TEAMS.keys())
    col_sel, _ = st.columns([2, 2])
    with col_sel:
        initial_hold = "Hvidovre" if "Hvidovre" in alle_hold else alle_hold[0]
        valgt_navn = st.selectbox("Vælg hold:", alle_hold, index=alle_hold.index(initial_hold), key=f"phys_rank_selector_{initial_hold.lower()}")
    
    target_wyid = TEAMS[valgt_navn]["team_wyid"]

    # 2. SQL: Bruger nu RANK() på tværs af hele ligaen
    query = f"""
    WITH LIGA_STATS AS (
        SELECT 
            PLAYER_NAME,
            AVG(DISTANCE) as DIST,
            AVG("HIGH SPEED RUNNING") as HSR,
            MAX(TOP_SPEED) as SPEED,
            AVG(NO_OF_HIGH_INTENSITY_RUNS) as ACCELS,
            COUNT(*) OVER () as TOTAL_PLAYERS -- Bruges til at beregne bar-længde
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'
        GROUP BY PLAYER_NAME
    ),
    LIGA_RANKED AS (
        SELECT *,
            RANK() OVER (ORDER BY DIST DESC) as DIST_RANK,
            RANK() OVER (ORDER BY HSR DESC) as HSR_RANK,
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
    INNER JOIN LIGA_RANKED r ON (t.FULL_NAME = r.PLAYER_NAME OR r.PLAYER_NAME LIKE '%' || t.FULL_NAME || '%')
    ORDER BY r.DIST DESC LIMIT 5
    """

    try:
        df = pd.read_sql(query, conn)
        if not df.empty:
            st.write("---")
            total_players = df['TOTAL_PLAYERS'].iloc[0] if 'TOTAL_PLAYERS' in df.columns else 500
            
            # --- HEADER ---
            cols = st.columns([2.5, 1, 1, 1, 1, 1])
            with cols[0]: st.write("")
            for i, (_, row) in enumerate(df.iterrows()):
                with cols[i+1]:
                    img = row['IMG'] if row['IMG'] and str(row['IMG']) != 'None' else "https://via.placeholder.com/150"
                    st.markdown(f'<div class="player-card"><img src="{img}" class="player-img-round" width="65" height="65"><br><b>{row["PLAYER_NAME"].split()[-1]}</b></div>', unsafe_allow_html=True)

            # --- KATEGORIER ---
            metrics_map = {
                "Volume Metrics": [("Distance Per 90", "DIST_RANK")],
                "High Intensity Metrics": [("Hi Distance Per 90", "HSR_RANK")],
                "Explosive Metrics": [("Top Speed", "SPEED_RANK"), ("Accelerations", "ACCELS_RANK")]
            }

            for kat_navn, metrics in metrics_map.items():
                st.markdown(f'<div class="category-header">{kat_navn}</div>', unsafe_allow_html=True)
                for label, col_name in metrics:
                    m_cols = st.columns([2.5, 1, 1, 1, 1, 1])
                    with m_cols[0]:
                        st.markdown(f'<div class="metric-label">{label}</div>', unsafe_allow_html=True)
                    
                    for i, (_, row) in enumerate(df.iterrows()):
                        rank_val = int(row[col_name])
                        
                        # Beregn bar-længde (Inverteret, da Rank 1 skal have fuld bar)
                        # Vi antager at top 100 er interessant, ellers bruger vi total_players
                        fill_width = max(5, (1 - (rank_val / 150)) * 100) if rank_val <= 150 else 5
                        
                        # Farver baseret på rank
                        if rank_val <= 20: color = "#22c55e"    # Top 20: Grøn
                        elif rank_val <= 100: color = "#facc15" # Top 100: Gul
                        else: color = "#fca5a5"                # Resten: Rød
                        
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
        st.error(f"Fejl: {e}")

vis_side()
