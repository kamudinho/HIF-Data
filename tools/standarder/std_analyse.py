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
    return sorted([k for k in TEAMS.keys()])

@st.cache_data(ttl=3600)
def load_team_setpiece_data(team_name):
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()

    team_uuid = TEAMS.get(team_name, {}).get('opta_uuid')
    if not team_uuid: return pd.DataFrame()

    # SQL OPDATERING: Vi henter nu de næste TO spillere/hold
    sql = f"""
    WITH BaseEvents AS (
        SELECT 
            e.EVENT_OPTAUUID, e.MATCH_OPTAUUID, e.EVENT_EVENTID,
            e.EVENT_CONTESTANT_OPTAUUID AS TEAM_UUID,
            TRIM(e.PLAYER_OPTAUUID) AS PLAYER_UUID,
            e.PLAYER_NAME,
            e.EVENT_X, e.EVENT_Y,
            -- Næste hændelse
            LEAD(TRIM(e.PLAYER_OPTAUUID), 1) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS NEXT_PLAYER_1,
            LEAD(e.PLAYER_NAME, 1) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS NEXT_NAME_1,
            LEAD(e.EVENT_CONTESTANT_OPTAUUID, 1) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS NEXT_TEAM_1,
            -- Næste-næste hændelse (for at fange dueller/støj)
            LEAD(TRIM(e.PLAYER_OPTAUUID), 2) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS NEXT_PLAYER_2,
            LEAD(e.PLAYER_NAME, 2) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS NEXT_NAME_2,
            LEAD(e.EVENT_CONTESTANT_OPTAUUID, 2) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS NEXT_TEAM_2
        FROM {DB}.OPTA_EVENTS e
        WHERE e.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
    ),
    Quals AS (
        SELECT 
            EVENT_OPTAUUID,
            MAX(CASE WHEN QUALIFIER_QID = 107 THEN 'Indkast'
                     WHEN QUALIFIER_QID = 6 THEN 'Hjørnespark'
                     WHEN QUALIFIER_QID = 5 THEN 'Frispark' END) AS TYPE_NAVN,
            MAX(CASE WHEN QUALIFIER_QID = 140 THEN QUALIFIER_VALUE END) AS END_X,
            MAX(CASE WHEN QUALIFIER_QID = 141 THEN QUALIFIER_VALUE END) AS END_Y,
            MAX(CASE WHEN QUALIFIER_QID IN (214, 154, 111) THEN 1 ELSE 0 END) AS ER_CHANCE
        FROM {DB}.OPTA_QUALIFIERS
        WHERE QUALIFIER_QID IN (5, 6, 107, 140, 141, 214, 154, 111)
        GROUP BY EVENT_OPTAUUID
    )
    SELECT 
        b.*, q.TYPE_NAVN, q.END_X, q.END_Y, q.ER_CHANCE
    FROM BaseEvents b
    JOIN Quals q ON b.EVENT_OPTAUUID = q.EVENT_OPTAUUID
    WHERE b.TEAM_UUID = '{team_uuid}'
      AND q.TYPE_NAVN IS NOT NULL
    """

    df = conn.query(sql)
    if df is None or df.empty: return pd.DataFrame()

    # --- NAVNE MAPPING ---
    try:
        df_lookup = pd.read_csv(PLAYER_FILE)
        name_map = df_lookup.set_index('PLAYER_OPTAUUID')['NAVN'].to_dict()
    except:
        name_map = {}

    def format_name(uuid, db_name):
        if pd.isna(uuid) or uuid is None: return None
        uuid_str = str(uuid).strip()
        full_name = name_map.get(uuid_str)
        if full_name: return full_name
        return f"{db_name if db_name else 'Ukendt'} ({uuid_str})"

    df['TAGER'] = df.apply(lambda x: format_name(x['PLAYER_UUID'], x['PLAYER_NAME']), axis=1)
    
    # --- NY MODTAGER LOGIK (Kig på to trin) ---
    def find_receiver(row):
        # Tjek trin 1: Er det en medspiller (og ikke tageren selv)?
        if row['NEXT_TEAM_1'] == row['TEAM_UUID'] and row['NEXT_PLAYER_1'] != row['PLAYER_UUID']:
            return format_name(row['NEXT_PLAYER_1'], row['NEXT_NAME_1'])
        
        # Tjek trin 2: Hvis trin 1 var støj/modstander-snit, er trin 2 så en medspiller?
        if row['NEXT_TEAM_2'] == row['TEAM_UUID'] and row['NEXT_PLAYER_2'] != row['PLAYER_UUID']:
            return format_name(row['NEXT_PLAYER_2'], row['NEXT_NAME_2'])
        
        return None

    df['MODTAGER'] = df.apply(find_receiver, axis=1)
    df['END_X'] = pd.to_numeric(df['END_X'], errors='coerce')
    df['END_Y'] = pd.to_numeric(df['END_Y'], errors='coerce')

    return df

def vis_side():
    st.set_page_config(layout="wide")
    st.title("🎯 Standard-Analyse")
    
    t_sel = st.selectbox("Vælg Hold", get_team_options())
    df_raw = load_team_setpiece_data(t_sel)
    
    if df_raw.empty:
        st.warning(f"Ingen data fundet for {t_sel}")
        return

    counts_tager = df_raw['TAGER'].value_counts()
    player_options = ["Alle"] + [f"{name} ({counts_tager[name]})" for name in counts_tager.index]
    
    c1, c2 = st.columns(2)
    with c1: 
        type_sel = st.selectbox("Type", ["Alle", "Hjørnespark", "Indkast", "Frispark"])
    with c2: 
        player_sel_raw = st.selectbox("Spiller (Tager)", player_options)
        player_sel = player_sel_raw.split(" (")[0] if player_sel_raw != "Alle" else "Alle"

    df_filtered = df_raw.copy()
    if type_sel != "Alle": df_filtered = df_filtered[df_filtered['TYPE_NAVN'] == type_sel]
    if player_sel != "Alle": df_filtered = df_filtered[df_filtered['TAGER'] == player_sel]

    tab1, tab2 = st.tabs(["📊 Statistik", "🏟️ Banevisning"])
    
    with tab1:
        if df_filtered.empty:
            st.info("Ingen data.")
        else:
            def get_stats(group):
                m_counts = group['MODTAGER'].value_counts()
                if not m_counts.empty:
                    top_m = m_counts.idxmax()
                    top_a = m_counts.max()
                    primær = f"{top_m} ({top_a})"
                else:
                    primær = "Ingen"

                return pd.Series({
                    'Antal': len(group),
                    'Ramt medspiller': group['MODTAGER'].notna().sum(),
                    'Chancer skabt': group['ER_CHANCE'].sum(),
                    'Primær Modtager': primær
                })

            stats_df = df_filtered.groupby(['TAGER', 'TYPE_NAVN']).apply(get_stats, include_groups=False).reset_index()
            st.dataframe(stats_df.sort_values('Antal', ascending=False), use_container_width=True, hide_index=True)

    with tab2:
        pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(8, 10))
        t_color = TEAM_COLORS.get(t_sel, {}).get('primary', '#cc0000')
        valid = df_filtered.dropna(subset=['END_X', 'END_Y'])
        if not valid.empty:
            pitch.arrows(valid.EVENT_X, valid.EVENT_Y, valid.END_X, valid.END_Y, color=t_color, ax=ax, alpha=0.3, width=2)
            pitch.scatter(valid.END_X, valid.END_Y, color=t_color, edgecolors='white', s=100, ax=ax, zorder=3)
        st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
