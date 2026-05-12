import streamlit as st
import pandas as pd
import numpy as np
from data.data_load import _get_snowflake_conn

# Konfiguration fra dine gemte oplysninger
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o"

@st.cache_data(ttl=3600)
def load_vasket_data():
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    
    # Vi bruger en Sub-query (CTE) til at samle alle qualifiers for hver unikt EVENT_OPTAUUID.
    # Dette sikrer, at vi kun har ÉN række pr. aktion.
    sql = f"""
    WITH UNIQUE_EVENTS AS (
        SELECT 
            e.EVENT_OPTAUUID,
            e.EVENT_X,
            e.EVENT_Y,
            e.EVENT_OUTCOME,
            e.EVENT_CONTESTANT_OPTAUUID,
            e.PLAYER_OPTAUUID,
            -- Vi bruger MAX for at se om en egenskab findes uden at skabe nye rækker
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
    FROM UNIQUE_EVENTS b
    LEFT JOIN {DB}.OPTA_PLAYERS p ON b.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
    """
    df = conn.query(sql)
    df.columns = [c.upper() for c in df.columns]
    
    # Definer typen baseret på de unikke flag
    def get_type(row):
        if row['IS_CORNER'] == 1: return "Hjørnespark"
        if row['IS_THROW_IN'] == 1: return "Indkast"
        return "Frispark"
    
    df['TYPE'] = df.apply(get_type, axis=1)
    return df

def vis_side():
    st.title("Standardsituationer - Valideret Oversigt")
    df_all = load_vasket_data()
    
    if df_all.empty:
        st.error("Ingen data fundet.")
        return

    # Filtrering på hold (Hvidovre som standard)
    teams = sorted(df_all['EVENT_CONTESTANT_OPTAUUID'].unique())
    # (Her kan du indsætte din hold-mapping hvis nødvendigt)
    df_team = df_all.copy() 

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
    
    st.dataframe(
        df_stats, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Hjørne Succes %": st.column_config.NumberColumn(format="%.1f%%"),
            "Indkast Succes %": st.column_config.NumberColumn(format="%.1f%%"),
            "Frispark Succes %": st.column_config.NumberColumn(format="%.1f%%")
        }
    )

if __name__ == "__main__":
    vis_side()
