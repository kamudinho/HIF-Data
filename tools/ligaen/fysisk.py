import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

# Vi bruger SSID fra din team_mapping.py for Hvidovre
HIF_SSIID = TEAMS["Hvidovre"]["ssid"]

def vis_side(conn, name_map=None):
    """
    Kører uafhængigt og oversætter SSID via TEAMS fra team_mapping.py
    """
    if name_map is None: name_map = {}

    # --- TRIN 1: HENT KAMP-LISTE (METADATA) ---
    @st.cache_data(ttl=600)
    def get_matches():
        query = f"""
        SELECT 
            STARTTIME,
            MATCH_SSIID,
            HOME_SSIID,
            AWAY_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA
        WHERE (HOME_SSIID = '{HIF_SSIID}' OR AWAY_SSIID = '{HIF_SSIID}')
        ORDER BY STARTTIME DESC
        """
        return conn.query(query)

    df_meta = get_matches()

    if df_meta.empty:
        st.warning("⚠️ Ingen kamp-metadata fundet i systemet.")
        return

    # Oversæt modstanderens SSID ved hjælp af TEAMS fra team_mapping.py
    def get_opponent_name(row):
        opp_id = row['AWAY_SSIID'] if row['HOME_SSIID'] == HIF_SSIID else row['HOME_SSIID']
        
        # Løber gennem TEAMS mappingen
        for team_name, info in TEAMS.items():
            if info.get('ssid') == opp_id:
                return team_name
        return f"Ukendt ({opp_id[:5]})"

    # Forbered kamp-vælgeren
    df_meta['DATO'] = pd.to_datetime(df_meta['STARTTIME']).dt.strftime('%d/%m-%Y')
    df_meta['MODSTANDER'] = df_meta.apply(get_opponent_name, axis=1)
    df_meta['STED'] = df_meta.apply(lambda x: "Hjemme" if x['HOME_SSIID'] == HIF_SSIID else "Ude", axis=1)
    df_meta['DISPLAY_NAME'] = df_meta['DATO'] + " - " + df_meta['MODSTANDER'] + " (" + df_meta['STED'] + ")"

    valgt_label = st.selectbox("Vælg kamp til fysisk analyse:", df_meta['DISPLAY_NAME'])
    valgt_match = df_meta[df_meta['DISPLAY_NAME'] == valgt_label].iloc[0]

    # --- TRIN 2: HENT SPILLER-DATA (PHYSICAL_SUMMARY) ---
    @st.cache_data(ttl=600)
    def get_physical_stats(ssiid):
        query = f"""
        SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE TRIM(MATCH_SSIID) = '{ssiid}'
        """
        return conn.query(query)

    df_phys = get_physical_stats(valgt_match['MATCH_SSIID'])

    if df_phys.empty:
        st.info(f"ℹ️ Metadata fundet, men de detaljerede fysiske data er ikke indlæst endnu.")
        return

    # Opret HI_RUN (HSR + Sprint) og map spillernavne
    df_phys['HI_RUN'] = df_phys['HIGH SPEED RUNNING'] + df_phys['SPRINTING']
    df_phys['Spiller'] = df_phys['PLAYER_NAME']

    # --- TRIN 3: VISNING ---
    st.caption(f"Statistik: {valgt_label}")
    
    t1, t2, t3 = st.tabs(["Overblik", "Sprint & HI", "Besiddelse"])

    with t1:
        st.dataframe(
            df_phys[['Spiller', 'MINUTES', 'DISTANCE', 'HI_RUN', 'TOP_SPEED']].sort_values('DISTANCE', ascending=False),
            column_config={
                "MINUTES": "Min.",
                "DISTANCE": st.column_config.NumberColumn("Total (m)", format="%.0f"),
                "HI_RUN": st.column_config.NumberColumn("Højintenst (m)", format="%.0f"),
                "TOP_SPEED": st.column_config.NumberColumn("Topfart", format="%.1f km/h")
            },
            use_container_width=True, hide_index=True
        )

    with t2:
        st.dataframe(
            df_phys[['Spiller', 'SPRINTING', 'NO_OF_HIGH_INTENSITY_RUNS', 'TOP_SPEED']].sort_values('SPRINTING', ascending=False),
            column_config={
                "SPRINTING": "Sprint (m)",
                "NO_OF_HIGH_INTENSITY_RUNS": "Antal HI-løb",
                "TOP_SPEED": "Topfart (km/h)"
            },
            use_container_width=True, hide_index=True
        )

    with t3:
        st.dataframe(
            df_phys[['Spiller', 'DISTANCE_TIP', 'DISTANCE_OTIP', 'DISTANCE_BOP']].sort_values('DISTANCE_TIP', ascending=False),
            column_config={
                "DISTANCE_TIP": "Med bold (m)",
                "DISTANCE_OTIP": "Modstander m. bold (m)",
                "DISTANCE_BOP": "Bold ude (m)"
            },
            use_container_width=True, hide_index=True
        )
