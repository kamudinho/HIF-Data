import streamlit as st
import pandas as pd

# Konstanter fra din profil
HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"

def vis_side(conn, name_map=None):
    st.title("Hvidovre IF | Fysisk Data")

    @st.cache_data(ttl=600)
    def get_unified_data():
        # 1. Find Hvidovre-kampe
        query_meta = f"""
        SELECT MATCH_SSIID, DESCRIPTION, "DATE", HOME_SSIID, AWAY_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA
        WHERE COMPETITION_OPTAUUID = '{COMP_UUID}' 
          AND (HOME_SSIID = '{HIF_SSIID}' OR AWAY_SSIID = '{HIF_SSIID}')
        ORDER BY "DATE" DESC
        """
        df_meta = conn.query(query_meta)
        if df_meta.empty: return None, None, None
        
        ids = "('" + "','".join(df_meta['MATCH_SSIID'].tolist()) + "')"

        # 2. Hold-performance (Her tilføjer vi citationstegn omkring kolonnenavne)
        query_team = f"""
        SELECT 
            MATCH_SSIID, 
            TEAM_SSIID, 
            TEAM_NAME, 
            "TEAMDISTANCE", 
            "HIGHSPEEDSPRINTING"
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_TEAM
        WHERE MATCH_SSIID IN {ids}
        """
        df_team = conn.query(query_team)

        # 3. Spiller-detaljer
        query_player = f"""
        SELECT 
            MATCH_SSIID, MATCH_TEAMS, PLAYER_NAME, "optaId", 
            MINUTES, DISTANCE, "HIGH SPEED RUNNING", SPRINTING, TOP_SPEED
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_SSIID IN {ids}
        """
        df_player = conn.query(query_player)
        
        return df_meta, df_team, df_player

    try:
        df_meta, df_team, df_player = get_unified_data()
    except Exception as e:
        st.error(f"SQL Fejl ved indlæsning: {e}")
        return

    # --- DATAPRÆPARERING ---
    # Parse minutter (MM:SS -> Decimal)
    def parse_mins(val):
        try:
            m, s = map(int, str(val).split(':'))
            return round(m + s/60, 1)
        except: return 0.0

    df_player['MINS_DECIMAL'] = df_player['MINUTES'].apply(parse_mins)
    # HI Dist for spillere (fra Summary tabellen)
    df_player['HI_DIST'] = df_player['HIGH SPEED RUNNING'] + df_player['SPRINTING']
    # HI Dist for holdet (fra Team tabellen)
    df_team['TEAM_HI'] = df_team['HIGHSPEEDRUNNING'] + df_team['HIGHSPEEDSPRINTING']

    # --- SEKTION 1: KAMP OVERBLIK ---
    st.subheader("Sæsonoverblik (Hold-totaler)")
    
    match_list = []
    for _, m in df_meta.iterrows():
        hif = df_team[(df_team['MATCH_SSIID'] == m['MATCH_SSIID']) & (df_team['TEAM_SSIID'] == HIF_SSIID)]
        opp = df_team[(df_team['MATCH_SSIID'] == m['MATCH_SSIID']) & (df_team['TEAM_SSIID'] != HIF_SSIID)]
        
        if not hif.empty:
            match_list.append({
                "id": m['MATCH_SSIID'],
                "Dato": m['DATE'],
                "Modstander": m['DESCRIPTION'].replace('Hvidovre', '').replace('-', '').strip(),
                "HIF (km)": round(hif.iloc[0]['TEAMDISTANCE'] / 1000, 1),
                "HIF HI (m)": int(hif.iloc[0]['TEAM_HI']),
                "Modst. (km)": round(opp.iloc[0]['TEAMDISTANCE'] / 1000, 1) if not opp.empty else 0
            })

    if match_list:
        df_ov = pd.DataFrame(match_list)
        st.dataframe(df_ov.drop(columns=['id']), use_container_width=True, hide_index=True)

        # --- SEKTION 2: SPILLER DETALJER ---
        st.divider()
        valgt_id = st.selectbox("Vælg kamp for spiller-detaljer:", 
                               options=df_ov['id'].tolist(),
                               format_func=lambda x: next(i['Modstander'] for i in match_list if i['id'] == x))

        p_stats = df_player[
            (df_player['MATCH_SSIID'] == valgt_id) & 
            (df_player['MATCH_TEAMS'].str.contains('Hvidovre|HVI', case=False, na=False))
        ].copy()

        st.write(f"### Spillerstatistik")
        st.dataframe(
            p_stats[['PLAYER_NAME', 'MINUTES', 'DISTANCE', 'HI_DIST', 'TOP_SPEED']].sort_values('DISTANCE', ascending=False),
            column_config={
                "PLAYER_NAME": "Spiller",
                "DISTANCE": st.column_config.NumberColumn("Total (m)", format="%d"),
                "HI_DIST": "HI Løb (m)",
                "TOP_SPEED": "km/t"
            },
            use_container_width=True, hide_index=True
        )
    else:
        st.info("Ingen data fundet.")
