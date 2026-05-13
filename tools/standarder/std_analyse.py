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
PLAYER_FILE = 'data/players/1div_overskrivning.csv'

@st.cache_data(ttl=3600)
def load_setpiece_data():
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    
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
            MAX(CASE WHEN QUALIFIER_QID = 140 THEN QUALIFIER_VALUE END) AS ENDX,
            MAX(CASE WHEN QUALIFIER_QID = 141 THEN QUALIFIER_VALUE END) AS ENDY
        FROM {DB}.OPTA_QUALIFIERS
        WHERE QUALIFIER_QID IN (5, 6, 107, 140, 141)
        GROUP BY EVENT_OPTAUUID
    )
    SELECT b.*, q.TYPE_NAVN, q.ENDX, q.ENDY
    FROM BaseEvents b
    JOIN Quals q ON b.EVENT_OPTAUUID = q.EVENT_OPTAUUID
    WHERE q.TYPE_NAVN IS NOT NULL
    """
    try:
        df = conn.query(sql)
        if df is None or df.empty: return pd.DataFrame()
        df.columns = [c.upper() for c in df.columns]
        
        try:
            df_lookup = pd.read_csv(PLAYER_FILE)
            df_lookup['PLAYER_OPTAUUID'] = df_lookup['PLAYER_OPTAUUID'].astype(str).str.strip()
            name_map = df_lookup.set_index('PLAYER_OPTAUUID')['NAVN'].to_dict()
        except:
            name_map = {}

        df['TAGER_NAVN'] = df.apply(lambda x: name_map.get(str(x['PLAYER_UUID']).strip(), x['PLAYER_NAME']), axis=1)
        
        def find_target(row):
            if row['P1_TEAM'] == row['TEAM_UUID'] and row['P1_UUID'] != row['PLAYER_UUID']:
                return name_map.get(str(row['P1_UUID']).strip(), row['P1_NAME'])
            if row['P2_TEAM'] == row['TEAM_UUID'] and row['P2_UUID'] != row['PLAYER_UUID']:
                return name_map.get(str(row['P2_UUID']).strip(), row['P2_NAME'])
            return None

        df['MODTAGER'] = df.apply(find_target, axis=1)
        return df
    except:
        return pd.DataFrame()

def to_metric(val, total_m): 
    return val * (total_m / 100)

def vis_side():
    st.set_page_config(layout="wide", page_title="Standardsituationer")
    
    # Minimal CSS for et rent look
    st.markdown("""
        <style>
        header {visibility: hidden;}
        .block-container {padding-top: 2rem !important;}
        /* Fjerner label-pladsen over dropdown i top-højre */
        div[data-testid="stSelectbox"] label { display: none !important; }
        </style>
    """, unsafe_allow_html=True)
    
    df_all = load_setpiece_data()
    if df_all.empty:
        st.warning("Ingen data fundet.")
        return

    # Forbered klubnavne
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['TEAM_UUID'].str.upper().map(uuid_to_name)
    teams = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])

    # --- TOPBAR ---
    col_title, col_empty, col_select = st.columns([2, 1, 1])
    with col_title:
        st.subheader("Standardsituationer")
    with col_select:
        t_sel = st.selectbox("hold_valg", teams, index=teams.index("Hvidovre") if "Hvidovre" in teams else 0)

    df_team_selected = df_all[df_all['KLUB_NAVN'] == t_sel].copy()

    # Tabs Definition
    tab1, tab2, tab3, tab4 = st.tabs(["Holdoversigt", "Spilleroversigt", "Analyse", "Zoneoversigt"])

    # --- TAB 1: Holdoversigt (Uafhængig) ---
    with tab1:
        hold_stats = df_all.groupby(['KLUB_NAVN', 'TYPE_NAVN']).size().unstack(fill_value=0).reset_index()
        st.dataframe(hold_stats, use_container_width=True, hide_index=True)

    # --- TAB 2: Spilleroversigt (Afhængig) ---
    with tab2:
        if not df_team_selected.empty:
            spiller_stats = df_team_selected.groupby(['TAGER_NAVN', 'TYPE_NAVN']).size().unstack(fill_value=0).reset_index()
            st.dataframe(spiller_stats, use_container_width=True, hide_index=True)

    # --- TAB 3: Analyse (Afhængig) ---
    with tab3:
        c1, c2, c3 = st.columns(3)
        with c1: sp_type = st.selectbox("Type", ["Hjørnespark", "Indkast", "Frispark"], key="sb_type_ana")
        with c2:
            p_list = ["Alle spillere"] + sorted(df_team_selected[df_team_selected['TYPE_NAVN'] == sp_type]['TAGER_NAVN'].unique().tolist())
            p_sel = st.selectbox("Spiller", p_list, key="sb_player_ana")
        with c3: vis_mode = st.selectbox("Visning", ["Zoner + Pile", "Kun Zoner", "Kun Pile"], key="sb_mode_ana")

        mask = (df_team_selected['TYPE_NAVN'] == sp_type)
        if p_sel != "Alle spillere": mask &= (df_team_selected['TAGER_NAVN'] == p_sel)
        df_plot = df_team_selected[mask].copy()

        # Konvertering til tal og metrikker
        for c in ['EVENT_X', 'EVENT_Y', 'ENDX', 'ENDY']: 
            df_plot[c] = pd.to_numeric(df_plot[c], errors='coerce')
        
        df_plot['X_M'] = df_plot['EVENT_X'].apply(lambda x: to_metric(x, 105))
        df_plot['Y_M'] = df_plot['EVENT_Y'].apply(lambda y: to_metric(y, 68))
        df_plot['ENDX_M'] = df_plot['ENDX'].apply(lambda x: to_metric(x, 105))
        df_plot['ENDY_M'] = df_plot['ENDY'].apply(lambda y: to_metric(y, 68))

        col_p, col_s = st.columns([2, 1])
        with col_p:
            pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(10, 12))
            ax.set_ylim(50, 105)
            if not df_plot.dropna(subset=['ENDX_M', 'ENDY_M']).empty:
                if "Zoner" in vis_mode:
                    pitch.hexbin(df_plot.ENDX_M, df_plot.ENDY_M, ax=ax, gridsize=(12, 12), cmap='Reds', alpha=0.6)
                if "Pile" in vis_mode:
                    pitch.arrows(df_plot.X_M, df_plot.Y_M, df_plot.ENDX_M, df_plot.ENDY_M, 
                                 color=TEAM_COLORS.get(t_sel, {}).get('primary', HIF_RED), ax=ax, alpha=0.3)
            st.pyplot(fig)
        with col_s:
            st.metric("Aktioner", len(df_plot))
            st.write("**Top modtagere**")
            mod_counts = df_plot['MODTAGER'].value_counts().reset_index()
            mod_counts.columns = ['Spiller', 'Antal']
            st.dataframe(mod_counts, use_container_width=True, hide_index=True)

    # --- TAB 4: Zoneoversigt (Afhængig) ---
    with tab4:
        def get_zone(y):
            if pd.isna(y): return "Ukendt"
            y_val = float(y)
            if y_val < 33: return "Venstre"
            if y_val > 66: return "Højre"
            return "Center"
        
        df_team_selected['ZONE'] = df_team_selected['ENDY'].apply(get_zone)
        zone_stats = df_team_selected.groupby(['ZONE', 'TYPE_NAVN']).size().unstack(fill_value=0).reset_index()
        st.dataframe(zone_stats, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    vis_side()
