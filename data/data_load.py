import streamlit as st
import pandas as pd
import uuid
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

# --- 0. KONFIGURATION ---
try:
    from data.season_show import SEASONNAME, COMPETITION_WYID
except ImportError:
    SEASONNAME = "2024/2025"
    COMPETITION_WYID = (3134,)

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
    res = {
        "shotevents": pd.DataFrame(), "team_matches": pd.DataFrame(), 
        "playerstats": pd.DataFrame(), "events": pd.DataFrame(), "hold_map": {}
    }

    if conn:
        try:
            # A: Hold Mapping
            df_t = conn.query("SELECT TEAM_WYID, TEAMNAME FROM AXIS.WYSCOUT_TEAMS")
            if df_t is not None:
                res["hold_map"] = {str(int(r[0])): str(r[1]).strip() for r in df_t.values}

            # B: Queries baseret på dine Schema-oplysninger
            queries = {
                "shotevents": f"""
                    SELECT c.*, m.MATCHLABEL, m.DATE 
                    FROM AXIS.WYSCOUT_MATCHEVENTS_COMMON c
                    JOIN AXIS.WYSCOUT_MATCHES m ON c.MATCH_WYID = m.MATCH_WYID
                    WHERE c.PRIMARYTYPE = 'shot' AND c.COMPETITION_WYID IN {comp_filter}
                """,
               "team_matches": f"""
                    SELECT 
                        tm.SEASON_WYID, 
                        tm.TEAM_WYID, 
                        tm.MATCH_WYID, 
                        tm.DATE, tm.STATUS, tm.COMPETITION_WYID, tm.GAMEWEEK, adv.SHOTS, adv.GOALS, adv.XG, adv.SHOTSONTARGET, m.MATCHLABEL 
                    FROM AXIS.WYSCOUT_TEAMMATCHES tm
                    LEFT JOIN AXIS.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv 
                        ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID
                    JOIN AXIS.WYSCOUT_MATCHES m 
                        ON tm.MATCH_WYID = m.MATCH_WYID
                    WHERE tm.COMPETITION_WYID IN {comp_filter}
                """,
                # I data/data_load.py - playerstats query
                "playerstats": f"""
                    SELECT 
                        PLAYER_WYID, 
                        GOALS, 
                        ASSISTS, 
                        XGSHOT, 
                        MATCHES, 
                        MINUTESONFIELD,  -- Den hedder MinutesOnField i din liste!
                        SHOTS,
                        PASSES,
                        SUCCESSFULPASSES,
                        DUELS,
                        DUELSWON
                    FROM AXIS.WYSCOUT_PLAYERADVANCEDSTATS_TOTAL
                    WHERE COMPETITION_WYID IN {comp_filter} 
                    AND SEASON_WYID IN (SELECT SEASON_WYID FROM AXIS.WYSCOUT_SEASONS WHERE SEASONNAME='{SEASONNAME}')
                """,
                "events": f"""
                    SELECT TEAM_WYID, PRIMARYTYPE, LOCATIONX, LOCATIONY, COMPETITION_WYID 
                    FROM AXIS.WYSCOUT_MATCHEVENTS_COMMON 
                    WHERE COMPETITION_WYID IN {comp_filter}
                    AND PRIMARYTYPE IN ('pass', 'duel', 'interception')
                """
            }
            for key, q in queries.items():
                df = conn.query(q)
                if df is not None:
                    df.columns = [c.upper() for c in df.columns]
                    res[key] = df
        except Exception as e:
            st.error(f"SQL Fejl: {e}")

    st.write("Forbinder til Snowflake...")
    conn = _get_snowflake_conn()
    st.write("Henter hold-mapping...")
    # --- 3. SAMLET PAKKE (i data_load.py) ---
    return {
        "players": df_players_gh,
        "scouting": df_scout_gh,
        "teams_csv": df_teams_csv,
        "shotevents": res["shotevents"],
        "team_matches": res["team_matches"],
        "playerstats": res["playerstats"],
        "season_stats": res["playerstats"],  # Tilføjet så den ikke fejler i tools
        "events": res["events"],
        "hold_map": res["hold_map"]
    }
