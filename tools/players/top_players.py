import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

DB = "KLUB_HVIDOVREIF.AXIS"

def vis_side():
    st.markdown("""
        <style>
        /* Container til spillerbillede - gør dem mindre og runde */
        .player-img-container {
            text-align: center;
            margin-bottom: 10px;
        }
        .player-img {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            object-fit: cover;
            border: 2px solid #f0f0f0;
        }
        .player-header { 
            background-color: black; color: white; text-align: center; 
            font-weight: bold; padding: 6px 2px; border-radius: 2px; 
            font-size: 10px; text-transform: uppercase;
            min-height: 40px; display: flex; align-items: center; justify-content: center;
        }
        /* Metrics Labels (Venstre kolonne) */
        .metric-label-col {
            font-size: 11px; color: #666; font-weight: bold;
            text-transform: uppercase; height: 55px;
            display: flex; align-items: center;
        }
        /* Stat række design */
        .stat-row { height: 55px; display: flex; flex-direction: column; justify-content: center; }
        .bar-bg { background-color: #f0f0f0; height: 8px; width: 100%; border-radius: 4px; position: relative; }
        .bar-fill { background-color: #df003b; height: 8px; border-radius: 4px; }
        .val-text { font-size: 11px; font-weight: bold; color: #1f1f1f; margin-top: 2px; }
        </style>
    """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn: return

    # --- DATA HENTNING (Samme logik som før) ---
    valgt_hold_navn = st.selectbox("Vælg Hold", sorted(list(TEAMS.keys())), label_visibility="collapsed")
    target_ssiid = TEAMS.get(valgt_hold_navn, {}).get('ssid')

    sql_phys = f"""
        SELECT PLAYER_NAME, 
               AVG(DISTANCE) as DIST, AVG("HIGH SPEED RUNNING") as HSR, 
               MAX(TOP_SPEED) as SPEED, AVG(NO_OF_HIGH_INTENSITY_RUNS) as ACCELS
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'
        AND MATCH_SSIID IN (SELECT MATCH_SSIID FROM {DB}.SECONDSPECTRUM_GAME_METADATA 
                            WHERE HOME_SSIID = '{target_ssiid}' OR AWAY_SSIID = '{target_ssiid}')
        GROUP BY PLAYER_NAME ORDER BY DIST DESC LIMIT 5
    """
    df_top5 = conn.query(sql_phys)

    if df_top5 is not None and not df_top5.empty:
        # Hent billeder fra Wyscout
        names_list = "('" + "','".join(df_top5['PLAYER_NAME'].tolist()) + "')"
        sql_img = f'SELECT (TRIM(FIRSTNAME) || \' \' || TRIM(LASTNAME)) as FULL_NAME, MAX(IMAGEDATAURL) as IMG FROM {DB}.WYSCOUT_PLAYERS WHERE FULL_NAME IN {names_list} GROUP BY 1'
        df_wyscout = conn.query(sql_img)

        # Definer rækkerne vi vil vise
        metrics = [
            ("Distance", "DIST", 1000, "km"),
            ("HSR", "HSR", 1, "m"),
            ("Topfart", "SPEED", 1, "km/t"),
            ("Eksplosiv", "ACCELS", 1, "akt")
        ]
        
        # Max værdier til bar-beregning
        max_vals = {m[1]: df_top5[m[1]].max() for m in metrics}

        # --- LAYOUT START ---
        # 6 kolonner: 1 til labels, 5 til spillere
        cols = st.columns([1.5, 2, 2, 2, 2, 2])

        # KOLONNE 0: Metrics Labels
        with cols[0]:
            st.write("") # Plads til billede-højde
            st.markdown("<div style='height: 140px;'></div>", unsafe_allow_html=True) # Spacer til header
            for label, key, div, unit in metrics:
                st.markdown(f"<div class='metric-label-col'>{label}</div>", unsafe_allow_html=True)

        # KOLONNE 1-5: Spillere
        for i, (idx, row) in enumerate(df_top5.iterrows()):
            with cols[i+1]:
                # 1. Billede (mindre)
                img = "https://via.placeholder.com/150"
                if df_wyscout is not None:
                    m = df_wyscout[df_wyscout['FULL_NAME'] == row['PLAYER_NAME']]
                    if not m.empty: img = m.iloc[0]['IMG']
                
                st.markdown(f"""
                    <div class='player-img-container'>
                        <img src='{img}' class='player-img'>
                    </div>
                """, unsafe_allow_html=True)

                # 2. Navn Header
                st.markdown(f"<div class='player-header'>{row['PLAYER_NAME']}</div>", unsafe_allow_html=True)

                # 3. Stats Rækker
                for label, key, div, unit in metrics:
                    val = row[key]
                    m_val = max_vals[key]
                    pct = min(int((val/m_val)*100), 100) if m_val > 0 else 0
                    display_val = f"{val/div:.1f}" if div > 1 else f"{int(val)}"
                    
                    st.markdown(f"""
                        <div class='stat-row'>
                            <div class="bar-bg"><div class="bar-fill" style="width:{pct}%;"></div></div>
                            <div class="val-text">{display_val} <span style='font-size:9px; color:#888;'>{unit}</span></div>
                        </div>
                    """, unsafe_allow_html=True)

if __name__ == "__main__":
    vis_side()
