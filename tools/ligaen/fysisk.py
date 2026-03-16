import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

# Konstanter fra din profil
HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"

def vis_side(conn, name_map=None):
    st.title("Betinia Ligaen | Fysisk Data")

    @st.cache_data(ttl=600)
    def get_data():
        # 1. Metadata - Vi bruger DATE fra SEASON_METADATA, da vi ved den virker
        query_meta = f"""
        SELECT 
            DATE, 
            MATCH_SSIID, 
            HOME_SSIID, 
            AWAY_SSIID, 
            HOME_SCORE, 
            AWAY_SCORE,
            DESCRIPTION
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA
        WHERE COMPETITION_OPTAUUID = '{COMP_UUID}' 
          AND YEAR = 2025
        ORDER BY DATE DESC
        """
        
        # 2. Fysisk Data - Vi bruger MATCH_TEAMS og "optaId"
        query_phys = """
        SELECT 
            MATCH_SSIID,
            MATCH_TEAMS,
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
        df_meta, df_phys = get_data()
    except Exception as e:
        st.error(f"SQL Fejl: {e}")
        return

    # --- DATABEHANDLING ---
    # Filtrér spillere der tilhører Hvidovre via MATCH_TEAMS
    df_hif_players = df_phys[df_phys['MATCH_TEAMS'].str.contains('Hvidovre', case=False, na=False)].copy()
    
    # Beregn HI Distance
    df_hif_players['HI_DIST'] = df_hif_players['HIGH SPEED RUNNING'] + df_hif_players['SPRINTING']

    # --- VISNING AF KAMP-LISTE ---
    kamp_data = []
    for _, m in df_meta.iterrows():
        m_id = m['MATCH_SSIID']
        # Find fysiske stats for denne specifikke kamp
        phys_match = df_hif_players[df_hif_players['MATCH_SSIID'] == m_id]
        
        if not phys_match.empty:
            is_home = m['HOME_SSIID'] == HIF_SSIID
            
            kamp_data.append({
                "Dato": m['DATE'],
                "Modstander": m['DESCRIPTION'].replace('Hvidovre', '').replace('-', '').strip(),
                "Res.": f"{int(m['HOME_SCORE'])} - {int(m['AWAY_SCORE'])}",
                "Total km": round(phys_match['DISTANCE'].sum() / 1000, 1),
                "HI Løb (m)": int(phys_match['HI_DIST'].sum()),
                "SSIID": m_id
            })

    if kamp_data:
        df_display = pd.DataFrame(kamp_data)
        st.dataframe(
            df_display[['Dato', 'Modstander', 'Res.', 'Total km', 'HI Løb (m)']], 
            use_container_width=True, 
            hide_index=True
        )

        st.divider()
        valgt_id = st.selectbox(
            "Vælg kamp for spiller-detaljer:", 
            options=df_display['SSIID'].tolist(),
            format_func=lambda x: next(i['Modstander'] for i in kamp_data if i['SSIID'] == x)
        )

        # Vis spillere for den valgte kamp
        match_stats = df_hif_players[df_hif_players['MATCH_SSIID'] == valgt_id].sort_values('DISTANCE', ascending=False)
        
        st.subheader("Spillerpræstationer")
        st.dataframe(
            match_stats[['PLAYER_NAME', 'MINUTES', 'DISTANCE', 'HI_DIST', 'TOP_SPEED']],
            column_config={
                "PLAYER_NAME": "Spiller",
                "MINUTES": "Min",
                "DISTANCE": st.column_config.NumberColumn("Meter", format="%d"),
                "HI_DIST": "HI Meter",
                "TOP_SPEED": "Topfart"
            },
            use_container_width=True, hide_index=True
        )
    else:
        st.info("Ingen fysiske data matchede de fundne kampe. Tjek om MATCH_SSIID i begge tabeller er ens.")
        # Debug hjælp hvis det stadig fejler
        if st.checkbox("Vis debug info"):
            st.write("SSIID fra Metadata:", df_meta['MATCH_SSIID'].head().tolist())
            st.write("SSIID fra Fysisk:", df_phys['MATCH_SSIID'].head().tolist())
