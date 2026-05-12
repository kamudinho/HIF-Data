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
    # 1. Hent navne-mapping fra din overskrivningsfil
    try:
        df_lookup = pd.read_csv(PLAYER_FILE)
        df_lookup['PLAYER_OPTAUUID'] = df_lookup['PLAYER_OPTAUUID'].astype(str).str.strip()
        name_map = df_lookup.dropna(subset=['PLAYER_OPTAUUID']).set_index('PLAYER_OPTAUUID')['NAVN'].to_dict()
    except Exception as e:
        st.error(f"Fejl ved læsning af spiller-fil: {e}")
        return pd.DataFrame()

    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()

    # 2. SQL - Håndterer tager, modtager og type-oversættelse
    sql = f"""
    WITH OrderedEvents AS (
        SELECT
            e.EVENT_OPTAUUID,
            e.MATCH_OPTAUUID,
            e.EVENT_TIMESTAMP,
            e.EVENT_EVENTID,
            e.EVENT_CONTESTANT_OPTAUUID AS TEAM_UUID,
            TRIM(e.PLAYER_OPTAUUID) AS TAGER_UUID,
            e.EVENT_X AS START_X,
            e.EVENT_Y AS START_Y,
            e.EVENT_OUTCOME,
            -- Kigger fremad efter næste spiller og deres hold
            LEAD(TRIM(e.PLAYER_OPTAUUID)) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS MODTAGER_UUID,
            LEAD(e.EVENT_CONTESTANT_OPTAUUID) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS NEXT_TEAM_UUID
        FROM {DB}.OPTA_EVENTS e
        WHERE e.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
    ),
    QualifiersMapped AS (
        SELECT 
            EVENT_OPTAUUID,
            -- Oversættelse direkte i SQL
            MAX(CASE 
                WHEN QUALIFIER_QID = 6 THEN 'Hjørnespark'
                WHEN QUALIFIER_QID = 107 THEN 'Indkast'
                WHEN QUALIFIER_QID = 5 THEN 'Frispark'
            END) AS TYPE_NAVN,
            MAX(CASE WHEN QUALIFIER_QID = 140 THEN TRY_TO_DOUBLE(QUALIFIER_VALUE) END) AS END_X,
            MAX(CASE WHEN QUALIFIER_QID = 141 THEN TRY_TO_DOUBLE(QUALIFIER_VALUE) END) AS END_Y,
            MAX(CASE WHEN QUALIFIER_QID IN (214, 154, 111) THEN 1 ELSE 0 END) AS ER_CHANCE
        FROM {DB}.OPTA_QUALIFIERS
        GROUP BY EVENT_OPTAUUID
    )
    SELECT 
        r.TAGER_UUID,
        -- Kun medtag modtager hvis det er samme hold
        CASE WHEN r.TEAM_UUID = r.NEXT_TEAM_UUID THEN r.MODTAGER_UUID ELSE NULL END AS MODTAGER_UUID,
        r.START_X, r.START_Y, q.END_X, q.END_Y, q.TYPE_NAVN, r.EVENT_OUTCOME, q.ER_CHANCE, r.TEAM_UUID, r.EVENT_TIMESTAMP
    FROM OrderedEvents r
    INNER JOIN QualifiersMapped q ON r.EVENT_OPTAUUID = q.EVENT_OPTAUUID
    WHERE q.TYPE_NAVN IS NOT NULL
    """
    df = conn.query(sql)
    if df is None or df.empty: return pd.DataFrame()
    df.columns = [c.upper() for c in df.columns]

    # 3. Map UUIDs til navne fra din CSV
    df['TAGER'] = df['TAGER_UUID'].map(name_map)
    df['MODTAGER'] = df['MODTAGER_UUID'].map(name_map)
    
    # Filtrer rækker fra hvor tageren ikke findes i din fil (fjerner modstandere helt)
    return df.dropna(subset=['TAGER'])

def vis_side():
    st.title("Standard-Analyse")
    df = load_setpiece_data()
    
    if df.empty:
        st.warning("Ingen data fundet.")
        return

    # Hold-mapping
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df['KLUB'] = df['TEAM_UUID'].str.upper().map(uuid_to_name)
    
    # UI Filtre
    c1, c2, c3 = st.columns(3)
    with c1: t_sel = st.selectbox("Hold", sorted(df['KLUB'].dropna().unique()))
    with c2: type_sel = st.selectbox("Type", ["Alle", "Hjørnespark", "Indkast", "Frispark"])
    with c3: player_sel = st.selectbox("Spiller (Tager)", ["Alle"] + sorted(df[df['KLUB'] == t_sel]['TAGER'].unique()))

    # Anvend filtre
    mask = (df['KLUB'] == t_sel)
    if type_sel != "Alle": mask &= (df['TYPE_NAVN'] == type_sel)
    if player_sel != "Alle": mask &= (df['TAGER'] == player_sel)
    df_plot = df[mask].copy()

    tab_stats, tab_bane = st.tabs(["Statistik", "Banevisning"])

    with tab_stats:
        # Grupperet statistik
        stats = df_plot.groupby(['TAGER', 'TYPE_NAVN']).apply(lambda x: pd.Series({
            'Antal': len(x),
            'Succesfulde': x['MODTAGER'].notna().sum(),
            'Chancer': x['ER_CHANCE'].sum(),
            'Primær Modtager': x['MODTAGER'].value_counts().idxmax() if not x['MODTAGER'].dropna().empty else "Ingen"
        })).reset_index()

        st.data_editor(
            stats.sort_values('Antal', ascending=False),
            column_config={
                "TAGER": "Spiller",
                "TYPE_NAVN": "Type",
                "Succesfulde": "Ramt medspiller",
                "Chancer": "Skud efter aktion"
            },
            use_container_width=True, hide_index=True
        )

    with tab_bane:
        pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(8, 10))
        t_color = TEAM_COLORS.get(t_sel, {}).get('primary', HIF_RED)
        
        valid = df_plot.dropna(subset=['END_X', 'END_Y'])
        if not valid.empty:
            pitch.arrows(valid.START_X, valid.START_Y, valid.END_X, valid.END_Y, color=t_color, ax=ax, alpha=0.3)
            pitch.scatter(valid.END_X, valid.END_Y, color=t_color, edgecolors='white', s=100, ax=ax)
        st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
