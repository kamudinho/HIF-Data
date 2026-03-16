import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAM_COLORS

def vis_side(conn, name_map=None):
    if name_map is None:
        name_map = {}
    
    st.title("🏃 Fysisk Data (Second Spectrum)")

    # 1. Hent alle tilgængelige kampe fra Metadata-tabellen
    # 1. Hent alle tilgængelige kampe fra Metadata-tabellen
    @st.cache_data(ttl=600)
    def get_physical_matches():
        # Vi bruger her de mest gængse kolonnenavne for SS metadata
        query = """
        SELECT 
            MATCH_OPTAUUID, 
            MATCH_SSIID, 
            CONTESTANTHOME_NAME as HOME_NAME, 
            CONTESTANTAWAY_NAME as AWAY_NAME, 
            GAME_DATE as DATE_TIME 
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA
        ORDER BY GAME_DATE DESC
        """
        return conn.query(query)
        
    df_matches = get_physical_matches()

    if df_matches.empty:
        st.warning("Ingen fysiske metadata fundet i Snowflake.")
        return

    # 2. Kampvælger
    df_matches['label'] = df_matches['DATE_TIME'].astype(str) + ": " + df_matches['HOME_NAME'] + " vs " + df_matches['AWAY_NAME']
    valgt_label = st.selectbox("Vælg kamp:", df_matches['label'].tolist())
    match_row = df_matches[df_matches['label'] == valgt_label].iloc[0]
    
    valgt_ssiid = match_row['MATCH_SSIID']
    h_name = match_row['HOME_NAME']
    a_name = match_row['AWAY_NAME']

    # 3. Hent fysisk data for den valgte kamp
    @st.cache_data(ttl=600)
    def get_player_data(ssiid):
        query = f"""
        SELECT 
            PLAYER_SSIID,
            PLAYER_NAME as RAW_NAME,
            TEAM_NAME,
            DISTANCE,
            TOP_SPEED,
            AVERAGE_SPEED,
            SPRINTS
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
    df_fys['PLAYER_NAME'] = df_fys['PLAYER_SSIID'].map(name_map).fillna(df_fys['RAW_NAME'])

    # 5. Hold-vælger
    st.write("---")
    valgt_hold = st.radio("Vælg hold:", [h_name, a_name], horizontal=True)
    
    # Farve-streg baseret på team_mapping.py
    color = TEAM_COLORS.get(valgt_hold, {}).get("primary", "#555555")
    st.markdown(f'<div style="height: 5px; background-color: {color}; border-radius: 5px; margin-bottom: 20px;"></div>', unsafe_allow_html=True)

    df_display = df_fys[df_fys['TEAM_NAME'] == valgt_hold].copy()

    if not df_display.empty:
        # Top-stats række
        c1, c2, c3 = st.columns(3)
        top_dist = df_display.loc[df_display['DISTANCE'].idxmax()]
        top_speed = df_display.loc[df_display['TOP_SPEED'].idxmax()]
        
        c1.metric("Mest løbende", top_dist['PLAYER_NAME'], f"{top_dist['DISTANCE']/1000:.2f} km")
        c2.metric("Topfart", top_speed['PLAYER_NAME'], f"{top_speed['TOP_SPEED']:.1f} km/h")
        c3.metric("Total Sprints", int(df_display['SPRINTS'].sum()))

        # Tabelvisning
        st.dataframe(
            df_display[['PLAYER_NAME', 'DISTANCE', 'TOP_SPEED', 'SPRINTS', 'AVERAGE_SPEED']].sort_values('DISTANCE', ascending=False),
            column_config={
                "PLAYER_NAME": "Spiller",
                "DISTANCE": st.column_config.NumberColumn("Distance (m)", format="%.0f"),
                "TOP_SPEED": st.column_config.NumberColumn("Topfart (km/h)", format="%.1f"),
                "AVERAGE_SPEED": st.column_config.NumberColumn("Gns. Fart (km/h)", format="%.1f"),
                "SPRINTS": "Sprints"
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.error(f"Kunne ikke finde data for {valgt_hold}. Tjek om holdnavnet i databasen matcher '{valgt_hold}'.")
