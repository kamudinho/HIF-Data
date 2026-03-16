import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

# Vi bruger SSID fra din team_mapping.py for Hvidovre
HIF_SSIID = TEAMS["Hvidovre"]["ssid"]

def vis_side(conn, name_map=None):
    if name_map is None: name_map = {}

    st.title("BETINIA LIGAEN | FYSISK DATA")
    st.subheader("Fysisk Rapport")

    # --- TRIN 1: HENT DATA ---
    @st.cache_data(ttl=600)
    def get_physical_data():
        # Vi henter data og sikrer os, at vi ikke bruger 'ssid' som kolonnenavn i SQL
        query = """
        SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        """
        df = conn.query(query)
        
        # Opret HI_RUN og Spiller-navn med de korrekte kolonne-referencer fra din tabel
        df['HI_RUN'] = df['HIGH SPEED RUNNING'] + df['SPRINTING']
        df['Spiller'] = df['PLAYER_NAME']
        return df

    df_all = get_physical_data()

    # Hent metadata til kamp-identifikation
    @st.cache_data(ttl=600)
    def get_meta():
        query = "SELECT STARTTIME, MATCH_SSIID, HOME_SSIID, AWAY_SSIID FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA"
        return conn.query(query)

    df_meta = get_meta()

    # --- TABS ---
    t1, t2, t3 = st.tabs(["Saeson Oversigt (HIF)", "Top 5 Liga", "Kampoversigt"])

    # TAB 1: HVIDOVRE SÆSON-TOTALER
    with t1:
        st.markdown("### Hvidovre-spillere samlet for saesonen")
        
        # Find alle kampe hvor Hvidovre har spillet (enten hjemme eller ude)
        hif_match_ids = df_meta[(df_meta['HOME_SSIID'] == HIF_SSIID) | (df_meta['AWAY_SSIID'] == HIF_SSIID)]['MATCH_SSIID'].unique()
        
        # Her aggregerer vi data for alle spillere i de kampe
        # Note: Hvis du vil filtrere KUN HIF-spillere fra modstandere, kræver det en TEAM_ID kolonne i dataen.
        df_hif_season = df_all[df_all['MATCH_SSIID'].isin(hif_match_ids)].groupby('Spiller').agg({
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

    # TAB 2: TOP 5 LIGA (HELE SÆSONEN)
    with t2:
        st.markdown("### Top 5 paa tvaers af ligaen (Saeson)")
        
        # Vi viser de 5 bedste i hele ligaen baseret på din Snowflake tabel
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Hojeste Topfart**")
            st.table(df_all.groupby('Spiller')['TOP_SPEED'].max().nlargest(5).reset_index().set_index('Spiller'))
            
            st.write("**Total Distance (m)**")
            st.table(df_all.groupby('Spiller')['DISTANCE'].sum().nlargest(5).reset_index().set_index('Spiller'))
            
        with c2:
            st.write("**Total HI-lob (m)**")
            st.table(df_all.groupby('Spiller')['HI_RUN'].sum().nlargest(5).reset_index().set_index('Spiller'))
            
            st.write("**Total Sprint (m)**")
            st.table(df_all.groupby('Spiller')['SPRINTING'].sum().nlargest(5).reset_index().set_index('Spiller'))

    # TAB 3: KAMPOVERSIGT
    with t3:
        # Hjælpefunktion til at få navne fra din TEAMS ordbog
        def get_team_name(ssiid_val):
            for name, info in TEAMS.items():
                if info.get('ssid') == ssiid_val:
                    return name
            return ssiid_val[:5]

        # Kun kampe involverende Hvidovre
        df_hif_meta = df_meta[(df_meta['HOME_SSIID'] == HIF_SSIID) | (df_meta['AWAY_SSIID'] == HIF_SSIID)].copy()
        df_hif_meta['DATO'] = pd.to_datetime(df_hif_meta['STARTTIME']).dt.strftime('%d/%m-%Y')
        df_hif_meta['KAMP'] = df_hif_meta.apply(lambda x: f"{x['DATO']}: {get_team_name(x['HOME_SSIID'])} vs {get_team_name(x['AWAY_SSIID'])}", axis=1)
        
        valgt_label = st.selectbox("Vaelg kamp:", df_hif_meta['KAMP'])
        m_id = df_hif_meta[df_hif_meta['KAMP'] == valgt_label]['MATCH_SSIID'].values[0]
        
        # Vis alle spillere i den valgte kamp
        df_match = df_all[df_all['MATCH_SSIID'].str.strip() == m_id.strip()]
        
        st.dataframe(
            df_match[['Spiller', 'MINUTES', 'DISTANCE', 'HI_RUN', 'TOP_SPEED']].sort_values('DISTANCE', ascending=False),
            use_container_width=True, hide_index=True
        )
