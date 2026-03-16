import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

# Konstanter fra din profil og dumps
HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"

def vis_side(conn, name_map=None):
    st.title("Hvidovre IF | Kampoverblik & Fysisk Data")

    @st.cache_data(ttl=600)
    def get_full_match_data():
        # 1. Hent Sæsonens kampe (Ankeret)
        query_season = f"""
        SELECT MATCH_SSIID, DESCRIPTION, "DATE", HOME_SSIID, AWAY_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA
        WHERE COMPETITION_OPTAUUID = '{COMP_UUID}' AND YEAR = 2025
        ORDER BY "DATE" DESC
        """
        df_season = conn.query(query_season)
        
        if df_season.empty:
            return None, None, None

        ids = "('" + "','".join(df_season['MATCH_SSIID'].tolist()) + "')"

        # 2. Hent Hold-totaler (Fra F53A_GAME_TEAM dumpet du lige sendte)
        # Her får vi holdets samlede distance og procenter
        query_team_phys = f"""
        SELECT 
            MATCH_SSIID, TEAM_SSIID, TEAM_NAME, 
            TEAMDISTANCE, HIGHSPEEDRUNNING, HIGHSPEEDSPRINTING
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_TEAM
        WHERE MATCH_SSIID IN {ids}
        """
        df_team_phys = conn.query(query_team_phys)

        # 3. Hent Spiller-stats (Summary tabellen)
        query_player_phys = f"""
        SELECT 
            MATCH_SSIID, PLAYER_NAME, MATCH_TEAMS,
            DISTANCE, "HIGH SPEED RUNNING", SPRINTING, TOP_SPEED, MINUTES
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_SSIID IN {ids}
        """
        df_player_phys = conn.query(query_player_phys)
        
        return df_season, df_team_phys, df_player_phys

    df_season, df_team_phys, df_player_phys = get_full_match_data()

    if df_season is None:
        st.error("Ingen data fundet.")
        return

    # --- DATABEHANDLING ---
    # Vi forbereder overblikket
    overblik_liste = []
    for _, m in df_season.iterrows():
        # Find HIF's hold-stats
        hif_team = df_team_phys[(df_team_phys['MATCH_SSIID'] == m['MATCH_SSIID']) & 
                                (df_team_phys['TEAM_SSIID'] == HIF_SSIID)]
        
        # Find modstanderens hold-stats
        opp_team = df_team_phys[(df_team_phys['MATCH_SSIID'] == m['MATCH_SSIID']) & 
                                (df_team_phys['TEAM_SSIID'] != HIF_SSIID)]
        
        if not hif_team.empty:
            h = hif_team.iloc[0]
            o = opp_team.iloc[0] if not opp_team.empty else None
            
            overblik_liste.append({
                "Dato": m['DATE'],
                "Kamp": m['DESCRIPTION'],
                "HIF Dist (km)": round(h['TEAMDISTANCE'] / 1000, 2),
                "HIF HI (m)": int(h['HIGHSPEEDRUNNING'] + h['HIGHSPEEDSPRINTING']),
                "Modst. Dist (km)": round(o['TEAMDISTANCE'] / 1000, 2) if o is not None else 0,
                "SSIID": m['MATCH_SSIID']
            })

    # --- VISNING: KAMP OVERBLIK ---
    if overblik_liste:
        df_ov = pd.DataFrame(overblik_liste)
        st.subheader("Sæsonoverblik: Holdpræstation")
        st.dataframe(df_ov.drop(columns=['SSIID']), use_container_width=True, hide_index=True)

        st.divider()

        # --- VISNING: DETALJERET SPILLER DATA ---
        valgt_kamp_id = st.selectbox("Dyk ned i spillertal for kamp:", 
                                     options=df_ov['SSIID'].tolist(),
                                     format_func=lambda x: df_ov[df_ov['SSIID'] == x]['Kamp'].iloc[0])

        st.subheader("Spillerstatistik (Hvidovre IF)")
        # Filtrer spillere på Hvidovre i den valgte kamp
        p_stats = df_player_phys[
            (df_player_phys['MATCH_SSIID'] == valgt_kamp_id) & 
            (df_player_phys['MATCH_TEAMS'].str.contains('Hvidovre', case=False, na=False))
        ].copy()
        
        p_stats['HI_DIST'] = p_stats['HIGH SPEED RUNNING'] + p_stats['SPRINTING']

        st.dataframe(
            p_stats[['PLAYER_NAME', 'MINUTES', 'DISTANCE', 'HI_DIST', 'TOP_SPEED']].sort_values('DISTANCE', ascending=False),
            column_config={
                "PLAYER_NAME": "Spiller",
                "DISTANCE": "Meter",
                "HI_DIST": "HI Meter",
                "TOP_SPEED": "Topfart"
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Ingen kampe med tilhørende fysisk data fundet endnu.")
