import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from mplsoccer import Pitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS
import requests
from PIL import Image
from io import BytesIO
import os

# --- IMPORT FRA MAPPING ---
from data.utils.mapping import get_action_label

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '335', '328', '329', '43319', '331')"
CURRENT_SEASON = "2025/2026"

def vis_side(dp=None):
    # --- 1. INDLÆS NAVNE-OVERSKRIVNING ---
    try:
        # Finder din fil i data/players/1div_overskrivning.csv
        base_path = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(base_path, '..', '..', 'data', 'players', '1div_overskrivning.csv')
        df_navne_csv = pd.read_csv(csv_path)
        
        # Vi mapper PLAYER_OPTAUUID (fra CSV) til NAVN (fra CSV)
        navne_map = dict(zip(df_navne_csv['PLAYER_OPTAUUID'].astype(str), df_navne_csv['NAVN']))
    except Exception as e:
        st.error(f"Kunne ikke læse navne-fil: {e}")
        navne_map = {}

    conn = _get_snowflake_conn()
    if not conn: return

    # --- 2. HENT HOLD ---
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
    if df_teams_raw is not None:
        df_teams_raw.columns = df_teams_raw.columns.str.lower()
    
    mapping_lookup = {str(info['opta_uuid']).lower().replace('t', ''): name for name, info in TEAMS.items() if 'opta_uuid' in info}
    team_map = {}
    if df_teams_raw is not None:
        for _, r in df_teams_raw.iterrows():
            uuid_clean = str(r['contestanthome_optauuid']).lower().replace('t','')
            if uuid_clean in mapping_lookup:
                team_map[mapping_lookup[uuid_clean]] = r['contestanthome_optauuid']

    col_h_hold, col_h_spiller = st.columns([1, 1])
    valgt_hold = col_h_hold.selectbox("Hold", sorted(list(team_map.keys())))
    valgt_uuid_hold = team_map[valgt_hold]

    # --- 3. HENT DATA (SQL RETTET FOR QUALIFIER FEJL) ---
    with st.spinner("Henter data..."):
        sql_events = f"""
            SELECT 
                e.EVENT_X, 
                e.EVENT_Y, 
                e.EVENT_TYPEID, 
                TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as DB_NAVN, 
                e.PLAYER_OPTAUUID, 
                e.EVENT_OUTCOME as OUTCOME,
                LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
            FROM {DB}.OPTA_EVENTS e
            JOIN (SELECT DISTINCT PLAYER_OPTAUUID, FIRST_NAME, LAST_NAME FROM {DB}.OPTA_PLAYERS) p 
                ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
            LEFT JOIN {DB}.OPTA_QUALIFIERS q 
                ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid_hold}' 
            AND e.EVENT_TIMESTAMP >= '2025-07-01'
            GROUP BY 1, 2, 3, 4, 5, 6
        """
        df_all = conn.query(sql_events)
        
    if df_all is not None and not df_all.empty:
        df_all.columns = df_all.columns.str.lower()
        
        # --- HER SKER OVERSÆTTELSEN ---
        # Vi tager PLAYER_OPTAUUID fra databasen og ser om den findes i din CSV
        def oversæt_navn(row):
            uuid = str(row['player_optauuid'])
            return navne_map.get(uuid, row['db_navn']) # Brug CSV-navn hvis det findes, ellers DB-navn
        
        df_all['visningsnavn'] = df_all.apply(oversæt_navn, axis=1)

        # Dropdown med de nye navne
        spiller_liste = sorted(df_all['visningsnavn'].unique())
        valgt_spiller_navn = col_h_spiller.selectbox("Spiller", spiller_liste)
        
        # Filtrer data på den valgte spiller
        df_spiller = df_all[df_all['visningsnavn'] == valgt_spiller_navn].copy()
        
        # --- VISNING (EKSEMPEL) ---
        st.subheader(f"Profil for {valgt_spiller_navn}")
        
        # Tilføj din Pitch eller Tabel logik herunder...
        pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
        fig, ax = pitch.draw()
        pitch.scatter(df_spiller.event_x, df_spiller.event_y, ax=ax, alpha=0.5)
        st.pyplot(fig)
    else:
        st.warning("Ingen data fundet for det valgte hold.")

if __name__ == "__main__":
    vis_side()
