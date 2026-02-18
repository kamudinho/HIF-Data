#data/data_load.py
import streamlit as st
import pandas as pd
import uuid
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

# --- 0. KONFIGURATION ---
try:
    from data.season_show import SEASONNAME, COMPETITION_WYID
except ImportError:
    SEASONNAME = "2025/2026"
    COMPETITION_WYID = (3134, 329, 43319, 331, 1305, 1570)

def _get_snowflake_conn():
    try:
        s = st.secrets["connections"]["snowflake"]
        p_key_pem = s["private_key"].strip() if isinstance(s["private_key"], str) else s["private_key"]
        p_key_obj = serialization.load_pem_private_key(
            p_key_pem.encode(), password=None, backend=default_backend()
        )
        p_key_der = p_key_obj.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        return st.connection(
            "snowflake", type="snowflake", account=s["account"], user=s["user"],
            role=s["role"], warehouse=s["warehouse"], database=s["database"],
            schema=s["schema"], private_key=p_key_der
        )
    except Exception as e:
        st.error(f"❌ Snowflake Connection Error: {e}")
        return None

@st.cache_data(ttl=3600)
def load_all_data():
    comp_filter = str(tuple(COMPETITION_WYID)) if len(COMPETITION_WYID) > 1 else f"({COMPETITION_WYID[0]})"
    season_filter = f"='{SEASONNAME}'"

    # --- 1. GITHUB DATA (CSV) ---
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

    # --- 2. SNOWFLAKE DATA (SQL) ---
    conn = _get_snowflake_conn()
    # Initialiser res med alle nødvendige nøgler for at undgå KeyError senere
    res = {
        "shotevents": pd.DataFrame(), 
        "team_matches": pd.DataFrame(), 
        "playerstats": pd.DataFrame(), 
        "events": pd.DataFrame(), 
        "players_snowflake": pd.DataFrame(), # Ny nøgle til scouting
        "hold_map": {}
    }

    if conn:
        try:
            # A: Hold Mapping (Henter alle team-navne)
            df_t = conn.query("SELECT TEAM_WYID, TEAMNAME FROM AXIS.WYSCOUT_TEAMS")
            if df_t is not None:
                res["hold_map"] = {str(int(r[0])): str(r[1]).strip() for r in df_t.values}

            # B: Optimerede Queries
            queries = {
                "shotevents": f"""
                    SELECT c.*, m.MATCHLABEL, m.DATE 
                    FROM AXIS.WYSCOUT_MATCHEVENTS_COMMON c
                    JOIN AXIS.WYSCOUT_MATCHES m ON c.MATCH_WYID = m.MATCH_WYID
                    JOIN AXIS.WYSCOUT_SEASONS s ON m.SEASON_WYID = s.SEASON_WYID
                    WHERE c.PRIMARYTYPE = 'shot' 
                    AND c.COMPETITION_WYID IN {comp_filter}
                    AND s.SEASONNAME {season_filter}
                """,
                "team_matches": f"""
                    SELECT 
                        tm.SEASON_WYID, tm.TEAM_WYID, tm.MATCH_WYID, 
                        tm.DATE, tm.STATUS, tm.COMPETITION_WYID, tm.GAMEWEEK,
                        c.COMPETITIONNAME AS COMPETITION_NAME, 
                        adv.SHOTS, adv.GOALS, adv.XG, adv.SHOTSONTARGET, m.MATCHLABEL 
                    FROM AXIS.WYSCOUT_TEAMMATCHES tm
                    LEFT JOIN AXIS.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv 
                        ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID
                    JOIN AXIS.WYSCOUT_MATCHES m ON tm.MATCH_WYID = m.MATCH_WYID
                    JOIN AXIS.WYSCOUT_SEASONS s ON m.SEASON_WYID = s.SEASON_WYID
                    JOIN AXIS.WYSCOUT_COMPETITIONS c ON tm.COMPETITION_WYID = c.COMPETITION_WYID
                    WHERE tm.COMPETITION_WYID IN {comp_filter} 
                    AND s.SEASONNAME {season_filter}
                """,
                "playerstats": f"""
                    SELECT * FROM AXIS.WYSCOUT_PLAYERADVANCEDSTATS_TOTAL
                    WHERE COMPETITION_WYID IN {comp_filter} 
                    AND SEASON_WYID IN (SELECT SEASON_WYID FROM AXIS.WYSCOUT_SEASONS WHERE SEASONNAME {season_filter})
                """,
                "events": f"""
                    SELECT e.TEAM_WYID, e.PRIMARYTYPE, e.LOCATIONX, e.LOCATIONY, e.COMPETITION_WYID 
                    FROM AXIS.WYSCOUT_MATCHEVENTS_COMMON e
                    JOIN AXIS.WYSCOUT_MATCHES m ON e.MATCH_WYID = m.MATCH_WYID
                    JOIN AXIS.WYSCOUT_SEASONS s ON m.SEASON_WYID = s.SEASON_WYID
                    WHERE e.COMPETITION_WYID IN {comp_filter}
                    AND s.SEASONNAME {season_filter}
                    AND e.PRIMARYTYPE IN ('pass', 'duel', 'interception')
                """,
                "playerstats": f"""
                    SELECT 
                        ps.*, 
                        s.SEASONNAME, 
                        t.TEAMNAME 
                    FROM AXIS.WYSCOUT_PLAYERADVANCEDSTATS_TOTAL ps
                    LEFT JOIN AXIS.WYSCOUT_SEASONS s ON ps.SEASON_WYID = s.SEASON_WYID
                    -- RETTELSE: Match på TEAM_WYID i stedet for SEASON_WYID
                    LEFT JOIN AXIS.WYSCOUT_TEAMS t ON ps.TEAM_WYID = t.TEAM_WYID 
                    WHERE ps.COMPETITION_WYID IN {comp_filter} 
                    AND ps.SEASON_WYID IN (SELECT SEASON_WYID FROM AXIS.WYSCOUT_SEASONS WHERE SEASONNAME {season_filter})
                """,
            }
            
            for key, q in queries.items():
                df = conn.query(q)
                if df is not None:
                    df.columns = [c.upper() for c in df.columns]
                    if 'LOCATIONX' in df.columns:
                        df['LOCATIONX'] = df['LOCATIONX'].astype('float32')
                        df['LOCATIONY'] = df['LOCATIONY'].astype('float32')
                    res[key] = df
        except Exception as e:
            st.error(f"SQL Fejl: {e}")

    # --- 3. SAMLET RETUR (ALLE NØGLER BEVARET + NYE TILFØJET) ---
    return {
        "players": df_players_gh,           # Original GitHub CSV
        "scouting": df_scout_gh,            # Original GitHub CSV
        "teams_csv": df_teams_csv,          # Original GitHub CSV
        "shotevents": res["shotevents"],
        "team_matches": res["team_matches"],
        "playerstats": res["playerstats"],
        "season_stats": res["playerstats"], # Alias bevaret til andre sider
        "players_snowflake": res["players_snowflake"], # Ny kilde til scout-input
        "events": res["events"],
        "hold_map": res["hold_map"]
    }
