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
PLAYER_FILE = 'data/players/spiller_overskrivning.csv'

@st.cache_data(ttl=3600)
def load_setpiece_data():
    # 1. Hent dine navne fra CSV med det samme
    try:
        df_lookup = pd.read_csv(PLAYER_FILE)
        # Vi sikrer os at UUIDs er strings og uden mellemrum
        df_lookup['PLAYER_OPTAUUID'] = df_lookup['PLAYER_OPTAUUID'].astype(str).str.strip()
        name_map = df_lookup.dropna(subset=['PLAYER_OPTAUUID']).set_index('PLAYER_OPTAUUID')['NAVN'].to_dict()
    except Exception as e:
        st.error(f"Fejl ved læsning af spiller-fil: {e}")
        return pd.DataFrame()

    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()

    # 2. SQL - Vi henter rå-data uden ACTIVE_STATUS filter
    sql = f"""
    WITH RAW_EVENTS AS (
        SELECT 
            e.EVENT_OPTAUUID, e.EVENT_X, e.EVENT_Y, e.EVENT_OUTCOME,
            e.EVENT_CONTESTANT_OPTAUUID as TEAM_UUID, 
            e.MATCH_OPTAUUID,
            TRIM(e.PLAYER_OPTAUUID) as PLAYER_OPTAUUID,
            -- Vi finder UUID på den næste spiller i sekvensen
            LEAD(TRIM(e.PLAYER_OPTAUUID)) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) as NEXT_PLAYER_UUID
        FROM {DB}.OPTA_EVENTS e
        WHERE e.MATCH_OPTAUUID IN (
            SELECT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO 
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        )
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

    # 3. Map navne og filtrer trup baseret på din CSV
    # Vi beholder kun spillere, der findes i din fil
    df = df[df['PLAYER_OPTAUUID'].isin(name_map.keys())].copy()
    df['PLAYER_NAME'] = df['PLAYER_OPTAUUID'].map(name_map)
    df['NEXT_PLAYER_NAME'] = df['NEXT_PLAYER_UUID'].map(name_map)

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
    st.title("Standard-Analyse")
    
    df_all = load_setpiece_data()
    if df_all.empty:
        st.warning("Ingen data fundet for de spillere, der er i din overskrivningsfil.")
        return

    # Hold-mapping
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['TEAM_UUID'].str.upper().map(uuid_to_name)
    teams_in_data = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])

    c1, c2, c3, c4 = st.columns(4)
    with c1: t_sel = st.selectbox("Hold", teams_in_data)
    with c2: sp_type = st.selectbox("Type", ["Hjørnespark", "Indkast", "Frispark"])
    with c3: side_filter = st.selectbox("Side i kampen", ["Begge", "Venstre", "Højre"])
    with c4: visning_mode = st.selectbox("Bane-mode", ["Normaliseret (Højre side)", "Faktisk position"])

    df_team = df_all[(df_all['KLUB_NAVN'] == t_sel) & (df_all['SET_PIECE_TYPE'] == sp_type)].copy()
    
    # Side-logik og normalisering (Præcis som din gamle kode)
    df_team['ACTUAL_SIDE'] = np.where(df_team['EVENT_Y'] < 50, "Venstre", "Højre")
    if side_filter != "Begge":
        df_team = df_team[df_team['ACTUAL_SIDE'] == side_filter]

    mask_flip = df_team['EVENT_X'] < 50
    for col in ['EVENT_X', 'EVENT_Y', 'EVENT_ENDX', 'EVENT_ENDY']:
        df_team.loc[mask_flip, col] = 100 - df_team.loc[mask_flip, col]
    
    if visning_mode == "Normaliseret (Højre side)":
        mask_mirror = df_team['EVENT_Y'] < 50
        df_team.loc[mask_mirror, 'EVENT_Y'] = 100 - df_team.loc[mask_mirror, 'EVENT_Y']
        df_team.loc[mask_mirror, 'EVENT_ENDY'] = 100 - df_team.loc[mask_mirror, 'EVENT_ENDY']

    df_team['X_M'], df_team['Y_M'] = to_metric(df_team['EVENT_X'], 105), to_metric(df_team['EVENT_Y'], 68)
    df_team['ENDX_M'], df_team['ENDY_M'] = to_metric(df_team['EVENT_ENDX'], 105), to_metric(df_team['EVENT_ENDY'], 68)

    # Ny Succes logik: Ramt en medspiller fra din liste (og ikke dig selv)
    df_team['REAL_SUCCESS'] = (df_team['NEXT_PLAYER_NAME'].notna()) & (df_team['NEXT_PLAYER_UUID'] != df_team['PLAYER_OPTAUUID'])

    tab_bane, tab_zone, tab_stats = st.tabs(["Banevisning", "Zoneoversigt", "Statistik"])

    with tab_bane:
        pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(8, 10))
        t_color = TEAM_COLORS.get(t_sel, {}).get('primary', HIF_RED)
        valid = df_team.dropna(subset=['ENDX_M', 'ENDY_M'])
        if not valid.empty:
            pitch.arrows(valid.X_M, valid.Y_M, valid.ENDX_M, valid.ENDY_M, color=t_color, ax=ax, alpha=0.4, width=2)
            pitch.scatter(valid.ENDX_M, valid.ENDY_M, s=80, edgecolors='white', c=t_color, ax=ax, zorder=3)
        st.pyplot(fig)

    with tab_zone:
        st.subheader("Landingszoner")
        pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='#555555')
        fig, ax = pitch.draw(figsize=(8, 10))
        if not valid.empty:
            pitch.kdeplot(valid.ENDX_M, valid.ENDY_M, ax=ax, cmap='Reds', fill=True, alpha=0.5, levels=10)
            pitch.scatter(valid.ENDX_M, valid.ENDY_M, s=20, color='black', ax=ax, alpha=0.3)
        st.pyplot(fig)

    with tab_stats:
        def get_top_receiver(row):
            # Tæl kun modtagere der er i din CSV (reelle succeser)
            receivers = row[row['REAL_SUCCESS']]['NEXT_PLAYER_NAME'].dropna()
            if not receivers.empty:
                counts = receivers.value_counts()
                return f"{counts.idxmax()} ({counts.max()})"
            return "Ingen medspiller ramt"

        stats_df = df_team.groupby('PLAYER_NAME').apply(lambda x: pd.Series({
            'Antal': len(x),
            'Succes': x['REAL_SUCCESS'].sum(),
            'Afslutninger': x['IS_CHANCE'].sum(),
            'Oftest_ramte': get_top_receiver(x)
        })).reset_index()
        
        stats_df['Succes %'] = (stats_df['Succes'] / stats_df['Antal'] * 100).round(1)
        stats_df['Effektivitet'] = stats_df['Afslutninger'] / stats_df['Antal']
        
        st.data_editor(
            stats_df.sort_values('Antal', ascending=False),
            column_config={
                "PLAYER_NAME": "Spiller",
                "Oftest_ramte": "Primær modtager (antal)",
                "Succes %": st.column_config.NumberColumn("Succes % (Ramt medspiller)", format="%.1f %%"),
                "Effektivitet": st.column_config.ProgressColumn("Effektivitet (Afslutninger)", min_value=0, max_value=1, format="%.2f")
            },
            hide_index=True, use_container_width=True
        )

if __name__ == "__main__":
    vis_side()
