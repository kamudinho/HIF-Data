import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

DB = "KLUB_HVIDOVREIF.AXIS"

def vis_side():
    # CSS - Præcis kontrol over rækker og labels
    st.markdown("""
        <style>
        .player-img {
            width: 85px; height: 85px;
            border-radius: 50%; object-fit: cover;
            border: 2px solid #f0f0f0; margin-bottom: 10px;
        }
        .player-header { 
            background-color: black; color: white; text-align: center; 
            font-weight: bold; padding: 6px 2px; border-radius: 2px; 
            font-size: 10px; text-transform: uppercase;
            min-height: 40px; display: flex; align-items: center; justify-content: center;
        }
        .metric-label {
            font-size: 11px; color: #444; font-weight: 800;
            text-transform: uppercase; height: 65px; /* Skal matche stat-row */
            display: flex; align-items: center;
        }
        .stat-row { height: 65px; display: flex; flex-direction: column; justify-content: center; }
        .bar-bg { background-color: #f2f2f2; height: 10px; width: 100%; border-radius: 5px; }
        .bar-fill { background-color: #df003b; height: 10px; border-radius: 5px; }
        .val-text { font-size: 11px; font-weight: 800; color: #1f1f1f; margin-top: 4px; }
        </style>
    """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn: return

    # 1. HOLDVALG
    valgt_hold_navn = st.selectbox("Vælg Hold", sorted(list(TEAMS.keys())), label_visibility="collapsed")
    target_ssiid = TEAMS.get(valgt_hold_navn, {}).get('ssid')

    # 2. HENT TOP 5 (Second Spectrum)
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
        # 3. HENT BILLEDER MED HOLD-KONTEKST
        # Vi filtrerer på holdnavnet for at få den rigtige spillerversion
        names_list = "('" + "','".join(df_top5['PLAYER_NAME'].tolist()) + "')"
        sql_img = f"""
            SELECT 
                (TRIM(FIRSTNAME) || ' ' || TRIM(LASTNAME)) as FULL_NAME,
                SHORTNAME,
                IMAGEDATAURL
            FROM {DB}.WYSCOUT_PLAYERS 
            WHERE (FULL_NAME IN {names_list} OR SHORTNAME IN {names_list})
            AND TEAMNAME ILIKE '%{valgt_hold_navn}%'
        """
        df_wyscout = conn.query(sql_img)

        metrics = [
            ("Distance", "DIST", 1000, "km"),
            ("Hsr", "HSR", 1, "m"),
            ("Topfart", "SPEED", 1, "km/t"),
            ("Eksplosiv", "ACCELS", 1, "akt")
        ]
        
        max_vals = {m[1]: df_top5[m[1]].max() for m in metrics}

        # --- GRID LAYOUT ---
        cols = st.columns([1.2, 2, 2, 2, 2, 2])

        # Kolonne 0: Labels
        with cols[0]:
            st.markdown("<div style='height: 160px;'></div>", unsafe_allow_html=True) # Spacer til billeder+navn
            for label, _, _, _ in metrics:
                st.markdown(f"<div class='metric-label'>{label}</div>", unsafe_allow_html=True)

        # Kolonne 1-5: Spillere
        for i, (idx, row) in enumerate(df_top5.iterrows()):
            with cols[i+1]:
                # Find billede (tjekker både fuldt navn og shortname match)
                img = "https://via.placeholder.com/150"
                if df_wyscout is not None and not df_wyscout.empty:
                    m = df_wyscout[(df_wyscout['FULL_NAME'] == row['PLAYER_NAME']) | 
                                   (df_wyscout['SHORTNAME'] == row['PLAYER_NAME'])]
                    if not m.empty:
                        img = m.iloc[0]['IMAGEDATAURL']
                
                st.markdown(f"<div style='text-align:center;'><img src='{img}' class='player-img'></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='player-header'>{row['PLAYER_NAME']}</div>", unsafe_allow_html=True)

                for label, key, div, unit in metrics:
                    val = row[key]
                    pct = min(int((val/max_vals[key])*100), 100) if max_vals[key] > 0 else 0
                    display_val = f"{val/div:.1f}" if div > 1 else f"{int(val)}"
                    
                    st.markdown(f"""
                        <div class='stat-row'>
                            <div class="bar-bg"><div class="bar-fill" style="width:{pct}%;"></div></div>
                            <div class="val-text">{display_val} <span style='font-size:8px; color:#888;'>{unit}</span></div>
                        </div>
                    """, unsafe_allow_html=True)

if __name__ == "__main__":
    vis_side()
