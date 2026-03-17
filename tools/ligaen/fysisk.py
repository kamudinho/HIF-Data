import streamlit as st
import pandas as pd
from datetime import datetime

HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
# Vi bruger din bekræftede OPTA UUID for NordicBet Liga 25/26
COMP_UUID = "6ifaeunfdelecgticvxanikzu" 

def vis_side(conn, name_map=None):
    @st.cache_data(ttl=600)
    def get_final_data():
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 1. Metadata - Finder kampene for den nye sæson
        query_meta = f"""
        SELECT "DATE", DESCRIPTION, MATCH_SSIID, HOME_SSIID, AWAY_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA
        WHERE (COMPETITION_OPTAUUID = '{COMP_UUID}' OR COMPETITION_OPTAID = '148')
          AND "DATE" >= '2025-07-01'
        ORDER BY "DATE" DESC
        """
        df_meta = conn.query(query_meta)
        
        if df_meta.empty:
            return pd.DataFrame(), pd.DataFrame()

        m_ids = tuple(df_meta['MATCH_SSIID'].tolist())
        formatted_ids = ",".join([f"'{i}'" for i in m_ids])

        # 2. Fysisk data - VI SKIFTER TIL F53A FOR AT FÅ 2025 DATA
        # Vi tager alt (P.*) som du foreslog, for at være sikre
        query_phys = f"""
        SELECT *
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER
        WHERE MATCH_SSIID IN ({formatted_ids})
        """
        df_phys = conn.query(query_phys)
        
        return df_meta, df_phys

    df_meta, df_phys = get_final_data()

    if df_phys.empty:
        st.warning("Fandt ingen fysiske data for 25/26 sæsonen i F53A tabellen.")
        return

    # --- DATABEHANDLING ---
    # Vi bruger de præcise kolonnenavne fra dit råtræk:
    # HIGHSPEEDRUNNING og HIGHSPEEDSPRINTING
    df_phys['HI_RUN'] = df_phys['HIGHSPEEDRUNNING'] + df_phys['HIGHSPEEDSPRINTING']
    
    # Identificer Hvidovre spillere via TEAM_SSIID
    df_phys['Is_HIF'] = df_phys['TEAM_SSIID'].str.lower() == HIF_SSIID.lower()

    # Tab-opdeling
    t1, t2, t3 = st.tabs(["Hvidovre IF", "Liga Top 5", "Enkelte Kampe"])

    with t1:
        # Kun Hvidovre spillere
        df_hif = df_phys[df_phys['Is_HIF'] == True].copy()
        
        if not df_hif.empty:
            summary = df_hif.groupby('PLAYER_NAME').agg({
                'MATCH_SSIID': 'nunique',
                'DISTANCE': 'sum',
                'HI_RUN': 'sum',
                'TOP_SPEED': 'max'
            }).reset_index().sort_values('DISTANCE', ascending=False)

            st.dataframe(
                summary, 
                column_config={
                    "PLAYER_NAME": "Spiller",
                    "MATCH_SSIID": "Kampe",
                    "DISTANCE": st.column_config.NumberColumn("Total Meter", format="%d"),
                    "HI_RUN": st.column_config.NumberColumn("HI Meter", format="%d"),
                    "TOP_SPEED": st.column_config.NumberColumn("Topfart", format="%.1f km/t")
                },
                use_container_width=True, hide_index=True
            )
        else:
            st.error("Ingen spillere fundet for Hvidovre. Tjek om TEAM_SSIID matcher.")

    with t2:
        # Liga Top 5 (Alle hold i de fundne kampe)
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Topfart (km/t)**")
            st.table(df_phys.groupby('PLAYER_NAME')['TOP_SPEED'].max().nlargest(5))
        with c2:
            st.write("**HI Distance (m)**")
            st.table(df_phys.groupby('PLAYER_NAME')['HI_RUN'].sum().nlargest(5))

    with t3:
        # Kampvælger baseret på metadata
        df_meta_hif = df_meta[df_meta['MATCH_SSIID'].isin(df_phys['MATCH_SSIID'].unique())].copy()
        df_meta_hif['LABEL'] = df_meta_hif['DATE'].astype(str) + " - " + df_meta_hif['DESCRIPTION']
        
        valgt = st.selectbox("Vælg kamp", df_meta_hif['LABEL'].unique())
        m_id = df_meta_hif[df_meta_hif['LABEL'] == valgt]['MATCH_SSIID'].values[0]
        
        df_match = df_phys[df_phys['MATCH_SSIID'] == m_id].copy()
        df_match['Hold'] = df_match['Is_HIF'].map({True: "Hvidovre IF", False: "Modstander"})
        df_match = df_match.sort_values(by=['Is_HIF', 'DISTANCE'], ascending=[False, False])
        
        st.dataframe(df_match[['PLAYER_NAME', 'Hold', 'DISTANCE', 'HI_RUN', 'TOP_SPEED']], use_container_width=True, hide_index=True)
