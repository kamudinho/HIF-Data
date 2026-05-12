import streamlit as st
import pandas as pd
import numpy as np
from data.data_load import _get_snowflake_conn

# Konfiguration
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o"

@st.cache_data(ttl=3600)
def load_vasket_standards_data():
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    
    # Denne SQL er "målrettet": Den finder kun hændelser der har de specifikke qualifiers
    # og filtrerer alt støj fra (som almindelige afleveringer).
    sql = f"""
    WITH STANDARDS_EVENTS AS (
        SELECT 
            e.EVENT_OPTAUUID,
            e.EVENT_OUTCOME,
            e.PLAYER_OPTAUUID,
            -- Vi markerer typen med det samme i SQL
            MAX(CASE WHEN q.QUALIFIER_QID = 6 THEN 1 ELSE 0 END) as IS_CORNER,
            MAX(CASE WHEN q.QUALIFIER_QID = 107 THEN 1 ELSE 0 END) as IS_THROW_IN,
            MAX(CASE WHEN q.QUALIFIER_QID IN (5, 26) THEN 1 ELSE 0 END) as IS_FREEKICK
        FROM {DB}.OPTA_EVENTS e
        INNER JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
        WHERE e.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        AND q.QUALIFIER_QID IN (6, 107, 5, 26) -- KUN disse typer hændelser!
        GROUP BY 1, 2, 3
    )
    SELECT 
        s.*,
        TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME
    FROM STANDARDS_EVENTS s
    LEFT JOIN {DB}.OPTA_PLAYERS p ON s.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
    WHERE PLAYER_NAME IS NOT NULL
    """
    df = conn.query(sql)
    df.columns = [c.upper() for c in df.columns]
    return df

def generate_clean_stats(df):
    stats_list = []
    for player, p_df in df.groupby('PLAYER_NAME'):
        # Her tæller vi kun de rækker vi har hentet (som nu KUN er standards)
        
        def get_metrics(sub_df):
            a = len(sub_df)
            s = int(sub_df['EVENT_OUTCOME'].sum()) if a > 0 else 0
            pct = (s / a * 100) if a > 0 else 0
            return f"{a} / {s}", pct

        # Opdel de 169 (for Oliver) i deres kategorier
        c_as, c_pct = get_metrics(p_df[p_df['IS_CORNER'] == 1])
        t_as, t_pct = get_metrics(p_df[p_df['IS_THROW_IN'] == 1])
        f_as, f_pct = get_metrics(p_df[p_df['IS_FREEKICK'] == 1])
        
        stats_list.append({
            'Navn': player,
            'Total Standards': len(p_df), # For Oliver vil denne nu være 169
            'Hjørne (A/S)': c_as,
            'Hjørne %': c_pct,
            'Indkast (A/S)': t_as,
            'Indkast %': t_pct,
            'Frispark (A/S)': f_as,
            'Frispark %': f_pct
        })
    
    return pd.DataFrame(stats_list).sort_values("Total Standards", ascending=False)

def vis_side():
    st.title("Standardsituationer - Valideret (Kun Dødbold)")
    
    df_raw = load_vasket_standards_data()
    
    if df_raw.empty:
        st.warning("Ingen data fundet.")
        return

    df_final = generate_clean_stats(df_raw)
    
    st.dataframe(
        df_final, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Hjørne %": st.column_config.NumberColumn(format="%.1f%%"),
            "Indkast %": st.column_config.NumberColumn(format="%.1f%%"),
            "Frispark %": st.column_config.NumberColumn(format="%.1f%%")
        }
    )

if __name__ == "__main__":
    vis_side()
