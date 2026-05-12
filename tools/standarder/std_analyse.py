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
    
    # Vi bruger nu det korrekte kolonnenavn: EVENT_OUTCOME
    sql = f"""
        WITH EVENT_BASE AS (
            SELECT 
                e.EVENT_OPTAUUID, 
                e.EVENT_X, 
                e.EVENT_Y, 
                e.EVENT_OUTCOME, -- Retttet her
                e.EVENT_CONTESTANT_OPTAUUID, 
                e.PLAYER_OPTAUUID, 
                e.MATCH_OPTAUUID,
                MAX(CASE WHEN q.QUALIFIER_QID = 107 THEN 1 ELSE 0 END) as IS_THROW_IN,
                MAX(CASE WHEN q.QUALIFIER_QID IN (2, 6) THEN 1 ELSE 0 END) as IS_CORNER,
                MAX(CASE WHEN q.QUALIFIER_QID IN (5, 26) THEN 1 ELSE 0 END) as IS_FREEKICK,
                MAX(CASE WHEN q.QUALIFIER_QID = 140 THEN TRY_TO_DOUBLE(q.QUALIFIER_VALUE) ELSE NULL END) as ENDX,
                MAX(CASE WHEN q.QUALIFIER_QID = 141 THEN TRY_TO_DOUBLE(q.QUALIFIER_VALUE) ELSE NULL END) as ENDY,
                MAX(CASE WHEN q.QUALIFIER_QID = 210 THEN 1 ELSE 0 END) as IS_ASSIST
            FROM {DB}.OPTA_EVENTS e
            LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE e.MATCH_OPTAUUID IN ({match_sql})
            GROUP BY 1, 2, 3, 4, 5, 6, 7
        )
        SELECT 
            b.*,
            TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME
        FROM EVENT_BASE b
        LEFT JOIN {DB}.OPTA_PLAYERS p ON b.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
        WHERE IS_THROW_IN = 1 OR IS_CORNER = 1 OR IS_FREEKICK = 1
    """
    df = conn.query(sql)
    df.columns = [c.upper() for c in df.columns]
    
    # Mappe typer
    def get_type(row):
        if row['IS_THROW_IN'] == 1: return "Indkast"
        if row['IS_CORNER'] == 1: return "Hjørnespark"
        return "Frispark"
    
    df['SET_PIECE_TYPE'] = df.apply(get_type, axis=1)
    
    # Numeriske værdier
    for col in ['EVENT_X', 'EVENT_Y', 'ENDX', 'ENDY']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    return df

def to_metric(val, total_m): return val * (total_m / 100)

def vis_side():
    st.set_page_config(layout="wide")
    df_all = load_setpiece_data()
    
    if df_all.empty:
        st.warning("Ingen data fundet.")
        return

    # Holdvælger
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['EVENT_CONTESTANT_OPTAUUID'].str.upper().map(uuid_to_name)
    teams = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])
    t_sel = st.selectbox("Vælg Hold", teams, index=teams.index("Hvidovre") if "Hvidovre" in teams else 0)
    
    df_team = df_all[df_all['KLUB_NAVN'] == t_sel].copy()

    tab1, tab2 = st.tabs(["📊 OVERSIGT", "🎯 INDSIGT"])

    # --- TAB 1: OVERSIGT ---
    with tab1:
        st.subheader(f"Statistik for {t_sel}")
        
        # Beregn statistikker pr. spiller
        def get_stats(group):
            res = {'Navn': group['PLAYER_NAME'].iloc[0], 'Aktioner': len(group)}
            # Succes er enten Outcome=1 eller IS_ASSIST=1
            succes_mask = (group['OUTCOME'] == 1) | (group['IS_ASSIST'] == 1)
            res['Succesfulde'] = succes_mask.sum()
            res['Succes %'] = (res['Succesfulde'] / res['Aktioner'] * 100)
            
            for cat in ["Indkast", "Hjørnespark", "Frispark"]:
                c_df = group[group['SET_PIECE_TYPE'] == cat]
                c_count = len(c_df)
                c_succes = ((c_df['OUTCOME'] == 1) | (c_df['IS_ASSIST'] == 1)).sum()
                res[f"{cat} (Antal)"] = c_count
                res[f"{cat} (Succes)"] = c_succes
                res[f"{cat} (%)"] = (c_succes / c_count * 100) if c_count > 0 else 0
            return pd.Series(res)

        df_stats = df_team.groupby('PLAYER_NAME').apply(get_stats).sort_values("Aktioner", ascending=False)
        
        st.dataframe(
            df_stats,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Succes %": st.column_config.NumberColumn(format="%.1f%%"),
                "Indkast (%)": st.column_config.NumberColumn(format="%.1f%%"),
                "Hjørnespark (%)": st.column_config.NumberColumn(format="%.1f%%"),
                "Frispark (%)": st.column_config.NumberColumn(format="%.1f%%"),
            }
        )

    # --- TAB 2: INDSIGT (Visualisering) ---
    with tab2:
        c1, c2, c3 = st.columns(3)
        with c1:
            sp_type = st.selectbox("Type", ["Hjørnespark", "Indkast", "Frispark"])
        with c2:
            p_list = ["Alle"] + sorted(df_team[df_team['SET_PIECE_TYPE'] == sp_type]['PLAYER_NAME'].unique().tolist())
            p_sel = st.selectbox("Spiller", p_list)
        with c3:
            mode = st.selectbox("Visning", ["Zoner + Pile", "Kun Zoner", "Kun Pile"])

        df_plot = df_team[df_team['SET_PIECE_TYPE'] == sp_type].copy()
        if p_sel != "Alle":
            df_plot = df_plot[df_plot['PLAYER_NAME'] == p_sel]

        # Pitch tegning
        pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='#555555')
        fig, ax = pitch.draw(figsize=(8, 10))
        
        if not df_plot.empty:
            df_plot['X_M'] = df_plot['EVENT_X'].apply(lambda x: to_metric(x, 105))
            df_plot['Y_M'] = df_plot['EVENT_Y'].apply(lambda y: to_metric(y, 68))
            df_plot['EX_M'] = df_plot['ENDX'].apply(lambda x: to_metric(x, 105))
            df_plot['EY_M'] = df_plot['ENDY'].apply(lambda y: to_metric(y, 68))

            if "Zoner" in mode:
                pitch.hexbin(df_plot.EX_M, df_plot.EY_M, ax=ax, gridsize=(10, 10), cmap='YlOrRd', alpha=0.5)
            if "Pile" in mode:
                t_color = TEAM_COLORS.get(t_sel, {}).get('primary', '#ff0000')
                pitch.arrows(df_plot.X_M, df_plot.Y_M, df_plot.EX_M, df_plot.EY_M, color=t_color, ax=ax, width=1.5, headwidth=3, alpha=0.4)
        
        st.pyplot(fig)

if __name__ == "__main__": vis_side()
