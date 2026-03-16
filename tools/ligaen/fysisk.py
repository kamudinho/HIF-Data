import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

# Konstanter fra din profil
HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"

def vis_side(conn, name_map=None):
    # --- 1. DATA INDLÆSNING (Præcis mapping efter dine specifikationer) ---
    @st.cache_data(ttl=600)
    def get_combined_data():
        # Metadata Join: Finder de rigtige kampe
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
        
        # Fysisk Summary: Her hedder spiller-id "optaId"
        query_phys = """
        SELECT 
            MATCH_SSIID,
            "optaId", 
            PLAYER_NAME,
            DISTANCE,
            "HIGH SPEED RUNNING",
            SPRINTING,
            TOP_SPEED,
            MINUTES
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        """
        
        # Relationstabel (F53A): Her hedder kolonnen PLAYER_OPTAID (ikke PLAYER_SSIID)
        query_rel = """
        SELECT 
            MATCH_SSIID, 
            PLAYER_OPTAID, 
            TEAM_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_TEAM
        """
        
        return conn.query(query_meta), conn.query(query_phys), conn.query(query_rel)

    # Hent data
    df_meta, df_phys, df_rel = get_combined_data()

    # --- 2. LOGIK: MERGE & BEREGNING ---
    # Vi omdøber "optaId" til PLAYER_OPTAID for at lave en ren join
    df_phys = df_phys.rename(columns={"optaId": "PLAYER_OPTAID"})
    
    # Kobler fysisk data med Team-information
    df_spillere = pd.merge(df_phys, df_rel, on=['MATCH_SSIID', 'PLAYER_OPTAID'], how='inner')
    
    # Beregner HI-dist (HSR + Sprint)
    df_spillere['HI_DIST'] = df_spillere['HIGH SPEED RUNNING'] + df_spillere['SPRINTING']

    # --- 3. VISNING: KAMP OVERBLIK ---
    st.title("Fysisk Data - NordicBet Liga")

    def get_team_name(ssiid):
        for name, info in TEAMS.items():
            if info.get('ssid') == ssiid: return name
        return str(ssiid)[:5]

    kamp_liste = []
    for _, kamp in df_meta.iterrows():
        # Find HIF spillere i den pågældende kamp
        hif_stats = df_spillere[(df_spillere['MATCH_SSIID'] == kamp['MATCH_SSIID']) & 
                                (df_spillere['TEAM_SSIID'] == HIF_SSIID)]
        
        if not hif_stats.empty:
            kamp_liste.append({
                "Dato": kamp['STARTTIME'].strftime('%d/%m %H:%M') if kamp['STARTTIME'] else "N/A",
                "Kamp": f"{get_team_name(kamp['HOME_SSIID'])} - {get_team_name(kamp['AWAY_SSIID'])}",
                "Res.": f"{int(kamp['HOME_SCORE'])} - {int(kamp['AWAY_SCORE'])}",
                "Total km": round(hif_stats['DISTANCE'].sum() / 1000, 1),
                "HI Løb (m)": int(hif_stats['HI_DIST'].sum()),
                "id": kamp['MATCH_SSIID']
            })

    if kamp_liste:
        df_display = pd.DataFrame(kamp_liste)
        st.dataframe(df_display.drop(columns=['id']), use_container_width=True, hide_index=True)

        # --- 4. DYK NED I SPILLERE ---
        st.divider()
        valgt_id = st.selectbox("Vælg kamp for spillerdetaljer:", 
                               options=df_display['id'].tolist(),
                               format_func=lambda x: next(i['Kamp'] for i in kamp_liste if i['id'] == x))

        st.subheader("Spiller-stats (Hvidovre IF)")
        match_stats = df_spillere[(df_spillere['MATCH_SSIID'] == valgt_id) & (df_spillere['TEAM_SSIID'] == HIF_SSIID)]
        
        st.dataframe(
            match_stats[['PLAYER_NAME', 'MINUTES', 'DISTANCE', 'HI_DIST', 'TOP_SPEED']].sort_values('DISTANCE', ascending=False),
            column_config={
                "PLAYER_NAME": "Spiller",
                "MINUTES": "Minutter",
                "DISTANCE": st.column_config.NumberColumn("Meter", format="%d"),
                "HI_DIST": st.column_config.NumberColumn("HI Meter", format="%d"),
                "TOP_SPEED": st.column_config.NumberColumn("km/t", format="%.1f")
            },
            use_container_width=True, hide_index=True
        )
    else:
        st.info("Ingen data fundet for Hvidovre IF i denne periode.")
