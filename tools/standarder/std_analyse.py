import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" 
PLAYER_FILE = 'data/players/1div_overskrivning.csv'

def get_team_options():
    """Henter hurtigt en liste over holdnavne uden at hente alle events."""
    # Her kan du bruge din eksisterende TEAMS mapping eller lave en hurtig SELECT DISTINCT
    return sorted([k for k in TEAMS.keys()])

@st.cache_data(ttl=3600)
def load_team_setpiece_data(team_name):
    """Henter KUN data for det valgte hold - sparer hukommelse."""
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()

    # Find holdets UUID
    team_uuid = TEAMS.get(team_name, {}).get('opta_uuid')
    if not team_uuid: return pd.DataFrame()

    # 1. Hent events KUN for dette hold + deres modtagere (som kan være næste event)
    # Vi begrænser til events hvor holdet er involveret
    sql_events = f"""
    SELECT 
        EVENT_OPTAUUID, MATCH_OPTAUUID, EVENT_EVENTID, 
        EVENT_CONTESTANT_OPTAUUID AS TEAM_UUID,
        TRIM(PLAYER_OPTAUUID) AS PLAYER_UUID,
        EVENT_X, EVENT_Y
    FROM {DB}.OPTA_EVENTS
    WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
      AND MATCH_OPTAUUID IN (
          SELECT DISTINCT MATCH_OPTAUUID 
          FROM {DB}.OPTA_EVENTS 
          WHERE EVENT_CONTESTANT_OPTAUUID = '{team_uuid}'
      )
    ORDER BY MATCH_OPTAUUID, EVENT_EVENTID
    """
    
    # 2. Hent Qualifiers for dette hold
    sql_quals = f"""
    SELECT q.EVENT_OPTAUUID, q.QUALIFIER_QID, q.QUALIFIER_VALUE
    FROM {DB}.OPTA_QUALIFIERS q
    JOIN {DB}.OPTA_EVENTS e ON q.EVENT_OPTAUUID = e.EVENT_OPTAUUID
    WHERE e.EVENT_CONTESTANT_OPTAUUID = '{team_uuid}'
      AND q.QUALIFIER_QID IN (5, 6, 107, 140, 141, 214, 154, 111)
    """

    df_e = conn.query(sql_events)
    df_q_raw = conn.query(sql_quals)
    
    if df_e is None or df_q_raw is None: return pd.DataFrame()

    # --- PROCESSING (Samme logik som før, men på små data) ---
    df_q_raw['QUALIFIER_QID'] = df_q_raw['QUALIFIER_QID'].astype(str)
    df_q = df_q_raw.pivot_table(index='EVENT_OPTAUUID', columns='QUALIFIER_QID', values='QUALIFIER_VALUE', aggfunc='first').reset_index()

    # Merge og find modtager
    df = df_e[df_e['TEAM_UUID'] == team_uuid].merge(df_q, on='EVENT_OPTAUUID', how='inner')
    
    # Find modtager ved hjælp af den fulde event-liste (df_e)
    df_e['NEXT_PLAYER'] = df_e.groupby('MATCH_OPTAUUID')['PLAYER_UUID'].shift(-1)
    df_e['NEXT_TEAM'] = df_e.groupby('MATCH_OPTAUUID')['TEAM_UUID'].shift(-1)
    
    receiver_map = df_e[['EVENT_OPTAUUID', 'NEXT_PLAYER', 'NEXT_TEAM']]
    df = df.merge(receiver_map, on='EVENT_OPTAUUID', how='left')

    # Validering og typer
    df['MODTAGER_UUID'] = np.where((df['NEXT_PLAYER'] != df['PLAYER_UUID']) & (df['NEXT_TEAM'] == df['TEAM_UUID']), df['NEXT_PLAYER'], None)
    
    type_map = {'6': 'Hjørnespark', '107': 'Indkast', '5': 'Frispark'}
    df['TYPE_NAVN'] = None
    for qid, label in type_map.items():
        if qid in df.columns:
            df.loc[df[qid].notna(), 'TYPE_NAVN'] = label

    # Mapping af navne
    df_lookup = pd.read_csv(PLAYER_FILE)
    name_map = df_lookup.set_index('PLAYER_OPTAUUID')['NAVN'].to_dict()
    df['TAGER'] = df['PLAYER_UUID'].map(name_map)
    df['MODTAGER'] = df['MODTAGER_UUID'].map(name_map)
    
    df['END_X'] = pd.to_numeric(df.get('140'), errors='coerce')
    df['END_Y'] = pd.to_numeric(df.get('141'), errors='coerce')
    df['ER_CHANCE'] = df[df.columns[df.columns.isin(['214', '154', '111'])]].notna().any(axis=1).astype(int)

    return df[df['TYPE_NAVN'].notna()].dropna(subset=['TAGER'])

def vis_side():
    st.title("🎯 Standard-Analyse")
    
    # Trin 1: Vælg hold først (så vi ikke loader alt)
    team_list = get_team_options()
    t_sel = st.selectbox("Vælg Hold", team_list)

    # Trin 2: Hent data KUN for det hold
    df_plot = load_team_setpiece_data(t_sel)
    
    if df_plot.empty:
        st.warning(f"Ingen data fundet for {t_sel}")
        return

    # Resten af filtrene
    c1, c2 = st.columns(2)
    with c1: type_sel = st.selectbox("Type", ["Alle", "Hjørnespark", "Indkast", "Frispark"])
    with c2: player_sel = st.selectbox("Spiller", ["Alle"] + sorted(df_plot['TAGER'].unique()))

    if type_sel != "Alle": df_plot = df_plot[df_plot['TYPE_NAVN'] == type_sel]
    if player_sel != "Alle": df_plot = df_plot[df_plot['TAGER'] == player_sel]

    tab1, tab2 = st.tabs(["Statistik", "Banevisning"])
    # ... (Statistik og banevisning koden herfra er den samme som før)
