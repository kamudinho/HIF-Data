import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

def vis_side():
    try:
        conn = _get_snowflake_conn()
    except Exception as e:
        st.error(f"Forbindelsesfejl: {e}")
        return

    # --- 1. Konfiguration via Team Mapping ---
    # Vi lader brugeren vælge holdet (dropdown baseret på dine 12 hold)
    valgt_hold_navn = st.selectbox("Vælg hold:", list(TEAMS.keys()), key="team_report_selector")
    
    # Henter ID'erne fra din mapping-fil
    target_wyid = TEAMS[valgt_hold_navn]["team_wyid"]
    # Her skal vi bruge Opta-ID'et. Hvis det ikke er i din mapping endnu, 
    # kan vi lave et opslag i OPTA_TEAMS tabellen baseret på navnet.
    
    st.title(f"{valgt_hold_navn} - Præstationsrapport 2026")

    # --- 2. Dynamisk SQL med Team-filtrering ---
    # Vi bruger EVENT_CONTESTANT_OPTAUUID til at låse data til det rigtige hold
    query = f"""
    WITH SELECTED_TEAM AS (
        -- Finder det korrekte Opta UUID for det valgte hold
        SELECT CONTESTANT_OPTAUUID 
        FROM KLUB_HVIDOVREIF.AXIS.OPTA_TEAMS 
        WHERE NAME = '{valgt_hold_navn}' 
        OR OFFICIALNAME = '{valgt_hold_navn}'
        LIMIT 1
    ),
    PLAYER_STATS AS (
        SELECT 
            PLAYER_OPTAUUID,
            COUNT(CASE WHEN EVENT_TYPEID = 16 THEN 1 END) as GOALS,
            COUNT(CASE WHEN EVENT_TYPEID = 1 AND EVENT_OUTCOME = 1 THEN 1 END) as SUCCESSFUL_PASSES,
            COUNT(CASE WHEN EVENT_TYPEID = 15 THEN 1 END) as TOTAL_TACKLES
        FROM KLUB_HVIDOVREIF.AXIS.OPTA_EVENTS
        WHERE DATE >= '2026-01-01'
          AND EVENT_CONTESTANT_OPTAUUID = (SELECT CONTESTANT_OPTAUUID FROM SELECTED_TEAM)
          AND PLAYER_OPTAUUID IS NOT NULL
        GROUP BY PLAYER_OPTAUUID
    ),
    LIGA_RANKED AS (
        -- Vi beregner stadig Ranks mod HELE ligaen (fjern team filter her for global rank)
        SELECT 
            p.MATCH_NAME as PLAYER_NAME,
            p.PLAYER_OPTAUUID,
            s.GOALS as M1,
            s.SUCCESSFUL_PASSES as M2,
            s.TOTAL_TACKLES as M3,
            RANK() OVER (ORDER BY s.GOALS DESC NULLS LAST) as M1_RANK,
            RANK() OVER (ORDER BY s.SUCCESSFUL_PASSES DESC NULLS LAST) as M2_RANK,
            RANK() OVER (ORDER BY s.TOTAL_TACKLES DESC NULLS LAST) as M3_RANK
        FROM KLUB_HVIDOVREIF.AXIS.OPTA_PLAYERS p
        JOIN PLAYER_STATS s ON p.PLAYER_OPTAUUID = s.PLAYER_OPTAUUID
    ),
    VALGT_TRUP_WYS AS (
        -- Henter kun spillere fra det valgte hold i Wyscout (til billeder)
        SELECT 
            TRIM(FIRSTNAME) as F_NAME,
            TRIM(LASTNAME) as L_NAME,
            (TRIM(FIRSTNAME) || ' ' || TRIM(LASTNAME)) as FULL_NAME, 
            MAX(IMAGEDATAURL) as IMG
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS 
        WHERE CURRENTTEAM_WYID = {target_wyid} 
        GROUP BY 1, 2, 3
    )
    SELECT DISTINCT
        t.IMG, 
        t.FULL_NAME as WYS_NAME, 
        r.PLAYER_NAME as OPTA_NAME,
        r.M1, r.M2, r.M3,
        r.M1_RANK, r.M2_RANK, r.M3_RANK
    FROM VALGT_TRUP_WYS t
    INNER JOIN LIGA_RANKED r ON (
        -- Nu er matchingen sikker, da PLAYER_STATS kun indeholder det valgte holds spillere
        r.PLAYER_NAME LIKE '%' || t.L_NAME || '%'
    )
    QUALIFY ROW_NUMBER() OVER (PARTITION BY t.FULL_NAME ORDER BY r.M2 DESC) = 1
    ORDER BY r.M2 DESC
    """

    try:
        df = pd.read_sql(query, conn)
        
        if not df.empty:
            # Vis de 5 spillere med flest afleveringer (M2)
            display_df = df.head(5)
            
            # --- Render layoutet (Billeder og Ranks) ---
            # (Jeg genbruger dit professionelle CSS herunder)
            st.markdown("<style>...</style>", unsafe_allow_html=True) 
            
            cols = st.columns([2.5, 1, 1, 1, 1, 1])
            for i, (_, row) in enumerate(display_df.iterrows()):
                with cols[i+1]:
                    img = row['IMG'] if row['IMG'] and str(row['IMG']) != 'None' else "https://via.placeholder.com/150"
                    st.image(img, width=65)
                    st.caption(f"**{row['WYS_NAME']}**")

            # --- Rækker med Ranks (Mål, Afleveringer, Tacklinger) ---
            # ... her indsættes din række-logik for R-værdierne
            
        else:
            st.warning(f"Ingen kampdata fundet for {valgt_hold_navn} i 2026.")

    except Exception as e:
        st.error(f"Fejl: {e}")

if __name__ == "__main__":
    vis_side()
