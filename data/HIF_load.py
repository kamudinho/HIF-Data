def get_scouting_package():
    conn = _get_snowflake_conn()
    DB = "KLUB_HVIDOVREIF.AXIS"
    
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
            id_str = f"({valid_ids[0]})" if len(valid_ids) == 1 else str(tuple(valid_ids))
            
            # A: Hent billeder
            img_query = f"SELECT PLAYER_WYID, IMAGEDATAURL FROM {DB}.WYSCOUT_PLAYERS WHERE PLAYER_WYID IN {id_str}"
            df_sql_p = conn.query(img_query)
            
            # B: Karriere stats - VI SKRIVER QUERYEN DIREKTE HER FOR AT UNDGÅ LIGA-FILTER
            # Vi bruger præcis de navne du bad om: SEASONNAME, TEAMNAME, MATCHES, MINUTES, GOALS, ASSISTS, YELLOWCARD, REDCARDS
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
            
            # Rens resultater (Kolonne navne til UPPER)
            for df in [df_sql_p, df_career]:
                if df is not None and not df.empty:
                    df.columns = [str(c).upper().strip() for c in df.columns]
                    df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
        except Exception as e:
            st.sidebar.error(f"SQL Fejl: {str(e)[:100]}")

    return {"scout_reports": scout_df, "players": load_local_players(), "sql_players": df_sql_p, "career": df_career}
