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

@st.cache_data(ttl=3600)
def load_setpiece_data():
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()

    # SQL med ACTIVE_STATUS filter
    sql = f"""
    WITH RAW_EVENTS AS (
        SELECT 
            e.EVENT_OPTAUUID, 
            e.EVENT_X, 
            e.EVENT_Y, 
            e.EVENT_OUTCOME,
            e.EVENT_CONTESTANT_OPTAUUID as TEAM_UUID, 
            e.MATCH_OPTAUUID,
            e.PLAYER_OPTAUUID,
            TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME,
            LEAD(TRIM(p_next.FIRST_NAME) || ' ' || TRIM(p_next.LAST_NAME)) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) as NEXT_PLAYER_NAME
        FROM {DB}.OPTA_EVENTS e
        LEFT JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
        LEFT JOIN {DB}.OPTA_EVENTS e_next ON e.MATCH_OPTAUUID = e_next.MATCH_OPTAUUID AND (e.EVENT_EVENTID + 1) = e_next.EVENT_EVENTID
        LEFT JOIN {DB}.OPTA_PLAYERS p_next ON e_next.PLAYER_OPTAUUID = p_next.PLAYER_OPTAUUID
        WHERE e.MATCH_OPTAUUID IN (
            SELECT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO 
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        )
        AND p.ACTIVE_STATUS = 'active'
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

    def assign_label(row):
        ql = ',' + str(row['QUAL_LIST']) + ','
        if ',6,' in ql: return "Hjørnespark"
        if ',107,' in ql: return "Indkast"
        if ',5,' in ql: return "Frispark"
        return "Andet"
    
    df['SET_PIECE_TYPE'] = df.apply(assign_label, axis=1)
    return df[df['SET_PIECE_TYPE'] != "Andet"]

def to_metric(val, total_m): return val * (total_m / 100)

def vis_side():
    st.title("Standard-Analyse (Renset)")
    
    df_all = load_setpiece_data()
    if df_all.empty:
        st.error("Ingen data fundet.")
        return

    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['TEAM_UUID'].str.upper().map(uuid_to_name)
    teams_in_data = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])

    c1, c2, c3, c4 = st.columns(4)
    with c1: t_sel = st.selectbox("Hold", teams_in_data)
    with c2: sp_type = st.selectbox("Type", ["Hjørnespark", "Indkast", "Frispark"])
    with c3: side_filter = st.selectbox("Side", ["Begge", "Venstre", "Højre"])
    with c4: mode = st.selectbox("Mode", ["Normaliseret (Højre)", "Faktisk"])

    df_team = df_all[(df_all['KLUB_NAVN'] == t_sel) & (df_all['SET_PIECE_TYPE'] == sp_type)].copy()
    
    # --- LOGIK FOR SUCCES ---
    # Vi definerer succes som: Næste spiller findes, og det er IKKE skytten selv
    df_team['REAL_SUCCESS'] = (df_team['NEXT_PLAYER_NAME'].notna()) & \
                              (df_team['NEXT_PLAYER_NAME'] != "None") & \
                              (df_team['NEXT_PLAYER_NAME'] != df_team['PLAYER_NAME'])

    # (Normalisering og Bane-beregninger her...)
    df_team['X_M'], df_team['Y_M'] = to_metric(df_team['EVENT_X'], 105), to_metric(df_team['EVENT_Y'], 68)
    df_team['ENDX_M'], df_team['ENDY_M'] = to_metric(df_team['EVENT_ENDX'], 105), to_metric(df_team['EVENT_ENDY'], 68)

    tab_bane, tab_stats = st.tabs(["Banevisning", "Statistik"])

    with tab_stats:
        def get_top_receiver(x):
            # Kun medspillere
            receivers = x[(x['NEXT_PLAYER_NAME'] != x['PLAYER_NAME']) & (x['NEXT_PLAYER_NAME'] != "None")]['NEXT_PLAYER_NAME'].dropna()
            if not receivers.empty:
                return f"{receivers.value_counts().idxmax()} ({receivers.value_counts().max()})"
            return "Ingen medspiller ramt"

        stats_df = df_team.groupby('PLAYER_NAME').apply(lambda x: pd.Series({
            'Antal': len(x),
            'Succes': x['REAL_SUCCESS'].sum(),
            'Afslutninger': x['IS_CHANCE'].sum(),
            'Oftest_ramte': get_top_receiver(x)
        })).reset_index()
        
        stats_df['Succes %'] = (stats_df['Succes'] / stats_df['Antal'] * 100).round(1)
        
        st.data_editor(
            stats_df.sort_values('Antal', ascending=False),
            column_config={
                "Succes %": st.column_config.NumberColumn("Succes % (Ramte medspiller)", format="%.1f %%")
            },
            hide_index=True, use_container_width=True
        )

if __name__ == "__main__":
    vis_side()
