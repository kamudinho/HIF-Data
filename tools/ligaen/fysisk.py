import streamlit as st
import pandas as pd

# HIF's SSIID
HIF_SSIID = 'f2b45639-d8e6-4d9b-9371-6f9f1fe2a9d9'

def vis_side(conn, teams_map=None, name_map=None):
    if name_map is None: name_map = {}
    if teams_map is None: teams_map = {}

    st.subheader("Fysisk Performance (Second Spectrum) - Komplet Oversigt")

    # --- TRIN 1: HENT KAMP-LISTE (METADATA) ---
    @st.cache_data(ttl=600)
    def get_matches():
        # Vi henter bredt fra metadata for at sikre vi har de rigtige ID'er
        query = """
        SELECT *
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA
        WHERE HOME_SSIID = '{0}' OR AWAY_SSIID = '{0}'
        ORDER BY STARTTIME DESC
        """.format(HIF_SSIID)
        return conn.query(query)

    df_meta = get_matches()

    if df_meta.empty:
        st.warning("Ingen kampe fundet i metadata.")
        return

    # Dynamisk navngivning af modstander
    def get_opp(row):
        opp_id = row['AWAY_SSIID'] if row['HOME_SSIID'] == HIF_SSIID else row['HOME_SSIID']
        for name, info in teams_map.items():
            if info.get('ssid') == opp_id: return name
        return f"Ukendt ({opp_id[:5]})"

    df_meta['DATE_LABEL'] = pd.to_datetime(df_meta['STARTTIME']).dt.strftime('%d/%m-%Y')
    df_meta['DISPLAY'] = df_meta['DATE_LABEL'] + " - " + df_meta.apply(get_opp, axis=1)

    valgt_kamp = st.selectbox("Vælg kamp:", df_meta['DISPLAY'])
    match_row = df_meta[df_meta['DISPLAY'] == valgt_kamp].iloc[0]
    m_ssiid = match_row['MATCH_SSIID']

    # --- TRIN 2: HENT DEN STORE PERFORMANCE TABEL (ALT!) ---
    @st.cache_data(ttl=600)
    def get_all_physical_data(ssiid):
        # Vi bruger den tabel der har de mest komplette tal jf. din oversigt
        query = f"""
        SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE TRIM(MATCH_SSIID) = '{ssiid}'
        """
        return conn.query(query)

    df = get_all_physical_data(m_ssiid)

    if df.empty:
        st.info("Ingen fysiske detaljer fundet i Summary-tabellen for denne kamp.")
        return

    # Mapping af spillernavne
    df['Spiller'] = df['PLAYER_NAME'] # Default fra tabel

    # --- TRIN 3: VISNING AF ALT ---
    st.write(f"### Data for kampen: {valgt_kamp}")
    
    # Formatering af kolonner så de er nemme at læse
    st.dataframe(
        df[[
            'Spiller', 'MINUTES', 'DISTANCE', 'TOP_SPEED', 
            'HIGH SPEED RUNNING', 'SPRINTING', 'AVERAGE_SPEED',
            'NO_OF_HIGH_INTENSITY_RUNS'
        ]].sort_values('DISTANCE', ascending=False),
        column_config={
            "DISTANCE": st.column_config.NumberColumn("Total (m)", format="%.0f"),
            "HIGH SPEED RUNNING": st.column_config.NumberColumn("HSR (m)", format="%.0f"),
            "SPRINTING": st.column_config.NumberColumn("Sprint (m)", format="%.0f"),
            "TOP_SPEED": st.column_config.NumberColumn("Max (km/h)", format="%.1f"),
            "MINUTES": "Min."
        },
        use_container_width=True,
        hide_index=True
    )

    # Ekstra sektion for intensitets-data (TIP/OTIP/BOP)
    with st.expander("Se avanceret intensitets-data (TIP/BOP/OTIP)"):
        st.write("TIP = Team In Possession | OTIP = Opponent In Possession | BOP = Ball Out of Play")
        st.dataframe(
            df[['Spiller', 'DISTANCE_TIP', 'DISTANCE_OTIP', 'DISTANCE_BOP']],
            use_container_width=True,
            hide_index=True
        )
