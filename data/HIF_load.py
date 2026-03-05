import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn, load_local_players

def get_scouting_package():
    """Henter data og sikrer billeder og stats til alle scoutede spillere"""
    conn = _get_snowflake_conn() # DENNE VAR VÆK - NU ER DEN HER
    DB = "KLUB_HVIDOVREIF.AXIS"
    
    # 1. Hent scouting CSV
    try:
        scout_df = pd.read_csv('data/scouting_db.csv')
        scout_df.columns = [c.strip().upper() for c in scout_df.columns]
        scout_df['PLAYER_WYID'] = scout_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
        valid_ids = [idx for idx in scout_df['PLAYER_WYID'].unique().tolist() if str(idx).isdigit()]
    except:
        scout_df = pd.DataFrame(); valid_ids = []

    df_sql_p = pd.DataFrame()
    df_career = pd.DataFrame()

    if conn and valid_ids:
        try:
            # Gør ID-listen klar til SQL: (123, 456)
            id_str = f"({valid_ids[0]})" if len(valid_ids) == 1 else str(tuple(valid_ids))
            
            # A: Hent billeder
            img_query = f"SELECT PLAYER_WYID, IMAGEDATAURL FROM {DB}.WYSCOUT_PLAYERS WHERE PLAYER_WYID IN {id_str}"
            df_sql_p = conn.query(img_query)
            
            # B: Hent Karriere stats (Uden liga-filter!)
            career_query = f"""
                SELECT 
                    pc.PLAYER_WYID, 
                    s.SEASONNAME, 
                    t.TEAMNAME, 
                    pc.APPEARANCES AS MATCHES, 
                    pc.MINUTESPLAYED AS MINUTES, 
                    pc.GOAL AS GOALS, 
                    pc.ASSIST AS ASSISTS, 
                    pc.YELLOWCARD, 
                    pc.REDCARDS
                FROM {DB}.WYSCOUT_PLAYERCAREER pc
                JOIN {DB}.WYSCOUT_SEASONS s ON pc.SEASON_WYID = s.SEASON_WYID
                JOIN {DB}.WYSCOUT_TEAMS t ON pc.TEAM_WYID = t.TEAM_WYID
                WHERE pc.PLAYER_WYID IN {id_str}
                ORDER BY s.SEASONNAME DESC
            """
            df_career = conn.query(career_query)
            
            # Rens alle dataframes for ID-match
            for df in [df_sql_p, df_career]:
                if df is not None and not df.empty:
                    df.columns = [str(c).upper().strip() for c in df.columns]
                    df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
                    
        except Exception as e:
            st.sidebar.error(f"Snowflake Fejl: {str(e)[:100]}")

    return {
        "scout_reports": scout_df, 
        "players": load_local_players(), 
        "sql_players": df_sql_p, 
        "career": df_career
    }
