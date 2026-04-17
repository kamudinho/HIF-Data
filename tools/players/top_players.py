import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

def vis_side():
    conn = _get_snowflake_conn()

    # --- CSS for det professionelle tabel-look ---
    st.markdown("""
        <style>
        .category-header { font-weight: bold; font-size: 1.05rem; padding: 15px 0 5px 0; color: #111; border-bottom: 2px solid #eee; margin-top: 10px; }
        .metric-label { font-size: 0.85rem; color: #444; display: flex; align-items: center; height: 35px; }
        .rank-container { position: relative; background-color: #f0f0f0; height: 32px; width: 100%; border-radius: 4px; overflow: hidden; display: flex; align-items: center; margin-bottom: 2px; }
        .rank-fill { height: 100%; display: flex; align-items: center; padding-left: 8px; font-weight: bold; color: black; font-size: 0.75rem; transition: width 0.5s ease; }
        .player-card { text-align: center; min-height: 110px; }
        .player-img-round { border-radius: 50%; object-fit: cover; border: 2px solid #f0f2f6; background-color: #fff; }
        </style>
    """, unsafe_allow_html=True)

    # 1. HOLDVALG
    alle_hold = list(TEAMS.keys())
    valgt_navn = st.selectbox("Vælg hold:", alle_hold, index=alle_hold.index("Hvidovre") if "Hvidovre" in alle_hold else 0)
    target_wyid = TEAMS[valgt_navn]["team_wyid"]

    # 2. SQL: Rettet til de korrekte kolonnenavne
    # Jeg har fjernet RUNNING_DISTANCE og SPRINT_DISTANCE da de fejlede. 
    # Vi bruger DISTANCE, HSR, SPEED og ACCELS som vi ved virker.
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
            -- Vi inverterer rank så 1.0 er bedst (100%)
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
            
            # --- TOP: SPILLER PROFILER ---
            cols = st.columns([2.5, 1, 1, 1, 1, 1])
            with cols[0]: st.write("")
            
            for i, (_, row) in enumerate(df.iterrows()):
                with cols[i+1]:
                    img_path = row['IMG'] if row['IMG'] and str(row['IMG']) != 'None' else "https://via.placeholder.com/150"
                    # Vis efternavnet (det sidste ord i navnet)
                    name_parts = row['PLAYER_NAME'].split()
                    short_name = name_parts[-1] if name_parts else "Spiller"
                    st.markdown(f"""
                        <div class="player-card">
                            <img src="{img_path}" class="player-img-round" width="65" height="65">
                            <br><b>{short_name}</b>
                        </div>
                    """, unsafe_allow_html=True)

            # --- DEFINER KATEGORIER ---
            # Vi bruger de metrics vi ved er i din tabel
            kategorier = {
                "Volume Metrics": [
                    ("Distance Per 90", "DIST_RANK")
                ],
                "High Intensity Metrics": [
                    ("Hi Distance Per 90", "HSR_RANK")
                ],
                "Explosive Metrics": [
                    ("Top Speed", "SPEED_RANK"),
                    ("Accelerations", "ACCELS_RANK")
                ]
            }

            # --- RENDER RÆKKER ---
            for kat_navn, metrics in kategorier.items():
                st.markdown(f'<div class="category-header">{kat_navn}</div>', unsafe_allow_html=True)
                
                for label, rank_col in metrics:
                    m_cols = st.columns([2.5, 1, 1, 1, 1, 1])
                    with m_cols[0]:
                        st.markdown(f'<div class="metric-label">{label}</div>', unsafe_allow_html=True)
                    
                    for i, (_, row) in enumerate(df.iterrows()):
                        # PERCENT_RANK giver 0 til 1.
                        val = row[rank_col] * 100
                        
                        # Farve-skala (Grøn for top, rød for bund)
                        if val >= 75: color = "#22c55e" # Grøn
                        elif val >= 40: color = "#86efac" # Lys grøn
                        else: color = "#fca5a5" # Rødlig
                        
                        with m_cols[i+1]:
                            st.markdown(f"""
                                <div class="rank-container">
                                    <div class="rank-fill" style="width: {max(val, 15)}%; background-color: {color};">
                                        {int(val)}%
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
        else:
            st.info("Ingen spillere fundet. Tjek om navnene i Wyscout og Second Spectrum matcher.")

    except Exception as e:
        st.error(f"Fejl ved indlæsning: {e}")

vis_side()
