import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

# Konstanter
HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"

def vis_side(conn, name_map=None):
    @st.cache_data(ttl=600)
    def get_combined_data():
        # 1. Hent Metadata (Joiner Season og Game for at filtrere korrekt)
        query_meta = f"""
        SELECT 
            g.STARTTIME, 
            g.MATCH_SSIID, 
            g.HOME_SSIID, 
            g.AWAY_SSIID, 
            g.HOME_SCORE, 
            g.AWAY_SCORE
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA g
        JOIN KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA s 
            ON g.MATCH_SSIID = s.MATCH_SSIID
        WHERE s.COMPETITION_OPTAUUID = '{COMP_UUID}' 
          AND s.YEAR = 2025
        ORDER BY g.STARTTIME DESC
        """
        
        # 2. Hent Fysisk Data
        # Vi henter MATCH_TEAMSTEXT for at kunne filtrere på HIF direkte i denne tabel
        query_phys = """
        SELECT 
            MATCH_SSIID,
            MATCH_TEAMSTEXT,
            "optaId", 
            PLAYER_NAME,
            DISTANCE,
            "HIGH SPEED RUNNING",
            SPRINTING,
            TOP_SPEED,
            MINUTES
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        """
        return conn.query(query_meta), conn.query(query_phys)

    try:
        df_meta, df_phys = get_combined_data()
    except Exception as e:
        st.error(f"SQL Fejl: {e}")
        return

    # --- DATABEHANDLING ---
    # Vi bruger MATCH_TEAMSTEXT til at finde HIF-spillere, hvis vi ikke kan joine team-tabellen sikkert
    # Typisk format: "TeamA vs TeamB" eller "TeamA - TeamB"
    df_hif_players = df_phys[df_phys['MATCH_TEAMSTEXT'].str.contains('Hvidovre', case=False, na=False)].copy()
    
    # Beregn HI_DIST
    df_hif_players['HI_DIST'] = df_hif_players['HIGH SPEED RUNNING'] + df_hif_players['SPRINTING']

    # --- VISNING ---
    st.title("Fysisk Data: Hvidovre IF")

    def get_team_name(ssiid):
        for name, info in TEAMS.items():
            if info.get('ssid') == ssiid: return name
        return "Ukendt"

    # Kampoversigt
    kamp_data = []
    for _, m in df_meta.iterrows():
        m_id = m['MATCH_SSIID']
        phys_match = df_hif_players[df_hif_players['MATCH_SSIID'] == m_id]
        
        if not phys_match.empty:
            kamp_data.append({
                "Dato": m['STARTTIME'].strftime('%d/%m') if m['STARTTIME'] else "N/A",
                "Modstander": get_team_name(m['AWAY_SSIID'] if m['HOME_SSIID'] == HIF_SSIID else m['HOME_SSIID']),
                "Resultat": f"{int(m['HOME_SCORE'])} - {int(m['AWAY_SCORE'])}",
                "Total Dist (km)": round(phys_match['DISTANCE'].sum() / 1000, 1),
                "HI Løb (m)": int(phys_match['HI_DIST'].sum()),
                "SSIID": m_id
            })

    if kamp_data:
        df_display = pd.DataFrame(kamp_data)
        st.dataframe(df_display.drop(columns=['SSIID']), use_container_width=True, hide_index=True)

        st.divider()
        valgt_id = st.selectbox("Vælg kamp for spiller-detaljer:", 
                               options=df_display['SSIID'].tolist(),
                               format_func=lambda x: next(i['Modstander'] for i in kamp_data if i['SSIID'] == x))

        # Spillerdetaljer for valgt kamp
        detail_df = df_hif_players[df_hif_players['MATCH_SSIID'] == valgt_id].sort_values('DISTANCE', ascending=False)
        
        st.dataframe(
            detail_df[['PLAYER_NAME', 'MINUTES', 'DISTANCE', 'HI_DIST', 'TOP_SPEED']],
            column_config={
                "PLAYER_NAME": "Spiller",
                "MINUTES": "Min",
                "DISTANCE": st.column_config.NumberColumn("Meter", format="%d"),
                "HI_DIST": "HI (m)",
                "TOP_SPEED": "Topfart"
            },
            use_container_width=True, hide_index=True
        )
    else:
        st.warning("Fandt ingen kampe med tilhørende fysisk data.")
