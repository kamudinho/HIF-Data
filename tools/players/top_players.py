import pandas as pd
import streamlit as st
from data.data_load import _get_snowflake_conn

def hent_hold_performance(valgt_hold_navn, teams_dict):
    conn = _get_snowflake_conn()
    
    # Trækker IDs fra din ordbog baseret på det hold, brugeren vælger
    config = teams_dict[valgt_hold_navn]
    wyid = config['team_wyid']
    opta_uuid = config['opta_uuid']
    ssid = config.get('ssid', '') # Vi tager ssid hvis den findes

    query = f"""
    WITH WYS_BASE AS (
        SELECT 
            PLAYER_WYID::VARCHAR as W_ID,
            LOWER(TRIM(FIRSTNAME)) as W_FIRST,
            LOWER(TRIM(LASTNAME)) as W_LAST,
            (FIRSTNAME || ' ' || LASTNAME) as FULL_NAME,
            IMAGEDATAURL as IMG_URL
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS
        WHERE CURRENTTEAM_WYID = {wyid}
    ),
    OPTA_BASE AS (
        SELECT 
            p.PLAYER_OPTAUUID::VARCHAR as O_ID,
            LOWER(TRIM(p.FIRST_NAME)) as O_FIRST,
            LOWER(TRIM(p.LAST_NAME)) as O_LAST,
            p.MATCH_NAME,
            COUNT(CASE WHEN e.EVENT_TYPEID = 16 THEN 1 END) as GOALS,
            COUNT(CASE WHEN e.EVENT_TYPEID = 1 AND e.EVENT_OUTCOME = 1 THEN 1 END) as PASSES
        FROM KLUB_HVIDOVREIF.AXIS.OPTA_EVENTS e
        JOIN KLUB_HVIDOVREIF.AXIS.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
        WHERE e.EVENT_CONTESTANT_OPTAUUID = '{opta_uuid}'
          AND e.DATE >= '2026-01-01'
        GROUP BY 1, 2, 3, 4
    )
    SELECT 
        w.FULL_NAME,
        COALESCE(o.GOALS, 0) as GOALS,
        COALESCE(o.PASSES, 0) as PASSES,
        w.IMG_URL
    FROM WYS_BASE w
    INNER JOIN OPTA_BASE o ON (
        (o.O_FIRST = w.W_FIRST AND o.O_LAST = w.W_LAST) OR
        (o.MATCH_NAME ILIKE '%' || w.W_LAST || '%' AND o.MATCH_NAME ILIKE '%' || LEFT(w.W_FIRST, 1) || '%')
    )
    -- QUALIFY fjerner dubletter (f.eks. Alexander Johansen) ved kun at tage den række med flest afleveringer
    QUALIFY ROW_NUMBER() OVER (PARTITION BY w.FULL_NAME ORDER BY o.PASSES DESC) = 1
    ORDER BY PASSES DESC
    """
    
    return pd.read_sql(query, conn)

# --- Streamlit UI eksempel ---
def app(TEAMS):
    st.title("Performance Oversigt")
    
    # Brugeren vælger hold (f.eks. 'Hvidovre')
    valg = st.selectbox("Vælg dit hold", list(TEAMS.keys()))
    
    if st.button("Hent Data"):
        df = hent_hold_performance(valg, TEAMS)
        
        # Visning i Streamlit
        st.dataframe(df[['FULL_NAME', 'GOALS', 'PASSES']])
        
        # Eksempel: Vis de 3 bedste spillere med billeder
        top3 = df.head(3)
        cols = st.columns(3)
        for i, (idx, row) in enumerate(top3.iterrows()):
            with cols[i]:
                st.image(row['IMG_URL'], width=120)
                st.write(f"**{row['FULL_NAME']}**")
                st.write(f"Mål: {int(row['GOALS'])}")
