import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS
from data.utils.mapping import OPTA_EVENT_TYPES
import requests
from PIL import Image
from io import BytesIO

# --- 1. KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o"

# --- 2. HJÆLPEFUNKTIONER ---

@st.cache_data(ttl=3600)
def get_logo_img(opta_uuid):
    url = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), None)
    if not url: return None
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except: return None

def draw_match_info_box(ax, scoring_team_logo, opp_team_logo, date_str, score_str, min_str):
    if scoring_team_logo:
        ax_l1 = ax.inset_axes([0.02, 0.08, 0.05, 0.05], transform=ax.transAxes)
        ax_l1.imshow(scoring_team_logo)
        ax_l1.axis('off')
    ax.text(0.08, 0.105, "vs.", transform=ax.transAxes, fontsize=8, fontweight='bold', va='center')
    if opp_team_logo:
        ax_l2 = ax.inset_axes([0.10, 0.08, 0.05, 0.05], transform=ax.transAxes)
        ax_l2.imshow(opp_team_logo)
        ax_l2.axis('off')
    full_info = f"{date_str} | Stilling: {score_str} ({min_str}. min)"
    ax.text(0.03, 0.07, full_info, transform=ax.transAxes, fontsize=8, color='#444444', va='top', fontweight='medium')

# --- 3. HOVEDFUNKTION ---

def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn: return

    with st.spinner("Beregner stats baseret på QID 213..."):
        df_matches = conn.query(f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'")
        
        # 3.1 SQL til Spiller-stats (STRICT QID 213 LOGIK)
        sql_stats = f"""
        WITH UniqueAssists AS (
            -- Finder de præcise hændelser markeret med Assist (QID 213)
            SELECT DISTINCT EVENT_OPTAUUID 
            FROM {DB}.OPTA_QUALIFIERS 
            WHERE QUALIFIER_QID = 213
        ),
        GoalPossessions AS (
            SELECT DISTINCT MATCH_OPTAUUID, POSSESSIONID 
            FROM {DB}.OPTA_EVENTS 
            WHERE EVENT_TYPEID = 16 AND TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        )
        SELECT 
            e.PLAYER_NAME as PLAYER,
            e.EVENT_CONTESTANT_OPTAUUID as TEAM_ID,
            COUNT(DISTINCT CASE WHEN e.EVENT_TYPEID = 16 THEN e.EVENT_OPTAUUID END) as GOALS,
            COUNT(DISTINCT ua.EVENT_OPTAUUID) as ASSISTS,
            -- Pasninger tælles kun hvis de IKKE er i UniqueAssists tabellen
            COUNT(DISTINCT CASE WHEN e.EVENT_TYPEID = 1 AND ua.EVENT_OPTAUUID IS NULL THEN e.EVENT_OPTAUUID END) as PASSES_NO_ASSIST,
            COUNT(DISTINCT e.EVENT_OPTAUUID) as TOTAL_ACTIONS
        FROM {DB}.OPTA_EVENTS e
        INNER JOIN GoalPossessions gp ON e.MATCH_OPTAUUID = gp.MATCH_OPTAUUID AND e.POSSESSIONID = gp.POSSESSIONID
        LEFT JOIN UniqueAssists ua ON e.EVENT_OPTAUUID = ua.EVENT_OPTAUUID
        WHERE e.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        AND e.PLAYER_NAME IS NOT NULL
        GROUP BY 1, 2
        HAVING (GOALS > 0 OR ASSISTS > 0 OR PASSES_NO_ASSIST > 0)
        ORDER BY GOALS DESC, ASSISTS DESC
        """
        df_all_stats = conn.query(sql_stats)

        # 3.2 Hent sekvenser til grafikken
        sql_seq = f"SELECT e.*, m.CONTESTANTHOME_NAME, m.CONTESTANTAWAY_NAME FROM {DB}.OPTA_EVENTS e JOIN {DB}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID WHERE e.EVENT_TYPEID = 16 OR e.POSSESSIONID IN (SELECT DISTINCT POSSESSIONID FROM {DB}.OPTA_EVENTS WHERE EVENT_TYPEID = 16)"
        # (Forenklet for eksemplet skyld, brug din eksisterende sekvens-SQL her)
        df_sequences = conn.query(sql_seq)

    # 4. UI LOGIK
    ids = pd.concat([df_matches['CONTESTANTHOME_OPTAUUID'], df_matches['CONTESTANTAWAY_OPTAUUID']]).unique()
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    team_map = {mapping_lookup.get(str(u).lower().replace('t','')): u for u in ids if mapping_lookup.get(str(u).lower().replace('t',''))}

    col_hold = st.columns([3, 1])[1]
    valgt_hold = col_hold.selectbox("Vælg hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]

    t1, t2, t3 = st.tabs(["EVENTS", "MÅL-SEKVENSER", "SPILLEROVERSIGT"])

    with t3:
        df_team_stats = df_all_stats[df_all_stats['TEAM_ID'] == valgt_uuid].drop(columns=['TEAM_ID']).copy()
        df_team_stats = df_team_stats.rename(columns={
            'PLAYER': 'Spiller',
            'GOALS': 'Mål',
            'ASSISTS': 'Assists',
            'PASSES_NO_ASSIST': 'Pasninger (ikke assist)',
            'TOTAL_ACTIONS': 'Involveringer i mål-sekvenser'
        })
        st.table(df_team_stats)
