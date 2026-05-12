import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o"

@st.cache_data(ttl=3600)
def load_setpiece_data():
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    
    match_sql = f"SELECT DISTINCT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"
    
    # Vi bruger en Sub-query til Qualifiers for at undgå at duplikere rækkerne i EVENT_BASE
    sql = f"""
        WITH QUALS AS (
            SELECT 
                EVENT_OPTAUUID,
                MAX(CASE WHEN QUALIFIER_QID = 107 THEN 1 ELSE 0 END) as IS_THROW_IN,
                MAX(CASE WHEN QUALIFIER_QID IN (2, 6) THEN 1 ELSE 0 END) as IS_CORNER,
                MAX(CASE WHEN QUALIFIER_QID IN (5, 26) THEN 1 ELSE 0 END) as IS_FREEKICK,
                MAX(CASE WHEN QUALIFIER_QID = 140 THEN TRY_TO_DOUBLE(QUALIFIER_VALUE) ELSE NULL END) as ENDX,
                MAX(CASE WHEN QUALIFIER_QID = 141 THEN TRY_TO_DOUBLE(QUALIFIER_VALUE) ELSE NULL END) as ENDY,
                MAX(CASE WHEN QUALIFIER_QID IN (210, 154) THEN 1 ELSE 0 END) as IS_CHANCE_CREATED
            FROM {DB}.OPTA_QUALIFIERS
            WHERE MATCH_OPTAUUID IN ({match_sql})
            GROUP BY EVENT_OPTAUUID
        )
        SELECT 
            e.EVENT_OPTAUUID, e.EVENT_X, e.EVENT_Y, e.EVENT_OUTCOME, 
            e.EVENT_CONTESTANT_OPTAUUID, e.PLAYER_OPTAUUID, e.MATCH_OPTAUUID,
            q.IS_THROW_IN, q.IS_CORNER, q.IS_FREEKICK, q.ENDX, q.ENDY, q.IS_CHANCE_CREATED,
            TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME
        FROM {DB}.OPTA_EVENTS e
        INNER JOIN QUALS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
        LEFT JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
        WHERE (q.IS_THROW_IN = 1 OR q.IS_CORNER = 1 OR q.IS_FREEKICK = 1)
    """
    df = conn.query(sql)
    df.columns = [c.upper() for c in df.columns]
    
    def get_type(row):
        if row['IS_THROW_IN'] == 1: return "Indkast"
        if row['IS_CORNER'] == 1: return "Hjørnespark"
        return "Frispark"
    
    df['SET_PIECE_TYPE'] = df.apply(get_type, axis=1)
    return df

def vis_side():
    st.title("Standardsituationer - Valideret Data")
    df_all = load_setpiece_data()
    if df_all.empty: return

    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['EVENT_CONTESTANT_OPTAUUID'].str.upper().map(uuid_to_name)
    
    teams = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])
    t_sel = st.selectbox("Vælg Hold", teams, index=teams.index("Hvidovre") if "Hvidovre" in teams else 0)
    
    df_team = df_all[df_all['KLUB_NAVN'] == t_sel].copy()

    tab1, tab2 = st.tabs(["📊 OVERSIGT", "🎯 INDSIGT"])

    with tab1:
        # Nu tæller vi unikke events pr. spiller
        def calc_stats(group):
            total = len(group)
            sp_mask = group['SET_PIECE_TYPE'].isin(['Hjørnespark', 'Frispark'])
            is_success = np.where(sp_mask, (group['IS_CHANCE_CREATED'] == 1), (group['EVENT_OUTCOME'] == 1))
            succes_antal = is_success.sum()
            
            res = {'Navn': group['PLAYER_NAME'].iloc[0], 'Aktioner': total, 'Succes %': (succes_antal / total * 100) if total > 0 else 0}
            
            for t in ["Indkast", "Hjørnespark", "Frispark"]:
                sub = group[group['SET_PIECE_TYPE'] == t]
                s_total = len(sub)
                res[f"{t} (Antal)"] = s_total
                if s_total > 0:
                    s_mask = np.where(t in ["Hjørnespark", "Frispark"], (sub['IS_CHANCE_CREATED'] == 1), (sub['EVENT_OUTCOME'] == 1))
                    res[f"{t} (%)"] = (s_mask.sum() / s_total * 100)
                else:
                    res[f"{t} (%)"] = 0
            return pd.Series(res)

        df_stats = df_team.groupby('PLAYER_OPTAUUID').apply(calc_stats).sort_values("Aktioner", ascending=False)
        st.dataframe(df_stats, use_container_width=True, hide_index=True)

    with tab2:
        # Bane-visualisering (samme som før, nu med korrekt dataantal)
        sp_type = st.radio("Kategori", ["Hjørnespark", "Indkast", "Frispark"], horizontal=True)
        df_plot = df_team[df_team['SET_PIECE_TYPE'] == sp_type]
        
        pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='#555555')
        fig, ax = pitch.draw(figsize=(8, 10))
        if not df_plot.empty:
            pitch.arrows(df_plot.EVENT_X * 1.05, df_plot.EVENT_Y * 0.68, 
                         df_plot.ENDX * 1.05, df_plot.ENDY * 0.68, 
                         color=TEAM_COLORS.get(t_sel, {}).get('primary', '#cc0000'), ax=ax, width=2, alpha=0.3)
        st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
