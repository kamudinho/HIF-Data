import streamlit as st
import pandas as pd
from datetime import datetime

# Konstanter
HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"

def vis_side(conn, name_map=None):
    @st.cache_data(ttl=600)
    def get_all_data():
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 1. Metadata: Alle kampe i perioden
        query_meta = f"""
        SELECT "DATE", HOME_SSIID, AWAY_SSIID, DESCRIPTION, MATCH_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA
        WHERE COMPETITION_OPTAUUID = '{COMP_UUID}' 
          AND "DATE" >= '2025-07-01'
          AND "DATE" <= '{today}'
        ORDER BY "DATE" DESC
        """
        
        # 2. Fysisk data (Præstationer)
        query_phys = """
        SELECT 
            MATCH_SSIID, PLAYER_NAME, 
            MINUTES, DISTANCE, 
            "HIGH SPEED RUNNING", "SPRINTING", "TOP_SPEED"
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        """

        # 3. Hold-tilhørsforhold (Fra din nye tabel)
        # Vi sikrer os at kolonnenavne matcher dit dump (TEAM_SSIID, PLAYER_NAME)
        query_teams = """
        SELECT DISTINCT MATCH_SSIID, PLAYER_NAME, TEAM_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER
        """
        
        return conn.query(query_meta), conn.query(query_phys), conn.query(query_teams)

    df_meta, df_phys, df_teams = get_all_data()

    # --- SAMMENKOBLING ---
    # Vi knytter TEAM_SSIID til de fysiske data
    df_combined = pd.merge(
        df_phys, 
        df_teams, 
        on=['MATCH_SSIID', 'PLAYER_NAME'], 
        how='left'
    )

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
    
    # Definer "Hold" baseret på SSIID
    df_combined['Hold'] = df_combined['TEAM_SSIID'].apply(
        lambda x: "Hvidovre IF" if str(x) == HIF_SSIID else "Modstander"
    )

    t1, t2, t3 = st.tabs(["Hvidovre IF", "Liga Top 5", "Enkelte Kampe"])

    with t1:
        # TRIN 1: Sæson-total for Hvidovre IF
        valid_match_ids = df_meta['MATCH_SSIID'].unique()
        df_hif_season = df_combined[
            (df_combined['Hold'] == "Hvidovre IF") & 
            (df_combined['MATCH_SSIID'].isin(valid_match_ids))
        ].copy()
        
        summary = df_hif_season.groupby('PLAYER_NAME').agg({
            'MINS_DECIMAL': 'sum',
            'DISTANCE': 'sum',
            'HI_RUN': 'sum',
            'TOP_SPEED': 'max'
        }).reset_index().sort_values('DISTANCE', ascending=False)

        st.dataframe(
            summary, 
            column_config={
                "PLAYER_NAME": "Spiller",
                "MINS_DECIMAL": st.column_config.NumberColumn("Minutter", format="%d"),
                "DISTANCE": st.column_config.NumberColumn("Total Meter", format="%d"),
                "HI_RUN": st.column_config.NumberColumn("HI Meter", format="%d"),
                "TOP_SPEED": st.column_config.NumberColumn("Topfart", format="%.1f km/t")
            },
            use_container_width=True, hide_index=True,
            height=(len(summary) + 1) * 35 + 5
        )

    with t2:
        # TRIN 2: Ligaens top-præstationer (Alle spillere i perioden)
        df_liga = df_combined[df_combined['MATCH_SSIID'].isin(df_meta['MATCH_SSIID'].unique())]
        c1, c2 = st.columns(2)
        with c1:
            st.write("Topfart (km/t)")
            st.table(df_liga.groupby('PLAYER_NAME')['TOP_SPEED'].max().nlargest(5))
        with c2:
            st.write("HI Distance total (m)")
            st.table(df_liga.groupby('PLAYER_NAME')['HI_RUN'].sum().nlargest(5))

    with t3:
        # TRIN 3: Enkelte kampe med korrekt sortering
        df_hif_matches = df_meta[(df_meta['HOME_SSIID'] == HIF_SSIID) | (df_meta['AWAY_SSIID'] == HIF_SSIID)].copy()
        df_hif_matches['LABEL'] = df_hif_matches['DATE'].astype(str) + " - " + df_hif_matches['DESCRIPTION']
        
        if not df_hif_matches.empty:
            valgt = st.selectbox("Vælg kamp", df_hif_matches['LABEL'].unique(), label_visibility="collapsed")
            m_id = df_hif_matches[df_hif_matches['LABEL'] == valgt]['MATCH_SSIID'].values[0]
            
            df_match = df_combined[df_combined['MATCH_SSIID'] == m_id].copy()
            # SORTERING: Først Hold (Hvidovre IF kommer før Modstander alfabetisk), så Distance
            df_match = df_match.sort_values(by=['Hold', 'DISTANCE'], ascending=[False, False])
            
            st.dataframe(
                df_match[['PLAYER_NAME', 'Hold', 'MINUTES', 'DISTANCE', 'HI_RUN', 'TOP_SPEED']], 
                use_container_width=True, hide_index=True,
                height=(len(df_match) + 1) * 35 + 5
            )
