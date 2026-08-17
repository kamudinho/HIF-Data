import streamlit as st
import pandas as pd
import os
import io
import base64

# --- DATA OG MAPPING ---
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS
from data.utils.mapping import is_assist, get_action_label
from data.utils.spiller_qualifiers import ACTION_CATEGORIES, POSITION_ACTIONS
from utils.helpers import get_logo_img, get_team_color
from data.sql.liga_spillere import hent_match_og_haendelsesdata

# --- KONSTANTER ---
DB = "KLUB_HVIDOVREIF.AXIS"
SEASONNAME = "2026/2027"
LIGA_IDS = "('2mb332vncy4450vu14paj8844', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '335', '328', '329', '43319', '331')"

# --- HJÆLPEFUNKTIONER (Effektiviseret) ---
def count_kamp_qual(df_group, eid, qids):
    # Hurtigere filtrering uden tung apply på alt
    mask = (df_group['event_typeid'] == eid)
    if isinstance(qids, list):
        mask &= df_group['qualifiers'].str.contains('|'.join(map(str, qids)), na=False)
    else:
        mask &= df_group['qualifiers'].str.contains(str(qids), na=False)
    return mask.sum()

def _forbered_events(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=['visningsnavn']).copy()
    df['Pasninger_Total'] = (df['event_typeid'] == 1).astype(int)
    df['Pasninger_Succes'] = ((df['event_typeid'] == 1) & (df['outcome'] == 1)).astype(int)
    return df

@st.cache_data(ttl=600)
def hent_holdliste(_conn):
    df = _conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
    if df is None: return {}
    mapping = {str(info['opta_uuid']).lower().replace('t', ''): name for name, info in TEAMS.items() if 'opta_uuid' in info}
    return {name: r['contestanthome_optauuid'] for _, r in df.iterrows() if str(r['contestanthome_optauuid']).lower().replace('t', '') in mapping}

@st.cache_data(ttl=300)
def hent_data(_conn, valgt_uuid_hold):
    # Henter kun hvad der er nødvendigt for holdoversigt
    df_all_raw, df_expected, _ = hent_match_og_haendelsesdata(_conn, DB, valgt_uuid_hold, LIGA_IDS, {})
    return df_all_raw, df_expected

# --- HOVEDSIDE ---
def vis_side():
    conn = _get_snowflake_conn()
    if not conn: return
    
    team_map = hent_holdliste(conn)
    team_names = sorted(list(team_map.keys()))
    valgt_hold = st.selectbox("Vælg Hold", team_names, index=team_names.index("Hvidovre") if "Hvidovre" in team_names else 0)
    valgt_uuid_hold = team_map[valgt_hold]

    with st.spinner("Henter data..."):
        df_all, df_expected = hent_data(conn, valgt_uuid_hold)
    
    if df_all is None or df_all.empty:
        st.warning("Ingen data.")
        return

    # Forenklet statistik-aggregering
    df_all = _forbered_events(df_all[df_all['hold_optauuid'] == valgt_uuid_hold])
    
    stats = df_all.groupby('visningsnavn').agg({
        'match_optauuid': 'nunique',
        'event_typeid': 'count',
        'Pasninger_Total': 'sum',
        'Pasninger_Succes': 'sum'
    }).rename(columns={'match_optauuid': 'Kampe', 'event_typeid': 'Aktioner'})
    
    stats['Pasningsprocent'] = (stats['Pasninger_Succes'] / stats['Pasninger_Total'] * 100).fillna(0)
    
    # UI visning
    st.subheader(f"Statistik for {valgt_hold}")
    st.dataframe(stats.sort_values('Aktioner', ascending=False), use_container_width=True)

if __name__ == "__main__":
    vis_side()
