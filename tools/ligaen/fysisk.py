import streamlit as st
import pandas as pd

# Konstanter
HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"

def vis_side(conn, name_map=None):

    @st.cache_data(ttl=600)
    def get_data():
        # Vi holder det ultra-simpelt for at undgå fejl
        # Vi bruger kun SEASON_METADATA til at finde kampene
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

        # Vi henter spillere fra SUMMARY_PLAYERS med de præcise navne fra dit dump
        # Bemærk citationstegnene pga. mellemrum i navnene
        query_phys = """
        SELECT 
            MATCH_SSIID, 
            MATCH_TEAMS,
            PLAYER_NAME, 
            MINUTES, 
            DISTANCE, 
            "HIGH SPEED RUNNING", 
            SPRINTING, 
            TOP_SPEED
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        """
        df_phys = conn.query(query_phys)
        
        return df_meta, df_phys

    df_meta, df_phys = get_data()

    if df_meta is None:
        st.warning("Ingen metadata fundet.")
        return

    # --- DATABEHANDLING ---
    # Vi finder Hvidovre-kampe i den fysiske tabel
    # Da jeres holdnavn varierer i teksten (HBK-EFB osv.), 
    # matcher vi på MATCH_SSIID fra vores filtrerede metadata
    valid_ids = df_meta['MATCH_SSIID'].unique()
    df_hif = df_phys[df_phys['MATCH_SSIID'].isin(valid_ids)].copy()

    # Beregn HI Distance (HSR + Sprint)
    df_hif['HI_DIST'] = df_hif['HIGH SPEED RUNNING'] + df_hif['SPRINTING']

    # --- UI ---
    st.subheader("Vælg Kamp")
    valgt_label = st.selectbox("Kamp:", df_meta['DESCRIPTION'].unique())
    selected_id = df_meta[df_meta['DESCRIPTION'] == valgt_label]['MATCH_SSIID'].iloc[0]

    # Vis spillere
    kamp_stats = df_hif[df_hif['MATCH_SSIID'] == selected_id]

    if not kamp_stats.empty:
        st.write(f"### Spillerstatistik for {valgt_label}")
        
        # Sorter efter hvem der løber mest
        st.dataframe(
            kamp_stats[['PLAYER_NAME', 'MINUTES', 'DISTANCE', 'HI_DIST', 'TOP_SPEED']].sort_values('DISTANCE', ascending=False),
            column_config={
                "PLAYER_NAME": "Spiller",
                "MINUTES": "Tid (MM:SS)",
                "DISTANCE": st.column_config.NumberColumn("Total Meter", format="%d"),
                "HI_DIST": st.column_config.NumberColumn("HI Meter", format="%d"),
                "TOP_SPEED": "Topfart"
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Ingen fysisk data fundet for denne specifikke kamp endnu.")
