import pandas as pd
import streamlit as st

def get_single_match_physical(match_uuid):
    """Oversætter Opta UUID til SSIID og henter fysisk data korrekt"""
    from data.data_load import _get_snowflake_conn
    conn = _get_snowflake_conn()
    if not match_uuid: return pd.DataFrame()

    # TRIN 1: Find SSIID baseret på Opta UUID (Metadata-broen)
    meta_sql = f"""
        SELECT MATCH_SSIID 
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA 
        WHERE MATCH_OPTAUUID = '{match_uuid}'
        LIMIT 1
    """
    
    try:
        meta_res = conn.query(meta_sql)
        
        # Hvis vi finder et SSIID, bruger vi det. Ellers prøver vi UUID (som fallback)
        ss_id = meta_res.iloc[0]['MATCH_SSIID'] if not meta_res.empty else match_uuid

        # TRIN 2: Hent fysisk data med det korrekte ID
        # Vi tjekker både MATCH_SSIID og MATCH_ID for at være sikre
        sql = f"""
            SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER 
            WHERE MATCH_SSIID = '{ss_id}' OR MATCH_ID = '{ss_id}'
        """
        res = conn.query(sql)
        return pd.DataFrame(res) if not isinstance(res, pd.DataFrame) else res

    except Exception as e:
        st.error(f"Fejl i ID-mapping eller Snowflake: {e}")
        return pd.DataFrame()
def get_analysis_package(hif_only=False):
    from data.data_load import _get_snowflake_conn, load_local_players
    from data.sql.opta_queries import get_opta_queries
    from data.utils.team_mapping import COMPETITION_NAME, TOURNAMENTCALENDAR_NAME, TEAM_COLORS

    conn = _get_snowflake_conn()
    if not conn: return {}

    comp_f = str(COMPETITION_NAME)
    season_f = str(TOURNAMENTCALENDAR_NAME)
    queries = get_opta_queries(liga_f=comp_f, saeson_f=season_f, hif_only=hif_only)
    
    def safe_query(query_key):
        q = queries.get(query_key)
        if not q: return pd.DataFrame()
        try:
            res = conn.query(q)
            return pd.DataFrame(res) if not isinstance(res, pd.DataFrame) else res
        except Exception as e:
            st.error(f"Fejl i Snowflake query '{query_key}': {e}")
            return pd.DataFrame()

    # Hent alle data
    df_opta_stats = safe_query("opta_team_stats")
    df_sequence = safe_query("opta_sequence_map")
    df_matches = safe_query("opta_matches")
    df_shots = safe_query("opta_shotevents")
    df_league_shots = safe_query("opta_league_shotevents")
    df_assists = safe_query("opta_assists")
    df_xg_agg = safe_query("opta_expected_goals")
    df_team_linebreaks = safe_query("opta_team_linebreaks")
    df_player_linebreaks = safe_query("opta_player_linebreaks")
    
    # Vi sætter denne til tom ved initial load for at undgå fejl
    df_fys = pd.DataFrame() 

    df_local = load_local_players()
    name_map = {}
    if df_local is not None and not df_local.empty:
        df_local.columns = [c.upper() for c in df_local.columns]
        navn_col = 'PLAYER_NAME' if 'PLAYER_NAME' in df_local.columns else 'NAVN'
        if 'PLAYER_OPTAUUID' in df_local.columns:
            name_map = dict(zip(df_local['PLAYER_OPTAUUID'].astype(str).str.strip().str.lower(), df_local[navn_col].astype(str).str.strip()))

    return {
        "matches": df_matches,
        "playerstats": df_shots,
        "fysisk_data": df_fys,
        "xg_agg": df_xg_agg,
        "assists": df_assists,
        "name_map": name_map,
        "local_players": df_local,
        "opta_player_linebreaks": df_player_linebreaks,
        "opta": {
            "matches": df_matches,
            "team_stats": df_opta_stats,
            "team_linebreaks": df_team_linebreaks,
            "opta_sequence_map": df_sequence,
            "player_linebreaks": df_player_linebreaks,
            "league_shotevents": df_league_shots
        },
        "config": {"liga_navn": comp_f, "season": season_f, "colors": TEAM_COLORS}
    }
