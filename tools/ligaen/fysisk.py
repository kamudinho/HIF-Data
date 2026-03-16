import streamlit as st
import pandas as pd

# Konstanter fra dit dump
COMP_UUID = "6ifaeunfdelecgticvxanikzu"
HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"

def vis_side(conn, name_map=None):
    st.title("Hvidovre IF | Fysisk Data")

    @st.cache_data(ttl=600)
    def get_data_flow():
        # 1. SEASON_METADATA: Find alle Hvidovre kampe
        # Vi filtrerer på både Home og Away for at få alle runder
        query_season = f"""
        SELECT 
            MATCH_SSIID, 
            MATCH_OPTAUUID, 
            DESCRIPTION, 
            DATE,
            HOME_SSIID,
            AWAY_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA
        WHERE COMPETITION_OPTAUUID = '{COMP_UUID}'
          AND (HOME_SSIID = '{HIF_SSIID}' OR AWAY_SSIID = '{HIF_SSIID}')
        ORDER BY DATE DESC
        """
        df_season = conn.query(query_season)
        
        if df_season.empty:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

        # Lav en liste af de SSIIDs vi har fundet
        ids = "('" + "','".join(df_season['MATCH_SSIID'].tolist()) + "')"

        # 2. F53A_GAME: Oversæt kampene (Brug MATCH_SSIID som anker)
        # Her henter vi de officielle holdnavne og kamp-detaljer
        query_f53a = f"""
        SELECT MATCH_SSIID, HOME_TEAM_NAME, AWAY_TEAM_NAME
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME
        WHERE MATCH_SSIID IN {ids}
        """
        df_f53a = conn.query(query_f53a)

        # 3. PHYSICAL_SUMMARY_PLAYERS: Hent tallene
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
        WHERE MATCH_SSIID IN {ids}
        """
        df_phys = conn.query(query_phys)
        
        return df_season, df_f53a, df_phys

    # Hent data
    df_season, df_f53a, df_phys = get_data_flow()

    if df_season.empty:
        st.warning("Ingen kampe fundet for Hvidovre i SEASON_METADATA.")
        return

    # --- MERGE & FILTRERING ---
    # Vi kobler metadata og holdnavne
    df_matches = pd.merge(df_season, df_f53a, on='MATCH_SSIID', how='left')
    
    # Sørg for at vi kun har Hvidovres spillere fra den fysiske tabel
    # Vi bruger "Hvidovre" som filter i MATCH_TEAMS
    df_hif_phys = df_phys[df_phys['MATCH_TEAMS'].str.contains('Hvidovre', case=False, na=False)].copy()
    df_hif_phys['HI_DIST'] = df_hif_phys['HIGH SPEED RUNNING'] + df_hif_phys['SPRINTING']

    # --- VISNING ---
    # Skab en pæn dropdown-menu
    df_matches['display_name'] = df_matches['DATE'].astype(str) + " | " + df_matches['DESCRIPTION']
    
    valgt_label = st.selectbox("Vælg kamp fra sæsonen:", df_matches['display_name'].unique())
    selected_id = df_matches[df_matches['display_name'] == valgt_label]['MATCH_SSIID'].iloc[0]

    # Vis data for den valgte kamp
    st.subheader(f"Statistik: {valgt_label}")
    
    kamp_stats = df_hif_phys[df_hif_phys['MATCH_SSIID'] == selected_id]
    
    if not kamp_stats.empty:
        # Metrics
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Dist", f"{round(kamp_stats['DISTANCE'].sum()/1000, 2)} km")
        c2.metric("HI Distance", f"{int(kamp_stats['HI_DIST'].sum())} m")
        c3.metric("Top Speed", f"{kamp_stats['TOP_SPEED'].max()} km/t")

        # Tabel
        st.dataframe(
            kamp_stats[['PLAYER_NAME', 'MINUTES', 'DISTANCE', 'HI_DIST', 'TOP_SPEED']].sort_values('DISTANCE', ascending=False),
            column_config={
                "PLAYER_NAME": "Spiller",
                "DISTANCE": "Meter",
                "HI_DIST": "HI Meter"
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Fysisk data for denne kamp er endnu ikke tilgængelig i summary-tabellen.")
