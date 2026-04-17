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

    # --- CSS: Scouting Layout ---
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

    # 1. HOLDVALG med dynamisk key
    alle_hold = list(TEAMS.keys())
    col_sel, _ = st.columns([2, 2])
    with col_sel:
        # Vi tilføjer valgt_navn til key'en for at gøre den unik
        initial_hold = "Hvidovre" if "Hvidovre" in alle_hold else alle_hold[0]
        valgt_navn = st.selectbox(
            "Vælg hold:", 
            alle_hold, 
            index=alle_hold.index(initial_hold),
            key=f"phys_top5_selector_{initial_hold.lower()}" 
        )
    
    target_wyid = TEAMS[valgt_navn]["team_wyid"]

    # 2. SQL: Percent_Rank på tværs af HELE ligaen
    query = f"""
    WITH LIGA_STATS AS (
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
    LIGA_RANKED AS (
        SELECT *,
            PERCENT_RANK() OVER (ORDER BY DIST ASC) as DIST_PR,
            PERCENT_RANK() OVER (ORDER BY HSR ASC) as HSR_PR,
            PERCENT_RANK() OVER (ORDER BY SPEED ASC) as SPEED_PR,
            PERCENT_RANK() OVER (ORDER BY ACCELS ASC) as ACCELS_PR
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
            
            # --- HEADER: SPILLER PROFILER ---
            cols = st.columns([2.5, 1, 1, 1, 1, 1])
            with cols[0]: st.write("")
            
            for i, (_, row) in enumerate(df.iterrows()):
                with cols[i+1]:
                    img_url = row['IMG'] if row['IMG'] and str(row['IMG']) != 'None' else "https://via.placeholder.com/150"
                    efternavn = row['PLAYER_NAME'].split()[-1]
                    st.markdown(f"""
                        <div class="player-card">
                            <img src="{img_url}" class="player-img-round" width="65" height="65">
                            <br><b>{efternavn}</b>
                        </div>
                    """, unsafe_allow_html=True)

            # --- KATEGORIER FRA DIT REFERENCEBILLEDE ---
            kategorier = {
                "Volume Metrics": [
                    ("Distance Per 90", "DIST_PR")
                ],
                "High Intensity Metrics": [
                    ("Hi Distance Per 90", "HSR_PR")
                ],
                "Explosive Metrics": [
                    ("Top Speed", "SPEED_PR"),
                    ("Accelerations", "ACCELS_PR")
                ]
            }

            # --- RENDER TABEL ---
            for kat_navn, metrics in kategorier.items():
                st.markdown(f'<div class="category-header">{kat_navn}</div>', unsafe_allow_html=True)
                
                for label, pr_col in metrics:
                    m_cols = st.columns([2.5, 1, 1, 1, 1, 1])
                    with m_cols[0]:
                        st.markdown(f'<div class="metric-label">{label}</div>', unsafe_allow_html=True)
                    
                    for i, (_, row) in enumerate(df.iterrows()):
                        val_pct = int(row[pr_col] * 100)
                        
                        # Farver: Grøn (>80), Gul (>40), Rød (<40)
                        if val_pct >= 80: color = "#22c55e"
                        elif val_pct >= 40: color = "#facc15"
                        else: color = "#fca5a5"
                        
                        with m_cols[i+1]:
                            st.markdown(f"""
                                <div class="rank-container">
                                    <div class="rank-fill" style="width: {max(val_pct, 15)}%; background-color: {color};">
                                        {val_pct}%
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
        else:
            st.info(f"Ingen match fundet for {valgt_navn}.")

    except Exception as e:
        st.error(f"Fejl ved datahentning: {e}")
