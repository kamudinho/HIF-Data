import streamlit as st
import pandas as pd
# Vi importerer din forbindelses-funktion direkte herinde
from data.data_load import _get_snowflake_conn

def vis_side():
    """
    Henter selv session og holdnavn, så kaldet fra HIF_dash.py kan forblive simpelt.
    """
    # 1. Hent Snowflake-forbindelsen
    try:
        session = _get_snowflake_conn()
    except Exception as e:
        st.error(f"Kunne ikke oprette forbindelse til Snowflake: {e}")
        return

    # 2. Find det valgte hold fra session_state
    # Jeg antager, at dit valgte hold gemmes i st.session_state["valgt_hold"] 
    # eller en lignende variabel fra din sidebar/menu.
    valgt_hold_navn = st.session_state.get("valgt_hold", "Hvidovre")

    # 3. Hent hold-info (Logo og ID)
    team_info_query = f"""
        SELECT team_wyid, imagedataurl 
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMS 
        WHERE teamname = '{valgt_hold_navn}' 
        LIMIT 1
    """
    
    try:
        team_data = session.sql(team_info_query).to_pandas()
        if team_data.empty:
            st.warning(f"Holdet '{valgt_hold_navn}' blev ikke fundet.")
            return

        wyid = team_data.iloc[0]['TEAM_WYID']
        logo_url = team_data.iloc[0]['IMAGEDATAURL']

        # 4. Hent Top 5 spillere baseret på distance
        # Vi joiner direkte på optaId for at koble SS og Wyscout
        query = f"""
        SELECT 
            s.PLAYER_NAME,
            AVG(s.DISTANCE) as DIST, 
            AVG(s."HIGH SPEED RUNNING") as HSR, 
            MAX(s.TOP_SPEED) as SPEED,
            MAX(w.IMAGEDATAURL) as PLAYER_IMG
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS s
        JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS w ON s.optaId = w.OPTAID
        WHERE w.CURRENTTEAM_WYID = {wyid}
        AND s.MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'
        GROUP BY s.PLAYER_NAME
        ORDER BY DIST DESC
        LIMIT 5
        """
        
        df = session.sql(query).to_pandas()

        # --- VISNING ---
        col_header1, col_header2 = st.columns([1, 5])
        with col_header1:
            st.image(logo_url, width=80)
        with col_header2:
            st.subheader(f"Top 5: Fysiske Profiler")

        if not df.empty:
            max_dist = df['DIST'].max()

            for _, row in df.iterrows():
                dist_km = row['DIST'] / 1000
                # Skalering af bar
                val = (row['DIST'] / max_dist) * 100
                
                c1, c2 = st.columns([1, 4])
                with c1:
                    st.image(row['PLAYER_IMG'] if row['PLAYER_IMG'] else "https://via.placeholder.com/150", width=70)
                with c2:
                    st.markdown(f"**{row['PLAYER_NAME']}**")
                    # Den røde bar
                    st.markdown(f"""
                        <div style="background:#333; width:100%; height:8px; border-radius:5px;">
                            <div style="background:#df003b; width:{val}%; height:8px; border-radius:5px;"></div>
                        </div>
                    """, unsafe_allow_html=True)
                    st.caption(f"{dist_km:.2f} km gns.  |  {int(row['HSR'])}m HSR  |  {row['SPEED']} km/t max")
                    st.write("")
        else:
            st.info("Ingen fysiske data fundet for dette hold i den valgte periode.")

    except Exception as e:
        st.error(f"Fejl ved hentning af data: {e}")
