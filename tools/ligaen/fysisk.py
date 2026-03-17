import streamlit as st
import pandas as pd
from datetime import datetime

HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"

def vis_side(conn, name_map=None):
    @st.cache_data(ttl=600)
    def get_data_v3():
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 1. Hent metadata for sæsonen (1. juli 2025 til nu)
        query_meta = f"""
        SELECT "DATE", DESCRIPTION, MATCH_SSIID, HOME_SSIID, AWAY_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA
        WHERE COMPETITION_OPTAUUID = '{COMP_UUID}' 
          AND "DATE" >= '2025-07-01'
          AND "DATE" <= '{today}'
        ORDER BY "DATE" DESC
        """
        df_meta = conn.query(query_meta)
        
        if df_meta.empty:
            return df_meta, pd.DataFrame(), pd.DataFrame()

        m_ids = tuple(df_meta['MATCH_SSIID'].tolist())
        formatted_ids = ','.join([f"'{i}'" for i in m_ids])

        # 2. Hent fysisk data (Den tabel vi ved virker jf. dit screenshot)
        query_phys = f"""
        SELECT 
            MATCH_SSIID, PLAYER_NAME, 
            MINUTES, DISTANCE, 
            "HIGH SPEED RUNNING", "SPRINTING", "TOP_SPEED"
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_SSIID IN ({formatted_ids})
        """
        
        # 3. Hent trup-tilhørsforhold (Hvem spiller for HIF i disse kampe?)
        query_teams = f"""
        SELECT DISTINCT MATCH_SSIID, PLAYER_NAME, TEAM_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER
        WHERE MATCH_SSIID IN ({formatted_ids})
        """
        
        return df_meta, conn.query(query_phys), conn.query(query_teams)

    df_meta, df_phys, df_teams = get_data_v3()

    # --- DATABEARBEJDNING ---
    # Vi laver en "ren" nøgle til at matche på tværs af tabeller
    df_phys['MATCH_KEY'] = df_phys['MATCH_SSIID'].astype(str) + df_phys['PLAYER_NAME'].str.lower().str.strip()
    df_teams['MATCH_KEY'] = df_teams['MATCH_SSIID'].astype(str) + df_teams['PLAYER_NAME'].str.lower().str.strip()
    
    # Merge hold-info på de fysiske data
    df_combined = pd.merge(df_phys, df_teams[['MATCH_KEY', 'TEAM_SSIID']], on='MATCH_KEY', how='left')

    def parse_minutes(val):
        try:
            val_str = str(val)
            if ':' in val_str:
                m, s = map(int, val_str.split(':'))
                return round(m + s/60, 1)
            return float(val)
        except: return 0.0

    df_combined['MINS_DECIMAL'] = df_combined['MINUTES'].apply(parse_minutes)
    df_combined['HI_RUN'] = df_combined['HIGH SPEED RUNNING'] + df_combined['SPRINTING']
    
    # Marker Hvidovre IF spillere
    target_id = HIF_SSIID.lower().strip()
    df_combined['Hold'] = df_combined['TEAM_SSIID'].astype(str).str.lower().str.strip().apply(
        lambda x: "Hvidovre IF" if x == target_id else "Modstander"
    )

    t1, t2, t3 = st.tabs(["Hvidovre IF", "Liga Top 5", "Enkelte Kampe"])

    with t1:
        # TRIN 1: Find alle unikke navne der har spillet for HIF i 2025/2026
        hif_squad_names = df_combined[df_combined['Hold'] == "Hvidovre IF"]['PLAYER_NAME'].unique()
        
        # Filtrér så vi kun ser disse spillere (og kun deres data fra de valgte kampe)
        df_hif_season = df_combined[df_combined['PLAYER_NAME'].isin(hif_squad_names)].copy()
        
        if not df_hif_season.empty:
            summary = df_hif_season.groupby('PLAYER_NAME').agg({
                'MATCH_SSIID': 'nunique',
                'MINS_DECIMAL': 'sum',
                'DISTANCE': 'sum',
                'HI_RUN': 'sum',
                'TOP_SPEED': 'max'
            }).reset_index().sort_values('DISTANCE', ascending=False)

            st.dataframe(
                summary, 
                column_config={
                    "PLAYER_NAME": "Spiller",
                    "MATCH_SSIID": "Kampe",
                    "MINS_DECIMAL": st.column_config.NumberColumn("Min.", format="%d"),
                    "DISTANCE": st.column_config.NumberColumn("Total Meter", format="%d"),
                    "HI_RUN": st.column_config.NumberColumn("HI Meter", format="%d"),
                    "TOP_SPEED": st.column_config.NumberColumn("Topfart", format="%.1f km/t")
                },
                use_container_width=True, hide_index=True,
                height=(len(summary) + 1) * 35 + 5
            )
        else:
            st.info("Søgning efter Hvidovre-spillere for 2025/2026 pågår...")

    with t2:
        # Top 5 uanset hold
        c1, c2 = st.columns(2)
        with c1:
            st.write("Topfart (km/t)")
            st.table(df_combined.groupby('PLAYER_NAME')['TOP_SPEED'].max().nlargest(5))
        with c2:
            st.write("HI Distance (m)")
            st.table(df_combined.groupby('PLAYER_NAME')['HI_RUN'].sum().nlargest(5))

    with t3:
        # Denne del virkede på dit billede - vi beholder logikken
        df_hif_matches = df_meta[(df_meta['HOME_SSIID'] == HIF_SSIID) | (df_meta['AWAY_SSIID'] == HIF_SSIID)].copy()
        df_hif_matches['LABEL'] = df_hif_matches['DATE'].astype(str) + " - " + df_hif_matches['DESCRIPTION']
        
        if not df_hif_matches.empty:
            valgt = st.selectbox("Vælg kamp", df_hif_matches['LABEL'].unique(), key="match_select")
            m_id = df_hif_matches[df_hif_matches['LABEL'] == valgt]['MATCH_SSIID'].values[0]
            
            df_match = df_combined[df_combined['MATCH_SSIID'] == m_id].sort_values(by=['Hold', 'DISTANCE'], ascending=[False, False])
            st.dataframe(
                df_match[['PLAYER_NAME', 'Hold', 'MINUTES', 'DISTANCE', 'HI_RUN', 'TOP_SPEED']], 
                use_container_width=True, hide_index=True,
                height=(len(df_match) + 1) * 35 + 5
            )
