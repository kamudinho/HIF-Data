import streamlit as st
import pandas as pd
import requests
from PIL import Image
from io import BytesIO
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
CURRENT_SEASON = "2025/2026"
LIGA_IDS = "('335', '328', '329', '43319', '331')"

def get_logo_img(opta_uuid):
    if not opta_uuid: return None
    uuid_clean = str(opta_uuid).lower().replace('t', '')
    url = next((info['logo'] for name, info in TEAMS.items() if str(info.get('opta_uuid', '')).lower().replace('t','') == uuid_clean), None)
    if not url: return None
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except: return None

def vis_side():
    # 1. CSS FOR FORBEDRET VISUEL PROFIL
    st.markdown("""
        <style>
        .player-card { border: 1px solid #eee; padding: 10px; border-radius: 5px; background: white; }
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

    st.markdown("<h2 style='text-align: center; color: #1a1a1a;'>PHYSICAL PERFORMANCE PROFILES</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666; margin-top: -15px;'>Top 5 Spillere - Gns. pr. kamp</p>", unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn: return

    # 2. HOLDVALG (Baseret på din eksisterende logik)
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
    mapping_lookup = {str(info['opta_uuid']).lower().replace('t', ''): name for name, info in TEAMS.items() if 'opta_uuid' in info}

    team_map = {}
    if df_teams_raw is not None:
        for _, r in df_teams_raw.iterrows():
            uuid_clean = str(r['CONTESTANTHOME_OPTAUUID']).lower().replace('t','')
            if uuid_clean in mapping_lookup:
                team_map[mapping_lookup[uuid_clean]] = r['CONTESTANTHOME_OPTAUUID']

    valgt_hold = st.selectbox("Vælg Hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    
    # 3. HENT DATA DIREKTE
    # Vi henter gennemsnit for alle spillere på holdet for at finde Top 5
    target_ssiid = TEAMS.get(valgt_hold, {}).get('ssid', '56fa29c7-3a48-4186-9d14-dbf45fbc78d9')
    
    sql_phys = f"""
        SELECT 
            p.PLAYER_NAME,
            ANY_VALUE(m.IMAGEDATAURL) as IMAGE,
            AVG(p.DISTANCE) as DIST,
            AVG(p."HIGH SPEED RUNNING") as HSR,
            MAX(p.TOP_SPEED) as SPEED,
            AVG(p.NO_OF_HIGH_INTENSITY_RUNS) as ACCELS
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS p
        LEFT JOIN {DB}.OPTA_PLAYERS m ON p."optaId" = m.PLAYER_OPTAUUID
        WHERE p.MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'
        AND p.MATCH_SSIID IN (
            SELECT MATCH_SSIID FROM {DB}.SECONDSPECTRUM_GAME_METADATA
            WHERE HOME_SSIID = '{target_ssiid}' OR AWAY_SSIID = '{target_ssiid}'
        )
        GROUP BY p.PLAYER_NAME
        ORDER BY DIST DESC
        LIMIT 5
    """
    
    try:
        df_top5 = conn.query(sql_phys)
        
        if df_top5 is None or df_top5.empty:
            st.warning("Ingen fysiske data fundet for det valgte hold.")
            return

        # 4. VISNING AF PROFILERNE I KOLONNER
        cols = st.columns(5)
        
        # Max værdier til bar-skalering (så de er relative til de 5 bedste)
        max_vals = {
            "DIST": df_top5['DIST'].max(),
            "HSR": df_top5['HSR'].max(),
            "SPEED": df_top5['SPEED'].max(),
            "ACCELS": df_top5['ACCELS'].max()
        }

        for i, (idx, row) in enumerate(df_top5.iterrows()):
            with cols[i]:
                # Spiller billede
                img_url = row['IMAGE'] if pd.notnull(row['IMAGE']) else "https://via.placeholder.com/150"
                st.image(img_url, use_container_width=True)
                
                # Sort header med fuldt navn
                st.markdown(f"<div class='player-header'>{row['PLAYER_NAME']}</div>", unsafe_allow_html=True)

                # Metrics sektion
                metrics = [
                    ("Distance", row['DIST']/1000, max_vals['DIST']/1000, "km"),
                    ("HSR", row['HSR'], max_vals['HSR'], "m"),
                    ("Topfart", row['SPEED'], max_vals['SPEED'], "km/t"),
                    ("Explosive", row['ACCELS'], max_vals['ACCELS'], "akt")
                ]

                for label, val, m_val, unit in metrics:
                    pct = min(int((val / m_val) * 100), 100) if m_val > 0 else 0
                    val_str = f"{val:.1f} {unit}" if unit != "m" else f"{int(val)} {unit}"
                    
                    st.markdown(f"""
                        <div class="stat-label">{label}</div>
                        <div class="bar-bg"><div class="bar-fill" style="width:{pct}%;"></div></div>
                        <div class="val-text">{val_str}</div>
                    """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Fejl ved datahentning: {e}")

if __name__ == "__main__":
    vis_side()
