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

    # --- CSS til professionel rapport ---
    st.markdown("""
        <style>
        .category-header { font-weight: bold; font-size: 1rem; padding: 15px 0 5px 0; color: #111; border-bottom: 2px solid #eee; margin-top: 10px; }
        .metric-label { font-size: 0.8rem; color: #444; display: flex; align-items: center; height: 35px; line-height: 1.1; }
        .rank-container { position: relative; background-color: #f0f0f0; height: 32px; width: 100%; border-radius: 4px; overflow: hidden; display: flex; align-items: center; margin-bottom: 2px; }
        .rank-fill { height: 100%; display: flex; align-items: center; padding-left: 8px; font-weight: bold; color: black; font-size: 0.72rem; white-space: nowrap; min-width: fit-content; }
        .player-card { text-align: center; min-height: 140px; }
        .player-img-round { border-radius: 50%; object-fit: cover; border: 2px solid #f0f2f6; background-color: white; margin-bottom: 5px; }
        .player-name-text { font-size: 0.72rem; line-height: 1.1; font-weight: bold; color: #111; display: block; }
        </style>
    """, unsafe_allow_html=True)

    # --- 1. Vælg hold fra team_mapping ---
    valgt_hold_navn = st.selectbox("Vælg hold fra Betinia Ligaen:", list(TEAMS.keys()))
    
    # Hent ID'er fra din mapping
    target_wyid = TEAMS[valgt_hold_navn]["team_wyid"]
    # Vi antager at team_mapping også indeholder opta_id eller vi matcher på holdnavnet
    target_opta_name = valgt_hold_navn 

    st.title(f"{valgt_hold_navn} - Teknisk Rapport")
    st.info("Data fra 01.01.2026 til dags dato.")

    # --- 2. SQL Query der bruger team_mapping til filtrering ---
    query = f"""
    WITH PLAYER_STATS AS (
        SELECT 
            PLAYER_OPTAUUID,
            COUNT(CASE WHEN EVENT_TYPEID = 16 THEN 1 END) as GOALS,
            COUNT(CASE WHEN EVENT_TYPEID = 1 AND EVENT_OUTCOME = 1 THEN 1 END) as SUCCESSFUL_PASSES,
            COUNT(CASE WHEN EVENT_TYPEID = 15 THEN 1 END) as TOTAL_TACKLES
        FROM KLUB_HVIDOVREIF.AXIS.OPTA_EVENTS
        WHERE DATE >= '2026-01-01'
          AND PLAYER_OPTAUUID IS NOT NULL
        GROUP BY PLAYER_OPTAUUID
    ),
    LIGA_RANKED AS (
        SELECT 
            p.MATCH_NAME as PLAYER_NAME,
            p.PLAYER_OPTAUUID,
            ot.NAME as TEAM_NAME,
            s.GOALS as M1,
            s.SUCCESSFUL_PASSES as M2,
            s.TOTAL_TACKLES as M3,
            -- Rank beregnes mod hele ligaen (før vi filtrerer på hold)
            RANK() OVER (ORDER BY s.GOALS DESC NULLS LAST) as M1_RANK,
            RANK() OVER (ORDER BY s.SUCCESSFUL_PASSES DESC NULLS LAST) as M2_RANK,
            RANK() OVER (ORDER BY s.TOTAL_TACKLES DESC NULLS LAST) as M3_RANK
        FROM KLUB_HVIDOVREIF.AXIS.OPTA_PLAYERS p
        JOIN PLAYER_STATS s ON p.PLAYER_OPTAUUID = s.PLAYER_OPTAUUID
        LEFT JOIN KLUB_HVIDOVREIF.AXIS.OPTA_TEAMS ot ON p.TEAM_OPTAUUID = ot.CONTESTANT_OPTAUUID
        -- FILTER: Her bruger vi holdnavnet fra din team_mapping
        WHERE ot.NAME = '{target_opta_name}'
    ),
    VALGT_TRUP AS (
        SELECT 
            TRIM(FIRSTNAME) as F_NAME,
            TRIM(LASTNAME) as L_NAME,
            (TRIM(FIRSTNAME) || ' ' || TRIM(LASTNAME)) as FULL_NAME, 
            MAX(IMAGEDATAURL) as IMG
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS 
        -- FILTER: Her bruger vi team_wyid fra din team_mapping
        WHERE CURRENTTEAM_WYID = {target_wyid} 
        GROUP BY 1, 2, 3
    )
    SELECT DISTINCT
        t.IMG, 
        t.FULL_NAME as WYS_NAME, 
        r.PLAYER_NAME as OPTA_NAME,
        r.TEAM_NAME,
        r.M1, r.M2, r.M3,
        r.M1_RANK, r.M2_RANK, r.M3_RANK
    FROM VALGT_TRUP t
    INNER JOIN LIGA_RANKED r ON (
        -- Nu er det sikkert at matche på efternavn, da r kun indeholder det valgte hold
        r.PLAYER_NAME LIKE '%' || t.L_NAME || '%'
    )
    QUALIFY ROW_NUMBER() OVER (PARTITION BY t.FULL_NAME ORDER BY r.M2 DESC) = 1
    ORDER BY r.M2 DESC
    """

    try:
        df = pd.read_sql(query, conn)
        
        if not df.empty:
            display_df = df.head(5)
            
            # --- Render Spiller-kort ---
            cols = st.columns([2.5, 1, 1, 1, 1, 1])
            for i, (_, row) in enumerate(display_df.iterrows()):
                with cols[i+1]:
                    img = row['IMG'] if row['IMG'] and str(row['IMG']) != 'None' else "https://via.placeholder.com/150"
                    st.markdown(f"""
                        <div class="player-card">
                            <img src="{img}" class="player-img-round" width="60" height="60"><br>
                            <span class="player-name-text">{row['WYS_NAME']}</span>
                        </div>
                    """, unsafe_allow_html=True)

            # --- Rækker med Ranks ---
            metrics_labels = {
                "Offensivt (2026)": [("Mål", "M1_RANK")],
                "Distribution (2026)": [("Vundne Afleveringer", "M2_RANK")],
                "Defensivt (2026)": [("Tacklinger", "M3_RANK")]
            }

            for kat_navn, metrics in metrics_labels.items():
                st.markdown(f'<div class="category-header">{kat_navn}</div>', unsafe_allow_html=True)
                for label, col_name in metrics:
                    m_cols = st.columns([2.5, 1, 1, 1, 1, 1])
                    with m_cols[0]: 
                        st.markdown(f'<div class="metric-label">{label}</div>', unsafe_allow_html=True)
                    
                    for i, (_, row) in enumerate(display_df.iterrows()):
                        rank_val = int(row[col_name]) if pd.notnull(row[col_name]) else 999
                        fill_width = max(15, (1 - (rank_val / 500)) * 100) if rank_val <= 500 else 10
                        color = "#22c55e" if rank_val <= 50 else "#facc15" if rank_val <= 150 else "#fca5a5"
                        
                        with m_cols[i+1]:
                            st.markdown(f"""
                                <div class="rank-container">
                                    <div class="rank-fill" style="width: {fill_width}%; background-color: {color};">
                                        R {rank_val}
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
        else:
            st.warning(f"Ingen data fundet for {valgt_hold_navn} i 2026. Tjek om holdnavnet matcher præcis i Opta.")

    except Exception as e:
        st.error(f"Fejl: {e}")

if __name__ == "__main__":
    vis_side()
