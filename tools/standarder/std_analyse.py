import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn
from PIL import Image
import requests
from io import BytesIO

# --- KONFIGURATION ---
HIF_RED = '#cc0000'
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o"

@st.cache_data(ttl=3600)
def load_setpiece_data():
    conn = _get_snowflake_conn()
    if not conn: 
        return pd.DataFrame()

    match_sql = f"SELECT DISTINCT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"

    # SQL der henter start- OG slutkoordinater via Qualifiers (140/141)
    sql = f"""
    WITH END_X AS (
        SELECT EVENT_OPTAUUID, QUALIFIER_VALUE as ENDX FROM {DB}.OPTA_QUALIFIERS WHERE QUALIFIER_QID = 140
    ),
    END_Y AS (
        SELECT EVENT_OPTAUUID, QUALIFIER_VALUE as ENDY FROM {DB}.OPTA_QUALIFIERS WHERE QUALIFIER_QID = 141
    ),
    SET_PIECE_EVENTS AS (
        SELECT e.EVENT_OPTAUUID, e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, 
               e.EVENT_CONTESTANT_OPTAUUID, e.PLAYER_OPTAUUID, q.QUALIFIER_QID, e.MATCH_OPTAUUID
        FROM {DB}.OPTA_EVENTS e
        JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
        WHERE q.QUALIFIER_QID IN (2, 5, 107, 124) -- Corner, Free Kick, Throw-in
        AND e.MATCH_OPTAUUID IN ({match_sql})
    )
    SELECT 
        s.*,
        ex.ENDX as EVENT_ENDX,
        ey.ENDY as EVENT_ENDY,
        TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME
    FROM SET_PIECE_EVENTS s
    LEFT JOIN END_X ex ON s.EVENT_OPTAUUID = ex.EVENT_OPTAUUID
    LEFT JOIN END_Y ey ON s.EVENT_OPTAUUID = ey.EVENT_OPTAUUID
    LEFT JOIN {DB}.OPTA_PLAYERS p ON s.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
    """
    df = conn.query(sql)
    df.columns = [c.upper() for c in df.columns]

    # Konverter koordinater til floats
    for col in ['EVENT_X', 'EVENT_Y', 'EVENT_ENDX', 'EVENT_ENDY']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Mapping af typer
    type_map = {2: "Hjørnespark", 124: "Hjørnespark", 5: "Frispark", 107: "Indkast"}
    df['SET_PIECE_TYPE'] = df['QUALIFIER_QID'].map(type_map)

    return df

def to_metric(val, total_m):
    return val * (total_m / 100)

# --- MAIN APP ---
def vis_side():
    st.markdown("<style>header {visibility: hidden;} .main .block-container { padding-top: 1rem; }</style>", unsafe_allow_html=True)

    df_all = load_setpiece_data()
    if df_all.empty:
        st.warning("Ingen data fundet. Tjek om ligaens UUID og Snowflake-forbindelsen er korrekt.")
        return

    # Team Mapping
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['EVENT_CONTESTANT_OPTAUUID'].str.upper().map(uuid_to_name)
    teams = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])

    # Filtre
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        t_sel = st.selectbox("Hold", teams, index=teams.index("Hvidovre") if "Hvidovre" in teams else 0)
    with col_f2:
        sp_type = st.selectbox("Type", ["Hjørnespark", "Indkast", "Frispark"])
    with col_f3:
        side_sel = st.selectbox("Side", ["Begge", "Venstre", "Højre"])

    # Data filter
    df_team = df_all[(df_all['KLUB_NAVN'] == t_sel) & (df_all['SET_PIECE_TYPE'] == sp_type)].copy()

    # Skalering til meter
    df_team['X_M'] = df_team['EVENT_X'].apply(lambda x: to_metric(x, 105))
    df_team['Y_M'] = df_team['EVENT_Y'].apply(lambda y: to_
