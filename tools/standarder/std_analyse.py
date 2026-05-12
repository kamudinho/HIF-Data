import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn

# Konfiguration
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o"

@st.cache_data(ttl=3600)
def load_pure_standards():
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    
    # Denne SQL tvinger databasen til KUN at kigge på hændelser, 
    # der har en af de 4 definerende "dødbolds-markører".
    sql = f"""
    SELECT 
        e.EVENT_OPTAUUID,
        e.EVENT_OUTCOME,
        TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME,
        -- Her definerer vi typerne benhårdt
        MAX(CASE WHEN q.QUALIFIER_QID = 6 THEN 1 ELSE 0 END) as IS_CORNER,
        MAX(CASE WHEN q.QUALIFIER_QID = 107 THEN 1 ELSE 0 END) as IS_THROW_IN,
        MAX(CASE WHEN q.QUALIFIER_QID IN (5, 26) THEN 1 ELSE 0 END) as IS_FREEKICK
    FROM {DB}.OPTA_EVENTS e
    INNER JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
    LEFT JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
    WHERE e.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
    -- DETTE FILTER ER AFGØRENDE:
    AND e.EVENT_OPTAUUID IN (
        SELECT DISTINCT EVENT_OPTAUUID 
        FROM {DB}.OPTA_QUALIFIERS 
        WHERE QUALIFIER_QID IN (6, 107, 5, 26)
    )
    GROUP BY 1, 2, 3
    """
    df = conn.query(sql)
    df.columns = [c.upper() for c in df.columns]
    return df

def generate_stats(df):
    stats_list = []
    for player, p_df in df.groupby('PLAYER_NAME'):
        
        # Funktion til at beregne Antal / Succes
        def get_metrics(sub_df):
            total = len(sub_df)
            success = int(sub_df['EVENT_OUTCOME'].sum()) if total > 0 else 0
            pct = (success / total * 100) if total > 0 else 0
            return f"{total} / {success}", pct

        # Vi filtrerer i de hentede data
        c_as, c_pct = get_metrics(p_df[p_df['IS_CORNER'] == 1])
        t_as, t_pct = get_metrics(p_df[p_df['IS_THROW_IN'] == 1])
        f_as, f_pct = get_metrics(p_df[p_df['IS_FREEKICK'] == 1])
        
        # Samlet antal standardsituationer
        total_standards = len(p_df)
        
        stats_list.append({
            'Navn': player,
            'Total Standards': total_standards,
            'Hjørne (A/S)': c_as,
            'Hjørne %': c_pct,
            'Indkast (A/S)': t_as,
            'Indkast %': t_pct,
            'Frispark (A/S)': f_as,
            'Frispark %': f_pct
        })
    
    return pd.DataFrame(stats_list).sort_values("Total Standards", ascending=False)

def vis_side():
    st.title("Dødbolds-statistik (Valideret)")
    
    df_raw = load_pure_standards()
    
    if df_raw.empty:
        st.warning("Ingen data fundet.")
        return

    df_final = generate_stats(df_raw)
    
    # Vis kun spillere der faktisk har taget en standardsituation
    df_final = df_final[df_final['Total Standards'] > 0]
    
    st.dataframe(
        df_final, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Hjørne %": st.column_config.NumberColumn(format="%.1f%%"),
            "Indkast %": st.column_config.NumberColumn(format="%.1f%%"),
            "Frispark %": st.column_config.NumberColumn(format="%.1f%%"),
            "Total Standards": st.column_config.NumberColumn(help="Kun summen af Hjørne, Indkast og Frispark")
        }
    )

if __name__ == "__main__":
    vis_side()
