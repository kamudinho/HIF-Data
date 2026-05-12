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
    
    # Denne SQL isolerer KUN de hændelser, der har en dødbolds-qualifier.
    # Vi fjerner alt andet støj ved at kræve, at hændelsen findes i filter-listen.
    sql = f"""
    SELECT 
        e.EVENT_OPTAUUID,
        e.EVENT_OUTCOME,
        TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME,
        MAX(CASE WHEN q.QUALIFIER_QID = 6 THEN 1 ELSE 0 END) as IS_CORNER,
        MAX(CASE WHEN q.QUALIFIER_QID = 107 THEN 1 ELSE 0 END) as IS_THROW_IN,
        MAX(CASE WHEN q.QUALIFIER_QID IN (5, 26) THEN 1 ELSE 0 END) as IS_FREEKICK
    FROM {DB}.OPTA_EVENTS e
    INNER JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
    LEFT JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
    WHERE e.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
    AND q.QUALIFIER_QID IN (6, 107, 5, 26) -- Dette filtrerer selve JOIN'en benhårdt
    GROUP BY 1, 2, 3
    """
    df = conn.query(sql)
    df.columns = [c.upper() for c in df.columns]
    return df

def generate_player_table(df):
    stats = []
    for player, p_df in df.groupby('PLAYER_NAME'):
        
        def get_as_pct(sub_df):
            antal = len(sub_df)
            succes = int(sub_df['EVENT_OUTCOME'].sum()) if antal > 0 else 0
            pct = (succes / antal * 100) if antal > 0 else 0
            return f"{antal} / {succes}", pct

        # Beregn for hver type
        hj_as, hj_pct = get_as_pct(p_df[p_df['IS_CORNER'] == 1])
        ind_as, ind_pct = get_as_pct(p_df[p_df['IS_THROW_IN'] == 1])
        fri_as, fri_pct = get_as_pct(p_df[p_df['IS_FREEKICK'] == 1])
        
        total_antal = len(p_df)
        
        stats.append({
            'Navn': player,
            'Total': total_antal,
            'Hjørne (A/S)': hj_as,
            'Hjørne %': hj_pct,
            'Indkast (A/S)': ind_as,
            'Indkast %': ind_pct,
            'Frispark (A/S)': fri_as,
            'Frispark %': fri_pct
        })
    
    return pd.DataFrame(stats).sort_values("Total", ascending=False)

def vis_side():
    st.title("Standardsituationer - Hvidovre IF")
    
    df_raw = load_pure_standards()
    
    if df_raw.empty:
        st.warning("Ingen data fundet.")
        return

    # Generer tabellen
    df_final = generate_player_table(df_raw)
    
    # Vis kun spillere med faktiske aktioner
    df_final = df_final[df_final['Total'] > 0]

    st.dataframe(
        df_final, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Hjørne %": st.column_config.NumberColumn("Hjørne %", format="%.1f%%"),
            "Indkast %": st.column_config.NumberColumn("Indkast %", format="%.1f%%"),
            "Frispark %": st.column_config.NumberColumn("Frispark %", format="%.1f%%"),
            "Total": st.column_config.NumberColumn("Total")
        }
    )

if __name__ == "__main__":
    vis_side()
