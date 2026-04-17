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

    # --- Layout & Styling ---
    st.markdown("""
        <style>
        .category-header { font-weight: bold; font-size: 1.1rem; padding: 12px 0 5px 0; color: #111; border-bottom: 2px solid #eee; margin-top: 15px; }
        .metric-label { font-size: 0.85rem; color: #444; display: flex; align-items: center; height: 35px; }
        .rank-container { position: relative; background-color: #f0f0f0; height: 30px; width: 100%; border-radius: 4px; overflow: hidden; display: flex; align-items: center; margin-bottom: 4px; }
        .rank-fill { height: 100%; display: flex; align-items: center; padding-left: 10px; font-weight: bold; color: black; font-size: 0.75rem; }
        .player-card { text-align: center; padding-bottom: 10px; }
        .player-img-round { border-radius: 50%; object-fit: cover; border: 3px solid #f0f2f6; background-color: white; }
        .player-name-text { font-size: 0.8rem; font-weight: bold; color: #111; display: block; margin-top: 5px; height: 35px; }
        </style>
    """, unsafe_allow_html=True)

    # --- Navigation ---
    st.title("Unified Performance Hub 2026")
    
    col1, col2 = st.columns([2, 2])
    with col1:
        valgt_hold = st.selectbox("Vælg hold:", list(TEAMS.keys()))
        target_wyid = TEAMS[valgt_hold]["team_wyid"]
    
    with col2:
        visning = st.radio("Vælg fokusområde:", ["Teknisk (OPTA)", "Fysisk (SS)"], horizontal=True)

    # --- Unified SQL Query ---
    # Vi bygger én stor query der mapper Wyscout -> Opta -> Second Spectrum
    query = f"""
    WITH TEAM_IDS AS (
        SELECT CONTESTANT_OPTAUUID 
        FROM KLUB_HVIDOVREIF.AXIS.OPTA_TEAMS 
        WHERE NAME = '{valgt_hold}' OR OFFICIALNAME = '{valgt_hold}' LIMIT 1
    ),
    WYS_BASE AS (
        SELECT 
            (TRIM(FIRSTNAME) || ' ' || TRIM(LASTNAME)) as FULL_NAME,
            SHORTNAME,
            PLAYER_WYID,
            MAX(IMAGEDATAURL) as IMG
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS 
        WHERE CURRENTTEAM_WYID = {target_wyid}
        GROUP BY 1, 2, 3
    ),
    OPTA_CORE AS (
        SELECT 
            p.PLAYER_OPTAUUID,
            p.MATCH_NAME as OPTA_NAME,
            COUNT(CASE WHEN e.EVENT_TYPEID = 16 THEN 1 END) as GOALS,
            COUNT(CASE WHEN e.EVENT_TYPEID = 1 AND e.EVENT_OUTCOME = 1 THEN 1 END) as PASSES,
            COUNT(CASE WHEN e.EVENT_TYPEID = 15 THEN 1 END) as TACKLES
        FROM KLUB_HVIDOVREIF.AXIS.OPTA_PLAYERS p
        LEFT JOIN KLUB_HVIDOVREIF.AXIS.OPTA_EVENTS e ON p.PLAYER_OPTAUUID = e.PLAYER_OPTAUUID
        WHERE e.DATE >= '2026-01-01'
          AND e.EVENT_CONTESTANT_OPTAUUID = (SELECT CONTESTANT_OPTAUUID FROM TEAM_IDS)
        GROUP BY 1, 2
    ),
    SS_CORE AS (
        SELECT 
            PLAYER_NAME as SS_NAME,
            "optaId" as SS_OPTAID,
            AVG(DISTANCE) as DIST,
            AVG("HIGH SPEED RUNNING") as HSR,
            MAX(TOP_SPEED) as VMAX
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_DATE >= '2026-01-01'
          AND MATCH_TEAMS LIKE '%{valgt_hold}%'
        GROUP BY 1, 2
    ),
    FINAL_JOIN AS (
        SELECT 
            w.*,
            o.GOALS, o.PASSES, o.TACKLES,
            s.DIST, s.HSR, s.VMAX,
            RANK() OVER (ORDER BY o.GOALS DESC NULLS LAST) as GOAL_RANK,
            RANK() OVER (ORDER BY o.PASSES DESC NULLS LAST) as PASS_RANK,
            RANK() OVER (ORDER BY o.TACKLES DESC NULLS LAST) as TACK_RANK,
            RANK() OVER (ORDER BY s.DIST DESC NULLS LAST) as DIST_RANK,
            RANK() OVER (ORDER BY s.HSR DESC NULLS LAST) as HSR_RANK,
            RANK() OVER (ORDER BY s.VMAX DESC NULLS LAST) as VMAX_RANK
        FROM WYS_BASE w
        LEFT JOIN OPTA_CORE o ON (o.PLAYER_OPTAUUID = w.PLAYER_WYID OR w.FULL_NAME LIKE '%' || o.OPTA_NAME || '%')
        LEFT JOIN SS_CORE s ON (s.SS_OPTAID = w.PLAYER_WYID OR s.SS_NAME = w.FULL_NAME OR s.SS_NAME = w.SHORTNAME)
    )
    SELECT * FROM FINAL_JOIN 
    WHERE (GOALS IS NOT NULL OR DIST IS NOT NULL)
    QUALIFY ROW_NUMBER() OVER (PARTITION BY FULL_NAME ORDER BY PASSES DESC NULLS LAST) = 1
    ORDER BY PASSES DESC NULLS LAST
    LIMIT 6
    """

    try:
        df = pd.read_sql(query, conn)
        
        if not df.empty:
            # --- Spiller række ---
            cols = st.columns([2.5, 1, 1, 1, 1, 1, 1])
            for i, (_, row) in enumerate(df.iterrows()):
                with cols[i+1]:
                    img = row['IMG'] if row['IMG'] else "https://via.placeholder.com/150"
                    st.markdown(f"""
                        <div class="player-card">
                            <img src="{img}" class="player-img-round" width="65" height="65">
                            <span class="player-name-text">{row['FULL_NAME']}</span>
                        </div>
                    """, unsafe_allow_html=True)

            # --- Metrics ---
            if visning == "Teknisk (OPTA)":
                cats = {
                    "Afslutningsspil": [("Mål", "GOAL_RANK")],
                    "Opspil": [("Succesf. Afleveringer", "PASS_RANK")],
                    "Nærkampe": [("Vundne Tacklinger", "TACK_RANK")]
                }
            else:
                cats = {
                    "Udholdenhed": [("Total Distance", "DIST_RANK")],
                    "Intensitet": [("Højintakt løb (HSR)", "HSR_RANK")],
                    "Explosivitet": [("Topfart (km/t)", "VMAX_RANK")]
                }

            for kat_navn, metrics in cats.items():
                st.markdown(f'<div class="category-header">{kat_navn}</div>', unsafe_allow_html=True)
                for label, r_col in metrics:
                    m_cols = st.columns([2.5, 1, 1, 1, 1, 1, 1])
                    with m_cols[0]: st.markdown(f'<div class="metric-label">{label}</div>', unsafe_allow_html=True)
                    
                    for i, (_, row) in enumerate(df.iterrows()):
                        rank = int(row[r_col]) if pd.notnull(row[r_col]) else 999
                        color = "#22c55e" if rank <= 30 else "#facc15" if rank <= 100 else "#fca5a5"
                        width = max(10, (1 - (rank / 400)) * 100) if rank <= 400 else 5
                        
                        with m_cols[i+1]:
                            st.markdown(f'<div class="rank-container"><div class="rank-fill" style="width:{width}%; background-color:{color};">R {rank}</div></div>', unsafe_allow_html=True)
        else:
            st.warning("Ingen kombinerede data fundet for dette hold i 2026.")

    except Exception as e:
        st.error(f"Systemfejl: {e}")

if __name__ == "__main__":
    vis_side()
