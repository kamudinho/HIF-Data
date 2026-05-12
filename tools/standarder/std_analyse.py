import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

# --- KONFIGURATION ---
HIF_RED = '#cc0000'
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" 
PLAYER_FILE = 'data/players/spiller_overskrivning.csv'

@st.cache_data(ttl=3600)
def load_setpiece_data():
    # 1. Hent dine navne fra CSV
    df_lookup = pd.read_csv(PLAYER_FILE)
    # Rens UUIDs så de matcher databasen
    df_lookup['PLAYER_OPTAUUID'] = df_lookup['PLAYER_OPTAUUID'].astype(str).str.strip()
    name_map = df_lookup.dropna(subset=['PLAYER_OPTAUUID']).set_index('PLAYER_OPTAUUID')['NAVN'].to_dict()

    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()

    # 2. SQL - Henter rå-data
    sql = f"""
    WITH RAW_EVENTS AS (
        SELECT 
            e.EVENT_OPTAUUID, e.EVENT_X, e.EVENT_Y, 
            e.EVENT_CONTESTANT_OPTAUUID as TEAM_UUID, 
            e.MATCH_OPTAUUID,
            TRIM(e.PLAYER_OPTAUUID) as PLAYER_OPTAUUID,
            LEAD(TRIM(e.PLAYER_OPTAUUID)) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) as NEXT_PLAYER_UUID
        FROM {DB}.OPTA_EVENTS e
        WHERE e.MATCH_OPTAUUID IN (
            SELECT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO 
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        )
    ),
    AGG_QUALS AS (
        SELECT 
            EVENT_OPTAUUID,
            LISTAGG(QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY QUALIFIER_QID) as QUAL_LIST,
            MAX(CASE WHEN QUALIFIER_QID = 140 THEN TRY_TO_DOUBLE(QUALIFIER_VALUE) END) as ENDX,
            MAX(CASE WHEN QUALIFIER_QID = 141 THEN TRY_TO_DOUBLE(QUALIFIER_VALUE) END) as ENDY,
            MAX(CASE WHEN QUALIFIER_QID IN (214, 154, 111) THEN 1 ELSE 0 END) as IS_CHANCE
        FROM {DB}.OPTA_QUALIFIERS
        GROUP BY EVENT_OPTAUUID
    )
    SELECT r.*, q.QUAL_LIST, q.ENDX as EVENT_ENDX, q.ENDY as EVENT_ENDY, q.IS_CHANCE
    FROM RAW_EVENTS r
    INNER JOIN AGG_QUALS q ON r.EVENT_OPTAUUID = q.EVENT_OPTAUUID
    WHERE (',' || q.QUAL_LIST || ',' LIKE '%,6,%' OR ',' || q.QUAL_LIST || ',' LIKE '%,107,%' OR ',' || q.QUAL_LIST || ',' LIKE '%,5,%')
    """
    df = conn.query(sql)
    if df is None or df.empty: return pd.DataFrame()
    df.columns = [c.upper() for c in df.columns]

    # 3. Map navne og filtrer trup
    df = df[df['PLAYER_OPTAUUID'].isin(name_map.keys())].copy()
    df['PLAYER_NAME'] = df['PLAYER_OPTAUUID'].map(name_map)
    df['NEXT_PLAYER_NAME'] = df['NEXT_PLAYER_UUID'].map(name_map)

    def assign_label(row):
        ql = ',' + str(row['QUAL_LIST']) + ','
        if ',6,' in ql: return "Hjørnespark"
        if ',107,' in ql: return "Indkast"
        if ',5,' in ql: return "Frispark"
        return "Andet"
    
    df['SET_PIECE_TYPE'] = df.apply(assign_label, axis=1)
    return df

def to_metric(val, total_m): return val * (total_m / 100)

def vis_side():
    st.title("Standard-Analyse")
    
    df_all = load_setpiece_data()
    if df_all.empty:
        st.warning("Ingen data fundet. Tjek spiller-UUIDs i din CSV.")
        return

    # Hold-valg
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['TEAM_UUID'].str.upper().map(uuid_to_name)
    teams_in_data = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])

    c1, c2 = st.columns(2)
    with c1: t_sel = st.selectbox("Vælg Hold", teams_in_data)
    with c2: sp_type = st.selectbox("Vælg Type", ["Hjørnespark", "Indkast", "Frispark"])

    df_team = df_all[(df_all['KLUB_NAVN'] == t_sel) & (df_all['SET_PIECE_TYPE'] == sp_type)].copy()
    
    # --- SUCCES LOGIK (Den vigtige del!) ---
    # Succes er kun sand, hvis den næste spiller er en medspiller fra din liste
    df_team['REAL_SUCCESS'] = (df_team['NEXT_PLAYER_NAME'].notna()) & \
                              (df_team['NEXT_PLAYER_UUID'] != df_team['PLAYER_OPTAUUID'])

    # Statistik-tabel
    def get_top_receiver(x):
        receivers = x[x['REAL_SUCCESS']]['NEXT_PLAYER_NAME']
        if not receivers.empty:
            c = receivers.value_counts()
            return f"{c.idxmax()} ({c.max()})"
        return "Ingen medspiller ramt"

    stats_df = df_team.groupby('PLAYER_NAME').apply(lambda x: pd.Series({
        'Antal': len(x),
        'Succes': int(x['REAL_SUCCESS'].sum()),
        'Afslutninger': int(x['IS_CHANCE'].sum()),
        'Primær modtager (antal)': get_top_receiver(x)
    })).reset_index()
    
    stats_df['Succes %'] = (stats_df['Succes'] / stats_df['Antal'] * 100).round(1)

    st.dataframe(
        stats_df.sort_values('Antal', ascending=False),
        column_config={"Succes %": st.column_config.NumberColumn("Succes %", format="%.1f %%")},
        hide_index=True, use_container_width=True
    )

if __name__ == "__main__":
    vis_side()
