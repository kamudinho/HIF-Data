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

    # 1. Hent ALLE events for at finde den korrekte næste spiller
    sql_events = f"""
    SELECT 
        MATCH_OPTAUUID, EVENT_EVENTID, 
        EVENT_CONTESTANT_OPTAUUID AS TEAM_UUID,
        TRIM(PLAYER_OPTAUUID) AS PLAYER_UUID
    FROM {DB}.OPTA_EVENTS
    WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
    ORDER BY MATCH_OPTAUUID, EVENT_EVENTID
    """
    
    # 2. Hent Qualifiers for standarder
    sql_quals = f"""
    SELECT 
        q.EVENT_OPTAUUID, e.MATCH_OPTAUUID, e.EVENT_EVENTID,
        q.QUALIFIER_QID, q.QUALIFIER_VALUE,
        e.EVENT_X AS START_X, e.EVENT_Y AS START_Y
    FROM {DB}.OPTA_QUALIFIERS q
    JOIN {DB}.OPTA_EVENTS e ON q.EVENT_OPTAUUID = e.EVENT_OPTAUUID
    WHERE e.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
      AND q.QUALIFIER_QID IN (5, 6, 107, 140, 141, 214, 154, 111)
    """

    df_all_events = conn.query(sql_events)
    df_quals = conn.query(sql_quals)
    
    if df_all_events is None or df_quals is None: return pd.DataFrame()

    # Find næste spiller i sekvensen
    df_all_events = df_all_events.sort_values(['MATCH_OPTAUUID', 'EVENT_EVENTID'])
    df_all_events['NEXT_PLAYER'] = df_all_events.groupby('MATCH_OPTAUUID')['PLAYER_UUID'].shift(-1)
    df_all_events['NEXT_TEAM'] = df_all_events.groupby('MATCH_OPTAUUID')['TEAM_UUID'].shift(-1)

    # Pivot Qualifiers (Sikrer at QIDs behandles som tekst for at undgå 'str' vs 'int' fejl)
    df_quals['QUALIFIER_QID'] = df_quals['QUALIFIER_QID'].astype(str)
    df_q = df_quals.pivot_table(
        index=['EVENT_OPTAUUID', 'MATCH_OPTAUUID', 'EVENT_EVENTID', 'START_X', 'START_Y'],
        columns='QUALIFIER_QID', values='QUALIFIER_VALUE', aggfunc='first'
    ).reset_index()

    # Join modtager-info på
    df = df_q.merge(df_all_events, on=['MATCH_OPTAUUID', 'EVENT_EVENTID'], how='inner')

    # Omdøb og logik (Vi bruger nu tekst-nøgler her)
    df = df.rename(columns={'6':'Hjørne', '107':'Indkast', '5':'Frispark', '140':'END_X', '141':'END_Y'})
    
    df['TYPE_NAVN'] = np.select(
        [df.get('Hjørne').notna() if 'Hjørne' in df else False, 
         df.get('Indkast').notna() if 'Indkast' in df else False, 
         df.get('Frispark').notna() if 'Frispark' in df else False],
        ['Hjørnespark', 'Indkast', 'Frispark'], default=None
    )
    
    # Valider modtager
    df['MODTAGER_UUID'] = np.where(
        (df['NEXT_PLAYER'] != df['PLAYER_UUID']) & (df['NEXT_TEAM'] == df['TEAM_UUID']),
        df['NEXT_PLAYER'], None
    )

    # Chance-logik (Her opstod fejlen typisk - vi bruger nu strenge)
    chance_ids = ['214', '154', '111']
    df['ER_CHANCE'] = df[df.columns[df.columns.isin(chance_ids)]].notna().any(axis=1).astype(int)

    # Map navne
    try:
        df_lookup = pd.read_csv(PLAYER_FILE)
        df_lookup['PLAYER_OPTAUUID'] = df_lookup['PLAYER_OPTAUUID'].astype(str).str.strip()
        name_map = df_lookup.set_index('PLAYER_OPTAUUID')['NAVN'].to_dict()
        df['TAGER'] = df['PLAYER_UUID'].map(name_map)
        df['MODTAGER'] = df['MODTAGER_UUID'].map(name_map)
    except:
        df['TAGER'] = df['PLAYER_UUID']
        df['MODTAGER'] = df['MODTAGER_UUID']

    return df[df['TYPE_NAVN'].notna()].dropna(subset=['TAGER'])

def vis_side():
    st.title("🎯 Standard-Analyse")
    df = load_setpiece_data()
    
    if df.empty:
        st.info("Ingen data indlæst.")
        return

    # Hold mapping
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
            pitch.arrows(valid.START_X, valid.START_Y, valid.END_X.astype(float), valid.END_Y.astype(float), color=t_color, ax=ax, alpha=0.3)
            pitch.scatter(valid.END_X.astype(float), valid.END_Y.astype(float), color=t_color, edgecolors='white', s=100, ax=ax)
        st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
