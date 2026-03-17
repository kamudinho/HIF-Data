import streamlit as st
import pandas as pd
from datetime import datetime

HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"

def vis_side(conn, name_map=None):
    @st.cache_data(ttl=600)
    def get_final_data():
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 1. Hent metadata for at definere sæsonens kampe
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
            return df_meta, pd.DataFrame()
            
        m_ids = tuple(df_meta['MATCH_SSIID'].tolist())
        formatted_ids = ','.join([f"'{i}'" for i in m_ids])

        # 2. Hent data fra GAME_PLAYER. 
        # Jeg bruger " (anførselstegn) for at ramme de præcise kolonnenavne fra din tabel
        query_main = f"""
        SELECT 
            MATCH_SSIID, 
            TEAM_SSIID, 
            PLAYER_NAME, 
            DISTANCE, 
            "HIGHSPEEDRUNNING", 
            "HIGHSPEEDSPRINTING", 
            TOP_SPEED
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER
        WHERE MATCH_SSIID IN ({formatted_ids})
        """
        return df_meta, conn.query(query_main)

    try:
        df_meta, df_raw = get_final_data()
    except Exception as e:
        # Hvis den stadig fejler på navnet, prøver vi med mellemrum i stedet
        st.info("Prøver alternativ kolonne-formatering...")
        try:
            # Alternativ query hvis ovenstående fejler
            query_alt = df_raw = conn.query(f"""
                SELECT MATCH_SSIID, TEAM_SSIID, PLAYER_NAME, DISTANCE, 
                "HIGH SPEED RUNNING" as "HIGHSPEEDRUNNING", 
                "SPRINTING" as "HIGHSPEEDSPRINTING", 
                TOP_SPEED
                FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER
                WHERE MATCH_SSIID IN (SELECT MATCH_SSIID FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA WHERE "DATE" >= '2025-07-01')
            """)
            df_raw = query_alt
        except:
            st.error(f"SQL Fejl: {e}")
            return

    # Beregn HI_RUN
    df_raw['HI_RUN'] = df_raw['HIGHSPEEDRUNNING'] + df_raw['HIGHSPEEDSPRINTING']
    
    # Identificer Hvidovre IF
    target_id = HIF_SSIID.lower().strip()
    df_raw['Hold'] = df_raw['TEAM_SSIID'].astype(str).str.lower().str.strip().apply(
        lambda x: "Hvidovre IF" if x == target_id else "Modstander"
    )

    t1, t2, t3 = st.tabs(["Hvidovre IF", "Liga Top 5", "Enkelte Kampe"])

    with t1:
        # Kun Hvidovre spillere fra 2025/2026 kampe
        df_hif = df_raw[df_raw['Hold'] == "Hvidovre IF"].copy()
        
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
            use_container_width=True, hide_index=True,
            height=(len(summary) + 1) * 35 + 5
        )

    with t2:
        c1, c2 = st.columns(2)
        with c1:
            st.write("Topfart (km/t)")
            st.table(df_raw.groupby('PLAYER_NAME')['TOP_SPEED'].max().nlargest(5))
        with c2:
            st.write("HI Distance (m)")
            st.table(df_raw.groupby('PLAYER_NAME')['HI_RUN'].sum().nlargest(5))

    with t3:
        df_hif_m = df_meta[(df_meta['HOME_SSIID'] == HIF_SSIID) | (df_meta['AWAY_SSIID'] == HIF_SSIID)].copy()
        df_hif_m['LABEL'] = df_hif_m['DATE'].astype(str) + " - " + df_hif_m['DESCRIPTION']
        
        if not df_hif_m.empty:
            valgt = st.selectbox("Vælg kamp", df_hif_m['LABEL'].unique(), label_visibility="collapsed")
            m_id = df_hif_m[df_hif_m['LABEL'] == valgt]['MATCH_SSIID'].values[0]
            
            df_match = df_raw[df_raw['MATCH_SSIID'] == m_id].sort_values(by=['Hold', 'DISTANCE'], ascending=[False, False])
            
            st.dataframe(
                df_match[['PLAYER_NAME', 'Hold', 'DISTANCE', 'HI_RUN', 'TOP_SPEED']], 
                use_container_width=True, hide_index=True,
                height=(len(df_match) + 1) * 35 + 5
            )
