import streamlit as st
import pandas as pd
import uuid

def _get_snowflake_conn():
    try:
        return st.connection("snowflake")
    except Exception as e:
        st.error(f"Snowflake Connection Error: {e}")
        return None

@st.cache_data(ttl=3600)
def load_all_data(season_id=191807, competition_id=3134, team_id=38331):
    # --- 1. GITHUB FILER (Stamdata) ---
    url_base = "https://raw.githubusercontent.com/Kamudinho/HIF-data/main/data/"
    def read_gh(file):
        try:
            u = f"{url_base}{file}?nocache={uuid.uuid4()}"
            d = pd.read_csv(u, sep=None, engine='python')
            d.columns = [str(c).strip().upper() for c in d.columns]
            return d
        except: return pd.DataFrame()

    df_players_gh = read_gh("players.csv")
    df_scout_gh = read_gh("scouting_db.csv")
    df_teams_csv = read_gh("teams.csv")

    # --- 2. SNOWFLAKE SETUP ---
    conn = _get_snowflake_conn()
    df_shotevents = pd.DataFrame()
    df_season_stats = pd.DataFrame()
    df_team_matches = pd.DataFrame()
    df_playerstats = pd.DataFrame()
    hold_map = {}

    if conn:
        try:
            # A: HOLD NAVNE
            q_teams = "SELECT TEAM_WYID, TEAMNAME FROM AXIS.WYSCOUT_TEAMS"
            df_teams_sn = conn.query(q_teams)
            hold_map = dict(zip(df_teams_sn['TEAM_WYID'].astype(str), df_teams_sn['TEAMNAME']))
            if not df_teams_csv.empty:
                hold_map.update(dict(zip(df_teams_csv['TEAM_WYID'].astype(str), df_teams_csv['TEAMNAME'])))

            # B: SHOT EVENTS (Heatmaps/Analyse)
            q_shots = f"""
                SELECT c.EVENT_WYID, c.PLAYER_WYID, c.LOCATIONX, c.LOCATIONY, c.MINUTE, c.SECOND,
                       c.PRIMARYTYPE, c.MATCHPERIOD, c.MATCH_WYID, s.SHOTBODYPART, s.SHOTISGOAL, 
                       s.SHOTXG, m.MATCHLABEL, m.DATE, e.SCORE, e.TEAM_WYID
                FROM AXIS.WYSCOUT_MATCHEVENTS_COMMON c
                JOIN AXIS.WYSCOUT_MATCHEVENTS_SHOTS s ON c.EVENT_WYID = s.EVENT_WYID
                JOIN AXIS.WYSCOUT_MATCHDETAIL_BASE e ON c.MATCH_WYID = e.MATCH_WYID AND c.TEAM_WYID = e.TEAM_WYID
                JOIN AXIS.WYSCOUT_MATCHES m ON c.MATCH_WYID = m.MATCH_WYID
            """
            df_shotevents = conn.query(q_shots)

            # C: SEASON STATS (Scouting)
            q_stats = """
                SELECT DISTINCT p.PLAYER_WYID, s.SEASONNAME, t.TEAMNAME, p.GOAL as GOALS, 
                                p.APPEARANCES as MATCHES, p.MINUTESPLAYED as MINUTESTAGGED,
                                adv.ASSISTS, adv.XGSHOT as XG, p.YELLOWCARD, p.REDCARDS,
                                adv.PASSES, adv.SUCCESSFULPASSES, adv.TOUCHINBOX, adv.PROGRESSIVEPASSES
                FROM AXIS.WYSCOUT_PLAYERCAREER p
                JOIN AXIS.WYSCOUT_PLAYERADVANCEDSTATS_TOTAL adv ON p.PLAYER_WYID = adv.PLAYER_WYID 
                     AND p.SEASON_WYID = adv.SEASON_WYID
                JOIN AXIS.WYSCOUT_SEASONS s ON p.SEASON_WYID = s.SEASON_WYID
                JOIN AXIS.WYSCOUT_TEAMS t ON p.TEAM_WYID = t.TEAM_WYID
                WHERE p.MINUTESPLAYED > 0
            """
            df_season_stats = conn.query(q_stats)

            # D: TEAM MATCHES (Hold Analyse)
            q_teammatches = f"""
                SELECT DISTINCT tm.MATCH_WYID, m.MATCHLABEL, tm.SEASON_WYID, tm.TEAM_WYID, tm.DATE, 
                       g.SHOTS, g.GOALS, g.XG, d.PPDA, p.POSSESSIONPERCENT, ps.PASSES, du.CHALLENGEINTENSITY
                FROM AXIS.WYSCOUT_TEAMMATCHES tm
                JOIN AXIS.WYSCOUT_MATCHES m ON tm.MATCH_WYID = m.MATCH_WYID
                LEFT JOIN AXIS.WYSCOUT_MATCHADVANCEDSTATS_GENERAL g ON tm.MATCH_WYID = g.MATCH_WYID AND tm.TEAM_WYID = g.TEAM_WYID
                LEFT JOIN AXIS.WYSCOUT_MATCHADVANCEDSTATS_DEFENCE d ON tm.MATCH_WYID = d.MATCH_WYID AND tm.TEAM_WYID = d.TEAM_WYID
                LEFT JOIN AXIS.WYSCOUT_MATCHADVANCEDSTATS_POSESSIONS p ON tm.MATCH_WYID = p.MATCH_WYID AND tm.TEAM_WYID = p.TEAM_WYID
                LEFT JOIN AXIS.WYSCOUT_MATCHADVANCEDSTATS_PASSES ps ON tm.MATCH_WYID = ps.MATCH_WYID AND tm.TEAM_WYID = ps.TEAM_WYID
                LEFT JOIN AXIS.WYSCOUT_MATCHADVANCEDSTATS_DUELS du ON tm.MATCH_WYID = du.MATCH_WYID AND tm.TEAM_WYID = du.TEAM_WYID
            """
            df_team_matches = conn.query(q_teammatches)

            # E: PLAYERSTATS (Trup Performance - Din store query)
            q_playerstats = f"""
                SELECT DISTINCT
                    p.PLAYER_WYID, p.FIRSTNAME, p.LASTNAME, p.ROLECODE3, p.BIRTHDATE, t.TEAMNAME,
                    SUM(DISTINCT s.MATCHES) AS KAMPE, SUM(DISTINCT s.MATCHESINSTART) AS MATCHESINSTART,
                    SUM(DISTINCT s.MATCHESSUBSTITUTED) AS MATCHESSUBSTITUTED, SUM(DISTINCT s.MATCHESCOMINGOFF) AS MATCHESCOMINGOFF,
                    SUM(DISTINCT s.MINUTESONFIELD) AS MINUTESONFIELD, SUM(DISTINCT s.MINUTESTAGGED) AS MINUTESTAGGED,
                    SUM(DISTINCT s.GOALS) AS GOALS, SUM(DISTINCT s.ASSISTS) AS ASSISTS, SUM(DISTINCT s.SHOTS) AS SHOTS,
                    SUM(DISTINCT s.HEADSHOTS) AS HEADSHOTS, SUM(DISTINCT s.YELLOWCARDS) AS YELLOWCARDS,
                    SUM(DISTINCT s.REDCARDS) AS REDCARDS, SUM(DISTINCT s.PENALTIES) AS PENALTIES,
                    SUM(DISTINCT s.DUELS) AS DUELS, SUM(DISTINCT s.DUELSWON) AS DUELSWON,
                    SUM(DISTINCT s.DEFENSIVEDUELS) AS DEFENSIVEDUELS, SUM(DISTINCT s.DEFENSIVEDUELSWON) AS DEFENSIVEDUELSWON,
                    SUM(DISTINCT s.OFFENSIVEDUELS) AS OFFENSIVEDUELS, SUM(DISTINCT s.OFFENSIVEDUELSWON) AS OFFENSIVEDUELSWON,
                    SUM(DISTINCT s.AERIALDUELS) AS AERIALDUELS, SUM(DISTINCT s.AERIALDUELSWON) AS AERIALDUELSWON,
                    SUM(DISTINCT s.PASSES) AS PASSES, SUM(DISTINCT s.SUCCESSFULPASSES) AS SUCCESSFULPASSES,
                    SUM(DISTINCT s.PASSESTOFINALTHIRD) AS PASSESTOFINALTHIRD, SUM(DISTINCT s.SUCCESSFULPASSESTOFINALTHIRD) AS SUCCESSFULPASSESTOFINALTHIRD,
                    SUM(DISTINCT s.FORWARDPASSES) AS FORWARDPASSES, SUM(DISTINCT s.SUCCESSFULFORWARDPASSES) AS SUCCESSFULFORWARDPASSES,
                    SUM(DISTINCT s.THROUGHPASSES) AS THROUGHPASSES, SUM(DISTINCT s.SUCCESSFULTHROUGHPASSES) AS SUCCESSFULTHROUGHPASSES,
                    SUM(DISTINCT s.DRIBBLES) AS DRIBBLES, SUM(DISTINCT s.SUCCESSFULDRIBBLES) AS SUCCESSFULDRIBBLES,
                    SUM(DISTINCT s.INTERCEPTIONS) AS INTERCEPTIONS, SUM(DISTINCT s.PROGRESSIVEPASSES) AS PROGRESSIVEPASSES,
                    SUM(DISTINCT s.XGSHOT) AS XGSHOT, SUM(DISTINCT s.XGASSIST) AS XGASSIST, SUM(DISTINCT s.TOUCHINBOX) AS TOUCHINBOX
                FROM AXIS.WYSCOUT_PLAYERADVANCEDSTATS_TOTAL s
                JOIN AXIS.WYSCOUT_PLAYERS p ON s.PLAYER_WYID = p.PLAYER_WYID AND s.COMPETITION_WYID = p.COMPETITION_WYID
                JOIN AXIS.WYSCOUT_TEAMS t ON p.CURRENTTEAM_WYID = t.TEAM_WYID
                GROUP BY 1, 2, 3, 4, 5, 6
            """
            df_playerstats = conn.query(q_playerstats)

        except Exception as e:
            st.error(f"SQL fejl i load_all_data: {e}")

    # Standardisering til UPPERCASE
    for df in [df_shotevents, df_season_stats, df_team_matches, df_playerstats]:
        if not df.empty:
            df.columns = [c.upper() for c in df.columns]

    return {
        "shotevents": df_shotevents,
        "season_stats": df_season_stats,
        "team_matches": df_team_matches,
        "playerstats": df_playerstats,
        "hold_map": hold_map,
        "players": df_players_gh,    
        "scouting": df_scout_gh,     
        "teams_csv": df_teams_csv,   
        "scouting_db": df_scout_gh, 
        "players_all": df_players_gh 
    }
