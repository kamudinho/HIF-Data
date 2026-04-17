import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
CURRENT_SEASON = "2025/2026"
LIGA_IDS = "('335', '328', '329', '43319', '331')"

def vis_side():
    # CSS - Stramt design med sorte headers og bar-charts
    st.markdown("""
        <style>
        .player-header { 
            background-color: black; color: white; text-align: center; 
            font-weight: bold; padding: 10px 5px; margin-bottom: 15px; 
            border-radius: 2px; font-size: 11px; text-transform: uppercase;
            min-height: 45px; display: flex; align-items: center; justify-content: center;
        }
        .stat-label { font-size: 10px; color: #666; text-transform: uppercase; margin-top: 8px; font-weight: 600; }
        .bar-bg { background-color: #f0f0f0; height: 6px; width: 100%; border-radius: 3px; margin-top: 2px; }
        .bar-fill { background-color: #df003b; height: 6px; border-radius: 3px; }
        .val-text { font-size: 11px; font-weight: bold; text-align: right; color: #1f1f1f; margin-top: 2px; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h2 style='text-align: center;'>PHYSICAL PERFORMANCE PROFILES</h2>", unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn: return

    # 1. HOLDVALG
    query_teams = f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}"
    df_teams_raw = conn.query(query_teams)
    
    mapping_lookup = {str(info['opta_uuid']).lower().replace('t', ''): name for name, info in TEAMS.items() if 'opta_uuid' in info}
    team_map = {}
    if df_teams_raw is not None:
        for _, r in df_teams_raw.iterrows():
            uuid_clean = str(r['CONTESTANTHOME_OPTAUUID']).lower().replace('t','')
            if uuid_clean in mapping_lookup:
                team_map[mapping_lookup[uuid_clean]] = r['CONTESTANTHOME_OPTAUUID']

    valgt_hold = st.selectbox("Vælg Hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    target_ssiid = TEAMS.get(valgt_hold, {}).get('ssid', '56fa29c7-3a48-4186-9d14-dbf45fbc78d9')

    # 2. HENT TOP 5 FYSISKE DATA (Second Spectrum)
    sql_phys = f"""
        SELECT 
            PLAYER_NAME,
            AVG(DISTANCE) as DIST,
            AVG("HIGH SPEED RUNNING") as HSR,
            MAX(TOP_SPEED) as SPEED,
            AVG(NO_OF_HIGH_INTENSITY_RUNS) as ACCELS
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'
        AND MATCH_SSIID IN (
            SELECT MATCH_SSIID FROM {DB}.SECONDSPECTRUM_GAME_METADATA
            WHERE HOME_SSIID = '{target_ssiid}' OR AWAY_SSIID = '{target_ssiid}'
        )
        GROUP BY PLAYER_NAME
        ORDER BY DIST DESC
        LIMIT 5
    """
    
    df_top5 = conn.query(sql_phys)
    if df_top5 is None or df_top5.empty:
        st.warning("Ingen fysiske data fundet for holdet.")
        return

    # 3. HENT BILLEDER FRA WYSCOUT_PLAYERS (Med de korrekte kolonnenavne)
    # Vi bruger TRIM(FIRSTNAME) || ' ' || TRIM(LASTNAME) for at matche Second Spectrum navnet
    names_list = "('" + "','".join(df_top5['PLAYER_NAME'].tolist()) + "')"
    sql_images = f"""
        SELECT 
            (TRIM(FIRSTNAME) || ' ' || TRIM(LASTNAME)) as FULL_NAME, 
            MAX(IMAGEDATAURL) as IMG 
        FROM {DB}.WYSCOUT_PLAYERS 
        WHERE FULL_NAME IN {names_list} 
        GROUP BY 1
    """
    df_wyscout = conn.query(sql_images)

    # 4. GRID VISNING
    cols = st.columns(5)
    max_vals = {
        "DIST": df_top5['DIST'].max(), 
        "HSR": df_top5['HSR'].max(), 
        "SPEED": df_top5['SPEED'].max(), 
        "ACCELS": df_top5['ACCELS'].max()
    }

    for i, (idx, row) in enumerate(df_top5.iterrows()):
        with cols[i]:
            # Match billede på tværs af kilder
            img_url = "https://via.placeholder.com/150"
            if df_wyscout is not None and not df_wyscout.empty:
                match = df_wyscout[df_wyscout['FULL_NAME'] == row['PLAYER_NAME']]
                if not match.empty and pd.notnull(match['IMG'].iloc[0]):
                    img_url = match['IMG'].iloc[0]

            st.image(img_url, use_container_width=True)
            st.markdown(f"<div class='player-header'>{row['PLAYER_NAME']}</div>", unsafe_allow_html=True)

            # Visning af fysiske stats
            metrics = [
                ("Distance", row['DIST']/1000, max_vals['DIST']/1000, "km"),
                ("HSR", row['HSR'], max_vals['HSR'], "m"),
                ("Topfart", row['SPEED'], max_vals['SPEED'], "km/t"),
                ("Eksplosiv", row['ACCELS'], max_vals['ACCELS'], "akt")
            ]

            for label, val, m_val, unit in metrics:
                pct = min(int((val / m_val) * 100), 100) if m_val > 0 else 0
                val_text = f"{val:.1f}" if unit != "m" else f"{int(val)}"
                
                st.markdown(f"""
                    <div class="stat-label">{label}</div>
                    <div class="bar-bg"><div class="bar-fill" style="width:{pct}%;"></div></div>
                    <div class="val-text">{val_text} <span style="font-size:9px; color:#888;">{unit}</span></div>
                """, unsafe_allow_html=True)

if __name__ == "__main__":
    vis_side()
