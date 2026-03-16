import streamlit as st
import pandas as pd

# Hvidovres SSID fra dine indstillinger
HIF_SSIID = '56fa29c7-3a48-4186-9d14-dbf45fbc78d9'

def vis_side(conn, teams_map=None, name_map=None):
    if name_map is None:
        name_map = {}
    if teams_map is None:
        teams_map = {}

    # --- TRIN 1: HENT KAMP-LISTE (METADATA) ---
    @st.cache_data(ttl=600)
    def get_matches():
        # Din SQL 1:1 - henter oversigt til UI
        query = f"""
        SELECT 
            *
            
            -- Tilføjer disse for at kunne sortere og identificere kampen i UI
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA
        WHERE (HOME_SSIID = '{HIF_SSIID}' OR AWAY_SSIID = '{HIF_SSIID}')
          AND COMPETITION_OPTAUUID = '6ifaeunfdelecgticvxanikzu'
        ORDER BY DATE DESC, START_TIME DESC;
        """
        return conn.query(query)

    df_meta = get_matches()

    if df_meta.empty:
        st.warning("Ingen fysiske kampdata fundet for denne sæson.")
        return

    # --- HJÆLPEFUNKTION TIL MODSTANDER-NAVN ---
    def get_opponent(row):
        # Find ud af hvem der ikke er Hvidovre
        opp_id = row['AWAY_SSIID'] if row['HOME_SSIID'] == HIF_SSIID else row['HOME_SSIID']
        
        # Slå op i din TEAMS mapping (baseret på SSID)
        for name, info in teams_map.items():
            if info.get('ssid') == opp_id:
                return name
        return "Ukendt modstander"

    # Lav en pæn label til selectbox
    df_meta['DATE'] = pd.to_datetime(df_meta['DATE'])
    df_meta['OPPONENT'] = df_meta.apply(get_opponent, axis=1)
    df_meta['VENUE'] = df_meta.apply(lambda x: "(H)" if x['HOME_SSIID'] == HIF_SSIID else "(U)", axis=1)
    
    df_meta['DISPLAY_NAME'] = (
        df_meta['DATE'].dt.strftime('%d/%m-%Y') + 
        " - " + df_meta['OPPONENT'] + " " + df_meta['VENUE']
    )

    valgt_kamp_label = st.selectbox("Vælg kamp for fysisk analyse:", df_meta['DISPLAY_NAME'])
    valgt_match = df_meta[df_meta['DISPLAY_NAME'] == valgt_kamp_label].iloc[0]
    valgt_ssiid = valgt_match['MATCH_SSIID']

    # --- TRIN 2: HENT SPILLER-DATA (F53A) ---
    @st.cache_data(ttl=600)
    def get_physical_stats(ssiid):
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
    # Mapper spiller-navne (SSIID -> Navn)
    df_phys['Navn'] = df_phys['PLAYER_SSIID'].map(name_map).fillna(df_phys['PLAYER_NAME'])
    
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
        st.write(f"Analyse af sprints og højintensitetsløb for kampen mod {valgt_match['OPPONENT']}.")
        # Her kan du tilføje yderligere kolonner fra F53A tabellen
