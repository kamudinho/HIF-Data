import streamlit as st
import pandas as pd

# Konstanter
HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"

def vis_side(conn, name_map=None):

    @st.cache_data(ttl=600)
    def get_data():
        # 1. Metadata
        query_meta = f"""
        SELECT MATCH_SSIID, DESCRIPTION, "DATE", HOME_SSIID, AWAY_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA
        WHERE COMPETITION_OPTAUUID = '{COMP_UUID}' 
          AND (HOME_SSIID = '{HIF_SSIID}' OR AWAY_SSIID = '{HIF_SSIID}')
        ORDER BY "DATE" DESC
        """
        df_meta = conn.query(query_meta)
        
        if df_meta.empty:
            return None, None

        # 2. Fysisk data med ALLE de kolonner vi skal bruge til vores tabs
        # Vi bruger dobbelte citationstegn for alle navne med mellemrum eller små bogstaver
        query_phys = """
        SELECT 
            MATCH_SSIID, 
            MATCH_TEAMS,
            PLAYER_NAME, 
            MINUTES, 
            DISTANCE, 
            "HIGH SPEED RUNNING", 
            "SPRINTING", 
            "TOP_SPEED",
            "DISTANCE_TIP", 
            "DISTANCE_OTIP", 
            "DISTANCE_BOP",
            "HSR_DISTANCE_TIP",
            "SPRINT_DISTANCE_TIP"
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        """
        df_phys = conn.query(query_phys)
        return df_meta, df_phys

    df_meta, df_phys = get_data()

    if df_meta is not None:
        # Filtrér til Hvidovre-kampe
        valid_ids = df_meta['MATCH_SSIID'].unique()
        df_hif = df_phys[df_phys['MATCH_SSIID'].isin(valid_ids)].copy()
        
        # Beregninger i Python (Sikkert og hurtigt)
        df_hif['HI_DIST'] = df_hif['HIGH SPEED RUNNING'] + df_hif['SPRINTING']
        df_hif['HI_DIST_TIP'] = df_hif['HSR_DISTANCE_TIP'] + df_hif['SPRINT_DISTANCE_TIP']

        # --- UI: KAMPVALG ---
        st.subheader("Vælg Kamp")
        valgt_kamp = st.selectbox("Kamp:", df_meta['DESCRIPTION'].unique())
        selected_id = df_meta[df_meta['DESCRIPTION'] == valgt_kamp]['MATCH_SSIID'].iloc[0]

        # --- UI: TABS ---
        tab1, tab2, tab3 = st.tabs(["Fysiske Totaler", "Besiddelse (TIP/OTIP)", "HI Aktiviteter"])
        
        kamp_stats = df_hif[df_hif['MATCH_SSIID'] == selected_id].sort_values('DISTANCE', ascending=False)

        with tab1:
            st.write("### Samlet volumen")
            st.dataframe(
                kamp_stats[['PLAYER_NAME', 'MINUTES', 'DISTANCE', 'HI_DIST', 'TOP_SPEED']],
                column_config={
                    "DISTANCE": st.column_config.NumberColumn("Total (m)", format="%d"),
                    "HI_DIST": "HI Meter",
                    "TOP_SPEED": "km/t"
                },
                use_container_width=True, hide_index=True
            )

        with tab2:
            st.write("### Distance ift. boldbesiddelse")
            st.dataframe(
                kamp_stats[['PLAYER_NAME', 'DISTANCE_TIP', 'DISTANCE_OTIP', 'DISTANCE_BOP']],
                column_config={
                    "DISTANCE_TIP": "Med bold (TIP)",
                    "DISTANCE_OTIP": "Modstander har bold (OTIP)",
                    "DISTANCE_BOP": "Bold ude (BOP)"
                },
                use_container_width=True, hide_index=True
            )

        with tab3:
            st.write("### High Intensity fokus")
            st.dataframe(
                kamp_stats[['PLAYER_NAME', 'HI_DIST', 'HI_DIST_TIP', 'SPRINTING']],
                column_config={
                    "HI_DIST": "Total HI (m)",
                    "HI_DIST_TIP": "HI med bold (m)",
                    "SPRINTING": "Sprint (m)"
                },
                use_container_width=True, hide_index=True
            )
    else:
        st.info("Kunne ikke finde data til de valgte tabs.")
