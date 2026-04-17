import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

DB = "KLUB_HVIDOVREIF.AXIS"

def vis_side():
    # CSS forbliver den samme som sidst...
    
    conn = _get_snowflake_conn()
    if not conn: return

    valgt_hold_navn = st.selectbox("Vælg Hold", sorted(list(TEAMS.keys())), label_visibility="collapsed")
    # Hent IDs fra mapping
    team_info = TEAMS.get(valgt_hold_navn, {})
    target_ssiid = team_info.get('ssid')
    target_wyid = team_info.get('wyid')
    
    # Sikkerhedstjek: Hvis wyid mangler, sætter vi det til en værdi der ikke fejler SQL (f.eks. 0)
    sql_wyid = target_wyid if target_wyid is not None else 0
    
    # KOMBINERET QUERY
    sql = f"""
        WITH SS_STATS AS (
            SELECT PLAYER_NAME, 
                   AVG(DISTANCE) as DIST, AVG("HIGH SPEED RUNNING") as HSR, 
                   MAX(TOP_SPEED) as SPEED, AVG(NO_OF_HIGH_INTENSITY_RUNS) as ACCELS
            FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
            WHERE MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'
            AND MATCH_SSIID IN (SELECT MATCH_SSIID FROM {DB}.SECONDSPECTRUM_GAME_METADATA 
                                WHERE HOME_SSIID = '{target_ssiid}' OR AWAY_SSIID = '{target_ssiid}')
            GROUP BY PLAYER_NAME
        ),
        WY_INFO AS (
            -- Vi bruger DISTINCT og filtrerer på det specifikke hold-ID
            SELECT DISTINCT
                (TRIM(FIRSTNAME) || ' ' || TRIM(LASTNAME)) as FULL_NAME,
                SHORTNAME,
                IMAGEDATAURL
            FROM {DB}.WYSCOUT_PLAYERS 
            WHERE CURRENTTEAM_WYID = {sql_wyid}
        )
        SELECT 
            s.PLAYER_NAME, s.DIST, s.HSR, s.SPEED, s.ACCELS,
            MAX(w.IMAGEDATAURL) as IMG -- Sikrer én række per spiller hvis der er dubletter
        FROM SS_STATS s
        LEFT JOIN WY_INFO w ON (s.PLAYER_NAME = w.FULL_NAME OR s.PLAYER_NAME = w.SHORTNAME)
        GROUP BY 1, 2, 3, 4, 5
        ORDER BY DIST DESC 
        LIMIT 5
    """
    
    df = conn.query(sql)

    if df is not None and not df.empty:
        # Metrics definition
        metrics = [("Distance", "DIST", 1000, "km"), ("Hsr", "HSR", 1, "m"), 
                   ("Topfart", "SPEED", 1, "km/t"), ("Eksplosiv", "ACCELS", 1, "akt")]
        
        max_vals = {m[1]: df[m[1]].max() for m in metrics}

        # LAYOUT (1 label kolonne + 5 spiller kolonner)
        cols = st.columns([1.2, 2, 2, 2, 2, 2])

        # Labels (Kolonne 0)
        with cols[0]:
            st.markdown("<div style='height: 160px;'></div>", unsafe_allow_html=True)
            for label, _, _, _ in metrics:
                st.markdown(f"<div class='metric-label'>{label}</div>", unsafe_allow_html=True)

        # Spillere (Kolonne 1-5)
        for i, row in enumerate(df.itertuples()):
            with cols[i+1]:
                img = row.IMG if pd.notnull(row.IMG) else "https://via.placeholder.com/150"
                
                st.markdown(f"<div style='text-align:center;'><img src='{img}' class='player-img'></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='player-header'>{row.PLAYER_NAME}</div>", unsafe_allow_html=True)

                for label, key, div, unit in metrics:
                    val = getattr(row, key)
                    m_val = max_vals[key]
                    pct = min(int((val/m_val)*100), 100) if m_val > 0 else 0
                    display_val = f"{val/div:.1f}" if div > 1 else f"{int(val)}"
                    
                    st.markdown(f"""
                        <div class='stat-row'>
                            <div class="bar-bg"><div class="bar-fill" style="width:{pct}%;"></div></div>
                            <div class="val-text">{display_val} <span style='font-size:8px; color:#888;'>{unit}</span></div>
                        </div>
                    """, unsafe_allow_html=True)
