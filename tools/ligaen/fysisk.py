import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS

# Konstanter fra dine indstillinger
HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"

def vis_side(conn, name_map=None):
    """Hovedfunktion til visning af Fysisk Data i appen."""
    
    # --- 1. DATA INDLÆSNING ---
    @st.cache_data(ttl=600)
    def get_fysisk_data():
        # Metadata og resultater
        query_meta = f"""
        SELECT DATE, MATCH_SSIID, DESCRIPTION, HOME_SSIID, AWAY_SSIID, HOME_SCORE, AWAY_SCORE
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA
        WHERE COMPETITION_OPTAUUID = '{COMP_UUID}' AND YEAR = '2025'
        ORDER BY DATE DESC
        """
        
        # Fysisk data (Bemærk: vi bruger 'optaId' da det er kolonnenavnet i din tabel)
        query_phys = """
        SELECT 
            MATCH_SSIID,
            "optaId" as PLAYER_OPTAID,
            PLAYER_NAME,
            DISTANCE,
            "HIGH SPEED RUNNING" + "SPRINTING" as HI_DIST,
            TOP_SPEED,
            CAST(MINUTES AS FLOAT) as MINS
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        """
        
        # Relationstabel for at vide hvem der spiller for HIF
        query_rel = f"""
        SELECT MATCH_SSIID, PLAYER_SSIID as PLAYER_OPTAID, TEAM_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_TEAM
        """
        
        return conn.query(query_meta), conn.query(query_phys), conn.query(query_rel)

    try:
        df_meta, df_phys, df_rel = get_fysisk_data()
    except Exception as e:
        st.error(f"Fejl ved hentning af data: {e}")
        return

    # --- 2. LOGIK: KAMP-OVERBLIK ---
    # Merge fysisk data med hold-relation
    df_merged = pd.merge(df_phys, df_rel, on=['MATCH_SSIID', 'PLAYER_OPTAID'], how='inner')
    
    # Gruppér på kamp og hold for at få hold-totaler
    hold_stats = df_merged.groupby(['MATCH_SSIID', 'TEAM_SSIID']).agg({
        'DISTANCE': 'sum',
        'HI_DIST': 'sum',
        'TOP_SPEED': 'max'
    }).reset_index()

    # --- 3. VISNING: KAMP LISTE ---
    st.subheader("Kampoverblik (HIF)")

    # Mapper holdnavne
    def get_team_name(ssiid):
        for name, info in TEAMS.items():
            if info.get('ssid') == ssiid: return name
        return "Ukendt"

    # Forbered tabel til visning
    display_list = []
    for _, match in df_meta.iterrows():
        # Find HIF's stats for denne kamp
        m_stats = hold_stats[(hold_stats['MATCH_SSIID'] == match['MATCH_SSIID']) & 
                            (hold_stats['TEAM_SSIID'] == HIF_SSIID)]
        
        if not m_stats.empty:
            stats = m_stats.iloc[0]
            display_list.append({
                "Dato": match['DATE'],
                "Kamp": f"{get_team_name(match['HOME_SSIID'])} - {get_team_name(match['AWAY_SSIID'])}",
                "Res.": f"{int(match['HOME_SCORE'])} - {int(match['AWAY_SCORE'])}",
                "Total Dist (km)": round(stats['DISTANCE'] / 1000, 2),
                "HI Løb (m)": int(stats['HI_DIST']),
                "Topfart": round(stats['TOP_SPEED'], 1),
                "MATCH_SSIID": match['MATCH_SSIID']
            })

    if display_list:
        df_display = pd.DataFrame(display_list)
        st.dataframe(
            df_display.drop(columns=['MATCH_SSIID']),
            use_container_width=True,
            hide_index=True
        )
        
        # Mulighed for at dykke ned i en kamp
        st.divider()
        valgt_kamp_navn = st.selectbox("Vælg en kamp for spiller-detaljer:", df_display['Kamp'] + " (" + df_display['Dato'].astype(str) + ")")
        
        # Find ID på valgt kamp
        idx = st.session_state.get('kamp_index', 0) # Simpelt eksempel
        m_id = df_display.iloc[0]['MATCH_SSIID'] # Default til nyeste
        
        # Vis spiller-stats for den valgte kamp
        st.write(f"**Spillerstatistik for HIF**")
        spiller_stats = df_merged[(df_merged['MATCH_SSIID'] == m_id) & (df_merged['TEAM_SSIID'] == HIF_SSIID)]
        st.dataframe(
            spiller_stats[['PLAYER_NAME', 'MINS', 'DISTANCE', 'HI_DIST', 'TOP_SPEED']].sort_values('DISTANCE', ascending=False),
            column_config={
                "PLAYER_NAME": "Spiller",
                "MINS": "Min",
                "DISTANCE": "Meter",
                "HI_DIST": "HI Meter",
                "TOP_SPEED": "km/t"
            },
            use_container_width=True, hide_index=True
        )
    else:
        st.info("Ingen fysiske data fundet for de valgte kampe.")
