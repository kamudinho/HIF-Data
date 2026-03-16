import streamlit as st
import pandas as pd

# HIF's SSIID
HIF_SSIID = '56fa29c7-3a48-4186-9d14-dbf45fbc78d9'

def vis_side(conn, teams_map=None, name_map=None):
    if name_map is None: name_map = {}
    if teams_map is None: teams_map = {}

    st.title("🏃 Fysisk Rapport")
    st.markdown("---")

    # --- TRIN 1: HENT KAMP-LISTE ---
    @st.cache_data(ttl=600)
    def get_matches():
        query = f"""
        SELECT *
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA
        WHERE (HOME_SSIID = '{HIF_SSIID}' OR AWAY_SSIID = '{HIF_SSIID}')
        ORDER BY STARTTIME DESC
        """
        return conn.query(query)

    df_meta = get_matches()

    if df_meta.empty:
        st.warning("⚠️ Ingen kampe fundet i systemet.")
        return

    # Oversæt modstander-ID til Navn
    def get_opp(row):
        opp_id = row['AWAY_SSIID'] if row['HOME_SSIID'] == HIF_SSIID else row['HOME_SSIID']
        for name, info in teams_map.items():
            if info.get('ssid') == opp_id: return name
        return f"Ukendt ({opp_id[:5]})"

    df_meta['DATO'] = pd.to_datetime(df_meta['STARTTIME']).dt.strftime('%d/%m-%Y')
    df_meta['MODSTANDER'] = df_meta.apply(get_opp, axis=1)
    df_meta['STED'] = df_meta.apply(lambda x: "Hjemme" if x['HOME_SSIID'] == HIF_SSIID else "Ude", axis=1)
    df_meta['DISPLAY'] = df_meta['DATO'] + " - " + df_meta['MODSTANDER'] + " (" + df_meta['STED'] + ")"

    valgt_kamp = st.selectbox("Vælg kamp til analyse:", df_meta['DISPLAY'])
    match_row = df_meta[df_meta['DISPLAY'] == valgt_kamp].iloc[0]

    # --- TRIN 2: HENT OG OVERSÆT SPILLER-DATA ---
    @st.cache_data(ttl=600)
    def get_physical_data(ssiid):
        query = f"""
        SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE TRIM(MATCH_SSIID) = '{ssiid}'
        """
        return conn.query(query)

    df = get_physical_data(match_row['MATCH_SSIID'])

    if df.empty:
        st.info("ℹ️ Der er endnu ikke indlæst fysiske data for denne kamp.")
        return

    # Beregn 'Højintensitetsløb' (HSR + Sprint)
    df['HI_RUN'] = df['HIGH SPEED RUNNING'] + df['SPRINTING']
    
    # Mapper spillernavne (hvis name_map findes)
    df['Navn'] = df['PLAYER_NAME']

    # --- TRIN 3: VISNING (Oversat) ---
    st.subheader(f"Statistik mod {match_row['MODSTANDER']}")
    
    # Faner til forskellige perspektiver
    tab1, tab2, tab3 = st.tabs(["📊 Hovedtal", "⚡ Sprint Analyse", "⚽ Boldbesiddelse"])

    with tab1:
        # Oversat tabel-visning
        st.dataframe(
            df[['Navn', 'MINUTES', 'DISTANCE', 'HI_RUN', 'TOP_SPEED']].sort_values('DISTANCE', ascending=False),
            column_config={
                "Navn": "Spiller",
                "MINUTES": "Minutter",
                "DISTANCE": st.column_config.NumberColumn("Total Meter", format="%.0f m"),
                "HI_RUN": st.column_config.NumberColumn("Højintenst (m)", format="%.0f m", help="HSR + Sprint"),
                "TOP_SPEED": st.column_config.NumberColumn("Topfart", format="%.1f km/h")
            },
            use_container_width=True, hide_index=True
        )

    with tab2:
        st.dataframe(
            df[['Navn', 'SPRINTING', 'NO_OF_HIGH_INTENSITY_RUNS', 'TOP_SPEED']].sort_values('SPRINTING', ascending=False),
            column_config={
                "SPRINTING": "Sprint Meter",
                "NO_OF_HIGH_INTENSITY_RUNS": "Antal HI-løb",
                "TOP_SPEED": "Topfart (km/h)"
            },
            use_container_width=True, hide_index=True
        )

    with tab3:
        st.info("Fordeling af distance baseret på hvem der har bolden")
        st.dataframe(
            df[['Navn', 'DISTANCE_TIP', 'DISTANCE_OTIP', 'DISTANCE_BOP']].sort_values('DISTANCE_TIP', ascending=False),
            column_config={
                "DISTANCE_TIP": "Med bold (m)",
                "DISTANCE_OTIP": "Uden bold (m)",
                "DISTANCE_BOP": "Bold ude (m)"
            },
            use_container_width=True, hide_index=True
        )
