import streamlit as st
import pandas as pd

# Konstanter
HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"

def vis_side(conn, name_map=None):

    @st.cache_data(ttl=600)
    def get_clean_data():
        # 1. Hent kampe fra Season Metadata
        query_meta = f"""
        SELECT MATCH_SSIID, DESCRIPTION, "DATE"
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA
        WHERE COMPETITION_OPTAUUID = '{COMP_UUID}' 
          AND (HOME_SSIID = '{HIF_SSIID}' OR AWAY_SSIID = '{HIF_SSIID}')
        ORDER BY "DATE" DESC
        """
        df_meta = conn.query(query_meta)
        
        if df_meta.empty:
            return None, None

        # 2. Hent fysisk data med de præcise kolonnenavne i citationstegn
        # Vi tager kun de mest basale for at sikre hul igennem
        query_phys = """
        SELECT 
            MATCH_SSIID, 
            PLAYER_NAME, 
            MINUTES, 
            DISTANCE, 
            "HIGH SPEED RUNNING", 
            "SPRINTING", 
            TOP_SPEED
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        """
        df_phys = conn.query(query_phys)
        
        return df_meta, df_phys

    try:
        df_meta, df_phys = get_clean_data()
    except Exception as e:
        st.error(f"SQL Fejl: {e}")
        return

    if df_meta is not None:
        # --- LOGIK ---
        # Vi bruger MATCH_SSIID til at filtrere spillere til de valgte kampe
        match_ids = df_meta['MATCH_SSIID'].unique()
        df_hif = df_phys[df_phys['MATCH_SSIID'].isin(match_ids)].copy()

        # Beregn HI Distance i Python (sikrere end i SQL lige nu)
        df_hif['HI_DIST'] = df_hif['HIGH SPEED RUNNING'] + df_hif['SPRINTING']

        # --- UI ---
        st.subheader("Vælg Kamp")
        valgt_kamp = st.selectbox("Kamp:", df_meta['DESCRIPTION'].unique())
        selected_id = df_meta[df_meta['DESCRIPTION'] == valgt_kamp]['MATCH_SSIID'].iloc[0]

        # Vis spillerne for den valgte kamp
        kamp_stats = df_hif[df_hif['MATCH_SSIID'] == selected_id]

        if not kamp_stats.empty:
            st.dataframe(
                kamp_stats[['PLAYER_NAME', 'MINUTES', 'DISTANCE', 'HI_DIST', 'TOP_SPEED']].sort_values('DISTANCE', ascending=False),
                column_config={
                    "PLAYER_NAME": "Spiller",
                    "MINUTES": "Tid",
                    "DISTANCE": st.column_config.NumberColumn("Meter", format="%d"),
                    "HI_DIST": st.column_config.NumberColumn("HI Meter", format="%d")
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Ingen fysisk data fundet for denne kamp.")
