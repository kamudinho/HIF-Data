import streamlit as st
import pandas as pd
from mplsoccer import Pitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS
from data.utils.mapping import OPTA_EVENT_TYPES
import matplotlib.pyplot as plt

# --- KONFIGURATION FRA DINE QUERIES ---
DB = "KLUB_HVIDOVREIF.AXIS"
HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" # NordicBet som standard

def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn: return

    # 1. HENT DATA BASERET PÅ DINE STRUKTURER
    with st.spinner("Synkroniserer med Hvidovre-databasen..."):
        # Vi henter kampinfo for at kunne mappe modstandere
        df_matches = conn.query(f"SELECT MATCH_OPTAUUID, CONTESTANTHOME_NAME, CONTESTANTAWAY_NAME, CONTESTANTHOME_OPTAUUID, MATCH_LOCALDATE FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'")
        
        # SQL til oversigt - rettet så assists er unikke pr. event
        sql_stats = f"""
        WITH GoalSequences AS (
            SELECT DISTINCT MATCH_OPTAUUID, POSSESSIONID 
            FROM {DB}.OPTA_EVENTS 
            WHERE EVENT_TYPEID = 16 
            AND TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        ),
        ActualAssists AS (
            SELECT EVENT_OPTAUUID, MATCH_OPTAUUID 
            FROM {DB}.OPTA_QUALIFIERS 
            WHERE QUALIFIER_QID = 213 -- Den officielle Opta-markør for assist
        )
        SELECT 
            e.PLAYER_NAME as PLAYER,
            e.EVENT_CONTESTANT_OPTAUUID as TEAM_ID,
            COUNT(*) as ACTIONS_IN_GOAL_PROD,
            COUNT(DISTINCT e.MATCH_OPTAUUID || e.POSSESSIONID) as GOAL_INVOLVEMENTS,
            COUNT(CASE WHEN e.EVENT_TYPEID = 16 THEN 1 END) as GOALS,
            COUNT(CASE WHEN aa.EVENT_OPTAUUID IS NOT NULL THEN 1 END) as ASSISTS,
            COUNT(CASE WHEN e.EVENT_TYPEID = 1 AND aa.EVENT_OPTAUUID IS NULL THEN 1 END) as PASSES_NON_ASSIST,
            COUNT(CASE WHEN e.EVENT_TYPEID IN (3, 7, 44) THEN 1 END) as DUELS
        FROM {DB}.OPTA_EVENTS e
        INNER JOIN GoalSequences gs ON e.MATCH_OPTAUUID = gs.MATCH_OPTAUUID AND e.POSSESSIONID = gs.POSSESSIONID
        LEFT JOIN ActualAssists aa ON e.EVENT_OPTAUUID = aa.EVENT_OPTAUUID AND e.MATCH_OPTAUUID = aa.MATCH_OPTAUUID
        WHERE e.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        AND e.PLAYER_NAME IS NOT NULL
        GROUP BY 1, 2
        ORDER BY GOAL_INVOLVEMENTS DESC
        """
        df_stats = conn.query(sql_stats)

    # 2. HOLDVALG (Baseret på dine mapping-principper)
    # Vi finder alle hold-ID'er fra de kampe vi har hentet
    hold_ids = pd.concat([df_matches['CONTESTANTHOME_OPTAUUID']]).unique()
    
    # Simpel mapping til dropdown
    team_options = {HIF_UUID: "Hvidovre IF"}
    for _, row in df_matches.iterrows():
        if row['CONTESTANTHOME_OPTAUUID'] not in team_options:
            team_options[row['CONTESTANTHOME_OPTAUUID']] = row['CONTESTANTHOME_NAME']

    col_spacer, col_hold = st.columns([3, 1])
    valgt_hold_name = col_hold.selectbox("Vælg hold", options=list(team_options.values()))
    valgt_uuid = [k for k, v in team_options.items() if v == valgt_hold_name][0]

    # 3. VISNING AF TABELLEN
    st.subheader(f"Spillere involveret i mål - {valgt_hold_name}")
    
    display_df = df_stats[df_stats['TEAM_ID'] == valgt_uuid].copy()
    
    # Omdøb til dine ønskede kolonnenavne
    display_df = display_df.rename(columns={
        'PLAYER': 'Spiller',
        'ACTIONS_IN_GOAL_PROD': 'Aktioner i målsekvenser',
        'GOAL_INVOLVEMENTS': 'Involveret i antal mål',
        'GOALS': 'Mål',
        'ASSISTS': 'Assists',
        'PASSES_NON_ASSIST': 'Pasninger (mål)',
        'DUELS': 'Dueller (mål)'
    })

    # Vis tabellen
    st.dataframe(
        display_df.drop(columns=['TEAM_ID']), 
        use_container_width=True, 
        hide_index=True
    )

    # 4. INFO-BOKS
    st.info("""
    **Forklaring:** * **Involveret i antal mål**: Antal unikke målsekvenser, hvor spilleren har haft mindst én aktion.
    * **Assists**: Kun aktioner direkte markeret som målgivende (Qualifier 213).
    * **Pasninger (mål)**: Øvrige pasninger i sekvensen, der førte til mål, men som ikke var den direkte assist.
    """)
