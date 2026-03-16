import streamlit as st
import pandas as pd

HIF_OPTA_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

def vis_side(conn, name_map=None):
    if name_map is None:
        name_map = {}

    # Ingen st.title - bruger markdown for et rent look

    @st.cache_data(ttl=600)
    def get_hif_matches():
        # Vi henter kampene og sikrer at vi får MATCH_SSIID i et rent format
        query = f"""
        SELECT DISTINCT
            TRIM(m.MATCH_SSIID) as MATCH_SSIID, 
            COALESCE(s.MATCH_TEAMS, 'Kamp ' || m.MATCH_SSIID) as MATCH_TEAMS, 
            m.STARTTIME as DATE_TIME,
            m.HOME_SSIID, m.AWAY_SSIID, m.HOMEOPTA_UUID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA m
        LEFT JOIN (SELECT DISTINCT MATCH_SSIID, MATCH_TEAMS FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS) s
            ON TRIM(m.MATCH_SSIID) = TRIM(s.MATCH_SSIID)
        WHERE m.HOMEOPTA_UUID = '{HIF_OPTA_UUID}' OR m.AWAY_OPTAUUID = '{HIF_OPTA_UUID}'
        ORDER BY m.STARTTIME DESC
        """
        return conn.query(query)

    df_matches = get_hif_matches()
    
    if df_matches.empty:
        st.warning("Ingen Hvidovre-kampe fundet med UUID.")
        return

    # Lav dropdown
    df_matches['DROPDOWN_LABEL'] = df_matches['DATE_TIME'].dt.strftime('%d/%m-%Y') + ": " + df_matches['MATCH_TEAMS']
    valgt_label = st.selectbox("Vælg kamp:", df_matches['DROPDOWN_LABEL'].unique())
    match_row = df_matches[df_matches['DROPDOWN_LABEL'] == valgt_label].iloc[0]
    
    # Her er nøglen: Vi stripper SSIID helt ren
    valgt_ssiid = str(match_row['MATCH_SSIID']).strip()

    @st.cache_data(ttl=300)
    def get_player_data(ssiid):
        # Vi bruger ILIKE og TRIM for at være ekstremt fleksible med ID-match
        query = f"""
        SELECT 
            PLAYER_SSIID, PLAYER_NAME, TEAM_SSIID,
            DISTANCE, TOP_SPEED, AVERAGE_SPEED, SPRINTS
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER
        WHERE LOWER(TRIM(MATCH_SSIID)) = LOWER('{ssiid}')
        AND DISTANCE > 0
        """
        res = conn.query(query)
        
        # Backup-plan: Hvis den er tom, prøv at søge på dato og holdnavn i stedet for ID
        if res.empty:
            alt_query = f"""
            SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER 
            WHERE MATCH_DATE = '{match_row['DATE_TIME'].date()}'
            AND (MATCH_TEAMS ILIKE '%Hvidovre%' OR MATCH_TEAMS ILIKE '%HVI%')
            """
            res = conn.query(alt_query)
        return res

    df_fys = get_player_data(valgt_ssiid)

    if df_fys.empty:
        st.error(f"❌ Fejl: Kunne ikke finde spiller-data for {valgt_label}")
        st.info("Dette sker ofte hvis MATCH_SSIID i spiller-tabellen ikke matcher metadata-tabellen.")
        return

    # --- Herfra kører din normale visning ---
    df_fys['DISPLAY_NAME'] = df_fys['PLAYER_SSIID'].map(name_map).fillna(df_fys['PLAYER_NAME'])
    
    # Find HIF team ID
    hif_ssiid = match_row['HOME_SSIID'] if match_row['HOMEOPTA_UUID'] == HIF_OPTA_UUID else match_row['AWAY_SSIID']
    teams = df_fys['TEAM_SSIID'].unique().tolist()
    
    st.write("---")
    valgt_hold = st.radio("Vælg hold:", teams, 
                          index=teams.index(hif_ssiid) if hif_ssiid in teams else 0,
                          horizontal=True,
                          format_func=lambda x: "Hvidovre IF" if x == hif_ssiid else "Modstander")
    
    df_display = df_fys[df_fys['TEAM_SSIID'] == valgt_hold]
    st.dataframe(df_display[['DISPLAY_NAME', 'DISTANCE', 'TOP_SPEED', 'SPRINTS']].sort_values('DISTANCE', ascending=False))
