import pandas as pd
import streamlit as st
from data.data_load import _get_snowflake_conn, load_local_players
from data.sql.opta_queries import get_opta_queries
from data.utils.team_mapping import COMPETITION_NAME, TOURNAMENTCALENDAR_NAME, TEAM_COLORS

def get_analysis_package(hif_only=False, match_uuid=None):
    """
    Henter den samlede datapakke. 
    Bruger nu den detaljerede OPTA_REMOTESHAPES til taktisk analyse.
    """
    conn = _get_snowflake_conn()
    if not conn:
        return {}

    # 1. Opsætning af filtre og queries
    comp_f = str(COMPETITION_NAME)
    season_f = str(TOURNAMENTCALENDAR_NAME)
    queries = get_opta_queries(liga_f=comp_f, saeson_f=season_f, hif_only=hif_only)
    
    def safe_query(query_key):
        q = queries.get(query_key)
        if not q:
            return pd.DataFrame()
        try:
            # Sørg for at bruge conn.query (Streamlit Snowflake connector standard)
            res = conn.query(q)
            df = pd.DataFrame(res) if not isinstance(res, pd.DataFrame) else res
            # Tving altid kolonnenavne til UPPERCASE for konsistens
            df.columns = [c.upper() for c in df.columns]
            return df
        except Exception as e:
            st.error(f"Fejl i Snowflake query '{query_key}': {e}")
            return pd.DataFrame()

    # 2. Hent kerne-data
    df_matches = safe_query("opta_matches")
    df_opta_stats = safe_query("opta_team_stats")
    df_sequence = safe_query("opta_sequence_map")
    df_shots = safe_query("opta_shotevents")
    df_league_shots = safe_query("opta_league_shotevents")
    df_assists = safe_query("opta_assists")
    df_xg_agg = safe_query("opta_expected_goals")
    df_player_linebreaks = safe_query("opta_player_linebreaks")
    df_team_linebreaks = safe_query("opta_team_linebreaks")
    df_all_events = safe_query("opta_events") 

    # 3. Hent den nye Remote Shapes data
    # Vi henter én samlet dataframe og splitter den i Streamlit efter 'POSSESSION_TYPE'
    df_remote_shapes = safe_query("opta_remote_shapes")
    
    # 4. Fysisk data (håndterer match_uuid filter)
    df_fys = safe_query("opta_physical_stats")
    if match_uuid and not df_fys.empty:
        clean_uuid = str(match_uuid).strip().replace('g', '') # Rens 'g' præfiks hvis det findes
        if 'MATCH_OPTAUUID' in df_fys.columns:
            df_fys = df_fys[df_fys['MATCH_OPTAUUID'].str.contains(clean_uuid, na=False, case=False)]

    # 5. Spiller-navne mapping (HIF lokale navne)
    df_local = load_local_players()
    name_map = {}
    if df_local is not None and not df_local.empty:
        df_local.columns = [c.upper() for c in df_local.columns]
        navn_col = 'PLAYER_NAME' if 'PLAYER_NAME' in df_local.columns else 'NAVN'
        if 'PLAYER_OPTAUUID' in df_local.columns:
            name_map = dict(zip(
                df_local['PLAYER_OPTAUUID'].astype(str).str.strip().str.lower(), 
                df_local[navn_col].astype(str).str.strip()
            ))

    # 6. Returner den færdige pakke
    return {
        "matches": df_opta_stats, # BRUG DENNE TIL TABELLEN (den har xG og scores)
        "matches_info": df_matches, # Gem den rå info her
        "playerstats": df_shots,
        "remote_shapes": df_remote_shapes, # Den nye hovedkilde til taktik
        "fysisk_data": df_fys,
        "xg_agg": df_xg_agg,
        "assists": df_assists,
        "name_map": name_map,
        "local_players": df_local,
        "opta": {
            "team_stats": df_opta_stats,
            "team_linebreaks": df_team_linebreaks,
            "player_linebreaks": df_player_linebreaks,
            "sequence_map": df_sequence,
            "league_shotevents": df_league_shots,
            "events": df_all_events
        },
        "config": {
            "liga_navn": comp_f, 
            "season": season_f, 
            "colors": TEAM_COLORS
        }
    }
