import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAM_COLORS

# Hvidovre Opta UUID fundet i din metadata
HIF_OPTA_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

def vis_side(conn, name_map=None):
    if name_map is None:
        name_map = {}

    st.title("🏃 Hvidovre IF | Fysisk Data")

    # 1. Hent kampe baseret på Hvidovres Opta UUID
    @st.cache_data(ttl=600)
    def get_hif_matches():
        query = f"""
        SELECT DISTINCT
            m.MATCH_SSIID, 
            COALESCE(s.MATCH_TEAMS, 'Kamp ' || m.MATCH_SSIID) as MATCH_TEAMS, 
            m.STARTTIME as DATE_TIME,
            m.HOME_SSIID,
            m.AWAY_SSIID,
            m.HOMEOPTA_UUID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA m
        LEFT JOIN (SELECT DISTINCT MATCH_SSIID, MATCH_TEAMS FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS) s
            ON m.MATCH_SSIID = s.MATCH_SSIID
        WHERE m.HOMEOPTA_UUID = '{HIF_OPTA_UUID}' 
           OR m.AWAY_OPTAUUID = '{HIF_OPTA_UUID}'
        ORDER BY m.STARTTIME DESC
        """
        return conn.query(query)

    df_matches = get_hif_matches()

    if df_matches.empty:
        st.warning("Ingen fysiske data fundet for Hvidovre IF via UUID.")
        return

    # 2. Kampvælger
    # Vi laver en pæn label med dato og hold
    df_matches['DROPDOWN_LABEL'] = df_matches['DATE_TIME'].dt.strftime('%d/%m-%Y') + ": " + df_matches['MATCH_TEAMS']
    
    valgt_label = st.selectbox("Vælg kamp:", df_matches['DROPDOWN_LABEL'].unique())
    match_row = df_matches[df_matches['DROPDOWN_LABEL'] == valgt_label].iloc[0]
    valgt_ssiid = match_row['MATCH_SSIID']

    # 3. Hent fysisk data for den valgte kamp
    @st.cache_data(ttl=600)
    def get_player_data(ssiid):
        query = f"""
        SELECT 
            PLAYER_SSIID, PLAYER_NAME, TEAM_SSIID,
            DISTANCE, TOP_SPEED, AVERAGE_SPEED, SPRINTS
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER
        WHERE MATCH_SSIID = '{ssiid}'
        AND DISTANCE > 0
        """
        return conn.query(query)

    df_fys = get_player_data(valgt_ssiid)

    if df_fys.empty:
        st.info("Ingen spiller-data fundet for denne kamp.")
        return

    # 4. Navne-mapning
    df_fys['DISPLAY_NAME'] = df_fys['PLAYER_SSIID'].map(name_map).fillna(df_fys['PLAYER_NAME'])

    # 5. Hold-vælger (Sætter automatisk Hvidovre som standard)
    # Find Hvidovres SSIID for denne specifikke kamp
    hif_ssiid = match_row['HOME_SSIID'] if match_row['HOMEOPTA_UUID'] == HIF_OPTA_UUID else match_row['AWAY_SSIID']
    
    teams = df_fys['TEAM_SSIID'].unique().tolist()
    
    # Sørg for at Hvidovre er default i radio-knappen
    try:
        default_idx = teams.index(hif_ssiid)
    except ValueError:
        default_idx = 0

    st.write("---")
    valgt_hold_ssiid = st.radio("Vælg hold:", teams, index=default_idx, horizontal=True, 
                                format_func=lambda x: "Hvidovre IF" if x == hif_ssiid else f"Modstander ({x[:8]})")
    
    df_display = df_fys[df_fys['TEAM_SSIID'] == valgt_hold_ssiid].copy()

    # 6. Visning
    if not df_display.empty:
        c1, c2, c3 = st.columns(3)
        
        # Beregn top-performers
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
