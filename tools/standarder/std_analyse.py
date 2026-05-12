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
    # 1. Hent navne-mapping fra din fil
    try:
        df_lookup = pd.read_csv(PLAYER_FILE)
        df_lookup['PLAYER_OPTAUUID'] = df_lookup['PLAYER_OPTAUUID'].astype(str).str.strip()
        name_map = df_lookup.dropna(subset=['PLAYER_OPTAUUID']).set_index('PLAYER_OPTAUUID')['NAVN'].to_dict()
    except Exception as e:
        st.error(f"Fejl ved læsning af spiller-fil: {e}")
        return pd.DataFrame()

    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()

    # 2. Din SQL-logik optimeret til Snowflake & Python
    sql = f"""
    WITH OrderedEvents AS (
        SELECT
            e.EVENT_OPTAUUID,
            e.MATCH_OPTAUUID,
            e.EVENT_TIMESTAMP,
            e.EVENT_EVENTID,
            TRIM(e.PLAYER_OPTAUUID) as PLAYER_OPTAUUID,
            e.EVENT_CONTESTANT_OPTAUUID as TEAM_UUID,
            e.EVENT_X, e.EVENT_Y, e.EVENT_OUTCOME,
            -- Find næste spiller og deres hold (for at tjekke succesfuld modtagelse)
            LEAD(TRIM(e.PLAYER_OPTAUUID)) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) as NEXT_PLAYER_UUID,
            LEAD(e.EVENT_CONTESTANT_OPTAUUID) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) as NEXT_TEAM_UUID,
            -- Hent slut-koordinater og typer fra Qualifiers
            MAX(CASE WHEN q.QUALIFIER_QID = 140 THEN TRY_TO_DOUBLE(q.QUALIFIER_VALUE) END) as END_X,
            MAX(CASE WHEN q.QUALIFIER_QID = 141 THEN TRY_TO_DOUBLE(q.QUALIFIER_VALUE) END) as END_Y,
            MAX(CASE WHEN q.QUALIFIER_QID = 6 THEN 'Hjørnespark'
                     WHEN q.QUALIFIER_QID = 107 THEN 'Indkast'
                     WHEN q.QUALIFIER_QID = 5 THEN 'Frispark'
                END) as EVENT_TYPE_NAVN,
            MAX(CASE WHEN q.QUALIFIER_QID IN (214, 154, 111) THEN 1 ELSE 0 END) as IS_CHANCE
        FROM {DB}.OPTA_EVENTS e
        LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
        WHERE e.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        GROUP BY 1,2,3,4,5,6,7,8,9
    )
    SELECT * FROM OrderedEvents
    WHERE EVENT_TYPE_NAVN IS NOT NULL
    """
    df = conn.query(sql)
    if df is None or df.empty: return pd.DataFrame()
    df.columns = [c.upper() for c in df.columns]

    # 3. Navne-mapping (Afsender og Modtager)
    df['TAGER'] = df['PLAYER_OPTAUUID'].map(name_map)
    # Vi tæller kun modtageren, hvis det er en medspiller (samme TEAM_UUID)
    df['MODTAGER'] = np.where(
        df['TEAM_UUID'] == df['NEXT_TEAM_UUID'], 
        df['NEXT_PLAYER_UUID'].map(name_map), 
        None
    )
    
    # Succes-logik (Modtager er en medspiller fra din navne-liste)
    df['SUCCESS'] = df['MODTAGER'].notna()
    
    return df

def vis_side():
    st.title("Standard-Analyse")
    df = load_setpiece_data()
    
    if df.empty:
        st.warning("Ingen data fundet.")
        return

    # Hold-mapping
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df['KLUB'] = df['TEAM_UUID'].str.upper().map(uuid_to_name)
    
    # Filtre
    c1, c2, c3 = st.columns(3)
    with c1: t_sel = st.selectbox("Hold", sorted(df['KLUB'].dropna().unique()))
    with c2: type_sel = st.selectbox("Type", ["Alle", "Hjørnespark", "Indkast", "Frispark"])
    with c3: player_sel = st.selectbox("Spiller (Tager)", ["Alle"] + sorted(df[df['KLUB'] == t_sel]['TAGER'].dropna().unique()))

    # Filtrering af data
    mask = (df['KLUB'] == t_sel)
    if type_sel != "Alle": mask &= (df['EVENT_TYPE_NAVN'] == type_sel)
    if player_sel != "Alle": mask &= (df['TAGER'] == player_sel)
    
    df_plot = df[mask].copy()

    # Tabs til visning
    tab_stats, tab_bane = st.tabs(["Statistik", "Banevisning"])

    with tab_stats:
        # Grupperet oversigt over "Tager" og hvem de finder
        stats = df_plot.groupby(['TAGER', 'EVENT_TYPE_NAVN']).apply(lambda x: pd.Series({
            'Antal': len(x),
            'Succes (Eget hold)': x['SUCCESS'].sum(),
            'Chancer skabt': x['IS_CHANCE'].sum(),
            'Oftest fundne modtager': x['MODTAGER'].value_counts().idxmax() if not x['MODTAGER'].dropna().empty else "Ingen"
        })).reset_index()

        st.dataframe(
            stats.sort_values('Antal', ascending=False),
            column_config={
                "TAGER": "Spiller",
                "EVENT_TYPE_NAVN": "Type",
                "Oftest fundne modtager": "Primær Modtager"
            },
            use_container_width=True,
            hide_index=True
        )

    with tab_bane:
        pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(8, 10))
        t_color = TEAM_COLORS.get(t_sel, {}).get('primary', HIF_RED)
        
        # Tegn pile fra start til slut
        valid_arrows = df_plot.dropna(subset=['END_X', 'END_Y'])
        if not valid_arrows.empty:
            pitch.arrows(valid_arrows.EVENT_X, valid_arrows.EVENT_Y, 
                         valid_arrows.END_X, valid_arrows.END_Y, 
                         color=t_color, ax=ax, alpha=0.3)
            pitch.scatter(valid_arrows.END_X, valid_arrows.END_Y, color=t_color, edgecolors='white', ax=ax)
        
        st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
