import streamlit as st
import pandas as pd
from datetime import datetime

HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"

def vis_side(conn, name_map=None):
    @st.cache_data(ttl=600)
    def get_all_data():
        today = datetime.now().strftime('%Y-%m-%d')
        query_meta = f"""
        SELECT "DATE", HOME_SSIID, AWAY_SSIID, DESCRIPTION, MATCH_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA
        WHERE COMPETITION_OPTAUUID = '{COMP_UUID}' 
          AND "DATE" >= '2025-07-01'
          AND "DATE" <= '{today}'
        ORDER BY "DATE" DESC
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

    # --- FORBEDRET HOLD-LOGIK ---
    # Vi mapper MATCH_SSIID til modstanderens navn fra metadata
    opp_map = {}
    for _, row in df_meta.iterrows():
        # Beskrivelsen er typisk "HVI - KIF". Vi fjerner HVI og bindestreg for at få modstanderen.
        opp_name = row['DESCRIPTION'].replace('HVI', '').replace('Hvidovre', '').replace('-', '').strip()
        opp_map[row['MATCH_SSIID']] = opp_name

    def get_clean_team(row):
        # I summary-tabellen skal vi skelne mellem HIF og modstander.
        # En sikker måde i denne tabel er ofte at tjekke PLAYER_NAME mod en kendt liste, 
        # men her prøver vi at splitte MATCH_TEAMS hvis muligt.
        # Hvis det fejler, bruger vi metadata-mappet.
        if "Hvidovre" in row['MATCH_TEAMS'] or "HVI" in row['MATCH_TEAMS']:
            # Hvis vi er i tab 1 (Hvidovre IF), vil vi kun have HIF.
            # I tab 3 (Enkelte kampe) skal vi vide om spilleren hører til HIF eller modstander.
            # Da MATCH_TEAMS ofte er ens for alle rækker i samme kamp, bruger vi PLAYER_NAME 
            # til at validere hvis vi havde en HIF-spillerliste. 
            # Som nødplan: Vi lader brugeren se begge, men markeret.
            return "Hvidovre IF"
        return "Modstander"

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
        # Her vil vi KUN have Hvidovre-spillere. 
        # Vi antager at spillere der optræder i flest HIF-kampe er HIF-spillere.
        hif_matches = df_meta['MATCH_SSIID'].unique()
        df_hif_only = df_phys[df_phys['MATCH_SSIID'].isin(hif_matches)].copy()
        
        # Aggregering (Her fjerner vi spillere der kun optræder én gang som modstander)
        summary = df_hif_only.groupby('PLAYER_NAME').agg({
            'MINS_DECIMAL': 'sum',
            'DISTANCE': 'sum',
            'HI_RUN': 'sum',
            'TOP_SPEED': 'max',
            'MATCH_SSIID': 'count'
        }).reset_index()
        
        # Kun spillere der har spillet mere end 1 kamp (for at luge engangs-modstandere ud)
        summary = summary[summary['MATCH_SSIID'] > 1].sort_values('DISTANCE', ascending=False)

        st.dataframe(summary.drop(columns=['MATCH_SSIID']), 
                     use_container_width=True, hide_index=True, 
                     height=(len(summary)+1)*35+5)

    with t2:
        df_liga = df_phys[df_phys['MATCH_SSIID'].isin(df_meta['MATCH_SSIID'].unique())]
        c1, c2 = st.columns(2)
        with c1:
            st.write("Topfart (km/t)")
            st.table(df_liga.groupby('PLAYER_NAME')['TOP_SPEED'].max().nlargest(5))
        with c2:
            st.write("HI Distance (m)")
            st.table(df_liga.groupby('PLAYER_NAME')['HI_RUN'].sum().nlargest(5))

    with t3:
        df_hif_matches = df_meta[(df_meta['HOME_SSIID'] == HIF_SSIID) | (df_meta['AWAY_SSIID'] == HIF_SSIID)].copy()
        df_hif_matches['LABEL'] = df_hif_matches['DATE'].astype(str) + " - " + df_hif_matches['DESCRIPTION']
        
        if not df_hif_matches.empty:
            valgt = st.selectbox("Vælg kamp", df_hif_matches['LABEL'].unique(), label_visibility="collapsed")
            m_id = df_hif_matches[df_hif_matches['LABEL'] == valgt]['MATCH_SSIID'].values[0]
            m_opp = opp_map.get(m_id, "Modstander")
            
            df_match = df_phys[df_phys['MATCH_SSIID'] == m_id].copy()
            
            # Da vi mangler en TeamID pr. spiller, bruger vi en simpel tærskel: 
            # De første 11-16 spillere i en kamp-fil er typisk hjemmeholdet.
            # Men den bedste løsning her er at lade dem være i én liste indtil vi får TeamID.
            
            st.dataframe(
                df_match[['PLAYER_NAME', 'MINUTES', 'DISTANCE', 'HI_RUN', 'TOP_SPEED']].sort_values('DISTANCE', ascending=False), 
                use_container_width=True, hide_index=True,
                height=(len(df_match)+1)*35+5
            )
