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
PLAYER_FILE = 'data/players/1div_overskrivning.csv'

@st.cache_data(ttl=3600)
def load_setpiece_data():
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()

    # 1. Hent ALLE events (Basis for tælling og modtager-logik)
    # Vi henter kun de kolonner, vi så i dit udtræk
    sql_events = f"""
    SELECT 
        EVENT_OPTAUUID, MATCH_OPTAUUID, EVENT_EVENTID, EVENT_TIMESTAMP,
        EVENT_CONTESTANT_OPTAUUID AS TEAM_UUID,
        TRIM(PLAYER_OPTAUUID) AS PLAYER_UUID,
        EVENT_TYPEID, EVENT_X, EVENT_Y
    FROM {DB}.OPTA_EVENTS
    WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
    ORDER BY MATCH_OPTAUUID, EVENT_EVENTID
    """
    
    # 2. Hent Qualifiers (Detaljer om sparket)
    sql_quals = f"""
    SELECT 
        EVENT_OPTAUUID, QUALIFIER_QID, QUALIFIER_VALUE
    FROM {DB}.OPTA_QUALIFIERS
    WHERE QUALIFIER_QID IN (5, 6, 107, 140, 141, 214, 154, 111)
    """

    df_e = conn.query(sql_events)
    df_q_raw = conn.query(sql_quals)
    
    if df_e is None or df_q_raw is None: return pd.DataFrame()

    # --- BEHANDLING I PYTHON (Hurtigt og præcist) ---

    # A. Pivot Qualifiers så vi får 1 række pr. event
    df_q_raw['QUALIFIER_QID'] = df_q_raw['QUALIFIER_QID'].astype(str)
    df_q = df_q_raw.pivot_table(
        index='EVENT_OPTAUUID', 
        columns='QUALIFIER_QID', 
        values='QUALIFIER_VALUE', 
        aggfunc='first'
    ).reset_index()

    # B. Merge Qualifiers på Events
    df = df_e.merge(df_q, on='EVENT_OPTAUUID', how='left')

    # C. Definer Standard-type (Fixer tælle-fejlen fra tidligere)
    conditions = [
        df.get('6').notna(),   # Corner
        df.get('107').notna(), # Throw-in
        df.get('5').notna()    # Free kick
    ]
    choices = ['Hjørnespark', 'Indkast', 'Frispark']
    df['TYPE_NAVN'] = np.select(conditions, choices, default=None)

    # Filtrer med det samme så vi kun arbejder med standarder
    df_standards = df[df['TYPE_NAVN'].notna()].copy()

    # D. Find MODTAGER (Kig på næste event i den fulde df_e tidslinje)
    df_e = df_e.sort_values(['MATCH_OPTAUUID', 'EVENT_EVENTID'])
    df_e['NEXT_PLAYER'] = df_e.groupby('MATCH_OPTAUUID')['PLAYER_UUID'].shift(-1)
    df_e['NEXT_TEAM'] = df_e.groupby('MATCH_OPTAUUID')['TEAM_UUID'].shift(-1)
    
    # Map modtager-info tilbage på vores standards
    receiver_info = df_e[['EVENT_OPTAUUID', 'NEXT_PLAYER', 'NEXT_TEAM']]
    df_standards = df_standards.merge(receiver_info, on='EVENT_OPTAUUID', how='left')

    # Valider: Modtager skal være en anden spiller på samme hold
    df_standards['MODTAGER_UUID'] = np.where(
        (df_standards['NEXT_PLAYER'] != df_standards['PLAYER_UUID']) & 
        (df_standards['NEXT_TEAM'] == df_standards['TEAM_UUID']),
        df_standards['NEXT_PLAYER'], None
    )

    # E. Navne-mapping
    try:
        df_lookup = pd.read_csv(PLAYER_FILE)
        df_lookup['PLAYER_OPTAUUID'] = df_lookup['PLAYER_OPTAUUID'].astype(str).str.strip()
        name_map = df_lookup.set_index('PLAYER_OPTAUUID')['NAVN'].to_dict()
        df_standards['TAGER'] = df_standards['PLAYER_UUID'].map(name_map)
        df_standards['MODTAGER'] = df_standards['MODTAGER_UUID'].map(name_map)
    except:
        df_standards['TAGER'] = df_standards['PLAYER_UUID']
        df_standards['MODTAGER'] = df_standards['MODTAGER_UUID']

    # Konverter slut-koordinater til tal
    df_standards['END_X'] = pd.to_numeric(df_standards.get('140'), errors='coerce')
    df_standards['END_Y'] = pd.to_numeric(df_standards.get('141'), errors='coerce')
    
    # Chance-logik (QIDs for skud/chancer)
    chance_ids = ['214', '154', '111']
    df_standards['ER_CHANCE'] = df_standards[df_standards.columns[df_standards.columns.isin(chance_ids)]].notna().any(axis=1).astype(int)

    return df_standards.dropna(subset=['TAGER'])

# --- UI VISNING (vis_side() er uændret, da dataformatet nu er korrekt) ---
def vis_side():
    st.title("🎯 Standard-Analyse")
    df = load_setpiece_data()
    
    if df.empty:
        st.warning("Ingen data fundet.")
        return

    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df['KLUB'] = df['TEAM_UUID'].str.upper().map(uuid_to_name)
    
    c1, c2, c3 = st.columns(3)
    with c1: t_sel = st.selectbox("Hold", sorted(df['KLUB'].dropna().unique()))
    with c2: type_sel = st.selectbox("Type", ["Alle", "Hjørnespark", "Indkast", "Frispark"])
    with c3: player_sel = st.selectbox("Spiller", ["Alle"] + sorted(df[df['KLUB'] == t_sel]['TAGER'].unique()))

    mask = (df['KLUB'] == t_sel)
    if type_sel != "Alle": mask &= (df['TYPE_NAVN'] == type_sel)
    if player_sel != "Alle": mask &= (df['TAGER'] == player_sel)
    df_plot = df[mask].copy()

    tab1, tab2 = st.tabs(["Statistik", "Banevisning"])
    
    with tab1:
        stats = df_plot.groupby(['TAGER', 'TYPE_NAVN']).apply(lambda x: pd.Series({
            'Antal': len(x),
            'Ramt medspiller': x['MODTAGER'].notna().sum(),
            'Skud efter aktion': x['ER_CHANCE'].sum(),
            'Primær Modtager': x['MODTAGER'].value_counts().idxmax() if not x['MODTAGER'].dropna().empty else "Ingen"
        })).reset_index()
        st.dataframe(stats.sort_values('Antal', ascending=False), use_container_width=True, hide_index=True)

    with tab2:
        pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(8, 10))
        t_color = TEAM_COLORS.get(t_sel, {}).get('primary', HIF_RED)
        valid = df_plot.dropna(subset=['END_X', 'END_Y'])
        if not valid.empty:
            pitch.arrows(valid.EVENT_X, valid.EVENT_Y, valid.END_X, valid.END_Y, color=t_color, ax=ax, alpha=0.3)
            pitch.scatter(valid.END_X, valid.END_Y, color=t_color, edgecolors='white', s=100, ax=ax)
        st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
