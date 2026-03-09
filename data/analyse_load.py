#data/analyse_load.py
import pandas as pd
from data.data_load import _get_snowflake_conn, parse_xg, load_local_players
from data.sql.opta_queries import get_opta_queries 
from data.utils.team_mapping import COMPETITION_NAME, TOURNAMENTCALENDAR_NAME, TEAM_COLORS

def get_analysis_package(hif_only=False):
    conn = _get_snowflake_conn()
    if not conn: 
        return {}

    # 1. Hent de stabile værdier fra mapping
    # Vi sikrer os at de er strenge
    comp_f = str(COMPETITION_NAME)
    season_f = str(TOURNAMENTCALENDAR_NAME)

    # 2. Hent queries - VIGTIGT: Brug de korrekte argumentnavne
    # Her linker vi 'saeson_navn' til din 'season_f' variabel
    queries = get_opta_queries(liga_uuid=comp_f, saeson_navn=season_f, hif_only=hif_only)

    def safe_query(query_key):
        q = queries.get(query_key)
        if not q:
            return pd.DataFrame()
        try:
            # Nogle Streamlit-forbindelser bruger st.connection, andre bruger legacy
            # Jeg antager du bruger den nye st.connection format:
            return conn.query(q)
        except Exception as e:
            print(f"Fejl i query '{query_key}': {e}")
            return pd.DataFrame()

    # --- Hent data ---
    df_matches = safe_query("opta_matches")
    df_shots = safe_query("opta_shotevents")
    df_opta_stats = safe_query("opta_team_stats")
    df_assists = safe_query("opta_assists")
    df_xg_agg = safe_query("opta_expected_goals")
    df_quals = safe_query("opta_qualifiers")
    df_team_linebreaks = safe_query("opta_team_linebreaks")
    df_player_linebreaks = safe_query("opta_player_linebreaks")

    # --- Navne-mapping ---
    df_local = load_local_players()
    name_map = {}
    if df_local is not None and not df_local.empty:
        df_local.columns = [c.upper() for c in df_local.columns]
        if 'PLAYER_OPTAUUID' in df_local.columns and 'NAVN' in df_local.columns:
            name_map = dict(zip(
                df_local['PLAYER_OPTAUUID'].astype(str).str.strip().str.lower(), 
                df_local['NAVN'].astype(str).str.strip()
            ))

    # Sikker mapping af linebreaks
    if not df_player_linebreaks.empty:
        df_player_linebreaks.columns = [c.upper() for c in df_player_linebreaks.columns]
        if 'PLAYER_OPTAUUID' in df_player_linebreaks.columns:
            df_player_linebreaks['PLAYER_NAME'] = (
                df_player_linebreaks['PLAYER_OPTAUUID']
                .astype(str).str.lower()
                .map(name_map)
                .fillna(df_player_linebreaks['PLAYER_OPTAUUID']) # Fallback til ID hvis navn mangler
            )

    return {
        "matches": df_matches,
        "playerstats": df_shots,
        "xg_agg": df_xg_agg,
        "assists": df_assists,
        "qualifiers": df_quals,
        "name_map": name_map,
        "players": df_local,
        "opta": {
            "matches": df_matches,
            "team_stats": df_opta_stats,
            "team_linebreaks": df_team_linebreaks,
            "player_linebreaks": df_player_linebreaks
        },
        "team_linebreaks": df_team_linebreaks,
        "player_linebreaks": df_player_linebreaks,
        "config": {
            "liga_navn": comp_f,
            "season": season_f,
            "colors": TEAM_COLORS
        }
    }
