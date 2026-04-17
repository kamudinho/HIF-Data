import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn

def hent_performance_data(valgt_hold_navn, teams_dict):
    conn = _get_snowflake_conn()
    
    # Hent specifikke IDs fra din TEAMS ordbog
    team_info = teams_dict[valgt_hold_navn]
    wyid = team_info['team_wyid']
    opta_uuid = team_info['opta_uuid']
    
    # Vi bruger en f-string til at indsætte de korrekte IDs i SQL'en
    query = f"""
    WITH WYS_BASE AS (
        SELECT 
            (TRIM(FIRSTNAME) || ' ' || TRIM(LASTNAME)) as FULL_NAME,
            TRIM(LASTNAME) as L_NAME,
            MAX(IMAGEDATAURL) as IMG_URL
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS
        WHERE CURRENTTEAM_WYID = {wyid}
        GROUP BY 1, 2
    ),
    OPTA_STATS AS (
        SELECT 
            p.MATCH_NAME,
            COUNT(CASE WHEN e.EVENT_TYPEID = 16 THEN 1 END) as GOALS,
            COUNT(CASE WHEN e.EVENT_TYPEID = 1 AND e.EVENT_OUTCOME = 1 THEN 1 END) as PASSES
        FROM KLUB_HVIDOVREIF.AXIS.OPTA_EVENTS e
        JOIN KLUB_HVIDOVREIF.AXIS.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
        WHERE e.EVENT_CONTESTANT_OPTAUUID = '{opta_uuid}'
          AND e.DATE >= '2026-01-01'
        GROUP BY 1
    ),
    SS_PHYSICAL AS (
        SELECT 
            PLAYER_NAME,
            AVG(DISTANCE) as DIST,
            MAX(TOP_SPEED) as SPEED
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_DATE >= '2026-01-01'
          -- Vi søger bredt i MATCH_TEAMS for at ramme holdet
          AND MATCH_TEAMS LIKE '%{valgt_hold_navn}%'
        GROUP BY 1
    )
    SELECT 
        w.FULL_NAME,
        COALESCE(o.GOALS, 0) as GOALS,
        COALESCE(o.PASSES, 0) as PASSES,
        ROUND(COALESCE(s.DIST, 0), 2) as DISTANCE,
        ROUND(COALESCE(s.SPEED, 0), 2) as TOP_SPEED,
        w.IMG_URL
    FROM WYS_BASE w
    LEFT JOIN OPTA_STATS o ON (w.FULL_NAME = o.MATCH_NAME OR o.MATCH_NAME LIKE '%' || w.L_NAME || '%')
    LEFT JOIN SS_PHYSICAL s ON (w.FULL_NAME = s.PLAYER_NAME OR s.PLAYER_NAME LIKE '%' || w.L_NAME || '%')
    WHERE (o.MATCH_NAME IS NOT NULL OR s.PLAYER_NAME IS NOT NULL)
    QUALIFY ROW_NUMBER() OVER (PARTITION BY w.FULL_NAME ORDER BY o.PASSES DESC) = 1
    ORDER BY PASSES DESC
    """
    
    return pd.read_sql(query, conn)

# --- Streamlit Implementering ---
def vis_side(TEAMS):
    st.title("Performance Hub 2026")
    
    valgt_hold = st.selectbox("Vælg hold:", list(TEAMS.keys()))
    
    if valgt_hold:
        df = hent_performance_data(valgt_hold, TEAMS)
        
        # Visning af de 5 bedste spillere (eksempel)
        top_spillere = df.head(5)
        
        cols = st.columns(len(top_spillere))
        for i, (index, row) in enumerate(top_spillere.iterrows()):
            with cols[i]:
                st.image(row['IMG_URL'], width=100)
                st.caption(f"**{row['FULL_NAME']}**")
                st.metric("Passes", int(row['PASSES']))
                if row['DISTANCE'] > 0:
                    st.metric("KM", row['DISTANCE'])
