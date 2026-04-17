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

    # --- Styling ---
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
    st.title("Performance Hub 2026")
    
    col_ctrl1, col_ctrl2 = st.columns([2, 2])
    with col_ctrl1:
        valgt_hold_navn = st.selectbox("Vælg hold:", list(TEAMS.keys()), index=0)
        target_wyid = TEAMS[valgt_hold_navn]["team_wyid"]
    
    with col_ctrl2:
        datakilde = st.radio("Vælg datakilde:", ["OPTA (Teknisk)", "Second Spectrum (Fysisk)"], horizontal=True)

    # --- SQL Logik ---
    if datakilde == "OPTA (Teknisk)":
        # OPTA Query
        metrics_def = {
            "Offensivt": [("Mål", "M1_RANK")],
            "Distribution": [("Succesf. Afleveringer", "M2_RANK")],
            "Defensivt": [("Tacklinger", "M3_RANK")]
        }
        query = f"""
        WITH SELECTED_TEAM AS (
            SELECT CONTESTANT_OPTAUUID FROM KLUB_HVIDOVREIF.AXIS.OPTA_TEAMS 
            WHERE NAME = '{valgt_hold_navn}' OR OFFICIALNAME = '{valgt_hold_navn}' LIMIT 1
        ),
        STATS AS (
            SELECT PLAYER_OPTAUUID,
                COUNT(CASE WHEN EVENT_TYPEID = 16 THEN 1 END) as M1,
                COUNT(CASE WHEN EVENT_TYPEID = 1 AND EVENT_OUTCOME = 1 THEN 1 END) as M2,
                COUNT(CASE WHEN EVENT_TYPEID = 15 THEN 1 END) as M3
            FROM KLUB_HVIDOVREIF.AXIS.OPTA_EVENTS
            WHERE DATE >= '2026-01-01'
              AND EVENT_CONTESTANT_OPTAUUID = (SELECT CONTESTANT_OPTAUUID FROM SELECTED_TEAM)
            GROUP BY PLAYER_OPTAUUID
        ),
        LIGA_RANKED AS (
            SELECT p.MATCH_NAME as P_NAME, p.PLAYER_OPTAUUID, s.*,
                RANK() OVER (ORDER BY s.M1 DESC NULLS LAST) as M1_RANK,
                RANK() OVER (ORDER BY s.M2 DESC NULLS LAST) as M2_RANK,
                RANK() OVER (ORDER BY s.M3 DESC NULLS LAST) as M3_RANK
            FROM KLUB_HVIDOVREIF.AXIS.OPTA_PLAYERS p
            JOIN STATS s ON p.PLAYER_OPTAUUID = s.PLAYER_OPTAUUID
        )
        """
    else:
        # Second Spectrum Query
        metrics_def = {
            "Løbe-volumen": [("Total Distance", "M1_RANK"), ("Højintakt løb", "M2_RANK")],
            "Sprints": [("Sprint Distance", "M3_RANK"), ("Top Speed", "M4_RANK")]
        }
        query = f"""
        WITH STATS AS (
            SELECT PLAYER_NAME,
                AVG(DISTANCE) as M1,
                AVG("HIGH SPEED RUNNING") as M2,
                AVG(SPRINTING) as M3,
                MAX(TOP_SPEED) as M4
            FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
            WHERE DATE >= '2026-01-01'
              AND TEAM_NAME = '{valgt_hold_navn}'
            GROUP BY PLAYER_NAME
        ),
        LIGA_RANKED AS (
            SELECT PLAYER_NAME as P_NAME, s.*,
                RANK() OVER (ORDER BY s.M1 DESC NULLS LAST) as M1_RANK,
                RANK() OVER (ORDER BY s.M2 DESC NULLS LAST) as M2_RANK,
                RANK() OVER (ORDER BY s.M3 DESC NULLS LAST) as M3_RANK,
                RANK() OVER (ORDER BY s.M4 DESC NULLS LAST) as M4_RANK
            FROM STATS s
        )
        """

    # --- Samling af data (Wyscout Join) ---
    final_query = query + f"""
    , VALGT_TRUP_WYS AS (
        SELECT TRIM(LASTNAME) as L_NAME, (TRIM(FIRSTNAME) || ' ' || TRIM(LASTNAME)) as FULL_NAME, MAX(IMAGEDATAURL) as IMG
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS WHERE CURRENTTEAM_WYID = {target_wyid} GROUP BY 1, 2
    )
    SELECT DISTINCT t.IMG, t.FULL_NAME as WYS_NAME, r.* FROM VALGT_TRUP_WYS t
    INNER JOIN LIGA_RANKED r ON (r.P_NAME LIKE '%' || t.L_NAME || '%')
    QUALIFY ROW_NUMBER() OVER (PARTITION BY t.FULL_NAME ORDER BY r.M2 DESC) = 1
    ORDER BY r.M2 DESC
    """

    try:
        df = pd.read_sql(final_query, conn)
        
        if not df.empty:
            display_df = df.head(5)
            
            # --- Spiller Billeder ---
            cols = st.columns([2.5, 1, 1, 1, 1, 1])
            for i, (_, row) in enumerate(display_df.iterrows()):
                with cols[i+1]:
                    img = row['IMG'] if row['IMG'] and str(row['IMG']) != 'None' else "https://via.placeholder.com/150"
                    st.markdown(f'<div class="player-card"><img src="{img}" class="player-img-round" width="70" height="70"><br><span class="player-name-text">{row["WYS_NAME"]}</span></div>', unsafe_allow_html=True)

            # --- Ranks ---
            for kat, items in metrics_def.items():
                st.markdown(f'<div class="category-header">{kat}</div>', unsafe_allow_html=True)
                for label, r_col in items:
                    m_cols = st.columns([2.5, 1, 1, 1, 1, 1])
                    with m_cols[0]: st.markdown(f'<div class="metric-label">{label}</div>', unsafe_allow_html=True)
                    for i, (_, row) in enumerate(display_df.iterrows()):
                        rank = int(row[r_col]) if pd.notnull(row[r_col]) else 999
                        color = "#22c55e" if rank <= 50 else "#facc15" if rank <= 150 else "#fca5a5"
                        width = max(15, (1 - (rank / 500)) * 100) if rank <= 500 else 10
                        with m_cols[i+1]:
                            st.markdown(f'<div class="rank-container"><div class="rank-fill" style="width: {width}%; background-color: {color};">R {rank}</div></div>', unsafe_allow_html=True)
        else:
            st.warning(f"Ingen data fundet for {valgt_hold_navn} i 2026 via {datakilde}.")

    except Exception as e:
        st.error(f"Fejl ved datahentning: {e}")

if __name__ == "__main__":
    vis_side()
