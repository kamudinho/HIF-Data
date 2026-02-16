import streamlit as st
import pandas as pd
import uuid

# --- 1. FORBINDELSES-FUNKTION (Dette fjerner din NameError) ---
def _get_snowflake_conn():
    try:
        # Bruger Streamlits indbyggede connection-manager
        return st.connection("snowflake")
    except Exception as e:
        st.error(f"Snowflake Connection Error: {e}")
        return None

@st.cache_data(ttl=3600)
def load_all_data(season_id=191807):
    # --- 2. GITHUB FILER ---
    url_base = "https://raw.githubusercontent.com/Kamudinho/HIF-data/main/data/"
    def read_gh(file):
        try:
            u = f"{url_base}{file}?nocache={uuid.uuid4()}"
            d = pd.read_csv(u, sep=None, engine='python')
            d.columns = [str(c).strip().upper() for c in d.columns]
            return d
        except: return pd.DataFrame()

    df_players = read_gh("players.csv")
    df_scout = read_gh("scouting_db.csv")
    df_teams_csv = read_gh("teams.csv")

    # --- 3. SNOWFLAKE DATA ---
    conn = _get_snowflake_conn()
    df_events = pd.DataFrame()
    df_season_stats = pd.DataFrame()
    hold_map = {}

    if conn:
        try:
            # A: Hold-navne (Vigtigt for dine Heatmaps og Modstanderanalyse)
            q_teams = "SELECT TEAM_WYID, TEAMNAME FROM AXIS.WYSCOUT_TEAMS"
            df_teams_sn = conn.query(q_teams)
            hold_map = dict(zip(df_teams_sn['TEAM_WYID'].astype(str), df_teams_sn['TEAMNAME']))
            
            # Merge med lokale team-navne fra GitHub
            if not df_teams_csv.empty:
                csv_map = dict(zip(df_teams_csv['TEAM_WYID'].astype(str), df_teams_csv['TEAMNAME']))
                hold_map.update(csv_map)

            # B: Event Query (Til din Modstanderanalyse og Heatmaps)
            q_combined = f"""
                SELECT c.LOCATIONX, c.LOCATIONY, c.PRIMARYTYPE, e.TEAM_WYID, 
                       m.MATCHLABEL, s.SHOTXG, sn.SEASONNAME
                FROM AXIS.WYSCOUT_MATCHEVENTS_COMMON c
                LEFT JOIN AXIS.WYSCOUT_MATCHEVENTS_SHOTS s ON c.EVENT_WYID = s.EVENT_WYID
                JOIN AXIS.WYSCOUT_MATCHDETAIL_BASE e ON c.MATCH_WYID = e.MATCH_WYID AND c.TEAM_WYID = e.TEAM_WYID
                JOIN AXIS.WYSCOUT_MATCHES m ON c.MATCH_WYID = m.MATCH_WYID
                JOIN AXIS.WYSCOUT_SEASONS sn ON m.SEASON_WYID = sn.SEASON_WYID
                WHERE m.SEASON_WYID = {season_id}
            """
            df_events = conn.query(q_combined)

            # C: Stats Query (Til Scouting Profiler og Spillerstats)
            q_stats = """
                SELECT p.PLAYER_WYID, s.SEASONNAME, t.TEAMNAME, p.GOAL as GOALS, 
                       p.APPEARANCES as MATCHES, adv.ASSISTS
                FROM AXIS.WYSCOUT_PLAYERCAREER p
                JOIN AXIS.WYSCOUT_PLAYERADVANCEDSTATS_TOTAL adv ON p.PLAYER_WYID = adv.PLAYER_WYID
                JOIN AXIS.WYSCOUT_SEASONS s ON p.SEASON_WYID = s.SEASON_WYID
                JOIN AXIS.WYSCOUT_TEAMS t ON p.TEAM_WYID = t.TEAM_WYID
                WHERE p.MINUTESPLAYED > 0
            """
            df_season_stats = conn.query(q_stats)

        except Exception as e:
            st.error(f"SQL fejl i load_all_data: {e}")

    # --- 4. RETURNERING ---
    # Vi returnerer præcis de nøgler, din HIF-dash.py leder efter
    return {
        "shotevents": df_events, 
        "hold_map": hold_map,
        "players": df_players,
        "season_stats": df_season_stats,
        "scouting": df_scout,
        "matches": pd.DataFrame() # Tom placeholder til Zoneinddeling
    }
