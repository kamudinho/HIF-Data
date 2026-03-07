def get_analysis_package(hif_only=False):
    conn = _get_snowflake_conn()
    if not conn: 
        return {}

    comp_f = str(COMPETITION_NAME)
    season_f = str(TOURNAMENTCALENDAR_NAME)
    queries = get_opta_queries(comp_f, season_f, hif_only=hif_only)
    
    # 1. Hent Snowflake data
    data = {
        "matches": conn.query(queries.get("opta_matches")),
        "shots": conn.query(queries.get("opta_shotevents")),
        "linebreaks": conn.query(queries.get("opta_linebreaks")),
        "xg_agg": conn.query(queries.get("opta_expected_goals")),
        "team_stats": conn.query(queries.get("opta_team_stats")),
        "assists": conn.query(queries.get("opta_assists")),
        "qualifiers": conn.query(queries.get("opta_qualifiers"))
    }

    # 2. Vask kolonnenavne med det samme i ordbogen
    for key in data:
        if data[key] is not None and not data[key].empty:
            data[key].columns = [str(c).upper().strip() for c in data[key].columns]
        else:
            # Hvis en vigtig dataframe er tom, så initier en tom DF med de rigtige kolonner
            # for at undgå 'NoneType' fejl senere i koden
            if data[key] is None:
                data[key] = pd.DataFrame()

    # 3. Navne-map (players.csv)
    df_local = load_local_players()
    name_map = {}
    if df_local is not None and not df_local.empty:
        df_local.columns = [str(c).upper().strip() for c in df_local.columns]
        # Vi mapper PLAYER_OPTAUUID -> NAVN
        if 'PLAYER_OPTAUUID' in df_local.columns and 'NAVN' in df_local.columns:
            name_map = dict(zip(
                df_local['PLAYER_OPTAUUID'].astype(str).str.strip().str.lower(), 
                df_local['NAVN'].astype(str).str.strip()
            ))

    # 4. Bearbejdning af specifikke tabeller (brug ordbogen 'data')
    df_shots = data["shots"]
    if not df_shots.empty:
        df_shots['XG_VAL'] = df_shots['XG_RAW'].apply(parse_xg)
        for col in ['EVENT_X', 'EVENT_Y']:
            if col in df_shots.columns:
                df_shots[col] = pd.to_numeric(df_shots[col], errors='coerce').fillna(0)

    # 5. Returnér den fulde pakke med konsistente nøgler
    return {
        "matches": data["matches"],
        "opta_matches": data["matches"],
        "playerstats": data["shots"],
        "linebreaks": data["linebreaks"], # <--- VIGTIG: Nu er den vasket og klar!
        "xg_agg": data["xg_agg"],
        "opta_team_stats": data["team_stats"],
        "assists": data["assists"],
        "qualifiers": data["qualifiers"],
        "players": df_local,
        "name_map": name_map,
        "config": {
            "liga_navn": comp_f,
            "season": season_f,
            "colors": TEAM_COLORS
        }
    }
