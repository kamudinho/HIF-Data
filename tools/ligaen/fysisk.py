import streamlit as st
import pandas as pd

HIF_OPTA_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

def vis_side(conn, name_map=None):
    if name_map is None:
        name_map = {}

    # Ingen st.title her
    st.markdown("### 🏃 Fysisk Overblik")

    @st.cache_data(ttl=300)
    def get_hif_matches():
        # Vi tjekker begge tabeller for at sikre, at kampen har data
        query = f"""
        SELECT DISTINCT
            m.MATCH_SSIID, 
            COALESCE(s.MATCH_TEAMS, 'Kamp ' || m.MATCH_SSIID) as MATCH_TEAMS, 
            m.STARTTIME as DATE_TIME,
            m.HOME_SSIID, m.AWAY_SSIID, m.HOMEOPTA_UUID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA m
        INNER JOIN (SELECT DISTINCT MATCH_SSIID, MATCH_TEAMS FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS) s
            ON m.MATCH_SSIID = s.MATCH_SSIID
        WHERE m.HOMEOPTA_UUID = '{HIF_OPTA_UUID}' OR m.AWAY_OPTAUUID = '{HIF_OPTA_UUID}'
        ORDER BY m.STARTTIME DESC
        """
        return conn.query(query)

    df_matches = get_hif_matches()
    
    if df_matches.empty:
        st.warning("Ingen kampe fundet.")
        return

    df_matches['DROPDOWN_LABEL'] = df_matches['DATE_TIME'].dt.strftime('%d/%m-%Y') + ": " + df_matches['MATCH_TEAMS']
    valgt_label = st.selectbox("Vælg kamp:", df_matches['DROPDOWN_LABEL'].unique())
    match_row = df_matches[df_matches['DROPDOWN_LABEL'] == valgt_label].iloc[0]
    valgt_ssiid = match_row['MATCH_SSIID']

    @st.cache_data(ttl=300)
    def get_player_data(ssiid):
        # CAST til string for at undgå UUID-match fejl
        return conn.query(f"SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER WHERE MATCH_SSIID::string = '{ssiid}'")

    df_fys = get_player_data(valgt_ssiid)

    if df_fys.empty:
        st.error(f"Data for denne kamp (ID: {valgt_ssiid[:8]}...) er ikke landet i Snowflake endnu.")
        return

    # Resten af din logik for visning af tabel...
    st.success(f"Data fundet: {len(df_fys)} rækker.")import streamlit as st
import pandas as pd

HIF_OPTA_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

def vis_side(conn, name_map=None):
    if name_map is None:
        name_map = {}

    # Ingen st.title her
    st.markdown("### 🏃 Fysisk Overblik")

    @st.cache_data(ttl=300)
    def get_hif_matches():
        # Vi tjekker begge tabeller for at sikre, at kampen har data
        query = f"""
        SELECT DISTINCT
            m.MATCH_SSIID, 
            COALESCE(s.MATCH_TEAMS, 'Kamp ' || m.MATCH_SSIID) as MATCH_TEAMS, 
            m.STARTTIME as DATE_TIME,
            m.HOME_SSIID, m.AWAY_SSIID, m.HOMEOPTA_UUID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA m
        INNER JOIN (SELECT DISTINCT MATCH_SSIID, MATCH_TEAMS FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS) s
            ON m.MATCH_SSIID = s.MATCH_SSIID
        WHERE m.HOMEOPTA_UUID = '{HIF_OPTA_UUID}' OR m.AWAY_OPTAUUID = '{HIF_OPTA_UUID}'
        ORDER BY m.STARTTIME DESC
        """
        return conn.query(query)

    df_matches = get_hif_matches()
    
    if df_matches.empty:
        st.warning("Ingen kampe fundet.")
        return

    df_matches['DROPDOWN_LABEL'] = df_matches['DATE_TIME'].dt.strftime('%d/%m-%Y') + ": " + df_matches['MATCH_TEAMS']
    valgt_label = st.selectbox("Vælg kamp:", df_matches['DROPDOWN_LABEL'].unique())
    match_row = df_matches[df_matches['DROPDOWN_LABEL'] == valgt_label].iloc[0]
    valgt_ssiid = match_row['MATCH_SSIID']

    @st.cache_data(ttl=300)
    def get_player_data(ssiid):
        # CAST til string for at undgå UUID-match fejl
        return conn.query(f"SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER WHERE MATCH_SSIID::string = '{ssiid}'")

    df_fys = get_player_data(valgt_ssiid)

    if df_fys.empty:
        st.error(f"Data for denne kamp (ID: {valgt_ssiid[:8]}...) er ikke landet i Snowflake endnu.")
        return

    # Resten af din logik for visning af tabel...
    st.success(f"Data fundet: {len(df_fys)} rækker.")
