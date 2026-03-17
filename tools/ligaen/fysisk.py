import streamlit as st
import pandas as pd

HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"

def vis_side(conn, name_map=None):
    @st.cache_data(ttl=600)
    def get_all_data():
        query_meta = f"""
        SELECT "DATE", HOME_SSIID, AWAY_SSIID, DESCRIPTION, MATCH_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA
        WHERE COMPETITION_OPTAUUID = '{COMP_UUID}' AND YEAR = '2025'
        """
        query_phys = """
        SELECT 
            MATCH_SSIID, MATCH_TEAMS, PLAYER_NAME, 
            MINUTES, DISTANCE, 
            "HIGH SPEED RUNNING", "SPRINTING", "TOP_SPEED"
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        """
        return conn.query(query_meta), conn.query(query_phys)

    df_meta, df_phys = get_all_data()

    # Konvertering af MM:SS til tal
    def parse_minutes(val):
        try:
            val_str = str(val)
            if ':' in val_str:
                m, s = map(int, val_str.split(':'))
                return round(m + s/60, 1)
            return float(val)
        except: return 0.0

    df_phys['MINS_DECIMAL'] = df_phys['MINUTES'].apply(parse_minutes)
    df_phys['HI_RUN'] = df_phys['HIGH SPEED RUNNING'] + df_phys['SPRINTING']

    t1, t2, t3 = st.tabs(["Hvidovre IF", "Liga Top 5", "Enkelte Kampe"])

    with t1:
        # 1. Filtrér KUN Hvidovre spillere (vi bruger både tekst og SSIID-logik hvis muligt)
        # Vi leder efter HVI eller Hvidovre i MATCH_TEAMS kolonnen
        df_hif_only = df_phys[df_phys['MATCH_TEAMS'].str.contains('Hvidovre|HVI', case=False, na=False)].copy()
        
        # 2. Sammentæl (Aggregér) alle rækker per spiller
        summary = df_hif_only.groupby('PLAYER_NAME').agg({
            'MINS_DECIMAL': 'sum',
            'DISTANCE': 'sum',
            'HI_RUN': 'sum',
            'TOP_SPEED': 'max'
        }).reset_index()

        # 3. Beregn gennemsnit eller sortering
        summary = summary.sort_values('DISTANCE', ascending=False)

        st.dataframe(
            summary, 
            column_config={
                "PLAYER_NAME": "Spiller",
                "MINS_DECIMAL": st.column_config.NumberColumn("Minutter", format="%d"),
                "DISTANCE": st.column_config.NumberColumn("Total Meter", format="%d"),
                "HI_RUN": st.column_config.NumberColumn("HI Meter", format="%d"),
                "TOP_SPEED": st.column_config.NumberColumn("Topfart", format="%.1f km/t")
            },
            use_container_width=True, 
            hide_index=True
        )

    with t2:
        # Liga overblik baseret på alle kampe i COMP_UUID
        df_liga = df_phys[df_phys['MATCH_SSIID'].isin(df_meta['MATCH_SSIID'].unique())]
        c1, c2 = st.columns(2)
        with c1:
            st.write("Topfart (km/t)")
            st.table(df_liga.groupby('PLAYER_NAME')['TOP_SPEED'].max().nlargest(5))
        with c2:
            st.write("HI Distance (m)")
            st.table(df_liga.groupby('PLAYER_NAME')['HI_RUN'].sum().nlargest(5))

    with t3:
        # Vælg specifik kamp for at se alle spillere (HIF + Modstander)
        df_hif_matches = df_meta[(df_meta['HOME_SSIID'] == HIF_SSIID) | (df_meta['AWAY_SSIID'] == HIF_SSIID)].copy()
        df_hif_matches['LABEL'] = df_hif_matches['DATE'].astype(str) + " - " + df_hif_matches['DESCRIPTION']
        
        if not df_hif_matches.empty:
            valgt = st.selectbox("Vælg kamp", df_hif_matches['LABEL'].unique(), label_visibility="collapsed")
            m_id = df_hif_matches[df_hif_matches['LABEL'] == valgt]['MATCH_SSIID'].values[0]
            
            df_match = df_phys[df_phys['MATCH_SSIID'] == m_id].sort_values('DISTANCE', ascending=False)
            st.dataframe(
                df_match[['PLAYER_NAME', 'MATCH_TEAMS', 'MINUTES', 'DISTANCE', 'HI_RUN', 'TOP_SPEED']], 
                use_container_width=True, 
                hide_index=True
            )
