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
    
    # SQL der sikrer unikke hændelser pr. EVENT_OPTAUUID
    sql = f"""
    WITH UNIQUE_EVENTS AS (
        SELECT 
            e.EVENT_OPTAUUID,
            e.EVENT_X,
            e.EVENT_Y,
            e.EVENT_OUTCOME,
            e.EVENT_CONTESTANT_OPTAUUID,
            e.PLAYER_OPTAUUID,
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
    
    def get_type(row):
        if row['IS_CORNER'] == 1: return "Hjørnespark"
        if row['IS_THROW_IN'] == 1: return "Indkast"
        return "Frispark"
    
    df['TYPE'] = df.apply(get_type, axis=1)
    return df

def generate_player_stats(df):
    """Beregner statistik lynhurtigt i Python for hver spiller."""
    stats_list = []
    
    for player, p_df in df.groupby('PLAYER_NAME'):
        
        def get_stat_line(sub_df):
            """Hjælpefunktion til at pakke Antal / Succes og Procent ud."""
            a = len(sub_df)
            # Vi tæller succeser baseret på EVENT_OUTCOME (1 = succes)
            s = int(sub_df['EVENT_OUTCOME'].sum()) if a > 0 else 0
            pct = (s / a * 100) if a > 0 else 0
            return f"{a} / {s}", pct

        # Opdel data i kategorier
        hj_as, hj_pct = get_stat_line(p_df[p_df['TYPE'] == "Hjørnespark"])
        ind_as, ind_pct = get_stat_line(p_df[p_df['TYPE'] == "Indkast"])
        fri_as, fri_pct = get_stat_line(p_df[p_df['TYPE'] == "Frispark"])
        
        stats_list.append({
            'Navn': player,
            'Total': len(p_df),
            'Hjørne (A/S)': hj_as,
            'Hjørne %': hj_pct,
            'Indkast (A/S)': ind_as,
            'Indkast %': ind_pct,
            'Frispark (A/S)': fri_as,
            'Frispark %': fri_pct
        })
    
    return pd.DataFrame(stats_list).sort_values("Total", ascending=False)

def vis_side():
    st.title("Standardsituationer - Hvidovre IF")
    
    # 1. Load data (Vasket via SQL)
    df_all = load_vasket_data()
    
    if df_all.empty:
        st.warning("Ingen data fundet.")
        return

    # 2. Beregn statistik (Lynhurtigt i Python)
    df_stats = generate_player_stats(df_all)
    
    # 3. Vis tabel med professionel formatering
    st.dataframe(
        df_stats, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Hjørne %": st.column_config.NumberColumn("Hjørne %", format="%.1f%%"),
            "Indkast %": st.column_config.NumberColumn("Indkast %", format="%.1f%%"),
            "Frispark %": st.column_config.NumberColumn("Frispark %", format="%.1f%%"),
            "Total": st.column_config.NumberColumn("Total aktioner", help="Summen af alle unikke hændelser")
        }
    )

if __name__ == "__main__":
    vis_side()
