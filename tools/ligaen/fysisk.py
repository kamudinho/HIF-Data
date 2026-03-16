import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

# Konstanter baseret på dine indstillinger
HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"
SEASON_NAME = "2025/2026"

def vis_side(conn, name_map=None):
    if name_map is None: name_map = {}

    # --- TRIN 1: HENT METADATA OG HIF-SPILLER RELATION ---
    @st.cache_data(ttl=600)
    def get_base_data():
        # Henter metadata for turnering og år
        query_meta = f"""
        SELECT DATE, HOME_SSIID, AWAY_SSIID, DESCRIPTION, MATCH_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA
        WHERE COMPETITION_OPTAUUID = '{COMP_UUID}' AND YEAR = '2025'
        """
        
        # Henter relationen mellem kamp, hold og spillere
        query_hif_players = f"""
        SELECT MATCH_SSIID, PLAYER_SSIID, PLAYER_NAME
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_TEAM
        WHERE TEAM_SSIID = '{HIF_SSIID}'
        """
        
        return conn.query(query_meta), conn.query(query_hif_players)

    # --- TRIN 2: HENT FYSISK DATA ---
    @st.cache_data(ttl=600)
    def get_phys_stats():
        query = "SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS"
        df = conn.query(query)
        df['HI_RUN'] = df['HIGH SPEED RUNNING'] + df['SPRINTING']
        df['Spiller'] = df['PLAYER_NAME']
        return df

    df_meta, df_hif_rel = get_base_data()
    df_all_phys = get_phys_stats()

    # --- TABS ---
    t1, t2, t3 = st.tabs(["Saeson Oversigt (HIF)", "Top 5 Liga", "Kampoversigt"])

    # TAB 1: HVIDOVRE SÆSON-TOTALER
    with t1:
        # Merger for at ramme kun HIF-spillere
        df_hif_only = pd.merge(
            df_all_phys, 
            df_hif_rel[['PLAYER_SSIID', 'MATCH_SSIID']], 
            on=['PLAYER_SSIID', 'MATCH_SSIID'], 
            how='inner'
        )

        df_hif_season = df_hif_only.groupby('Spiller').agg({
            'MINUTES': 'sum',
            'DISTANCE': 'sum',
            'HI_RUN': 'sum',
            'TOP_SPEED': 'max',
            'SPRINTING': 'sum'
        }).reset_index()

        st.dataframe(
            df_hif_season.sort_values('DISTANCE', ascending=False),
            column_config={
                "DISTANCE": st.column_config.NumberColumn("Total Distance (m)", format="%.0f"),
                "HI_RUN": "Total HI (m)",
                "TOP_SPEED": "Max Topfart",
                "SPRINTING": "Total Sprint (m)"
            },
            use_container_width=True, hide_index=True
        )

    # TAB 2: TOP 5 LIGA
    with t2:
        df_liga_phys = df_all_phys[df_all_phys['MATCH_SSIID'].isin(df_meta['MATCH_SSIID'].unique())]
        
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Hojeste Topfart**")
            st.table(df_liga_phys.groupby('Spiller')['TOP_SPEED'].max().nlargest(5).reset_index().set_index('Spiller'))
            st.write("**Total Distance (m)**")
            st.table(df_liga_phys.groupby('Spiller')['DISTANCE'].sum().nlargest(5).reset_index().set_index('Spiller'))
        with c2:
            st.write("**Total HI-lob (m)**")
            st.table(df_liga_phys.groupby('Spiller')['HI_RUN'].sum().nlargest(5).reset_index().set_index('Spiller'))
            st.write("**Total Sprint (m)**")
            st.table(df_liga_phys.groupby('Spiller')['SPRINTING'].sum().nlargest(5).reset_index().set_index('Spiller'))

    # TAB 3: KAMPOVERSIGT
    with t3:
        def get_team_name(ssiid):
            for name, info in TEAMS.items():
                if info.get('ssid') == ssiid: return name
            return ssiid[:5]

        df_hif_meta = df_meta[(df_meta['HOME_SSIID'] == HIF_SSIID) | (df_meta['AWAY_SSIID'] == HIF_SSIID)].copy()
        df_hif_meta['DISPLAY'] = df_hif_meta['DATE'].astype(str) + ": " + df_hif_meta['DESCRIPTION']
        
        valgt_kamp = st.selectbox("Vaelg kamp:", df_hif_meta['DISPLAY'])
        m_id = df_hif_meta[df_hif_meta['DISPLAY'] == valgt_kamp]['MATCH_SSIID'].values[0]
        
        row = df_hif_meta[df_hif_meta['MATCH_SSIID'] == m_id].iloc[0]
        hold_valg = st.selectbox("Vaelg hold:", ["Begge hold", get_team_name(row['HOME_SSIID']), get_team_name(row['AWAY_SSIID'])])
        
        # Filtrering baseret på holdvalg
        df_match = df_all_phys[df_all_phys['MATCH_SSIID'].str.strip() == m_id.strip()]
        
        if hold_valg != "Begge hold":
            target_ssiid = row['HOME_SSIID'] if hold_valg == get_team_name(row['HOME_SSIID']) else row['AWAY_SSIID']
            # Her bruger vi relationen til at filtrere spillere for det valgte hold
            query_players = f"SELECT PLAYER_SSIID FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_TEAM WHERE TEAM_SSIID = '{target_ssiid}' AND MATCH_SSIID = '{m_id}'"
            target_players = conn.query(query_players)['PLAYER_SSIID'].tolist()
            df_match = df_match[df_match['PLAYER_SSIID'].isin(target_players)]

        st.dataframe(
            df_match[['Spiller', 'MINUTES', 'DISTANCE', 'HI_RUN', 'TOP_SPEED']].sort_values('DISTANCE', ascending=False),
            use_container_width=True, hide_index=True
        )
