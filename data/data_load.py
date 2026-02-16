import streamlit as st
import snowflake.connector
import pandas as pd
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import uuid

@st.cache_data(ttl=3600)
def load_all_data(season_id=191807): 
    # 1. GitHub filer
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

    # 2. Snowflake
    conn = _get_snowflake_conn()
    df_events = pd.DataFrame()
    df_season_stats = pd.DataFrame()
    hold_map = {}

    if conn:
        try:
            # A: Hold-navne
            q_teams = "SELECT TEAM_WYID, TEAMNAME FROM AXIS.WYSCOUT_TEAMS"
            df_teams_sn = pd.read_sql(q_teams, conn)
            hold_map = dict(zip(df_teams_sn['TEAM_WYID'].astype(str), df_teams_sn['TEAMNAME']))
            if not df_teams_csv.empty:
                csv_map = dict(zip(df_teams_csv['TEAM_WYID'].astype(str), df_teams_csv['TEAMNAME']))
                hold_map.update(csv_map)

            # B: Event Query (Til Modstanderanalyse) - SHOTXG er allerede med her
            q_combined = f"""
            SELECT 
                c.LOCATIONX, c.LOCATIONY, c.PRIMARYTYPE, e.TEAM_WYID, 
                m.MATCHLABEL, s.SHOTXG, sn.SEASONNAME
            FROM AXIS.WYSCOUT_MATCHEVENTS_COMMON c
            LEFT JOIN AXIS.WYSCOUT_MATCHEVENTS_SHOTS s ON c.EVENT_WYID = s.EVENT_WYID
            JOIN AXIS.WYSCOUT_MATCHDETAIL_BASE e ON c.MATCH_WYID = e.MATCH_WYID AND c.TEAM_WYID = e.TEAM_WYID
            JOIN AXIS.WYSCOUT_MATCHES m ON c.MATCH_WYID = m.MATCH_WYID
            JOIN AXIS.WYSCOUT_SEASONS sn ON m.SEASON_WYID = sn.SEASON_WYID
            WHERE m.SEASON_WYID = {season_id}
            AND (c.PRIMARYTYPE IN ('shot', 'pass', 'shot_against'))
            """

            # C: Avanceret Stats Query med xG (Til Scouting Profil)
            # Vi joiner COMMON med SHOTS for at få fat i xG pr. spiller
            q_stats = """
            WITH player_xg AS (
                SELECT 
                    c.PLAYER_WYID, 
                    m.SEASON_WYID,
                    SUM(s.SHOTXG) as XG_TOTAL
                FROM AXIS.WYSCOUT_MATCHEVENTS_COMMON c
                JOIN AXIS.WYSCOUT_MATCHEVENTS_SHOTS s ON c.EVENT_WYID = s.EVENT_WYID
                JOIN AXIS.WYSCOUT_MATCHES m ON c.MATCH_WYID = m.MATCH_WYID
                GROUP BY 1, 2
            )
            SELECT DISTINCT
                p.PLAYER_WYID,
                s.SEASONNAME,
                t.TEAMNAME,
                p.APPEARANCES as MATCHES,
                p.MINUTESPLAYED as MINUTESTAGGED,
                p.GOAL as GOALS,
                COALESCE(pxg.XG_TOTAL, 0) as XG,
                p.YELLOWCARD,
                p.REDCARDS,
                adv.PASSES,
                adv.SUCCESSFULPASSES,
                adv.PASSESTOFINALTHIRD,
                adv.SUCCESSFULPASSESTOFINALTHIRD,
                adv.FORWARDPASSES,
                adv.SUCCESSFULFORWARDPASSES,
                adv.TOUCHINBOX,
                adv.ASSISTS,
                adv.DUELS,
                adv.DUELSWON,
                adv.PROGRESSIVEPASSES,
                adv.SUCCESSFULPROGRESSIVEPASSES
            FROM AXIS.WYSCOUT_PLAYERCAREER p
            JOIN AXIS.WYSCOUT_PLAYERADVANCEDSTATS_TOTAL adv 
                ON p.PLAYER_WYID = adv.PLAYER_WYID AND p.SEASON_WYID = adv.SEASON_WYID
            JOIN AXIS.WYSCOUT_SEASONS s ON p.SEASON_WYID = s.SEASON_WYID
            JOIN AXIS.WYSCOUT_TEAMS t ON p.TEAM_WYID = t.TEAM_WYID
            LEFT JOIN player_xg pxg ON p.PLAYER_WYID = pxg.PLAYER_WYID AND p.SEASON_WYID = pxg.SEASON_WYID
            WHERE p.MINUTESPLAYED > 0
            ORDER BY s.SEASONNAME DESC
            """
            
            df_events = pd.read_sql(q_combined, conn)
            df_season_stats = pd.read_sql(q_stats, conn)
            
        except Exception as e:
            st.error(f"SQL Error: {e}")
        finally:
            conn.close()

    # Standardisering
    for df in [df_events, df_season_stats]:
        if not df.empty:
            df.columns = [c.upper() for c in df.columns]

    return {
        "shotevents": df_events, 
        "hold_map": hold_map,
        "players": df_players,
        "season_stats": df_season_stats,
        "scouting": df_scout
    }
