import streamlit as st
import pandas as pd

# HIF's specifikke ID fra dine indstillinger
HIF_OPTA_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

def vis_side(conn, name_map=None):
    if name_map is None:
        name_map = {}

    st.subheader("Fysisk Performance (Second Spectrum)")

    # --- TRIN 1: HENT KAMP-LISTE (METADATA) ---
    @st.cache_data(ttl=600)
    def get_matches():
        # Query rettet til dit SEASON_METADATA dump
        query = f"""
        SELECT 
            DATE,
            MATCH_SSIID,
            HOME_OPTAUUID,
            AWAY_OPTAUUID,
            COMPETITION_OPTAUUID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA
        WHERE (HOME_OPTAUUID = '{HIF_OPTA_UUID}' OR AWAY_OPTAUUID = '{HIF_OPTA_UUID}')
          AND COMPETITION_OPTAUUID = '6ifaeunfdelecgticvxanikzu'
        ORDER BY DATE DESC
        """
        return conn.query(query)

    df_meta = get_matches()

    if df_meta.empty:
        st.warning("Ingen fysiske kampdata fundet for denne sæson.")
        return

    # Lav en pæn label til selectbox
    df_meta['DATE'] = pd.to_datetime(df_meta['DATE'])
    df_meta['DISPLAY_NAME'] = df_meta['DATE'].dt.strftime('%d/%m-%Y') + " - " + \
                               df_meta.apply(lambda x: "Hjemme" if x['HOME_OPTAUUID'] == HIF_OPTA_UUID else "Ude", axis=1)

    valgt_kamp_label = st.selectbox("Vælg kamp for fysisk analyse:", df_meta['DISPLAY_NAME'])
    valgt_match = df_meta[df_meta['DISPLAY_NAME'] == valgt_kamp_label].iloc[0]
    valgt_ssiid = valgt_match['MATCH_SSIID']

    # --- TRIN 2: HENT SPILLER-DATA (F53A) ---
    @st.cache_data(ttl=600)
    def get_physical_stats(ssiid):
        # Vi trimmer ID'et for at sikre match mod Snowflake
        query = f"""
        SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER 
        WHERE TRIM(MATCH_SSIID) = '{ssiid}'
        """
        return conn.query(query)

    df_phys = get_physical_stats(valgt_ssiid)

    if df_phys.empty:
        st.info(f"Metadata fundet, men de detaljerede spiller-data (F53A) er ikke indlæst endnu for denne kamp.")
        return

    # --- TRIN 3: VISNING ---
    # Mapping af navne hvis muligt
    df_phys['Navn'] = df_phys['PLAYER_SSIID'].map(name_map).fillna(df_phys['PLAYER_NAME'])
    
    # Opdel i faner for overblik
    tab1, tab2 = st.tabs(["Løbedistance", "Højintenst løb"])

    with tab1:
        st.dataframe(
            df_phys[['Navn', 'DISTANCE', 'TOP_SPEED', 'SPRINTS']].sort_values('DISTANCE', ascending=False),
            column_config={
                "DISTANCE": st.column_config.NumberColumn("Meter", format="%.0f"),
                "TOP_SPEED": st.column_config.NumberColumn("Topfart (km/h)", format="%.1f")
            },
            use_container_width=True, hide_index=True
        )

    with tab2:
        # Her kan du tilføje High Speed Running hvis kolonnerne findes i din F53A tabel
        st.write("Detaljeret sprint-analyse kommer her...")
