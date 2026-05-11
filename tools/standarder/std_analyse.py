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

@st.cache_data(ttl=3600)
def load_setpiece_data():
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    
    match_sql = f"SELECT DISTINCT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"
    
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
            WHERE q.QUALIFIER_QID IN (2, 5, 107, 124)
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
    for col in ['EVENT_X', 'EVENT_Y', 'EVENT_ENDX', 'EVENT_ENDY']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    type_map = {2: "Hjørnespark", 124: "Hjørnespark", 5: "Frispark", 107: "Indkast"}
    df['SET_PIECE_TYPE'] = df['QUALIFIER_QID'].map(type_map)
    return df

def to_metric(val, total_m):
    return val * (total_m / 100)

def vis_side():
    st.markdown("<style>header {visibility: hidden;}</style>", unsafe_allow_html=True)
    df_all = load_setpiece_data()
    if df_all.empty: return

    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['EVENT_CONTESTANT_OPTAUUID'].str.upper().map(uuid_to_name)
    teams = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])

    # --- FILTRE ---
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        t_sel = st.selectbox("Hold", teams, index=teams.index("Hvidovre") if "Hvidovre" in teams else 0)
    
    df_team = df_all[df_all['KLUB_NAVN'] == t_sel].copy()
    
    with c2:
        sp_type = st.selectbox("Type", ["Hjørnespark", "Indkast", "Frispark"])
    with c3:
        # Dynamisk spillervælger baseret på det valgte hold og type
        players = ["Alle spillere"] + sorted(df_team[df_team['SET_PIECE_TYPE'] == sp_type]['PLAYER_NAME'].unique().tolist())
        p_sel = st.selectbox("Spiller", players)
    with c4:
        vis_mode = st.selectbox("Visning", ["Zoner + Pile", "Kun Zoner", "Kun Pile"])

    # --- DATA FILTERING ---
    df_plot = df_team[df_team['SET_PIECE_TYPE'] == sp_type].copy()
    if p_sel != "Alle spillere":
        df_plot = df_plot[df_plot['PLAYER_NAME'] == p_sel]

    # Skalering
    for c in ['EVENT_X', 'EVENT_ENDX']: df_plot[c+'_M'] = df_plot[c].apply(lambda x: to_metric(x, 105))
    for c in ['EVENT_Y', 'EVENT_ENDY']: df_plot[c+'_M'] = df_plot[c].apply(lambda y: to_metric(y, 68))

    t_color = TEAM_COLORS.get(t_sel, {}).get('primary', HIF_RED)
    
    # --- PITCH ---
    col_p, col_s = st.columns([2, 1])
    
    with col_p:
        pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 12))
        ax.set_ylim(50, 105)

        if not df_plot.dropna(subset=['EVENT_ENDX_M', 'EVENT_ENDY_M']).empty:
            # 1. ZONER (Hexbin) - viser hvor boldene lander
            if "Zoner" in vis_mode:
                pitch.hexbin(df_plot.EVENT_ENDX_M, df_plot.EVENT_ENDY_M, ax=ax, 
                             gridsize=(12, 12), cmap='Reds', alpha=0.6, edgecolors='#f0f0f0')

            # 2. PILE - viser bevægelsen
            if "Pile" in vis_mode:
                # Vi gør pilene tyndere hvis der er mange, for at undgå rod
                alpha_val = 0.4 if len(df_plot) < 100 else 0.15
                pitch.arrows(df_plot.EVENT_X_M, df_plot.EVENT_Y_M, df_plot.EVENT_ENDX_M, df_plot.EVENT_ENDY_M, 
                             width=1, headwidth=3, color=t_color, ax=ax, alpha=alpha_val)
        
        st.pyplot(fig)

    with col_s:
        st.subheader("Statistik")
        st.metric("Antal aktioner", len(df_plot))
        st.write("**Top eksekutører:**")
        st.dataframe(df_plot['PLAYER_NAME'].value_counts(), use_container_width=True)

if __name__ == "__main__":
    vis_side()
