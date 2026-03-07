import streamlit as st
import pandas as pd
import os
from data.data_load import _get_snowflake_conn, load_local_players
from data.sql.wy_queries import get_wy_queries  # Vigtigt: Hent dine queries her

def get_scouting_package():
"""Henter data og sikrer billeder og stats til alle scoutede spillere"""
conn = _get_snowflake_conn()
DB = "KLUB_HVIDOVREIF.AXIS"

    # 1. Hent dine definerede queries (inkl. den nye wyscout_players)
    # Vi sender None, None med her, da dine liga-ids er hardcoded i wy_queries.py
    # 1. Hent dine definerede queries
queries = get_wy_queries(None, None) 

# 2. Hent scouting CSV (din historik)
@@ -22,40 +21,36 @@
except:
scout_df = pd.DataFrame(); valid_ids = []

    df_sql_p = pd.DataFrame() # Til billeder
    df_career = pd.DataFrame() # Til stats
    df_wyscout_search = pd.DataFrame() # Til din dropdown-søgning
    df_sql_p = pd.DataFrame() 
    df_career = pd.DataFrame() 
    df_wyscout_search = pd.DataFrame() 
    df_advanced_stats = pd.DataFrame() # NY: Til avancerede performance stats

if conn:
try:
            # A: Hent den store søgeliste (Den du lige sendte til mig!)
            # A: Hent den store søgeliste til dropdown
df_wyscout_search = conn.query(queries["wyscout_players"])
if not df_wyscout_search.empty:
df_wyscout_search.columns = [c.upper().strip() for c in df_wyscout_search.columns]

            # B: Hent billeder og stats KUN for spillere der allerede er i din CSV
            # B: Hent data KUN for de relevante spillere (valid_ids)
if valid_ids:
id_str = f"({valid_ids[0]})" if len(valid_ids) == 1 else str(tuple(valid_ids))

# Billeder
img_query = f"SELECT PLAYER_WYID, IMAGEDATAURL FROM {DB}.WYSCOUT_PLAYERS WHERE PLAYER_WYID IN {id_str}"
df_sql_p = conn.query(img_query)

                # Karriere
                career_query = f"""
                    SELECT DISTINCT
                        pc.PLAYER_WYID, s.SEASONNAME, t.TEAMNAME, 
                        pc.APPEARANCES, pc.MINUTESPLAYED, pc.GOAL, pc.YELLOWCARD, pc.REDCARDS
                    FROM {DB}.WYSCOUT_PLAYERCAREER pc
                    JOIN {DB}.WYSCOUT_SEASONS s ON pc.SEASON_WYID = s.SEASON_WYID
                    JOIN {DB}.WYSCOUT_TEAMS t ON pc.TEAM_WYID = t.TEAM_WYID
                    WHERE pc.PLAYER_WYID IN {id_str}
                    ORDER BY s.SEASONNAME DESC
                """
                df_career = conn.query(career_query)
                # Karriere (Historik)
                df_career = conn.query(queries["player_career"].replace("ORDER BY", f"WHERE pc.PLAYER_WYID IN {id_str} ORDER BY"))

                # Rens ID'er for match
                for df in [df_sql_p, df_career]:
                # AVANCEREDE STATS (Den nye query fra din SQL fil)
                # Vi tilføjer filteret for de relevante spillere her
                perf_query = queries["player_stats_total"] + f" AND pt.PLAYER_WYID IN {id_str}"
                df_advanced_stats = conn.query(perf_query)
                
                # Rens ID'er og kolonnenavne for alle DataFrames
                for df in [df_sql_p, df_career, df_advanced_stats]:
if df is not None and not df.empty:
df.columns = [str(c).upper().strip() for c in df.columns]
df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
@@ -64,9 +59,10 @@
st.sidebar.error(f"Snowflake Fejl: {str(e)[:100]}")

return {
        "scout_reports": scout_df,           # Fra CSV (Historikken)
        "wyscout_players": df_wyscout_search, # Den store dropdown-liste (SQL)
        "players": load_local_players(),     # Fra players.csv
        "sql_players": df_sql_p,             # Billeder til rapporter
        "career": df_career                  # Stats til rapporter
        "scout_reports": scout_df,
        "wyscout_players": df_wyscout_search,
        "players": load_local_players(),
        "sql_players": df_sql_p,
        "career": df_career,
        "advanced_stats": df_advanced_stats  # NU TILGÆNGELIG I APPEN
}
