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

    sql = f"""
    WITH BaseEvents AS (
        SELECT 
            e.EVENT_OPTAUUID, e.MATCH_OPTAUUID, e.EVENT_EVENTID,
            e.EVENT_CONTESTANT_OPTAUUID AS TEAM_UUID,
            TRIM(e.PLAYER_OPTAUUID) AS PLAYER_UUID,
            e.PLAYER_NAME,
            e.EVENT_X, e.EVENT_Y,
            LEAD(TRIM(e.PLAYER_OPTAUUID), 1) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P1_UUID,
            LEAD(e.PLAYER_NAME, 1) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P1_NAME,
            LEAD(e.EVENT_CONTESTANT_OPTAUUID, 1) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P1_TEAM,
            LEAD(TRIM(e.PLAYER_OPTAUUID), 2) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P2_UUID,
            LEAD(e.PLAYER_NAME, 2) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P2_NAME,
            LEAD(e.EVENT_CONTESTANT_OPTAUUID, 2) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P2_TEAM
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
    SELECT b.*, q.TYPE_NAVN, q.END_X, q.END_Y, q.ER_CHANCE
    FROM BaseEvents b
    JOIN Quals q ON b.EVENT_OPTAUUID = q.EVENT_OPTAUUID
    WHERE b.TEAM_UUID = '{team_uuid}' AND q.TYPE_NAVN IS NOT NULL
    """

    df = conn.query(sql)
    if df is None or df.empty: return pd.DataFrame()

    try:
        df_lookup = pd.read_csv(PLAYER_FILE)
        df_lookup['PLAYER_OPTAUUID'] = df_lookup['PLAYER_OPTAUUID'].astype(str).str.strip()
        name_map = df_lookup.set_index('PLAYER_OPTAUUID')['NAVN'].to_dict()
    except:
        name_map = {}

    def format_name(uuid, db_name):
        if pd.isna(uuid) or uuid is None: return None
        u = str(uuid).strip()
        full_name = name_map.get(u)
        return full_name if full_name else f"{db_name} ({u})"

    df['TAGER'] = df.apply(lambda x: format_name(x['PLAYER_UUID'], x['PLAYER_NAME']), axis=1)

    def find_target(row):
        if row['P1_TEAM'] == row['TEAM_UUID'] and row['P1_UUID'] != row['PLAYER_UUID']:
            return format_name(row['P1_UUID'], row['P1_NAME'])
        if row['P2_TEAM'] == row['TEAM_UUID'] and row['P2_UUID'] != row['PLAYER_UUID']:
            return format_name(row['P2_UUID'], row['P2_NAME'])
        return None

    df['MODTAGER'] = df.apply(find_target, axis=1)
    df['END_X'] = pd.to_numeric(df['END_X'], errors='coerce')
    df['END_Y'] = pd.to_numeric(df['END_Y'], errors='coerce')
    return df

def vis_side():
    st.set_page_config(layout="wide")
    st.title("Standard-Analyse")
    
    # Globalt valg af hold - gælder for begge tabs
    t_sel = st.selectbox("Vælg Hold", get_team_options())
    df_raw = load_team_setpiece_data(t_sel)
    
    if df_raw.empty:
        st.warning(f"Ingen data fundet for {t_sel}")
        return

    tab1, tab2 = st.tabs(["Statistik", "Banevisning"])
    
    with tab1:
        # Specifikke valg under statistik tab
        c1, c2 = st.columns(2)
        with c1:
            type_sel = st.selectbox("Vælg Type", ["Alle", "Hjørnespark", "Indkast", "Frispark"])
        with c2:
            counts_tager = df_raw['TAGER'].value_counts()
            tager_options = ["Alle"] + [f"{name} ({counts_tager[name]})" for name in counts_tager.index]
            player_sel_raw = st.selectbox("Vælg Tager", tager_options)
            player_sel = player_sel_raw.split(" (")[0] if player_sel_raw != "Alle" else "Alle"

        df_filtered = df_raw.copy()
        if type_sel != "Alle": df_filtered = df_filtered[df_filtered['TYPE_NAVN'] == type_sel]
        if player_sel != "Alle": df_filtered = df_filtered[df_filtered['TAGER'] == player_sel]

        if df_filtered.empty:
            st.info("Ingen data for de valgte filtre.")
        else:
            def get_stats(group):
                m_counts = group['MODTAGER'].value_counts()
                top_modtager = f"{m_counts.idxmax()} ({m_counts.max()})" if not m_counts.empty else "Ingen"
                return pd.Series({
                    'Antal': len(group),
                    'Ramt / Duel': group['MODTAGER'].notna().sum(),
                    'Chancer': group['ER_CHANCE'].sum(),
                    'Primær Modtager': top_modtager
                })

            stats_df = df_filtered.groupby(['TAGER', 'TYPE_NAVN']).apply(get_stats, include_groups=False).reset_index()
            st.dataframe(stats_df.sort_values('Antal', ascending=False), use_container_width=True, hide_index=True)

    with tab2:
        # Banevisningen bruger hele datasættet for det valgte hold (medmindre man vil have filtrene herover også)
        pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(8, 10))
        t_color = TEAM_COLORS.get(t_sel, {}).get('primary', '#cc0000')
        
        # Her bruger vi df_filtered så banevisningen følger valgene i Statistik-tabben
        valid = df_filtered.dropna(subset=['END_X', 'END_Y'])
        if not valid.empty:
            pitch.arrows(valid.EVENT_X, valid.EVENT_Y, valid.END_X, valid.END_Y, color=t_color, ax=ax, alpha=0.3, width=2)
            pitch.scatter(valid.END_X, valid.END_Y, color=t_color, edgecolors='white', s=100, ax=ax, zorder=3)
        st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
