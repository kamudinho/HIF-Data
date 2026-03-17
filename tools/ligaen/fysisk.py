import streamlit as st
import pandas as pd
from datetime import datetime

# Dine faste værdier
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
            MATCH_SSIID, PLAYER_NAME, 
            MINUTES, DISTANCE, 
            "HIGH SPEED RUNNING", "SPRINTING", "TOP_SPEED"
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        """

        # Vi henter TEAM_SSIID her. Vi bruger "AS", så vi er sikre på navnet.
        query_teams = """
        SELECT DISTINCT MATCH_SSIID, PLAYER_NAME, TEAM_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER
        """
        
        return conn.query(query_meta), conn.query(query_phys), conn.query(query_teams)

    df_meta, df_phys, df_teams = get_all_data()

    # --- ROBUST MATCHING ---
    # Vi gør alt til lowercase og fjerner spaces for at sikre match
    df_teams['MATCH_KEY'] = df_teams['MATCH_SSIID'].astype(str) + df_teams['PLAYER_NAME'].astype(str).str.lower().str.strip()
    df_phys['MATCH_KEY'] = df_phys['MATCH_SSIID'].astype(str) + df_phys['PLAYER_NAME'].astype(str).str.lower().str.strip()
    
    # Merge hold-info på præstationerne
    df_combined = pd.merge(
        df_phys, 
        df_teams[['MATCH_KEY', 'TEAM_SSIID']], 
        on='MATCH_KEY', 
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
    
    # "Blødt" tjek på ID
    target_id = HIF_SSIID.lower().strip()
    df_combined['Hold'] = df_combined['TEAM_SSIID'].astype(str).str.lower().str.strip().apply(
        lambda x: "Hvidovre IF" if x == target_id else "Modstander"
    )

    t1, t2, t3 = st.tabs(["Hvidovre IF", "Liga Top 5", "Enkelte Kampe"])

    with t1:
        valid_ids = df_meta['MATCH_SSIID'].unique()
        # Fallback: Hvis hold-matching stadig driller, viser vi spillere med > 1 kamp
        df_hif = df_combined[df_combined['Hold'] == "Hvidovre IF"].copy()
        
        if df_hif.empty:
            # Hvis den er tom pga. ID-fejl, så tag spillere der optræder ofte (som før)
            appearance_count = df_combined[df_combined['MATCH_SSIID'].isin(valid_ids)].groupby('PLAYER_NAME')['MATCH_SSIID'].nunique()
            hif_squad = appearance_count[appearance_count > 1].index.tolist()
            df_hif = df_combined[df_combined['PLAYER_NAME'].isin(hif_squad)].copy()

        summary = df_hif.groupby('PLAYER_NAME').agg({
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
            use_container_width=True, hide_index=True,
            height=(len(summary) + 1) * 35 + 5
        )

    with t2:
        df_liga = df_combined[df_combined['MATCH_SSIID'].isin(df_meta['MATCH_SSIID'].unique())]
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
            
            df_match = df_combined[df_combined['MATCH_SSIID'] == m_id].copy()
            df_match = df_match.sort_values(by=['Hold', 'DISTANCE'], ascending=[False, False])
            
            st.dataframe(
                df_match[['PLAYER_NAME', 'Hold', 'MINUTES', 'DISTANCE', 'HI_RUN', 'TOP_SPEED']], 
                use_container_width=True, hide_index=True,
                height=(len(df_match) + 1) * 35 + 5
            )
