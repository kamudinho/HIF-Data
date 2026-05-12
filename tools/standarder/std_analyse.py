import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
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
    
    # SQL opdateret med de korrekte kolonnenavne fra din oversigt
    sql = f"""
        WITH EVENT_BASE AS (
            SELECT 
                e.EVENT_OPTAUUID, 
                e.EVENT_X, 
                e.EVENT_Y, 
                e.EVENT_OUTCOME, -- Korrekt kolonnenavn fundet i din tabeloversigt
                e.EVENT_CONTESTANT_OPTAUUID, 
                e.PLAYER_OPTAUUID, 
                e.MATCH_OPTAUUID,
                MAX(CASE WHEN q.QUALIFIER_QID = 107 THEN 1 ELSE 0 END) as IS_THROW_IN,
                MAX(CASE WHEN q.QUALIFIER_QID IN (2, 6) THEN 1 ELSE 0 END) as IS_CORNER,
                MAX(CASE WHEN q.QUALIFIER_QID IN (5, 26) THEN 1 ELSE 0 END) as IS_FREEKICK,
                -- Slutkoordinater for pile
                MAX(CASE WHEN q.QUALIFIER_QID = 140 THEN TRY_TO_DOUBLE(q.QUALIFIER_VALUE) ELSE NULL END) as ENDX,
                MAX(CASE WHEN q.QUALIFIER_QID = 141 THEN TRY_TO_DOUBLE(q.QUALIFIER_VALUE) ELSE NULL END) as ENDY,
                -- Succes-indikatorer fra din liste (Assist, Cross, etc.)
                MAX(CASE WHEN q.QUALIFIER_QID IN (210, 2, 154, 163) THEN 1 ELSE 0 END) as IS_CHANCE_CREATED
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
    
    def get_type(row):
        if row['IS_THROW_IN'] == 1: return "Indkast"
        if row['IS_CORNER'] == 1: return "Hjørnespark"
        return "Frispark"
    
    df['SET_PIECE_TYPE'] = df.apply(get_type, axis=1)
    
    for col in ['EVENT_X', 'EVENT_Y', 'ENDX', 'ENDY']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    return df

def vis_side():
    st.title("Standardsituationer Analyse")
    df_all = load_setpiece_data()
    
    if df_all.empty:
        st.warning("Kunne ikke indlæse data.")
        return

    # Holdvælger
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['EVENT_CONTESTANT_OPTAUUID'].str.upper().map(uuid_to_name)
    teams = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])
    t_sel = st.selectbox("Vælg Hold", teams)
    
    df_team = df_all[df_all['KLUB_NAVN'] == t_sel].copy()

    tab1, tab2 = st.tabs(["📊 OVERSIGT", "🎯 INDSIGT"])

    with tab1:
        st.subheader(f"Statistik for {t_sel}")
        
        # Beregn succes baseret på din QID liste og EVENT_OUTCOME
        def calc_stats(group):
            # En aktion er succesfuld hvis den når en medspiller (1) eller skaber en chance
            succes = ((group['EVENT_OUTCOME'] == 1) | (group['IS_CHANCE_CREATED'] == 1)).sum()
            total = len(group)
            
            res = {
                'Navn': group['PLAYER_NAME'].iloc[0],
                'Aktioner': total,
                'Succesfulde': int(succes),
                'Succes %': (succes / total * 100) if total > 0 else 0
            }
            
            for t in ["Indkast", "Hjørnespark", "Frispark"]:
                sub = group[group['SET_PIECE_TYPE'] == t]
                s_total = len(sub)
                s_succes = ((sub['EVENT_OUTCOME'] == 1) | (sub['IS_CHANCE_CREATED'] == 1)).sum()
                res[f"{t} (Antal)"] = s_total
                res[f"{t} (Succes)"] = int(s_succes)
                res[f"{t} (%)"] = (s_succes / s_total * 100) if s_total > 0 else 0
            return pd.Series(res)

        df_stats = df_team.groupby('PLAYER_NAME').apply(calc_stats).sort_values("Aktioner", ascending=False)
        
        st.dataframe(df_stats, use_container_width=True, hide_index=True,
                     column_config={f"{c} (%)": st.column_config.NumberColumn(format="%.1f%%") for c in ["Succes", "Indkast", "Hjørnespark", "Frispark"]})

    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            sp_type = st.radio("Type", ["Indkast", "Hjørnespark", "Frispark"], horizontal=True)
        with col2:
            p_sel = st.selectbox("Spiller", ["Alle"] + sorted(df_team['PLAYER_NAME'].unique().tolist()))
            
        df_plot = df_team[df_team['SET_PIECE_TYPE'] == sp_type]
        if p_sel != "Alle":
            df_plot = df_plot[df_plot['PLAYER_NAME'] == p_sel]
            
        pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='#555555')
        fig, ax = pitch.draw(figsize=(8, 10))
        
        if not df_plot.empty:
            t_color = TEAM_COLORS.get(t_sel, {}).get('primary', '#cc0000')
            pitch.arrows(df_plot.EVENT_X * 1.05, df_plot.EVENT_Y * 0.68, 
                         df_plot.ENDX * 1.05, df_plot.ENDY * 0.68, 
                         color=t_color, ax=ax, width=2, headwidth=4, alpha=0.5)
            
        st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
