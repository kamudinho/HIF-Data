import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

# Konstanter baseret på din profil
HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"

def vis_kamp_overblik(conn):
    # --- 1. HENT DATA ---
    @st.cache_data(ttl=600)
    def get_match_overview_data():
        # Hent basis kamp-info
        query_meta = f"""
        SELECT 
            DATE, 
            MATCH_SSIID, 
            DESCRIPTION, 
            HOME_SSIID, 
            AWAY_SSIID, 
            HOME_SCORE, 
            AWAY_SCORE
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA
        WHERE COMPETITION_OPTAUUID = '{COMP_UUID}' AND YEAR = '2025'
        ORDER BY DATE DESC
        """
        
        # Hent opsummeret fysisk data per kamp per hold
        # Vi joiner med F53A for at kunne gruppere på hold-niveau
        query_phys = """
        SELECT 
            p.MATCH_SSIID,
            t.TEAM_SSIID,
            SUM(p.DISTANCE) as TOTAL_DIST,
            SUM(p."HIGH SPEED RUNNING" + p.SPRINTING) as TOTAL_HI,
            MAX(p.TOP_SPEED) as MAX_SPEED
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS p
        JOIN KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_TEAM t 
            ON p.MATCH_SSIID = t.MATCH_SSIID 
            AND p."optaId" = t.PLAYER_SSIID -- Vi ved nu det er optaId i summary tabellen
        GROUP BY p.MATCH_SSIID, t.TEAM_SSIID
        """
        return conn.query(query_meta), conn.query(query_phys)

    df_meta, df_phys = get_match_overview_data()

    # --- 2. BEHANDLING AF DATA ---
    # Merge fysisk data på metadata for både hjemme- og udehold
    df = df_meta.copy()
    
    # Mapper holdnavne fra din TEAMS ordbog
    def name_lookup(ssiid):
        for name, info in TEAMS.items():
            if info.get('ssid') == ssiid: return name
        return "Ukendt"

    df['Hjemmehold'] = df['HOME_SSIID'].apply(name_lookup)
    df['Udehold'] = df['AWAY_SSIID'].apply(name_lookup)
    df['Resultat'] = df['HOME_SCORE'].astype(str) + " - " + df['AWAY_SCORE'].astype(str)

    # Hent HIF's specifikke tal for hver kamp
    hif_phys = df_phys[df_phys['TEAM_SSIID'] == HIF_SSIID]
    df = pd.merge(df, hif_phys[['MATCH_SSIID', 'TOTAL_DIST', 'TOTAL_HI', 'MAX_SPEED']], on='MATCH_SSIID', how='left')

    # --- 3. VISNING I STREAMLIT ---
    st.write("### Kampoversigt: NordicBet Liga 25/26")
    
    # Key Metrics øverst
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        avg_dist = df['TOTAL_DIST'].mean() / 1000 # km
        c1.metric("Gns. Hold-distance", f"{avg_dist:.1f} km")
        c2.metric("Højeste HI Distance", f"{df['TOTAL_HI'].max():.0f} m")
        c3.metric("Sæsonens Topfart", f"{df['MAX_SPEED'].max():.1f} km/t")

    # Tabel med alle kampe
    st.dataframe(
        df[['DATE', 'Hjemmehold', 'Resultat', 'Udehold', 'TOTAL_DIST', 'TOTAL_HI']],
        column_config={
            "DATE": "Dato",
            "TOTAL_DIST": st.column_config.NumberColumn("HIF Total Dist (m)", format="%.0f"),
            "TOTAL_HI": st.column_config.NumberColumn("HIF HI-løb (m)", format="%.0f"),
        },
        use_container_width=True,
        hide_index=True
    )

    return df
