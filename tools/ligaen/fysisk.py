import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

# Vi bruger SSID fra din team_mapping.py for Hvidovre
HIF_SSIID = TEAMS["Hvidovre"]["ssid"]

def vis_side(conn, name_map=None):
    if name_map is None: name_map = {}

    st.title("Fysisk Rapport")

    # --- TRIN 1: HENT ALLE DATA FOR SÆSONEN (TIL TOP 5 OG SÆSON-TOTALER) ---
    @st.cache_data(ttl=600)
    def get_season_data():
        # Henter alt for ligaen for at kunne lave Top 5 på tværs
        query = """
        SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        """
        df = conn.query(query)
        df['HI_RUN'] = df['HIGH SPEED RUNNING'] + df['SPRINTING']
        df['Spiller'] = df['PLAYER_NAME']
        return df

    df_all = get_season_data()

    # --- TABS ---
    t1, t2, t3 = st.tabs(["Sæson Oversigt (HIF)", "Top 5 Liga", "Kampoversigt"])

    # TAB 1: HVIDOVRE SÆSON-TOTALER
    with t1:
        st.subheader("Hvidovre-spillere samlet for sæsonen")
        # Filtrer på Hvidovres spiller-data (vi antager de er knyttet til HIF_SSIID i dataen)
        # Hvis MATCH_SSIID/TEAM_SSIID er tilgængelig, bruger vi den. 
        # Her aggregerer vi per spiller:
        df_hif_season = df_all[df_all['TEAM_SSIID'] == HIF_SSIID].groupby('Spiller').agg({
            'MINUTES': 'sum',
            'DISTANCE': 'sum',
            'HI_RUN': 'sum',
            'TOP_SPEED': 'max',
            'SPRINTING': 'sum'
        }).reset_index()

        st.dataframe(
            df_hif_season.sort_values('DISTANCE', ascending=False),
            column_config={
                "MINUTES": "Total Min.",
                "DISTANCE": st.column_config.NumberColumn("Total Distance (m)", format="%.0f"),
                "HI_RUN": "Total HI (m)",
                "TOP_SPEED": "Max Topfart",
                "SPRINTING": "Total Sprint (m)"
            },
            use_container_width=True, hide_index=True
        )

    # TAB 2: TOP 5 LIGA (HELE SÆSONEN)
    with t2:
        st.subheader("Top 5 på tværs af ligaen (Sæson)")
        
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Højeste Topfart**")
            # Vi finder den absolutte max-fart per spiller i sæsonen
            top_speed_season = df_all.groupby('Spiller')['TOP_SPEED'].max().nlargest(5).reset_index()
            st.table(top_speed_season.set_index('Spiller'))

            st.write("**Total Distance (m)**")
            top_dist_season = df_all.groupby('Spiller')['DISTANCE'].sum().nlargest(5).reset_index()
            st.table(top_dist_season.set_index('Spiller'))

        with c2:
            st.write("**Total HI-løb (m)**")
            top_hi_season = df_all.groupby('Spiller')['HI_RUN'].sum().nlargest(5).reset_index()
            st.table(top_hi_season.set_index('Spiller'))

            st.write("**Total Sprint (m)**")
            top_sprint_season = df_all.groupby('Spiller')['SPRINTING'].sum().nlargest(5).reset_index()
            st.table(top_sprint_season.set_index('Spiller'))

    # TAB 3: KAMPOVERSIGT MED BEGGE HOLD
    with t3:
        # Hent metadata for at vælge kamp
        query_meta = f"""
        SELECT STARTTIME, MATCH_SSIID, HOME_SSIID, AWAY_SSIID 
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA
        WHERE (HOME_SSIID = '{HIF_SSIID}' OR AWAY_SSIID = '{HIF_SSIID}')
        ORDER BY STARTTIME DESC
        """
        df_meta = conn.query(query_meta)
        
        # Hjælper til navne (bruger din TEAMS mapping)
        def get_team_name(ssiid):
            for name, info in TEAMS.items():
                if info.get('ssid') == ssiid: return name
            return ssiid[:5]

        df_meta['DATO'] = pd.to_datetime(df_meta['STARTTIME']).dt.strftime('%d/%m-%Y')
        df_meta['KAMP'] = df_meta.apply(lambda x: f"{x['DATO']}: {get_team_name(x['HOME_SSIID'])} vs {get_team_name(x['AWAY_SSIID'])}", axis=1)
        
        valgt_kamp_label = st.selectbox("Vælg kamp:", df_meta['KAMP'])
        valgt_match_id = df_meta[df_meta['KAMP'] == valgt_kamp_label]['MATCH_SSIID'].values[0]
        
        # Filtrer data for den valgte kamp
        df_match = df_all[df_all['MATCH_SSIID'].str.strip() == valgt_match_id.strip()]

        # Holddropdown til at filtrere i kampen
        alle_hold_i_kamp = [get_team_name(id) for id in [df_meta[df_meta['MATCH_SSIID']==valgt_match_id]['HOME_SSIID'].values[0], 
                                                        df_meta[df_meta['MATCH_SSIID']==valgt_match_id]['AWAY_SSIID'].values[0]]]
        
        valgt_hold = st.selectbox("Vis statistik for:", ["Begge hold"] + alle_hold_i_kamp)

        if valgt_hold != "Begge hold":
            hold_ssiid = TEAMS[valgt_hold]['ssid']
            df_display = df_match[df_match['TEAM_SSIID'] == hold_ssiid]
        else:
            df_display = df_match

        st.dataframe(
            df_display[['Spiller', 'MINUTES', 'DISTANCE', 'HI_RUN', 'TOP_SPEED']].sort_values('DISTANCE', ascending=False),
            use_container_width=True, hide_index=True
        )
