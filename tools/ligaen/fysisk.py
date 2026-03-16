import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

# Vi bruger SSID fra din team_mapping.py for Hvidovre
HIF_SSIID = TEAMS["Hvidovre"]["ssid"]

def vis_side(conn, name_map=None):
    if name_map is None: name_map = {}

    # --- TRIN 1: HENT DATA OG FILTRER TIL 1. DIVISION ---
    @st.cache_data(ttl=600)
    def get_filtered_data():
        # Hent al data
        query = "SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS"
        df = conn.query(query)
        
        # Hent metadata for at vide hvilke hold der spiller i hvilke kampe
        query_meta = "SELECT MATCH_SSIID, HOME_SSIID, AWAY_SSIID FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA"
        df_meta = conn.query(query_meta)
        
        # Lav en liste over alle SSID'er fra din TEAMS ordbog (dem du har defineret som relevante)
        relevante_ssids = [info['ssid'] for info in TEAMS.values()]
        
        # Find de MATCH_SSIIDs hvor mindst ét af holdene er i din liste
        relevante_kampe = df_meta[
            df_meta['HOME_SSIID'].isin(relevante_ssids) | 
            df_meta['AWAY_SSIID'].isin(relevante_ssids)
        ]['MATCH_SSIID'].unique()
        
        # Filtrer fysisk data så vi kun ser disse kampe
        df = df[df['MATCH_SSIID'].isin(relevante_kampe)].copy()
        
        df['HI_RUN'] = df['HIGH SPEED RUNNING'] + df['SPRINTING']
        df['Spiller'] = df['PLAYER_NAME']
        return df, df_meta

    df_all, df_meta = get_filtered_data()

    # --- TABS ---
    t1, t2, t3 = st.tabs(["Saeson Oversigt (HIF)", "Top 5 Liga", "Kampoversigt"])

    # TAB 1: HVIDOVRE SÆSON-TOTALER
    with t1:
        st.markdown("### Hvidovre-spillere samlet for saesonen")
        # Filtrer kun kampe hvor Hvidovre har spillet
        hif_matches = df_meta[(df_meta['HOME_SSIID'] == HIF_SSIID) | (df_meta['AWAY_SSIID'] == HIF_SSIID)]['MATCH_SSIID'].unique()
        df_hif_season = df_all[df_all['MATCH_SSIID'].isin(hif_matches)].groupby('Spiller').agg({
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

    # TAB 2: TOP 5 LIGA (KUN RELEVANTE HOLD FRA DIN LISTE)
    with t2:
        st.markdown("### Top 5 paa tvaers af ligaen (Saeson)")
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
        def get_team_name(ssiid):
            for name, info in TEAMS.items():
                if info.get('ssid') == ssiid: return name
            return None # Returner None hvis holdet ikke er i din 1. div liste

        # Kun kampe hvor HIF deltager
        df_hif_meta = df_meta[(df_meta['HOME_SSIID'] == HIF_SSIID) | (df_meta['AWAY_SSIID'] == HIF_SSIID)].copy()
        df_hif_meta['DATO'] = pd.to_datetime(df_hif_meta['STARTTIME']).dt.strftime('%d/%m-%Y')
        
        # Lav pæne navne og filtrer dem fra der ikke er i mappingen
        df_hif_meta['KAMP'] = df_hif_meta.apply(lambda x: f"{x['DATO']}: {get_team_name(x['HOME_SSIID']) or 'Ukendt'} vs {get_team_name(x['AWAY_SSIID']) or 'Ukendt'}", axis=1)
        
        valgt_label = st.selectbox("Vaelg kamp:", df_hif_meta['KAMP'])
        m_id = df_hif_meta[df_hif_meta['KAMP'] == valgt_label]['MATCH_SSIID'].values[0]
        
        df_match = df_all[df_all['MATCH_SSIID'].str.strip() == m_id.strip()]
        
        st.dataframe(
            df_match[['Spiller', 'MINUTES', 'DISTANCE', 'HI_RUN', 'TOP_SPEED']].sort_values('DISTANCE', ascending=False),
            use_container_width=True, hide_index=True
        )
