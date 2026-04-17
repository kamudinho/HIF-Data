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

    # 1. HOLDVALG FRA DIN TEAM_MAPPING
    # Vi tager alle hold fra din fil
    liga_hold = list(TEAMS.keys())
    
    col_sel, _ = st.columns([2, 2])
    with col_sel:
        default_idx = liga_hold.index("Hvidovre") if "Hvidovre" in liga_hold else 0
        valgt_navn = st.selectbox("Vælg hold:", liga_hold, index=default_idx)
    
    # Hent ID og Logo direkte fra din mapping ordbog
    team_info = TEAMS[valgt_navn]
    target_wyid = team_info["team_wyid"]
    logo_url = team_info["logo"]

    # 2. SQL: Din velfungerende logik gjort dynamisk
    # Vi bruger target_wyid til at isolere truppen
    query = f"""
    WITH SELECTED_TRUP AS (
        SELECT 
            (TRIM(FIRSTNAME) || ' ' || TRIM(LASTNAME)) as FULL_NAME,
            SHORTNAME,
            PLAYER_WYID,
            MAX(IMAGEDATAURL) as IMG_URL
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS 
        WHERE CURRENTTEAM_WYID = {target_wyid}
        GROUP BY 1, 2, 3
    ),
    SS_PHYSICAL AS (
        SELECT 
            PLAYER_NAME,
            AVG(DISTANCE) as DIST, 
            AVG("HIGH SPEED RUNNING") as HSR, 
            MAX(TOP_SPEED) as SPEED, 
            AVG(NO_OF_HIGH_INTENSITY_RUNS) as ACCELS
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'
        GROUP BY PLAYER_NAME
    )
    SELECT 
        w.FULL_NAME,
        s.DIST,
        s.HSR,
        s.SPEED,
        s.ACCELS,
        COALESCE(w.IMG_URL, 'https://via.placeholder.com/150') as FINAL_IMAGE_URL
    FROM SELECTED_TRUP w
    INNER JOIN SS_PHYSICAL s ON (
        -- Din stærke navne-match logik
        s.PLAYER_NAME = w.FULL_NAME 
        OR s.PLAYER_NAME = w.SHORTNAME
        OR w.FULL_NAME LIKE '%' || s.PLAYER_NAME || '%'
        OR s.PLAYER_NAME LIKE '%' || w.SHORTNAME || '%'
    )
    ORDER BY s.DIST DESC 
    LIMIT 5
    """

    try:
        df = pd.read_sql(query, conn)
        df.columns = [x.upper() for x in df.columns]

        if not df.empty:
            st.write("---")
            c_logo, c_text = st.columns([1, 6])
            with c_logo:
                st.image(logo_url, width=80)
            with c_text:
                st.subheader(f"Top 5: Fysiske Profiler | {valgt_navn}")

            max_dist = df['DIST'].max()

            for _, row in df.iterrows():
                p1, p2 = st.columns([1, 5])
                with p1:
                    p_img = row['FINAL_IMAGE_URL']
                    if not p_img or str(p_img) == 'None' or "ndplayer" in str(p_img):
                        p_img = "https://via.placeholder.com/150"
                    st.image(p_img, width=70)
                with p2:
                    st.markdown(f"**{row['FULL_NAME']}**")
                    procent = (row['DIST'] / max_dist) * 100
                    st.markdown(f"""
                        <div style="background:#333; width:100%; height:12px; border-radius:6px;">
                            <div style="background:#df003b; width:{procent}%; height:12px; border-radius:6px;"></div>
                        </div>
                    """, unsafe_allow_html=True)
                    km = row['DIST'] / 1000
                    st.caption(f"{km:.2f} km | {int(row['HSR'])}m HSR | {row['SPEED']} km/t max")
                    st.write("")
        else:
            st.info(f"Ingen kampdata fundet for {valgt_navn} (WYID: {target_wyid}).")

    except Exception as e:
        st.error(f"Fejl ved datahentning: {e}")
