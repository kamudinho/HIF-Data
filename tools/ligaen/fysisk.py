import streamlit as st
import pandas as pd
from datetime import datetime

HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"

def vis_side(conn, name_map=None):
    @st.cache_data(ttl=600)
    def get_final_data():
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 1. Metadata (Hvem er modstanderen i hver kamp?)
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

        # 2. Fysisk data
        query_phys = f"""
        SELECT MATCH_SSIID, PLAYER_NAME, MINUTES, DISTANCE, 
               "HIGH SPEED RUNNING", "SPRINTING", "TOP_SPEED"
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_SSIID IN ({formatted_ids})
        """
        
        # 3. Hold-data (Vi bruger kun denne til at identificere modstanderens ID)
        query_teams = f"""
        SELECT DISTINCT MATCH_SSIID, PLAYER_NAME, TEAM_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER
        WHERE MATCH_SSIID IN ({formatted_ids})
        """
        
        return df_meta, conn.query(query_phys), conn.query(query_teams)

    df_meta, df_phys, df_teams = get_final_data()

    # --- MATCHING LOGIK ---
    # Vi parrer fysisk data med team_ssiid
    df_phys['KEY'] = df_phys['MATCH_SSIID'].astype(str) + df_phys['PLAYER_NAME'].str.lower().str.strip()
    df_teams['KEY'] = df_teams['MATCH_SSIID'].astype(str) + df_teams['PLAYER_NAME'].str.lower().str.strip()
    
    df_combined = pd.merge(df_phys, df_teams[['KEY', 'TEAM_SSIID']], on='KEY', how='left')

    # Beregn værdier
    df_combined['HI_RUN'] = df_combined['HIGH SPEED RUNNING'] + df_combined['SPRINTING']
    
    # Identifikation: Hvis TEAM_SSIID matcher HIF, eller hvis TEAM_SSIID er tom men spilleren har spillet for HIF før
    hif_id_clean = HIF_SSIID.lower().strip()
    df_combined['Is_HIF'] = df_combined['TEAM_SSIID'].astype(str).str.lower().str.strip() == hif_id_clean
    
    # Vi finder alle navne, der mindst én gang er markeret som HIF
    hif_names = df_combined[df_combined['Is_HIF'] == True]['PLAYER_NAME'].unique()
    
    # Tab-opdeling
    t1, t2, t3 = st.tabs(["Hvidovre IF", "Liga Top 5", "Enkelte Kampe"])

    with t1:
        # Vi viser alle spillere fra listen over bekræftede HIF-navne
        df_hif = df_combined[df_combined['PLAYER_NAME'].isin(hif_names)].copy()
        
        if not df_hif.empty:
            summary = df_hif.groupby('PLAYER_NAME').agg({
                'MATCH_SSIID': 'nunique',
                'DISTANCE': 'sum',
                'HI_RUN': 'sum',
                'TOP_SPEED': 'max'
            }).reset_index().sort_values('DISTANCE', ascending=False)

            st.dataframe(summary, use_container_width=True, hide_index=True)
        else:
            st.warning("Ingen spillere matchede Hvidovre IF ID'et. Tjekker TEAM_SSIID formatering...")

    with t2:
        c1, c2 = st.columns(2)
        with c1:
            st.write("Topfart (km/t)")
            st.table(df_combined.groupby('PLAYER_NAME')['TOP_SPEED'].max().nlargest(5))
        with c2:
            st.write("HI Distance (m)")
            st.table(df_combined.groupby('PLAYER_NAME')['HI_RUN'].sum().nlargest(5))

    with t3:
        # Din velfungerende kamp-oversigt
        df_hif_m = df_meta[(df_meta['HOME_SSIID'] == HIF_SSIID) | (df_meta['AWAY_SSIID'] == HIF_SSIID)].copy()
        df_hif_m['LABEL'] = df_hif_m['DATE'].astype(str) + " - " + df_hif_m['DESCRIPTION']
        
        if not df_hif_m.empty:
            valgt = st.selectbox("Vælg kamp", df_hif_m['LABEL'].unique())
            m_id = df_hif_m[df_hif_m['LABEL'] == valgt]['MATCH_SSIID'].values[0]
            
            df_match = df_combined[df_combined['MATCH_SSIID'] == m_id].copy()
            df_match['Hold'] = df_match['Is_HIF'].map({True: "Hvidovre IF", False: "Modstander"})
            df_match = df_match.sort_values(by=['Is_HIF', 'DISTANCE'], ascending=[False, False])
            
            st.dataframe(df_match[['PLAYER_NAME', 'Hold', 'DISTANCE', 'HI_RUN', 'TOP_SPEED']], use_container_width=True, hide_index=True)
