#data/analyse_load.py
import pandas as pd
import streamlit as st

def check_physical_data_availability(match_uuid):
    from data.data_load import _get_snowflake_conn
    conn = _get_snowflake_conn()
    
    # Rens UUID (hvis der er et 'g' foran)
    clean_uuid = str(match_uuid).strip()
    if clean_uuid.startswith('g'):
        clean_uuid = clean_uuid[1:]
        
    res = {"meta": False, "rows": 0, "ss_id": None}
    
    # Tjek metadata
    meta_df = conn.query(f"SELECT \"MATCH_SSIID\" FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA WHERE \"MATCH_OPTAUUID\" = '{clean_uuid}'")
    
    if not meta_df.empty:
        ss_id = meta_df.iloc[0, 0]
        res["meta"] = True
        res["ss_id"] = ss_id
        
        # Tjek fysiske rækker i F53A tabellen
        count_df = conn.query(f"SELECT COUNT(*) as CNT FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER WHERE \"MATCH_SSIID\" = '{ss_id}'")
        res["rows"] = count_df.iloc[0, 0]
        
    return res

def debug_physical_data_dump():
    """Henter et råt udtræk af de første rækker for at verificere indholdet"""
    from data.data_load import _get_snowflake_conn
    conn = _get_snowflake_conn()
    
    results = {}
    
    try:
        # 1. Tjek Metadata-tabellen (første 3 rækker)
        # Vi vælger SELECT * for at se ALLE kolonnenavne præcis som de er
        meta_sql = 'SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA LIMIT 3'
        results['metadata_sample'] = conn.query(meta_sql)
        
        # 2. Tjek den fysiske tabel (første 3 rækker)
        fys_sql = 'SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER LIMIT 3'
        results['physical_sample'] = conn.query(fys_sql)
        
        return results
    except Exception as e:
        st.error(f"Debug udtræk fejlede: {e}")
        return None

# I din Streamlit main fil eller hvor du tester:
if st.button("Kør Rå Data Debug"):
    data = debug_physical_data_dump()
    if data:
        st.write("### Rå Metadata (Første 3 rækker)")
        st.dataframe(data['metadata_sample'])
        
        st.write("### Rå Fysisk Data (Første 3 rækker)")
        st.dataframe(data['physical_sample'])

def get_analysis_package(hif_only=False, match_uuid=None):
    from data.data_load import _get_snowflake_conn, load_local_players
    from data.sql.opta_queries import get_opta_queries
    from data.utils.team_mapping import COMPETITION_NAME, TOURNAMENTCALENDAR_NAME, TEAM_COLORS

    conn = _get_snowflake_conn()
    if not conn: return {}

    comp_f = str(COMPETITION_NAME)
    season_f = str(TOURNAMENTCALENDAR_NAME)
    queries = get_opta_queries(liga_f=comp_f, saeson_f=season_f, hif_only=hif_only)
    
    def safe_query(query_key, params=None):
        q = queries.get(query_key)
        if not q: return pd.DataFrame()
        if params:
            q = q.format(**params) # Indsætter variabler som {ss_id} eller {match_uuid}
        try:
            res = conn.query(q)
            return pd.DataFrame(res) if not isinstance(res, pd.DataFrame) else res
        except Exception as e:
            st.error(f"Fejl i Snowflake query '{query_key}': {e}")
            return pd.DataFrame()

    # Standard data
    df_opta_stats = safe_query("opta_team_stats")
    df_sequence = safe_query("opta_sequence_map")
    df_matches = safe_query("opta_matches")
    df_shots = safe_query("opta_shotevents")
    df_league_shots = safe_query("opta_league_shotevents")
    df_assists = safe_query("opta_assists")
    df_xg_agg = safe_query("opta_expected_goals")
    df_team_linebreaks = safe_query("opta_team_linebreaks")
    df_player_linebreaks = safe_query("opta_player_linebreaks")
    
    # --- I din get_analysis_package i analyse_load.py ---
    df_fys = pd.DataFrame()
    if match_uuid:
        # 1. RENS UUID: Opta sender nogle gange 'g' foran, men metadata-tabellen bruger det ikke
        # Eksempel: 'gd200y...' bliver til 'd200y...'
        clean_uuid = str(match_uuid).strip()
        if clean_uuid.startswith('g') and len(clean_uuid) > 20: # Sikrer vi ikke stripper korte koder
            clean_uuid = clean_uuid[1:]
        
        # 2. Find Second Spectrum ID (SS_ID)
        meta_sql = f"""
            SELECT "MATCH_SSIID"
            FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA
            WHERE "MATCH_OPTAUUID" = '{clean_uuid}'
            LIMIT 1
        """
        
        try:
            meta_res = conn.query(meta_sql)
            if meta_res is not None and not meta_res.empty:
                ss_id = meta_res.iloc[0, 0]
                
                # 3. Hent den fysiske data via SSIID
                fys_sql = f"""
                    SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER 
                    WHERE "MATCH_SSIID" = '{ss_id}'
                """
                df_fys = conn.query(fys_sql)
            else:
                # Hvis den stadig ikke finder noget, viser vi det rensede ID i debug
                st.sidebar.error(f"Ingen metadata for: {clean_uuid}")
        except Exception as e:
            st.error(f"Fysisk data fejl: {e}")

    # Resten af din eksisterende logik (name_map etc.)
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
        "fysisk_data": df_fys, # Nu indeholder denne data, hvis match_uuid er givet
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
