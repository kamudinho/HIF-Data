# tools/players/top_players.py
import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn

def hent_performance_data(wyid, opta_uuid):
    conn = _get_snowflake_conn()
    
    # Den optimerede query med Fuzzy Match og unikt ID-tjek
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
    QUALIFY ROW_NUMBER() OVER (PARTITION BY w.FULL_NAME ORDER BY o.PASSES DESC) = 1
    ORDER BY PASSES DESC
    """
    return pd.read_sql(query, conn)

def vis_side(TEAMS):
    st.header("🏆 Top 5: Spillere (Sæson 25/26)")
    
    # Vi henter værdierne for Hvidovre som standard, eller lader brugeren vælge
    valgt_hold = st.selectbox("Vælg hold:", list(TEAMS.keys()), index=0)
    
    team_cfg = TEAMS[valgt_hold]
    
    with st.spinner(f"Henter data for {valgt_hold}..."):
        df = hent_performance_data(team_cfg['team_wyid'], team_cfg['opta_uuid'])
    
    if not df.empty:
        # Vis Top 5 i kolonner med billeder
        st.subheader("Flest afleveringer")
        top_5 = df.head(5)
        
        cols = st.columns(5)
        for i, (idx, row) in enumerate(top_5.iterrows()):
            with cols[i]:
                # Vi bruger en placeholder hvis billedet mangler
                img = row['IMG_URL'] if row['IMG_URL'] else "https://cdn.wyscout.com/photos/players/public/ndplayer_100x130.png"
                st.image(img, use_container_width=True)
                st.markdown(f"**{row['FULL_NAME']}**")
                st.caption(f"⚽ {int(row['GOALS'])} mål")
                st.metric("Passes", int(row['PASSES']))
        
        st.divider()
        st.dataframe(df[['FULL_NAME', 'GOALS', 'PASSES']], use_container_width=True)
    else:
        st.warning("Ingen aktive spillere fundet for dette hold i 2026.")
