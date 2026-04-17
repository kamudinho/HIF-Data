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

    # --- TOP BAR ---
    col1, col2 = st.columns([2, 2])
    with col1:
        valgt_navn = st.selectbox(
            "Vælg hold:", 
            list(TEAMS.keys()), 
            key="sb_top5_final_v4" 
        )
        target_wyid = TEAMS[valgt_navn]["team_wyid"]
        
    with col2:
        mode = st.radio(
            "Vælg data-visning:", 
            ["Fysiske Data (P90)", "Tekniske Data (P90)"], 
            horizontal=True,
            key="radio_top5_final_v4"
        )

    # --- MANUELT NAVNE-FILTER (Kolding-specifikt) ---
    # Vi fjerner dem fra Kolding (7482)
    exclusion_sql = ""
    if valgt_navn == "Kolding IF":
        exclusion_sql = """
            AND (TRIM(FIRSTNAME) || ' ' || TRIM(LASTNAME)) NOT LIKE '%Enemark%'
            AND (TRIM(FIRSTNAME) || ' ' || TRIM(LASTNAME)) NOT LIKE '%Westh%'
        """

    if "Fysiske Data" in mode:
        query = f"""
        WITH LIGA_STATS AS (
            SELECT PLAYER_NAME, 
                AVG(DISTANCE) as M1, AVG(RUNNING) as M2, AVG("HIGH SPEED RUNNING") as M3,
                AVG(SPRINTING) as M4, MAX(TOP_SPEED) as M5, AVG(NO_OF_HIGH_INTENSITY_RUNS) as M6
            FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
            WHERE MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'
            GROUP BY PLAYER_NAME
        ),
        LIGA_RANKED AS (
            SELECT *,
                RANK() OVER (ORDER BY M1 DESC) as M1_RANK, RANK() OVER (ORDER BY M2 DESC) as M2_RANK,
                RANK() OVER (ORDER BY M3 DESC) as M3_RANK, RANK() OVER (ORDER BY M4 DESC) as M4_RANK,
                RANK() OVER (ORDER BY M5 DESC) as M5_RANK, RANK() OVER (ORDER BY M6 DESC) as M6_RANK
            FROM LIGA_STATS
        ),
        VALGT_TRUP AS (
            SELECT 
                (TRIM(FIRSTNAME) || ' ' || TRIM(LASTNAME)) as FULL_NAME, 
                MAX(IMAGEDATAURL) as IMG
            FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS 
            WHERE CURRENTTEAM_WYID = {target_wyid}
            {exclusion_sql}
            GROUP BY 1
        )
        SELECT t.IMG, t.FULL_NAME as WYS_NAME, r.* FROM VALGT_TRUP t
        INNER JOIN LIGA_RANKED r ON (t.FULL_NAME LIKE '%' || r.PLAYER_NAME || '%' OR r.PLAYER_NAME LIKE '%' || t.FULL_NAME || '%')
        """
        metrics_labels = {
            "Volume (P90)": [("Total Dist.", "M1_RANK", "M1"), ("Running", "M2_RANK", "M2")],
            "Intensity (P90)": [("Hi Dist.", "M3_RANK", "M3"), ("Sprints", "M4_RANK", "M4")],
            "Top Speed": [("Max Speed", "M5_RANK", "M5")]
        }
    else:
        query = f"""
        WITH PLAYER_STATS AS (
            SELECT PLAYER_OPTAUUID,
                AVG(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_VALUE END) as AVG_XG,
                AVG(CASE WHEN STAT_TYPE = 'goals' THEN STAT_VALUE END) as AVG_GOALS
            FROM KLUB_HVIDOVREIF.AXIS.OPTA_MATCHEXPECTEDGOALS
            WHERE MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'
            GROUP BY PLAYER_OPTAUUID
        ),
        LIGA_RANKED AS (
            SELECT p.MATCH_NAME as PLAYER_NAME, s.AVG_XG as M1, s.AVG_GOALS as M2,
                RANK() OVER (ORDER BY s.AVG_XG DESC) as M1_RANK,
                RANK() OVER (ORDER BY s.AVG_GOALS DESC) as M2_RANK
            FROM PLAYER_STATS s
            JOIN KLUB_HVIDOVREIF.AXIS.OPTA_PLAYERS p ON s.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
        ),
        VALGT_TRUP AS (
            SELECT 
                (TRIM(FIRSTNAME) || ' ' || TRIM(LASTNAME)) as FULL_NAME, 
                MAX(IMAGEDATAURL) as IMG
            FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS 
            WHERE CURRENTTEAM_WYID = {target_wyid}
            {exclusion_sql}
            GROUP BY 1
        )
        SELECT t.IMG, t.FULL_NAME as WYS_NAME, r.* FROM VALGT_TRUP t
        INNER JOIN LIGA_RANKED r ON (t.FULL_NAME LIKE '%' || r.PLAYER_NAME || '%' OR r.PLAYER_NAME LIKE '%' || t.FULL_NAME || '%')
        """
        metrics_labels = {
            "Attacking (P90)": [("xG p90", "M1_RANK", "M1"), ("Mål p90", "M2_RANK", "M2")]
        }

    # --- RENDER ---
    try:
        df = pd.read_sql(query, conn)
        if not df.empty:
            df = df.sort_values("M1_RANK").head(5)
            
            st.write("---")
            cols = st.columns([2.5, 1, 1, 1, 1, 1])
            for i, (_, row) in enumerate(df.iterrows()):
                with cols[i+1]:
                    img = row['IMG'] if row['IMG'] and str(row['IMG']) != 'None' else "https://cdn.wyscout.com/photos/players/public/ndplayer_100x130.png"
                    st.markdown(f'''
                        <div style="text-align:center">
                            <img src="{img}" style="border-radius:50%; border: 1px solid #ddd;" width="65">
                            <div style="font-size: 11px; font-weight: bold; margin-top: 5px;">{row["WYS_NAME"].split()[-1]}</div>
                        </div>
                    ''', unsafe_allow_html=True)

            for kat, metrics in metrics_labels.items():
                st.markdown(f'<div style="margin-top:20px; font-weight:bold; font-size: 13px;">{kat}</div>', unsafe_allow_html=True)
                for label, rank_col, val_col in metrics:
                    m_cols = st.columns([2.5, 1, 1, 1, 1, 1])
                    m_cols[0].markdown(f'<div style="font-size: 11px; color: #666; padding-top: 4px;">{label}</div>', unsafe_allow_html=True)
                    
                    for i, (_, row) in enumerate(df.iterrows()):
                        rank = int(row[rank_col])
                        val = row[val_col]
                        val_str = f"{val:.2f}"
                        
                        color = "#22c55e" if rank <= 20 else "#facc15" if rank <= 50 else "#ef4444"
                        bar_width = max(35, 100 - (rank / 2.2)) 

                        m_cols[i+1].markdown(f"""
                            <div style="background-color: #f0f2f6; border-radius: 4px; width: 100%; height: 26px; position: relative; margin-top: 4px;">
                                <div style="background-color: {color}; width: {bar_width}%; height: 100%; border-radius: 4px; display: flex; align-items: center; padding-left: 5px; overflow: hidden;">
                                    <span style="color: black; font-size: 8.5px; font-weight: bold; white-space: nowrap;">
                                        R{rank} ({val_str})
                                    </span>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Fejl: {e}")

vis_side()
