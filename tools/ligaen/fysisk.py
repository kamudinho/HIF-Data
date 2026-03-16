import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

# Vi bruger SSID fra din team_mapping.py for Hvidovre
HIF_SSIID = TEAMS["Hvidovre"]["ssid"]

def vis_side(conn, name_map=None):
    if name_map is None: name_map = {}


    # --- TRIN 1: HENT ALLE DATA ---
    @st.cache_data(ttl=600)
    def get_all_physical_data():
        # Henter alle rækker fra tabellen
        query = "SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS"
        df = conn.query(query)
        df['HI_RUN'] = df['HIGH SPEED RUNNING'] + df['SPRINTING']
        df['Spiller'] = df['PLAYER_NAME']
        return df

    df_all = get_all_physical_data()

    # Hent metadata for at kunne koble hold på kampene
    @st.cache_data(ttl=600)
    def get_meta():
        query = f"SELECT STARTTIME, MATCH_SSIID, HOME_SSIID, AWAY_SSIID FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA"
        return conn.query(query)

    df_meta = get_meta()

    # --- TABS UDEN IKONER ---
    t1, t2, t3 = st.tabs(["Saeson Oversigt (HIF)", "Top 5 Liga", "Kampoversigt"])

    # TAB 1: HVIDOVRE SÆSON-TOTALER
    with t1:
        st.markdown("### Hvidovre-spillere samlet for saesonen")
        
        # Vi filtrerer spillere der optræder i kampe hvor Hvidovre er hjemme- eller udehold
        hif_matches = df_meta[(df_meta['HOME_SSIID'] == HIF_SSIID) | (df_meta['AWAY_SSIID'] == HIF_SSIID)]['MATCH_SSIID'].unique()
        # Da vi ikke har TEAM_SSIID på spiller-niveau, bruger vi PLAYER_SSIID eller navn til at sikre vi kun ser HIF (hvis muligt)
        # Her viser vi alle HIF rækker baseret på de kampe de har spillet
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

    # TAB 2: TOP 5 LIGA (HELE SÆSONEN)
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
        # Forbered kampvælger
        def get_team_name(ssiid):
            for name, info in TEAMS.items():
                if info.get('ssid') == ssiid: return name
            return ssiid[:5]

        df_hif_meta = df_meta[(df_meta['HOME_SSIID'] == HIF_SSIID) | (df_meta['AWAY_SSIID'] == HIF_SSIID)].copy()
        df_hif_meta['DATO'] = pd.to_datetime(df_hif_meta['STARTTIME']).dt.strftime('%d/%m-%Y')
        df_hif_meta['KAMP'] = df_hif_meta.apply(lambda x: f"{x['DATO']}: {get_team_name(x['HOME_SSIID'])} vs {get_team_name(x['AWAY_SSIID'])}", axis=1)
        
        valgt_label = st.selectbox("Vaelg kamp:", df_hif_meta['KAMP'])
        m_id = df_hif_meta[df_hif_meta['KAMP'] == valgt_label]['MATCH_SSIID'].values[0]
        
        # Hent holdene i den valgte kamp
        h_id = df_hif_meta[df_hif_meta['MATCH_SSIID'] == m_id]['HOME_SSIID'].values[0]
        a_id = df_hif_meta[df_hif_meta['MATCH_SSIID'] == m_id]['AWAY_SSIID'].values[0]
        
        hold_valg = st.selectbox("Vaelg hold:", ["Begge hold", get_team_name(h_id), get_team_name(a_id)])
        
        df_match = df_all[df_all['MATCH_SSIID'].str.strip() == m_id.strip()]
        
        # Da vi ikke har TEAM_SSIID i tabellen, viser vi hele kampens data. 
        # Hvis du har en måde at skelne spillere på (f.eks. via en spiller-tabel), kan vi filtrere her.
        st.dataframe(
            df_match[['Spiller', 'MINUTES', 'DISTANCE', 'HI_RUN', 'TOP_SPEED']].sort_values('DISTANCE', ascending=False),
            use_container_width=True, hide_index=True
        )
