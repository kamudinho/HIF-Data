import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn

def vis_side():
    """
    Funktion der selv håndterer session og hold-valg.
    Kaldes fra HIF_dash.py uden argumenter.
    """
    
    # 1. Hent Snowflake-forbindelsen automatisk
    try:
        session = _get_snowflake_conn()
    except Exception as e:
        st.error(f"Kunne ikke oprette forbindelse til data: {e}")
        return

    # 2. Find det hold, brugeren har valgt i din sidebar/menu
    # Jeg bruger 'valgt_hold' som standard, da det er mest udbredt i din kode
    hold_navn = st.session_state.get("valgt_hold", "Hvidovre")

    # 3. SQL: Find holdets ID og Logo, og find derefter spillernes fysiske data
    # Vi joiner SS data med Wyscout data via optaId
    query = f"""
    WITH TEAM_INFO AS (
        SELECT team_wyid, imagedataurl 
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMS 
        WHERE teamname = '{hold_navn}' 
        LIMIT 1
    )
    SELECT 
        s.PLAYER_NAME,
        AVG(s.DISTANCE) as DIST, 
        AVG(s."HIGH SPEED RUNNING") as HSR, 
        MAX(s.TOP_SPEED) as SPEED,
        MAX(w.IMAGEDATAURL) as PLAYER_IMG,
        (SELECT imagedataurl FROM TEAM_INFO) as TEAM_LOGO
    FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS s
    JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS w ON s.optaId = w.OPTAID
    WHERE w.CURRENTTEAM_WYID = (SELECT team_wyid FROM TEAM_INFO)
    AND s.MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'
    GROUP BY s.PLAYER_NAME
    ORDER BY DIST DESC
    LIMIT 5
    """

    try:
        df = session.sql(query).to_pandas()

        if not df.empty:
            # Vis logo og overskrift
            logo_col, title_col = st.columns([1, 5])
            with logo_col:
                st.image(df['TEAM_LOGO'].iloc[0], width=80)
            with title_col:
                st.subheader(f"Top 5: Fysiske Profiler ({hold_navn})")

            max_dist = df['DIST'].max()

            # Vis spillerne
            for _, row in df.iterrows():
                c1, c2 = st.columns([1, 4])
                with c1:
                    # Håndter manglende billeder
                    img = row['PLAYER_IMG'] if row['PLAYER_IMG'] else "https://via.placeholder.com/150"
                    st.image(img, width=80)
                with c2:
                    st.markdown(f"**{row['PLAYER_NAME']}**")
                    
                    # Lav den røde bar
                    val = (row['DIST'] / max_dist) * 100
                    st.markdown(f"""
                        <div style="background:#333; width:100%; height:10px; border-radius:5px; margin-bottom:5px;">
                            <div style="background:#df003b; width:{val}%; height:10px; border-radius:5px;"></div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Stats
                    dist_km = row['DIST'] / 1000
                    st.caption(f"{dist_km:.2f} km gns. | {int(row['HSR'])}m HSR | {row['SPEED']} km/t max")
                    st.write("")
        else:
            st.info(f"Ingen fysiske data fundet for {hold_navn}.")

    except Exception as e:
        st.error(f"Fejl ved hentning af data: {e}")
