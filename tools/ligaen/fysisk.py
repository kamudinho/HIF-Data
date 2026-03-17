import streamlit as st
import pandas as pd
from datetime import datetime

# 1. DEFINER TRUPPEN (Navnene skal matche dem i Second Spectrum / Opta)
HIF_SQUAD = [
    "M. Jensen", "M. Spelmann", "C. Jakobsen", "N. Geertsen", 
    "A. Iljazovski", "M. Kaalund", "L. Qamili", "T. Thomsen",
    "J. Lindberg", "E. Pappoe", "K. Stenderup", "F. Carlsen" 
    # Tilføj selv resten af de aktuelle navne her...
]

HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"

def vis_side(conn, name_map=None):
    @st.cache_data(ttl=600)
    def get_data():
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Metadata for 2025/2026
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

        # Fysisk data - Vi henter kun for de kampe vi fandt i metadata
        query_phys = f"""
        SELECT MATCH_SSIID, PLAYER_NAME, DISTANCE, 
               "HIGH SPEED RUNNING", "SPRINTING", "TOP_SPEED"
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_SSIID IN ({formatted_ids})
        """
        return df_meta, conn.query(query_phys)

    df_meta, df_phys = get_data()

    if df_phys.empty:
        st.warning("Ingen data fundet.")
        return

    # --- LOGIK BASERET PÅ SPILLERLISTE ---
    df_phys['HI_RUN'] = df_phys['HIGH SPEED RUNNING'] + df_phys['SPRINTING']
    
    # Vi tjekker om navnet findes i vores HIF_SQUAD liste
    df_phys['Er_HIF'] = df_phys['PLAYER_NAME'].isin(HIF_SQUAD)
    df_phys['Hold'] = df_phys['Er_HIF'].map({True: "Hvidovre IF", False: "Modstander"})

    t1, t2, t3 = st.tabs(["Hvidovre IF", "Liga Top 5", "Enkelte Kampe"])

    with t1:
        # Tab 1: Viser kun dem fra din liste
        df_hif = df_phys[df_phys['Er_HIF'] == True].copy()
        
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

    with t2:
        # Liga Top 5 (Alle)
        c1, c2 = st.columns(2)
        with c1:
            st.write("Topfart (km/t)")
            st.table(df_phys.groupby('PLAYER_NAME')['TOP_SPEED'].max().nlargest(5))
        with c2:
            st.write("HI Distance (m)")
            st.table(df_phys.groupby('PLAYER_NAME')['HI_RUN'].sum().nlargest(5))

    with t3:
        # Enkelte kampe - sorteret så HIF er øverst
        df_hif_m = df_meta[(df_meta['HOME_SSIID'] == HIF_SSIID) | (df_meta['AWAY_SSIID'] == HIF_SSIID)].copy()
        df_hif_m['LABEL'] = df_hif_m['DATE'].astype(str) + " - " + df_hif_m['DESCRIPTION']
        
        if not df_hif_m.empty:
            valgt = st.selectbox("Vælg kamp", df_hif_m['LABEL'].unique())
            m_id = df_hif_m[df_hif_m['LABEL'] == valgt]['MATCH_SSIID'].values[0]
            
            df_match = df_phys[df_phys['MATCH_SSIID'] == m_id].sort_values(by=['Er_HIF', 'DISTANCE'], ascending=[False, False])
            st.dataframe(df_match[['PLAYER_NAME', 'Hold', 'DISTANCE', 'HI_RUN', 'TOP_SPEED']], use_container_width=True, hide_index=True)
