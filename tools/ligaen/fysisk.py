import streamlit as st
import pandas as pd
from datetime import datetime

HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"

def vis_side(conn, name_map=None):
    @st.cache_data(ttl=600)
    def get_clean_data():
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 1. Hent kun kampe for denne sæson
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
        # Formatering til SQL IN clause
        formatted_ids = ','.join([f"'{i}'" for i in m_ids])

        # 2. Hent fysisk data - vi bruger de kolonner vi ved virker her
        query_phys = f"""
        SELECT 
            MATCH_SSIID, PLAYER_NAME, 
            MINUTES, DISTANCE, 
            "HIGH SPEED RUNNING", "SPRINTING", "TOP_SPEED"
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_SSIID IN ({formatted_ids})
        """
        
        # 3. Hent hold-tilhørsforhold separat for at undgå fejl i hoved-query
        query_teams = f"""
        SELECT MATCH_SSIID, PLAYER_NAME, TEAM_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER
        WHERE MATCH_SSIID IN ({formatted_ids})
        """
        
        return df_meta, conn.query(query_phys), conn.query(query_teams)

    df_meta, df_phys, df_teams = get_clean_data()

    if df_phys.empty:
        st.warning("Kunne ikke finde fysiske data for de valgte kampe.")
        return

    # --- SAMLING AF DATA ---
    # Vi renser navne for at sikre match
    df_phys['JOIN_KEY'] = df_phys['MATCH_SSIID'].astype(str) + df_phys['PLAYER_NAME'].str.lower().str.strip()
    df_teams['JOIN_KEY'] = df_teams['MATCH_SSIID'].astype(str) + df_teams['PLAYER_NAME'].str.lower().str.strip()
    
    df_combined = pd.merge(df_phys, df_teams[['JOIN_KEY', 'TEAM_SSIID']], on='JOIN_KEY', how='left')

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
    
    # Identificer Hvidovre IF
    df_combined['Hold'] = df_combined['TEAM_SSIID'].apply(
        lambda x: "Hvidovre IF" if str(x).lower().strip() == HIF_SSIID.lower().strip() else "Modstander"
    )

    t1, t2, t3 = st.tabs(["Hvidovre IF", "Liga Top 5", "Enkelte Kampe"])

    with t1:
        # Kun HIF-spillere fra denne sæsons kampe
        df_hif = df_combined[df_combined['Hold'] == "Hvidovre IF"].copy()
        
        # Hvis merging fejlede, bruger vi spiller-tæller som nødplan så Tab 1 ikke er tom
        if df_hif.empty:
            counts = df_combined.groupby('PLAYER_NAME')['MATCH_SSIID'].transform('nunique')
            df_hif = df_combined[counts > 1].copy()

        summary = df_hif.groupby('PLAYER_NAME').agg({
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
                "DISTANCE": st.column_config.NumberColumn("Meter", format="%d"),
                "HI_RUN": st.column_config.NumberColumn("HI Meter", format="%d"),
                "TOP_SPEED": st.column_config.NumberColumn("Topfart", format="%.1f km/t")
            },
            use_container_width=True, hide_index=True,
            height=(len(summary) + 1) * 35 + 5
        )

    with t2:
        c1, c2 = st.columns(2)
        with c1:
            st.write("Topfart (km/t)")
            st.table(df_combined.groupby('PLAYER_NAME')['TOP_SPEED'].max().nlargest(5))
        with c2:
            st.write("HI Distance (m)")
            st.table(df_combined.groupby('PLAYER_NAME')['HI_RUN'].sum().nlargest(5))

    with t3:
        df_hif_matches = df_meta[(df_meta['HOME_SSIID'] == HIF_SSIID) | (df_meta['AWAY_SSIID'] == HIF_SSIID)].copy()
        df_hif_matches['LABEL'] = df_hif_matches['DATE'].astype(str) + " - " + df_hif_matches['DESCRIPTION']
        
        if not df_hif_matches.empty:
            valgt = st.selectbox("Vælg kamp", df_hif_matches['LABEL'].unique(), label_visibility="collapsed")
            m_id = df_hif_matches[df_hif_matches['LABEL'] == valgt]['MATCH_SSIID'].values[0]
            
            df_match = df_combined[df_combined['MATCH_SSIID'] == m_id].sort_values(by=['Hold', 'DISTANCE'], ascending=[False, False])
            
            st.dataframe(
                df_match[['PLAYER_NAME', 'Hold', 'MINUTES', 'DISTANCE', 'HI_RUN', 'TOP_SPEED']], 
                use_container_width=True, hide_index=True,
                height=(len(df_match) + 1) * 35 + 5
            )
