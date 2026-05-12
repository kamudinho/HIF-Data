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
def load_vasket_data():
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    
    # Denne SQL bruger COUNT(DISTINCT) logikken til at undgå duplikater
    # og henter kun de nødvendige kolonner til tabellen og plottet
    sql = f"""
    WITH EVENT_BASE AS (
        SELECT 
            e.EVENT_OPTAUUID,
            e.EVENT_X,
            e.EVENT_Y,
            e.EVENT_OUTCOME,
            e.EVENT_CONTESTANT_OPTAUUID,
            e.PLAYER_OPTAUUID,
            -- Vi bruger MAX(DISTINCT) for at se om en type findes uden at duplikere rækker
            MAX(CASE WHEN q.QUALIFIER_QID = 107 THEN 1 ELSE 0 END) as IS_THROW_IN,
            MAX(CASE WHEN q.QUALIFIER_QID = 6 THEN 1 ELSE 0 END) as IS_CORNER,
            MAX(CASE WHEN q.QUALIFIER_QID IN (5, 26) THEN 1 ELSE 0 END) as IS_FREEKICK,
            MAX(CASE WHEN q.QUALIFIER_QID = 210 THEN 1 ELSE 0 END) as IS_ASSIST,
            MAX(CASE WHEN q.QUALIFIER_QID = 140 THEN TRY_TO_DOUBLE(q.QUALIFIER_VALUE) ELSE NULL END) as ENDX,
            MAX(CASE WHEN q.QUALIFIER_QID = 141 THEN TRY_TO_DOUBLE(q.QUALIFIER_VALUE) ELSE NULL END) as ENDY
        FROM {DB}.OPTA_EVENTS e
        INNER JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
        WHERE e.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        AND e.EVENT_TYPEID IN (1, 15, 16)
        AND q.QUALIFIER_QID IN (6, 107, 5, 26, 210, 140, 141)
        GROUP BY 1, 2, 3, 4, 5, 6
    )
    SELECT 
        b.*,
        TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME
    FROM EVENT_BASE b
    LEFT JOIN {DB}.OPTA_PLAYERS p ON b.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
    """
    df = conn.query(sql)
    df.columns = [c.upper() for c in df.columns]
    
    def get_type(row):
        if row['IS_CORNER'] == 1: return "Hjørnespark"
        if row['IS_THROW_IN'] == 1: return "Indkast"
        return "Frispark"
    
    df['TYPE'] = df.apply(get_type, axis=1)
    return df

def vis_side():
    st.title("Standardsituationer - Hvidovre App")
    
    df_all = load_vasket_data()
    if df_all.empty:
        st.error("Kunne ikke hente data.")
        return

    # Holdmapping
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['HOLD'] = df_all['EVENT_CONTESTANT_OPTAUUID'].str.upper().map(uuid_to_name)
    
    teams = sorted([n for n in df_all['HOLD'].unique() if pd.notna(n)])
    t_sel = st.selectbox("Vælg Hold", teams, index=teams.index("Hvidovre") if "Hvidovre" in teams else 0)
    
    df_team = df_all[df_all['HOLD'] == t_sel].copy()

    tab1, tab2 = st.tabs(["📊 SPILLER STATISTIK", "🎯 BANEOVERSIGT"])

    with tab1:
        # Nu beregner vi tabellen baseret på de unikke rækker
        stats_list = []
        for player, p_df in df_team.groupby('PLAYER_NAME'):
            c_df = p_df[p_df['TYPE'] == "Hjørnespark"]
            t_df = p_df[p_df['TYPE'] == "Indkast"]
            f_df = p_df[p_df['TYPE'] == "Frispark"]
            
            stats_list.append({
                'Navn': player,
                'Total': len(p_df),
                'Hjørne': len(c_df),
                'Hjørne Succes %': (c_df['IS_ASSIST'].sum() / len(c_df) * 100) if len(c_df) > 0 else 0,
                'Indkast': len(t_df),
                'Indkast Succes %': (t_df[t_df['EVENT_OUTCOME'] == 1].shape[0] / len(t_df) * 100) if len(t_df) > 0 else 0,
                'Frispark': len(f_df),
                'Frispark Succes %': (f_df['IS_ASSIST'].sum() / len(f_df) * 100) if len(f_df) > 0 else 0
            })
            
        df_stats = pd.DataFrame(stats_list).sort_values("Total", ascending=False)
        st.dataframe(df_stats, use_container_width=True, hide_index=True,
                     column_config={f"{k} Succes %": st.column_config.NumberColumn(format="%.1f%%") for k in ["Hjørne", "Indkast", "Frispark"]})

    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            type_sel = st.radio("Type", ["Hjørnespark", "Indkast", "Frispark"], horizontal=True)
        with col2:
            p_sel = st.selectbox("Spiller", ["Alle"] + sorted(df_team[df_team['TYPE'] == type_sel]['PLAYER_NAME'].unique().tolist()))

        df_plot = df_team[df_team['TYPE'] == type_sel]
        if p_sel != "Alle":
            df_plot = df_plot[df_plot['PLAYER_NAME'] == p_sel]
            
        pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='#555555')
        fig, ax = pitch.draw(figsize=(8, 10))
        
        if not df_plot.empty:
            color = TEAM_COLORS.get(t_sel, {}).get('primary', '#cc0000')
            pitch.arrows(df_plot.EVENT_X * 1.05, df_plot.EVENT_Y * 0.68, 
                         df_plot.ENDX.fillna(df_plot.EVENT_X) * 1.05, df_plot.ENDY.fillna(df_plot.EVENT_Y) * 0.68, 
                         color=color, ax=ax, width=2, alpha=0.3)
        st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
