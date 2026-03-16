import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

# Konstanter
HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"

def vis_side(conn, name_map=None):
    # --- 1. DATA INDLÆSNING (Metadata fra GAME_METADATA) ---
    @st.cache_data(ttl=600)
    def get_match_data():
        # Metadata query som forespurgt
        query_meta = f"""
        SELECT STARTTIME, MATCH_SSIID, HOME_SSIID, AWAY_SSIID, HOME_SCORE, AWAY_SCORE
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA
        WHERE COMPETITION_OPTAUUID = '{COMP_UUID}' AND YEAR = '2025'
        ORDER BY STARTTIME DESC
        """
        
        # Fysisk data (Mapping af hold og spillere)
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
        
        query_rel = """
        SELECT MATCH_SSIID, PLAYER_SSIID as PLAYER_OPTAID, TEAM_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_TEAM
        """
        
        return conn.query(query_meta), conn.query(query_phys), conn.query(query_rel)

    df_meta, df_phys, df_rel = get_match_data()

    # --- 2. DATA BEHANDLING ---
    # Hjælpefunktion til navne
    def get_team_name(ssiid):
        for name, info in TEAMS.items():
            if info.get('ssid') == ssiid: return name
        return ssiid[:5]

    # Sammensæt overblikket
    st.subheader("Kampoverblik")
    
    # Vi merger fysiske hold-totaler ind i metadata
    df_merged = pd.merge(df_phys, df_rel, on=['MATCH_SSIID', 'PLAYER_OPTAID'], how='inner')
    hold_totals = df_merged.groupby(['MATCH_SSIID', 'TEAM_SSIID']).agg({
        'DISTANCE': 'sum',
        'HI_DIST': 'sum'
    }).reset_index()

    # Visningstabel
    display_rows = []
    for _, row in df_meta.iterrows():
        hif_stats = hold_totals[(hold_totals['MATCH_SSIID'] == row['MATCH_SSIID']) & 
                               (hold_totals['TEAM_SSIID'] == HIF_SSIID)]
        
        if not hif_stats.empty:
            stats = hif_stats.iloc[0]
            display_rows.append({
                "Tidspunkt": row['STARTTIME'],
                "Hjemme": get_team_name(row['HOME_SSIID']),
                "Res.": f"{int(row['HOME_SCORE'])} - {int(row['AWAY_SCORE'])}",
                "Ude": get_team_name(row['AWAY_SSIID']),
                "HIF Distance (km)": round(stats['DISTANCE'] / 1000, 2),
                "HIF HI Løb (m)": int(stats['HI_DIST'])
            })

    if display_rows:
        st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)
    else:
        st.warning("Ingen fysisk data fundet for de valgte kampe.")

    # --- KLAR TIL DIN NÆSTE KODE HERUNDER ---
    # (Send din kode, så integrerer jeg den i flowet)
