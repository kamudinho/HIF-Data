import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
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

    # SQL der bruger en Sub-query til at aggregere Qualifiers FØRST
    # Dette sikrer 1:1 forhold mellem Event og Qualifiers
    sql = f"""
    WITH AGG_QUALS AS (
        SELECT 
            EVENT_OPTAUUID,
            LISTAGG(QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY QUALIFIER_QID) as QUAL_LIST,
            MAX(CASE WHEN QUALIFIER_QID = 140 THEN TRY_TO_DOUBLE(QUALIFIER_VALUE) END) as ENDX,
            MAX(CASE WHEN QUALIFIER_QID = 141 THEN TRY_TO_DOUBLE(QUALIFIER_VALUE) END) as ENDY,
            MAX(CASE WHEN QUALIFIER_QID = 223 THEN 'Inswinger' 
                     WHEN QUALIFIER_QID = 224 THEN 'Outswinger' 
                     WHEN QUALIFIER_QID = 225 THEN 'Straight' ELSE 'Standard' END) as SWING_TYPE
        FROM {DB}.OPTA_QUALIFIERS
        GROUP BY EVENT_OPTAUUID
    )
    SELECT 
        e.EVENT_OPTAUUID, 
        e.EVENT_X, 
        e.EVENT_Y, 
        e.EVENT_CONTESTANT_OPTAUUID as TEAM_UUID, 
        e.PLAYER_OPTAUUID as PLAYER_UUID,
        q.QUAL_LIST,
        q.ENDX as EVENT_ENDX,
        q.ENDY as EVENT_ENDY,
        q.SWING_TYPE,
        TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME
    FROM {DB}.OPTA_EVENTS e
    INNER JOIN AGG_QUALS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
    LEFT JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
    WHERE e.MATCH_OPTAUUID IN (
        SELECT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO 
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
    )
    AND e.EVENT_TYPEID = 1 -- Kun pasninger/igangsætninger
    AND (
        ',' || q.QUAL_LIST || ',' LIKE '%,6,%' OR 
        ',' || q.QUAL_LIST || ',' LIKE '%,107,%' OR 
        ',' || q.QUAL_LIST || ',' LIKE '%,5,%'
    )
    """
    
    df = conn.query(sql)
    if df is None or df.empty: return pd.DataFrame()
    df.columns = [c.upper() for c in df.columns]

    # Type labeling
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
    st.title("🎯 Standardsituationer (Præcis tælling)")
    
    df_all = load_setpiece_data()
    if df_all.empty:
        st.warning("Ingen data fundet.")
        return

    # Team mapping
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['TEAM_UUID'].str.upper().map(uuid_to_name)
    
    teams_in_data = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        t_sel = st.selectbox("Vælg hold", teams_in_data)
    with col_f2:
        sp_type = st.selectbox("Type", ["Hjørnespark", "Indkast", "Frispark"])

    # Filtrering
    df_team = df_all[(df_all['KLUB_NAVN'] == t_sel) & (df_all['SET_PIECE_TYPE'] == sp_type)].copy()

    # Fjern dubletter for en sikkerheds skyld (hvis SQL'en mod forventning stadig spytter dem ud)
    df_team = df_team.drop_duplicates(subset=['EVENT_OPTAUUID'])

    # --- RESTEN AF DIN VISUALISERING ---
    # (Beregninger af X_M, Y_M og Pitch tegning herfra er uændret)
    
    # Skalering
    mask_flip = df_team['EVENT_X'] < 50
    for col_x, col_y in [('EVENT_X', 'EVENT_Y'), ('EVENT_ENDX', 'EVENT_ENDY')]:
        df_team.loc[mask_flip, col_x] = 100 - df_team.loc[mask_flip, col_x]
        df_team.loc[mask_flip, col_y] = 100 - df_team.loc[mask_flip, col_y]

    df_team['X_M'] = df_team['EVENT_X'].apply(lambda x: to_metric(x, 105))
    df_team['Y_M'] = df_team['EVENT_Y'].apply(lambda y: to_metric(y, 68))
    df_team['ENDX_M'] = df_team['EVENT_ENDX'].apply(lambda x: to_metric(x, 105))
    df_team['ENDY_M'] = df_team['EVENT_ENDY'].apply(lambda y: to_metric(y, 68))

    st.metric(f"Antal unikke {sp_type}", len(df_team))
    
    # Vis statistikken som i "Skærmbillede 2026-05-12 kl. 12.49.41.png"
    st.write("**Top udførere:**")
    st.dataframe(df_team['PLAYER_NAME'].value_counts())

if __name__ == "__main__":
    vis_side()
