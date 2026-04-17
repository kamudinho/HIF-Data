import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

def vis_side():
    try:
        conn = _get_snowflake_conn()
    except Exception as e:
        st.error(f"Kunne ikke forbinde til Snowflake: {e}")
        return

    # --- Professionelt Scouting Layout ---
    st.markdown("""
        <style>
        .category-header { font-weight: bold; font-size: 1.1rem; padding: 15px 0 5px 0; color: #111; border-bottom: 2px solid #eee; margin-top: 20px; }
        .metric-label { font-size: 0.85rem; color: #444; display: flex; align-items: center; height: 35px; }
        .rank-container { position: relative; background-color: #f0f0f0; height: 32px; width: 100%; border-radius: 4px; overflow: hidden; display: flex; align-items: center; margin-bottom: 4px; }
        .rank-fill { height: 100%; display: flex; align-items: center; padding-left: 10px; font-weight: bold; color: black; font-size: 0.75rem; white-space: nowrap; }
        .player-card { text-align: center; min-height: 150px; }
        .player-img-round { border-radius: 50%; object-fit: cover; border: 3px solid #f0f2f6; background-color: white; margin-bottom: 8px; }
        .player-name-text { font-size: 0.8rem; line-height: 1.2; font-weight: bold; color: #111; display: block; height: 40px; }
        </style>
    """, unsafe_allow_html=True)

    # --- Kontrolpanel ---
    st.title("NordicBet Liga - Præstationsrapport 2026")
    
    col_ctrl1, col_ctrl2 = st.columns([2, 2])
    with col_ctrl1:
        # Vælg hold baseret på din team_mapping.py
        valgt_hold_navn = st.selectbox("Vælg hold:", list(TEAMS.keys()), index=0)
        target_wyid = TEAMS[valgt_hold_navn]["team_wyid"]
    
    with col_ctrl2:
        st.write("") # Spacer
        st.info(f"Viser data fra 1. jan 2026 til i dag")

    # --- SQL Query: Dynamisk filtrering på holdets Opta-identitet ---
    query = f"""
    WITH SELECTED_TEAM_ID AS (
        -- Sikrer vi har det rigtige hold-ID fra Opta
        SELECT CONTESTANT_OPTAUUID 
        FROM KLUB_HVIDOVREIF.AXIS.OPTA_TEAMS 
        WHERE NAME = '{valgt_hold_navn}' OR OFFICIALNAME = '{valgt_hold_navn}'
        LIMIT 1
    ),
    PLAYER_STATS AS (
        -- Henter rå stats KUN for det valgte hold via EVENT_CONTESTANT_OPTAUUID
        SELECT 
            PLAYER_OPTAUUID,
            COUNT(CASE WHEN EVENT_TYPEID = 16 THEN 1 END) as M1, -- Mål
            COUNT(CASE WHEN EVENT_TYPEID = 1 AND EVENT_OUTCOME = 1 THEN 1 END) as M2, -- Afleveringer
            COUNT(CASE WHEN EVENT_TYPEID = 15 THEN 1 END) as M3 -- Tacklinger
        FROM KLUB_HVIDOVREIF.AXIS.OPTA_EVENTS
        WHERE DATE >= '2026-01-01'
          AND EVENT_CONTESTANT_OPTAUUID = (SELECT CONTESTANT_OPTAUUID FROM SELECTED_TEAM_ID)
          AND PLAYER_OPTAUUID IS NOT NULL
        GROUP BY PLAYER_OPTAUUID
    ),
    LIGA_RANKED AS (
        -- Beregner ranks mod hele ligaen (uden team-filter i denne sub-query)
        SELECT 
            p.MATCH_NAME as PLAYER_NAME,
            p.PLAYER_OPTAUUID,
            s.M1, s.M2, s.M3,
            RANK() OVER (ORDER BY s.M1 DESC NULLS LAST) as M1_RANK,
            RANK() OVER (ORDER BY s.M2 DESC NULLS LAST) as M2_RANK,
            RANK() OVER (ORDER BY s.M3 DESC NULLS LAST) as M3_RANK
        FROM KLUB_HVIDOVREIF.AXIS.OPTA_PLAYERS p
        JOIN PLAYER_STATS s ON p.PLAYER_OPTAUUID = s.PLAYER_OPTAUUID
    ),
    VALGT_TRUP_WYS AS (
        -- Henter spillere og billeder fra Wyscout for det valgte hold
        SELECT 
            TRIM(LASTNAME) as L_NAME,
            (TRIM(FIRSTNAME) || ' ' || TRIM(LASTNAME)) as FULL_NAME, 
            MAX(IMAGEDATAURL) as IMG
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS 
        WHERE CURRENTTEAM_WYID = {target_wyid} 
        GROUP BY 1, 2
    )
    SELECT DISTINCT
        t.IMG, 
        t.FULL_NAME as WYS_NAME, 
        r.PLAYER_NAME as OPTA_NAME,
        r.M1, r.M2, r.M3,
        r.M1_RANK, r.M2_RANK, r.M3_RANK
    FROM VALGT_TRUP_WYS t
    INNER JOIN LIGA_RANKED r ON (
        -- Nu er matchingen sikker, da LIGA_RANKED kun indeholder holdets spillere
        r.PLAYER_NAME LIKE '%' || t.L_NAME || '%'
    )
    QUALIFY ROW_NUMBER() OVER (PARTITION BY t.FULL_NAME ORDER BY r.M2 DESC) = 1
    ORDER BY r.M2 DESC
    """

    try:
        df = pd.read_sql(query, conn)
        
        if not df.empty:
            # Top 5 spillere baseret på aktivitet (M2)
            display_df = df.head(5)
            
            # --- Spiller Oversigt (Billeder) ---
            st.write("### Top Præstationer")
            cols = st.columns([2.5, 1, 1, 1, 1, 1])
            
            for i, (_, row) in enumerate(display_df.iterrows()):
                with cols[i+1]:
                    img_url = row['IMG'] if row['IMG'] and str(row['IMG']) != 'None' else "https://via.placeholder.com/150"
                    st.markdown(f"""
                        <div class="player-card">
                            <img src="{img_url}" class="player-img-round" width="70" height="70"><br>
                            <span class="player-name-text">{row['WYS_NAME']}</span>
                        </div>
                    """, unsafe_allow_html=True)

            # --- Metrics Sektioner ---
            metrics = {
                "Offensiv Impact": [("Mål scoret", "M1_RANK")],
                "Distribution": [("Succesfulde afleveringer", "M2_RANK")],
                "Defensiv Styrke": [("Vundne tacklinger", "M3_RANK")]
            }

            for kat_navn, items in metrics.items():
                st.markdown(f'<div class="category-header">{kat_navn}</div>', unsafe_allow_html=True)
                
                for label, rank_col in items:
                    m_cols = st.columns([2.5, 1, 1, 1, 1, 1])
                    
                    with m_cols[0]:
                        st.markdown(f'<div class="metric-label">{label}</div>', unsafe_allow_html=True)
                    
                    for i, (_, row) in enumerate(display_df.iterrows()):
                        rank_val = int(row[rank_col]) if pd.notnull(row[rank_col]) else 999
                        
                        # Dynamisk farve og bredde
                        # Ranks under 50 er grønne, under 150 gule, resten røde
                        color = "#22c55e" if rank_val <= 50 else "#facc15" if rank_val <= 150 else "#fca5a5"
                        width = max(15, (1 - (rank_val / 500)) * 100) if rank_val <= 500 else 10
                        
                        with m_cols[i+1]:
                            st.markdown(f"""
                                <div class="rank-container">
                                    <div class="rank-fill" style="width: {width}%; background-color: {color};">
                                        R {rank_val}
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
        else:
            st.warning(f"Ingen kampdata fundet for {valgt_hold_navn} i 2026.")

    except Exception as e:
        st.error(f"Fejl ved hentning af data: {e}")

if __name__ == "__main__":
    vis_side()
