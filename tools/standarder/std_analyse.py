import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

# --- KONFIGURATION ---
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
            SELECT e.EVENT_OPTAUUID, e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, e.OUTCOME,
                   e.EVENT_CONTESTANT_OPTAUUID, e.PLAYER_OPTAUUID, q.QUALIFIER_QID, e.MATCH_OPTAUUID
            FROM {DB}.OPTA_EVENTS e
            JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE q.QUALIFIER_QID IN (2, 5, 107, 124)
            AND e.MATCH_OPTAUUID IN ({match_sql})
        )
        SELECT 
            s.*, ex.ENDX, ey.ENDY,
            TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME
        FROM SET_PIECE_EVENTS s
        LEFT JOIN END_X ex ON s.EVENT_OPTAUUID = ex.EVENT_OPTAUUID
        LEFT JOIN END_Y ey ON s.EVENT_OPTAUUID = ey.EVENT_OPTAUUID
        LEFT JOIN {DB}.OPTA_PLAYERS p ON s.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
    """
    df = conn.query(sql)
    df.columns = [c.upper() for c in df.columns]
    for col in ['EVENT_X', 'EVENT_Y', 'ENDX', 'ENDY']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    type_map = {2: "Hjørnespark", 124: "Hjørnespark", 5: "Frispark", 107: "Indkast"}
    df['SET_PIECE_TYPE'] = df['QUALIFIER_QID'].map(type_map)
    return df

def to_metric(val, total_m): return val * (total_m / 100)

def vis_side():
    st.markdown("<style>header {visibility: hidden;} .stTabs [data-baseweb='tab-list'] {gap: 24px;} </style>", unsafe_allow_html=True)
    
    df_all = load_setpiece_data()
    if df_all.empty: return

    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['EVENT_CONTESTANT_OPTAUUID'].str.upper().map(uuid_to_name)
    teams = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])

    t_sel = st.selectbox("Vælg Hold", teams, index=teams.index("Hvidovre") if "Hvidovre" in teams else 0)
    df_team = df_all[df_all['KLUB_NAVN'] == t_sel].copy()

    tab1, tab2 = st.tabs(["📊 OVERSIGT", "🎯 INDSIGT"])

    # --- TAB 1: OVERSIGT ---
    with tab1:
        st.subheader(f"Statistik for {t_sel}")
        
        # Aggregering pr. spiller og type
        stats_data = []
        for player, p_df in df_team.groupby('PLAYER_NAME'):
            row = {"Navn": player}
            # Total
            row["Total"] = len(p_df)
            row["Total Succes %"] = (p_df['OUTCOME'].mean() * 100)
            
            # Kategorier
            for cat in ["Indkast", "Hjørnespark", "Frispark"]:
                c_df = p_df[p_df['SET_PIECE_TYPE'] == cat]
                count = len(c_df)
                row[f"{cat} (Antal)"] = count
                row[f"{cat} (%)"] = (c_df['OUTCOME'].mean() * 100) if count > 0 else 0
            
            stats_data.append(row)
        
        df_stats = pd.DataFrame(stats_data).sort_values("Total", ascending=False)
        
        # Formatering af tabellen
        st.dataframe(
            df_stats,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Total Succes %": st.column_config.NumberColumn(format="%.1f%%"),
                "Indkast (%)": st.column_config.NumberColumn(format="%.1f%%"),
                "Hjørnespark (%)": st.column_config.NumberColumn(format="%.1f%%"),
                "Frispark (%)": st.column_config.NumberColumn(format="%.1f%%"),
            }
        )

    # --- TAB 2: INDSIGT ---
    with tab2:
        c_i1, c_i2, c_i3 = st.columns(3)
        with c_i1:
            sp_type = st.selectbox("Vælg Type", ["Hjørnespark", "Indkast", "Frispark"])
        with c_i2:
            p_list = ["Alle spillere"] + sorted(df_team[df_team['SET_PIECE_TYPE'] == sp_type]['PLAYER_NAME'].unique().tolist())
            p_sel = st.selectbox("Vælg Spiller", p_list)
        with c_i3:
            vis_mode = st.selectbox("Visning", ["Zoner + Pile", "Kun Zoner", "Kun Pile"])

        df_plot = df_team[df_team['SET_PIECE_TYPE'] == sp_type].copy()
        if p_sel != "Alle spillere":
            df_plot = df_plot[df_plot['PLAYER_NAME'] == p_sel]

        # Skalering
        df_plot['X_M'] = df_plot['EVENT_X'].apply(lambda x: to_metric(x, 105))
        df_plot['Y_M'] = df_plot['EVENT_Y'].apply(lambda y: to_metric(y, 68))
        df_plot['ENDX_M'] = df_plot['ENDX'].apply(lambda x: to_metric(x, 105))
        df_plot['ENDY_M'] = df_plot['ENDY'].apply(lambda y: to_metric(y, 68))

        col_pitch, col_metrics = st.columns([2, 1])
        
        with col_pitch:
            pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(10, 12))
            ax.set_ylim(50, 105)

            if not df_plot.empty:
                if "Zoner" in vis_mode:
                    pitch.hexbin(df_plot.ENDX_M, df_plot.ENDY_M, ax=ax, gridsize=(12, 12), cmap='Reds', alpha=0.6)
                if "Pile" in vis_mode:
                    t_color = TEAM_COLORS.get(t_sel, {}).get('primary', '#cc0000')
                    pitch.arrows(df_plot.X_M, df_plot.Y_M, df_plot.ENDX_M, df_plot.ENDY_M, 
                                 width=1, color=t_color, ax=ax, alpha=0.3)
            st.pyplot(fig)

        with col_metrics:
            st.metric("Valgte aktioner", len(df_plot))
            st.metric("Succesrate", f"{(df_plot['OUTCOME'].mean()*100):.1f}%")

if __name__ == "__main__":
    vis_side()
