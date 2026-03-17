import streamlit as st
import pandas as pd

# Konstanter baseret på din data
HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"

def vis_side(conn, name_map=None):
    st.title("Hvidovre IF | Fysisk Data")

    # --- TRIN 1: HENT DATA (Med rettet SQL-syntaks) ---
    @st.cache_data(ttl=600)
    def get_all_data():
        # Metadata
        query_meta = f"""
        SELECT "DATE", HOME_SSIID, AWAY_SSIID, DESCRIPTION, MATCH_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA
        WHERE COMPETITION_OPTAUUID = '{COMP_UUID}' AND YEAR = '2025'
        """
        # Fysisk data (Bemærk citationstegnene her - det er dem der fjerner fejlen)
        query_phys = """
        SELECT 
            MATCH_SSIID, MATCH_TEAMS, PLAYER_NAME, 
            MINUTES, DISTANCE, 
            "HIGH SPEED RUNNING", "SPRINTING", "TOP_SPEED"
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        """
        return conn.query(query_meta), conn.query(query_phys)

    df_meta, df_phys = get_all_data()

    # --- TRIN 2: RENSNING OG BEREGNING ---
    def parse_minutes(val):
        try:
            if ':' in str(val):
                m, s = map(int, str(val).split(':'))
                return round(m + s/60, 1)
            return float(val)
        except: return 0.0

    df_phys['MINS_DECIMAL'] = df_phys['MINUTES'].apply(parse_minutes)
    # HI_RUN beregnes i Python for at undgå SQL-identifikationsfejl
    df_phys['HI_RUN'] = df_phys['HIGH SPEED RUNNING'] + df_phys['SPRINTING']

    # --- TRIN 3: TABS ---
    t1, t2, t3 = st.tabs(["Hvidovre IF", "Liga Top 5", "Enkelte Kampe"])

    with t1:
        # Filtrer via MATCH_TEAMS som vi ved virker for HIF
        df_hif = df_phys[df_phys['MATCH_TEAMS'].str.contains('Hvidovre', case=False, na=False)].copy()
        
        summary = df_hif.groupby('PLAYER_NAME').agg({
            'MINS_DECIMAL': 'sum',
            'DISTANCE': 'sum',
            'HI_RUN': 'sum',
            'TOP_SPEED': 'max'
        }).reset_index().sort_values('DISTANCE', ascending=False)

        st.dataframe(summary, 
                     column_config={"MINS_DECIMAL": "Minutter total"},
                     use_container_width=True, hide_index=True)

    with t2:
        # Liga overblik (kun kampe fra den valgte liga-uuid)
        df_liga = df_phys[df_phys['MATCH_SSIID'].isin(df_meta['MATCH_SSIID'].unique())]
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Topfart (km/t)**")
            top_speed = df_liga.groupby('PLAYER_NAME')['TOP_SPEED'].max().nlargest(5)
            st.table(top_speed)
        with col2:
            st.write("**HI Distance total (m)**")
            top_hi = df_liga.groupby('PLAYER_NAME')['HI_RUN'].sum().nlargest(5)
            st.table(top_hi)

    with t3:
        # Kampvælger (HIF kampe)
        df_hif_matches = df_meta[(df_meta['HOME_SSIID'] == HIF_SSIID) | (df_meta['AWAY_SSIID'] == HIF_SSIID)].copy()
        df_hif_matches['LABEL'] = df_hif_matches['DATE'].astype(str) + " - " + df_hif_matches['DESCRIPTION']
        
        if not df_hif_matches.empty:
            valgt = st.selectbox("Vælg kamp", df_hif_matches['LABEL'].unique())
            m_id = df_hif_matches[df_hif_matches['LABEL'] == valgt]['MATCH_SSIID'].values[0]
            
            # Vis alle spillere i den kamp (både HIF og modstander)
            df_match = df_phys[df_phys['MATCH_SSIID'] == m_id].sort_values('DISTANCE', ascending=False)
            st.dataframe(df_match[['PLAYER_NAME', 'MATCH_TEAMS', 'MINUTES', 'DISTANCE', 'HI_RUN', 'TOP_SPEED']], 
                         use_container_width=True, hide_index=True)
        else:
            st.info("Ingen kampe fundet i metadata.")
