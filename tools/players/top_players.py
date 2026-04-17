import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

def load_player_overrides():
    try:
        df_overrides = pd.read_csv("data/player_overrides.csv")
        overrides = {}
        for _, row in df_overrides.iterrows():
            spiller = row['PLAYER_NAME'].strip()
            klub_navn = row['TEAM_NAME'].strip()
            if klub_navn in TEAMS:
                overrides[spiller] = TEAMS[klub_navn]["team_wyid"]
        return overrides
    except:
        return {}

def vis_side():
    try:
        conn = _get_snowflake_conn()
    except Exception as e:
        st.error(f"Forbindelsesfejl: {e}")
        return

    player_overrides = load_player_overrides()

    # --- TOP BAR ---
    col1, col2 = st.columns([2, 2])
    with col1:
        valgt_navn = st.selectbox("Vælg hold:", list(TEAMS.keys()), key="phys_tech_rank")
        target_wyid = TEAMS[valgt_navn]["team_wyid"]
        target_opta_uuid = TEAMS[valgt_navn]["opta_uuid"]
    with col2:
        mode = st.radio("Vælg data-visning:", ["Fysiske Data", "Tekniske Data (Opta)"], horizontal=True)

    # --- SQL LOGIK ---
    if mode == "Fysiske Data":
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
            SELECT (TRIM(FIRSTNAME) || ' ' || TRIM(LASTNAME)) as FULL_NAME, MAX(IMAGEDATAURL) as IMG
            FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS WHERE CURRENTTEAM_WYID = {target_wyid} GROUP BY 1
        )
        SELECT t.IMG, t.FULL_NAME as WYS_NAME, r.* FROM VALGT_TRUP t
        INNER JOIN LIGA_RANKED r ON (t.FULL_NAME LIKE '%' || r.PLAYER_NAME || '%' OR r.PLAYER_NAME LIKE '%' || t.FULL_NAME || '%')
        """
        metrics_labels = {
            "Volume": [("Total Distance", "M1_RANK", "M1", "km"), ("Running Distance", "M2_RANK", "M2", "km")],
            "Intensity": [("Hi Distance", "M3_RANK", "M3", "m"), ("Sprint Distance", "M4_RANK", "M4", "m")],
            "Explosive": [("Top Speed", "M5_RANK", "M5", "km/t"), ("Accelerations", "M6_RANK", "M6", "stk")]
        }
    else:
        query = f"""
        WITH PLAYER_XG AS (
            SELECT PLAYER_OPTAUUID,
                AVG(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_VALUE END) as AVG_XG,
                AVG(CASE WHEN STAT_TYPE = 'goals' THEN STAT_VALUE END) as AVG_GOALS
            FROM KLUB_HVIDOVREIF.AXIS.OPTA_MATCHEXPECTEDGOALS
            WHERE MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'
            GROUP BY PLAYER_OPTAUUID
        ),
        LIGA_RANKED AS (
            SELECT p.MATCH_NAME as PLAYER_NAME,
                x.AVG_XG as M1, x.AVG_GOALS as M2, x.AVG_XG as M3, x.AVG_GOALS as M4, x.AVG_XG as M5, x.AVG_GOALS as M6,
                RANK() OVER (ORDER BY x.AVG_XG DESC) as M1_RANK,
                RANK() OVER (ORDER BY x.AVG_GOALS DESC) as M2_RANK,
                RANK() OVER (ORDER BY x.AVG_XG DESC) as M3_RANK,
                RANK() OVER (ORDER BY x.AVG_GOALS DESC) as M4_RANK,
                RANK() OVER (ORDER BY x.AVG_XG DESC) as M5_RANK,
                RANK() OVER (ORDER BY x.AVG_GOALS DESC) as M6_RANK
            FROM PLAYER_XG x
            JOIN KLUB_HVIDOVREIF.AXIS.OPTA_PLAYERS p ON x.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
        ),
        VALGT_TRUP AS (
            SELECT (TRIM(FIRSTNAME) || ' ' || TRIM(LASTNAME)) as FULL_NAME, MAX(IMAGEDATAURL) as IMG
            FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS WHERE CURRENTTEAM_WYID = {target_wyid} GROUP BY 1
        )
        SELECT t.IMG, t.FULL_NAME as WYS_NAME, r.* FROM VALGT_TRUP t
        INNER JOIN LIGA_RANKED r ON (t.FULL_NAME LIKE '%' || r.PLAYER_NAME || '%' OR r.PLAYER_NAME LIKE '%' || t.FULL_NAME || '%')
        """
        metrics_labels = {
            "Attacking": [("xG", "M1_RANK", "M1", "xG"), ("Goals", "M2_RANK", "M2", "stk")],
            "Efficiency": [("Conv.", "M5_RANK", "M5", "%")]
        }

    # --- RENDER LOGIK ---
    try:
        df = pd.read_sql(query, conn)
        if not df.empty:
            if player_overrides:
                df = df[df.apply(lambda row: player_overrides.get(row['WYS_NAME'], target_wyid) == target_wyid, axis=1)]
            
            df = df.sort_values("M1_RANK").head(5)
            
            st.write("---")
            # Header række med billeder
            cols = st.columns([2.5, 1, 1, 1, 1, 1])
            for i, (_, row) in enumerate(df.iterrows()):
                with cols[i+1]:
                    img = row['IMG'] if row['IMG'] and str(row['IMG']) != 'None' else "https://cdn.wyscout.com/photos/players/public/ndplayer_100x130.png"
                    st.markdown(f'<div style="text-align:center"><img src="{img}" style="border-radius:50%" width="60"><br><small><b>{row["PLAYER_NAME"].split()[-1]}</b></small></div>', unsafe_allow_html=True)

            # Rækker med Metrics og Bars
            for kat, metrics in metrics_labels.items():
                st.markdown(f'<br><b>{kat}</b>', unsafe_allow_html=True)
                for label, rank_col, val_col, unit in metrics:
                    m_cols = st.columns([2.5, 1, 1, 1, 1, 1])
                    m_cols[0].caption(label)
                    
                    for i, (_, row) in enumerate(df.iterrows()):
                        rank = int(row[rank_col])
                        raw_val = row[val_col]
                        
                        # Farve baseret på rank
                        if rank <= 20: color = "#22c55e"
                        elif rank <= 50: color = "#facc15"
                        else: color = "#ef4444"
                        
                        # Formatering af tal (f.eks. 10.22 km)
                        val_str = f"{raw_val:.2f}" if isinstance(raw_val, float) else str(raw_val)
                        
                        # Render Bar med Rank og (Værdi)
                        m_cols[i+1].markdown(
                            f'''
                            <div style="background-color: #f0f2f6; border-radius: 4px; width: 100%; position: relative; height: 24px; margin-bottom: 2px;">
                                <div style="background-color: {color}; width: {max(5, 100 - (rank/5))}%; height: 100%; border-radius: 4px; display: flex; align-items: center; justify-content: center;">
                                    <span style="color: black; font-size: 10px; font-weight: bold; white-space: nowrap; padding: 0 5px;">
                                        R {rank} ({val_str} {unit})
                                    </span>
                                </div>
                            </div>
                            ''', 
                            unsafe_allow_html=True
                        )
    except Exception as e:
        st.error(f"Fejl: {e}")

vis_side()
