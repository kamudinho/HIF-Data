import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

# Konstanter fra din profil
HIF_WYID = 7490
COMP_UUID = "6ifaeunfdelecgticvxanikzu"

def vis_side(conn, name_map=None):
    st.title("Hvidovre IF | Fysisk Data")

    @st.cache_data(ttl=600)
    def get_hif_data():
        # TRIN 1: Hent alle relevante MATCH_SSIIDs for sæsonen
        query_season = f"""
        SELECT MATCH_SSIID, DESCRIPTION, "DATE"
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA
        WHERE COMPETITION_OPTAUUID = '{COMP_UUID}' AND YEAR = 2025
        """
        df_season = conn.query(query_season)
        
        if df_season.empty:
            return pd.DataFrame(), pd.DataFrame()

        # TRIN 2: Hent kamp-detaljer fra F53A (Oversættelse af kampen)
        # Vi bruger SSIIDs fra første query til at filtrere
        ssiid_list = "('" + "','".join(df_season['MATCH_SSIID'].tolist()) + "')"
        query_f53a = f"""
        SELECT MATCH_SSIID, HOME_TEAM_NAME, AWAY_TEAM_NAME
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME
        WHERE MATCH_SSIID IN {ssiid_list}
        """
        df_f53a = conn.query(query_f53a)

        # TRIN 3: Hent fysisk data for spillere
        query_phys = f"""
        SELECT 
            MATCH_SSIID, 
            PLAYER_NAME, 
            MATCH_TEAMS,
            DISTANCE, 
            "HIGH SPEED RUNNING", 
            SPRINTING, 
            TOP_SPEED, 
            MINUTES
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_SSIID IN {ssiid_list}
        """
        df_phys = conn.query(query_phys)
        
        return df_season, df_f53a, df_phys

    df_season, df_f53a, df_phys = get_hif_data()

    if df_season.empty:
        st.error("Kunne ikke finde data for sæsonen 2025.")
        return

    # --- SAMLING AF DATA ---
    # Vi merger Season og F53A for at få de rigtige holdnavne på kampene
    df_matches = pd.merge(df_season, df_f53a, on='MATCH_SSIID', how='left')
    
    # Filtrér fysisk data til kun at være Hvidovre IF (HIF)
    df_hif_phys = df_phys[df_phys['MATCH_TEAMS'].str.contains('Hvidovre', case=False, na=False)].copy()
    df_hif_phys['HI_DIST'] = df_hif_phys['HIGH SPEED RUNNING'] + df_hif_phys['SPRINTING']

    # --- UI: KAMPVALG ---
    st.subheader("Vælg Kamp")
    
    # Skab en læsbar label til selectboxen
    df_matches['label'] = df_matches['DATE'].astype(str) + ": " + df_matches['HOME_TEAM_NAME'] + " - " + df_matches['AWAY_TEAM_NAME']
    
    valgt_match_label = st.selectbox("Kamp:", df_matches['label'].unique())
    valgt_match_id = df_matches[df_matches['label'] == valgt_match_label]['MATCH_SSIID'].iloc[0]

    # --- UI: VISNING AF SPILLER DATA ---
    st.divider()
    st.write(f"### Fysisk output for {valgt_match_label}")
    
    kamp_stats = df_hif_phys[df_hif_phys['MATCH_SSIID'] == valgt_match_id]
    
    if not kamp_stats.empty:
        # Hovedtal
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Distance", f"{round(kamp_stats['DISTANCE'].sum()/1000, 1)} km")
        col2.metric("HI Distance", f"{int(kamp_stats['HI_DIST'].sum())} m")
        col3.metric("Top Speed", f"{kamp_stats['TOP_SPEED'].max()} km/t")

        # Spiller tabel
        st.dataframe(
            kamp_stats[['PLAYER_NAME', 'MINUTES', 'DISTANCE', 'HI_DIST', 'TOP_SPEED']].sort_values('DISTANCE', ascending=False),
            column_config={
                "PLAYER_NAME": "Spiller",
                "MINUTES": "Min",
                "DISTANCE": "Meter",
                "HI_DIST": "HI Meter",
                "TOP_SPEED": "km/t"
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("Ingen fysiske data fundet for denne kamp.")
