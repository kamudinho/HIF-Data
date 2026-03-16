import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

# Konstanter fra dine indstillinger
HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"

def vis_side(conn, name_map=None):
    # --- 1. DATA INDLÆSNING (JOIN MELLEM METADATA OG FYSISK) ---
    @st.cache_data(ttl=600)
    def get_combined_data():
        # Her joiner vi Game Metadata med Season Metadata for at få filteret på plads
        # Vi bruger MATCH_SSIID som bro.
        query_meta = f"""
        SELECT 
            g.STARTTIME, 
            g.MATCH_SSIID, 
            g.HOME_SSIID, 
            g.AWAY_SSIID, 
            g.HOME_SCORE, 
            g.AWAY_SCORE,
            s.COMPETITION_OPTAUUID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA g
        JOIN KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA s 
            ON g.MATCH_SSIID = s.MATCH_SSIID
        WHERE s.COMPETITION_OPTAUUID = '{COMP_UUID}' 
          AND s.YEAR = 2025
        ORDER BY g.STARTTIME DESC
        """
        
        # Henter den fysiske opsummering for spillere
        # Bemærk "optaId" (lille o) fra din tabeloversigt
        query_phys = """
        SELECT 
            MATCH_SSIID,
            "optaId" as PLAYER_OPTAID,
            PLAYER_NAME,
            DISTANCE,
            "HIGH SPEED RUNNING" + "SPRINTING" as HI_DIST,
            TOP_SPEED,
            MINUTES
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        """
        
        # Henter relationen for at identificere HIF-spillere
        query_rel = f"""
        SELECT MATCH_SSIID, PLAYER_SSIID as PLAYER_OPTAID, TEAM_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_TEAM
        """
        
        return conn.query(query_meta), conn.query(query_phys), conn.query(query_rel)

    df_meta, df_phys, df_rel = get_combined_data()

    # --- 2. LOGIK & MAPPING ---
    def get_team_name(ssiid):
        for name, info in TEAMS.items():
            if info.get('ssid') == ssiid: return name
        return str(ssiid)[:5]

    # Merge fysisk data med hold-id (rel)
    df_spillere = pd.merge(df_phys, df_rel, on=['MATCH_SSIID', 'PLAYER_OPTAID'], how='inner')

    # --- 3. VISNING: KAMP OVERBLIK ---
    st.subheader("Hold-overblik (HIF)")

    kamp_liste = []
    for _, kamp in df_meta.iterrows():
        # Find HIF's samlede tal for denne kamp
        hif_i_kamp = df_spillere[(df_spillere['MATCH_SSIID'] == kamp['MATCH_SSIID']) & 
                                (df_spillere['TEAM_SSIID'] == HIF_SSIID)]
        
        if not hif_i_kamp.empty:
            kamp_liste.append({
                "Dato": kamp['STARTTIME'],
                "Modstander": get_team_name(kamp['AWAY_SSIID'] if kamp['HOME_SSIID'] == HIF_SSIID else kamp['HOME_SSIID']),
                "Resultat": f"{int(kamp['HOME_SCORE'])} - {int(kamp['AWAY_SCORE'])}",
                "Total Dist (km)": round(hif_i_kamp['DISTANCE'].sum() / 1000, 2),
                "HI Løb (m)": int(hif_i_kamp['HI_DIST'].sum()),
                "Max Sprint": round(hif_i_kamp['TOP_SPEED'].max(), 1),
                "id": kamp['MATCH_SSIID']
            })

    if kamp_liste:
        df_display = pd.DataFrame(kamp_liste)
        st.dataframe(df_display.drop(columns=['id']), use_container_width=True, hide_index=True)

        # --- 4. SPILLER DETALJER ---
        st.divider()
        valgt_kamp_id = st.selectbox("Vælg kamp for spillerdetaljer:", 
                                     options=df_display['id'].tolist(),
                                     format_func=lambda x: next(item['Modstander'] for item in kamp_liste if item['id'] == x))

        st.write(f"**Spillerpræstationer**")
        match_stats = df_spillere[(df_spillere['MATCH_SSIID'] == valgt_kamp_id) & (df_spillere['TEAM_SSIID'] == HIF_SSIID)]
        
        st.dataframe(
            match_stats[['PLAYER_NAME', 'MINUTES', 'DISTANCE', 'HI_DIST', 'TOP_SPEED']].sort_values('DISTANCE', ascending=False),
            column_config={
                "PLAYER_NAME": "Spiller",
                "DISTANCE": "Meter",
                "HI_DIST": "HI Meter",
                "TOP_SPEED": "Topfart"
            },
            use_container_width=True, hide_index=True
        )
    else:
        st.info("Ingen fysisk data fundet for de valgte filtre.")
