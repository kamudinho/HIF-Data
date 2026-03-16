import streamlit as st
import pandas as pd

# HIF's SSIID fra din oversigt
HIF_SSIID = 'f2b45639-d8e6-4d9b-9371-6f9f1fe2a9d9'

def vis_side(conn, teams_map=None, name_map=None):
    if name_map is None: name_map = {}
    if teams_map is None: teams_map = {}

    st.subheader("Fysisk Performance (Second Spectrum)")

    # --- TRIN 1: HENT KAMP-LISTE (METADATA) ---
    @st.cache_data(ttl=600)
    def get_matches():
        # Rettet kolonnenavne: HOMEOPTA_UUID og AWAY_OPTAUUID jf. din skema-dump
        query = f"""
        SELECT 
            STARTTIME as DATE,
            MATCH_SSIID,
            HOME_SSIID,
            AWAY_SSIID,
            HOMEOPTA_UUID,
            AWAY_OPTAUUID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA
        WHERE (HOME_SSIID = '{HIF_SSIID}' OR AWAY_SSIID = '{HIF_SSIID}')
        ORDER BY STARTTIME DESC
        """
        return conn.query(query)

    df_meta = get_matches()

    if df_meta.empty:
        st.warning("Ingen kamp-metadata fundet i SECONDSPECTRUM_GAME_METADATA.")
        return

    # Hjælpefunktion til at finde modstander i din TEAMS dict
    def get_opponent_name(row):
        opp_ssiid = row['AWAY_SSIID'] if row['HOME_SSIID'] == HIF_SSIID else row['HOME_SSIID']
        for name, info in teams_map.items():
            if info.get('ssid') == opp_ssiid:
                return name
        return f"Ukendt ({opp_ssiid[:5]})"

    df_meta['OPPONENT'] = df_meta.apply(get_opponent_name, axis=1)
    df_meta['DISPLAY_NAME'] = pd.to_datetime(df_meta['DATE']).dt.strftime('%d/%m-%Y') + " - " + df_meta['OPPONENT']

    valgt_label = st.selectbox("Vælg kamp:", df_meta['DISPLAY_NAME'])
    valgt_match = df_meta[df_meta['DISPLAY_NAME'] == valgt_label].iloc[0]

    # --- TRIN 2: HENT SPILLER-DATA ---
    @st.cache_data(ttl=600)
    def get_physical_stats(ssiid):
        # Bruger tabellen fra din oversigt
        query = f"""
        SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER 
        WHERE TRIM(MATCH_SSIID) = '{ssiid}'
        """
        return conn.query(query)

    df_phys = get_physical_stats(valgt_match['MATCH_SSIID'])

    if df_phys.empty:
        st.info("Ingen spiller-statistikker fundet for denne kamp (F53A).")
        return

    # Mapping af navne
    df_phys['Spiller'] = df_phys['PLAYER_SSIID'].map(name_map).fillna(df_phys['PLAYER_NAME'])

    # --- TRIN 3: VISNING ---
    tab1, tab2 = st.tabs(["Løbedistance", "Sprint & Hastighed"])

    with tab1:
        # Sorteret efter DISTANCE (kolonnenavnet findes i din F53A dump)
        st.dataframe(
            df_phys[['Spiller', 'DISTANCE', 'AVERAGE_SPEED', 'TOP_SPEED']].sort_values('DISTANCE', ascending=False),
            column_config={
                "DISTANCE": st.column_config.NumberColumn("Total Meter", format="%d m"),
                "AVERAGE_SPEED": st.column_config.NumberColumn("Gns. Fart", format="%.2f km/h")
            },
            use_container_width=True, hide_index=True
        )

    with tab2:
        # High Speed Running kolonner fra din dump
        st.dataframe(
            df_phys[['Spiller', 'SPRINTS', 'SPEED_RUNS', 'TOP_SPEED']].sort_values('SPRINTS', ascending=False),
            use_container_width=True, hide_index=True
        )
