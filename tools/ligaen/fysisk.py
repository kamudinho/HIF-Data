import streamlit as st
import pandas as pd
from datetime import datetime

HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"

def vis_side(conn, name_map=None):
    @st.cache_data(ttl=600)
    def get_all_data():
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 1. Metadata: Kun færdigspillede kampe fra denne sæson
        query_meta = f"""
        SELECT "DATE", HOME_SSIID, AWAY_SSIID, DESCRIPTION, MATCH_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA
        WHERE COMPETITION_OPTAUUID = '{COMP_UUID}' 
          AND "DATE" >= '2025-07-01'
          AND "DATE" <= '{today}'
        ORDER BY "DATE" DESC
        """
        
        # 2. Fysisk data - her bruger vi de sikre kolonner fra SUMMARY tabellen
        query_phys = """
        SELECT 
            MATCH_SSIID, MATCH_TEAMS, PLAYER_NAME, 
            MINUTES, DISTANCE, 
            "HIGH SPEED RUNNING", "SPRINTING", "TOP_SPEED"
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        """
        return conn.query(query_meta), conn.query(query_phys)

    try:
        df_meta, df_phys = get_all_data()
    except Exception as e:
        st.error(f"SQL Fejl: {e}")
        return

    # --- LOGIK TIL AT SKILLE HOLDENE AD ---
    # Vi identificerer HIF-spillere ved at se på dem, der optræder i flest Hvidovre-kampe
    # Da vi ved, at modstanderne skifter hver uge, er HIF-spillerne de eneste gengangere.
    hif_match_ids = df_meta['MATCH_SSIID'].unique()
    df_period = df_phys[df_phys['MATCH_SSIID'].isin(hif_match_ids)].copy()

    # Tæl hvor mange HIF-kampe hver spiller har spillet i denne periode
    appearance_count = df_period.groupby('PLAYER_NAME')['MATCH_SSIID'].nunique()
    hif_squad = appearance_count[appearance_count > 1].index.tolist()

    def parse_minutes(val):
        try:
            val_str = str(val)
            if ':' in val_str:
                m, s = map(int, val_str.split(':'))
                return round(m + s/60, 1)
            return float(val)
        except: return 0.0

    df_period['MINS_DECIMAL'] = df_period['MINUTES'].apply(parse_minutes)
    df_period['HI_RUN'] = df_period['HIGH SPEED RUNNING'] + df_period['SPRINTING']
    df_period['Hold'] = df_period['PLAYER_NAME'].apply(lambda x: "Hvidovre IF" if x in hif_squad else "Modstander")

    t1, t2, t3 = st.tabs(["Hvidovre IF", "Liga Top 5", "Enkelte Kampe"])

    with t1:
        # Samlet oversigt for HIF-truppen
        df_hif_only = df_period[df_period['Hold'] == "Hvidovre IF"].copy()
        
        summary = df_hif_only.groupby('PLAYER_NAME').agg({
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
                "DISTANCE": st.column_config.NumberColumn("Meter", format="%d"),
                "HI_RUN": st.column_config.NumberColumn("HI Meter", format="%d"),
                "TOP_SPEED": st.column_config.NumberColumn("Topfart", format="%.1f km/t")
            },
            use_container_width=True, 
            hide_index=True,
            height=(len(summary) + 1) * 35 + 5
        )

    with t2:
        # Liga overblik
        c1, c2 = st.columns(2)
        with c1:
            st.write("Topfart (km/t)")
            st.table(df_period.groupby('PLAYER_NAME')['TOP_SPEED'].max().nlargest(5))
        with c2:
            st.write("HI Distance (m)")
            st.table(df_period.groupby('PLAYER_NAME')['HI_RUN'].sum().nlargest(5))

    with t3:
        # Kampvælger
        df_hif_matches = df_meta[(df_meta['HOME_SSIID'] == HIF_SSIID) | (df_meta['AWAY_SSIID'] == HIF_SSIID)].copy()
        df_hif_matches['LABEL'] = df_hif_matches['DATE'].astype(str) + " - " + df_hif_matches['DESCRIPTION']
        
        if not df_hif_matches.empty:
            valgt = st.selectbox("Vælg kamp", df_hif_matches['LABEL'].unique(), label_visibility="collapsed")
            m_id = df_hif_matches[df_hif_matches['LABEL'] == valgt]['MATCH_SSIID'].values[0]
            
            df_match = df_period[df_period['MATCH_SSIID'] == m_id].sort_values(['Hold', 'DISTANCE'], ascending=[False, False])
            
            st.dataframe(
                df_match[['PLAYER_NAME', 'Hold', 'MINUTES', 'DISTANCE', 'HI_RUN', 'TOP_SPEED']], 
                use_container_width=True, 
                hide_index=True,
                height=(len(df_match) + 1) * 35 + 5
            )
