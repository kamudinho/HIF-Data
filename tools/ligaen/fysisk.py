import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAM_COLORS

def vis_side(conn, name_map=None):
    if name_map is None:
        name_map = {}

    st.title("🏃 Fysisk Data (Second Spectrum)")

    # 1. Hent kampe - Vi bruger PHYSICAL_SUMMARY tabellen til at få team-navne
    @st.cache_data(ttl=600)
    def get_physical_matches():
        query = """
        SELECT DISTINCT
            MATCH_SSIID, 
            MATCH_TEAMS, 
            MATCH_DATE as DATE_TIME
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        ORDER BY MATCH_DATE DESC
        """
        return conn.query(query)

    df_matches = get_physical_matches()

    if df_matches.empty:
        st.warning("Ingen fysiske metadata fundet.")
        return

    # 2. Kampvælger
    # MATCH_TEAMS indeholder ofte "Hold A vs Hold B"
    valgt_label = st.selectbox("Vælg kamp:", df_matches['MATCH_TEAMS'].unique())
    match_row = df_matches[df_matches['MATCH_TEAMS'] == valgt_label].iloc[0]
    valgt_ssiid = match_row['MATCH_SSIID']

    # 3. Hent fysisk data (fra F53A tabellen som har de detaljerede tal)
    @st.cache_data(ttl=600)
    def get_physical_matches():
        # Vi henter alle kampe der findes i de fysiske tabeller
        # uanset om det er Superliga eller NordicBet
        query = """
        SELECT DISTINCT
            MATCH_SSIID, 
            MATCH_TEAMS, 
            MATCH_DATE as DATE_TIME
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_DATE >= '2025-07-01'  -- Sikrer vi ser den nuværende sæson 25/26
        ORDER BY MATCH_DATE DESC
        """
        return conn.query(query)

    df_fys = get_player_data(valgt_ssiid)

    if df_fys.empty:
        st.info("Ingen spiller-data fundet for denne kamp.")
        return

    # 4. Navne-mapning (SSIID -> Navn fra din CSV)
    df_fys['DISPLAY_NAME'] = df_fys['PLAYER_SSIID'].map(name_map).fillna(df_fys['PLAYER_NAME'])

    # 5. Hold-vælger
    teams = df_fys['TEAM_SSIID'].unique()
    st.write("---")
    valgt_hold_ssiid = st.radio("Vælg hold (SSIID):", teams, horizontal=True)
    
    df_display = df_fys[df_fys['TEAM_SSIID'] == valgt_hold_ssiid].copy()

    # Visning
    if not df_display.empty:
        c1, c2, c3 = st.columns(3)
        top_dist = df_display.loc[df_display['DISTANCE'].idxmax()]
        top_speed = df_display.loc[df_display['TOP_SPEED'].idxmax()]
        
        c1.metric("Mest løbende", top_dist['DISPLAY_NAME'], f"{top_dist['DISTANCE']/1000:.2f} km")
        c2.metric("Topfart", top_speed['DISPLAY_NAME'], f"{top_speed['TOP_SPEED']:.1f} km/h")
        c3.metric("Total Sprints", int(df_display['SPRINTS'].sum()))

        st.dataframe(
            df_display[['DISPLAY_NAME', 'DISTANCE', 'TOP_SPEED', 'SPRINTS', 'AVERAGE_SPEED']].sort_values('DISTANCE', ascending=False),
            column_config={
                "DISPLAY_NAME": "Spiller",
                "DISTANCE": st.column_config.NumberColumn("Distance (m)", format="%.0f"),
                "TOP_SPEED": st.column_config.NumberColumn("Topfart (km/h)", format="%.1f"),
                "AVERAGE_SPEED": st.column_config.NumberColumn("Gns. Fart (km/h)", format="%.1f"),
                "SPRINTS": "Sprints"
            },
            use_container_width=True,
            hide_index=True
        )
