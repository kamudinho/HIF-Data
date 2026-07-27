import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, TEAM_COLORS, SEASONS
from data.data_load import _get_snowflake_conn

st.set_page_config(page_title="Winning Performance", layout="wide")

st.title("🎯 Winning Performance & Kamp-KPI'er")
st.markdown("Denne analyse viser, hvilke præstationsmål der statistisk set skal opfyldes for at vinde kampe i 1. Division.")

conn = _get_snowflake_conn()
if not conn:
    st.error("Kunne ikke forbinde til Snowflake.")
    st.stop()

DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_NAVN = "1. Division"

# --- SÆSON OG HOLD VALG ---
col_s, col_t = st.columns(2)
with col_s:
    valgt_saeson = st.selectbox("Sæson", list(SEASONS.keys()), key="wp_season")
with col_t:
    hvidovre_uuid = TEAMS.get("Hvidovre", {}).get("opta_uuid", "")
    hvidovre_uuid = str(hvidovre_uuid).strip().upper()

LIGA_UUID = SEASONS[valgt_saeson][LIGA_NAVN]

# --- HENT DATA (Samme struktur som din hovedside) ---
sql = f"""
    WITH MatchBase AS (
        SELECT 
            MATCH_OPTAUUID, MATCH_DATE_FULL, MATCH_STATUS,
            CONTESTANTHOME_OPTAUUID, CONTESTANTAWAY_OPTAUUID,
            TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE
        FROM {DB}.OPTA_MATCHINFO
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
    ),
    StatsPivot AS (
        SELECT 
            MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
            MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL END) AS POSSESSION,
            SUM(CASE WHEN STAT_TYPE = 'totalPass' THEN STAT_TOTAL ELSE 0 END) AS PASSES,
            SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_TOTAL ELSE 0 END) AS SHOTS
        FROM {DB}.OPTA_MATCHSTATS
        GROUP BY 1, 2
    ),
    XGPivot AS (
        SELECT 
            MATCH_ID, CONTESTANT_OPTAUUID,
            SUM(CASE WHEN STAT_TYPE IN ('expectedGoals', 'expectedGoal') THEN STAT_VALUE ELSE 0 END) AS XG,
            SUM(CASE WHEN STAT_TYPE = 'bigChanceCreated' THEN STAT_VALUE ELSE 0 END) AS BIG_CHANCES
        FROM {DB}.OPTA_MATCHEXPECTEDGOALS
        GROUP BY 1, 2
    )
    SELECT 
        b.*,
        h.POSSESSION AS HOME_POSS, hx.XG AS HOME_XG, hx.BIG_CHANCES AS HOME_BIG_CHANCES, h.SHOTS AS HOME_SHOTS,
        a.POSSESSION AS AWAY_POSS, ax.XG AS AWAY_XG, ax.BIG_CHANCES AS AWAY_BIG_CHANCES, a.SHOTS AS AWAY_SHOTS
    FROM MatchBase b
    LEFT JOIN StatsPivot h ON b.MATCH_OPTAUUID = h.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = h.CONTESTANT_OPTAUUID
    LEFT JOIN StatsPivot a ON b.MATCH_OPTAUUID = a.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = a.CONTESTANT_OPTAUUID
    LEFT JOIN XGPivot hx ON b.MATCH_OPTAUUID = hx.MATCH_ID AND b.CONTESTANTHOME_OPTAUUID = hx.CONTESTANT_OPTAUUID
    LEFT JOIN XGPivot ax ON b.MATCH_OPTAUUID = ax.MATCH_ID AND b.CONTESTANTAWAY_OPTAUUID = ax.CONTESTANT_OPTAUUID
"""

@st.cache_data
def load_data(query):
    c = _get_snowflake_conn()
    return c.query(query) if hasattr(c, 'query') else pd.read_sql(query, c)

df_matches = load_data(sql)

if df_matches.empty:
    st.warning("Ingen data fundet.")
    st.stop()

# Rensning
df_matches.columns = [str(c).upper() for c in df_matches.columns]
played = df_matches[df_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].copy()

# --- BEGREB: UDLED HOLDETS RESULTATER ---
match_rows = []
for _, row in played.iterrows():
    h_uuid = str(row['CONTESTANTHOME_OPTAUUID']).strip().upper()
    a_uuid = str(row['CONTESTANTAWAY_OPTAUUID']).strip().upper()
    
    h_score = int(row['TOTAL_HOME_SCORE'])
    a_score = int(row['TOTAL_AWAY_SCORE'])
    
    # Hjemmeholdets perspektiv
    match_rows.append({
        'TEAM_UUID': h_uuid,
        'RESULTAT': 'Sejr' if h_score > a_score else ('Uafgjort' if h_score == a_score else 'Nederlag'),
        'POSS': row.get('HOME_POSS', 0),
        'XG': row.get('HOME_XG', 0),
        'SHOTS': row.get('HOME_SHOTS', 0),
        'BIG_CHANCES': row.get('HOME_BIG_CHANCES', 0)
    })
    # Udeholdets perspektiv
    match_rows.append({
        'TEAM_UUID': a_uuid,
        'RESULTAT': 'Sejr' if a_score > h_score else ('Uafgjort' if h_score == h_score else 'Nederlag'),
        'POSS': row.get('AWAY_POSS', 0),
        'XG': row.get('AWAY_XG', 0),
        'SHOTS': row.get('AWAY_SHOTS', 0),
        'BIG_CHANCES': row.get('AWAY_BIG_CHANCES', 0)
    })

df_perf = pd.DataFrame(match_rows)

# Filtrer kun for Hvidovre (eller lad brugeren vælge)
hvidovre_perf = df_perf[df_perf['TEAM_UUID'] == hvidovre_uuid]

st.subheader("📊 Hvidovre IF: Hvad skal der til for at vinde?")
st.markdown("Nedenfor ses gennemsnittet af holdets præstationer opdelt efter kampens udfald i den valgte sæson.")

if not hvidovre_perf.empty:
    # Beregn gennemsnit pr. udfald
    summary_table = hvidovre_perf.groupby('RESULTAT')[['POSS', 'XG', 'SHOTS', 'BIG_CHANCES']].mean().reindex(['Sejr', 'Uafgjort', 'Nederlag'])
    
    # Vis tabellen pænt
    st.dataframe(summary_table.style.format("{:.2f}").background_gradient(cmap="Greens", subset=["XG", "BIG_CHANCES"]), use_container_width=True)
    
    st.info("""
    **Sådan læses tabellen:**
    * **xG (Expected Goals):** Viser det gennemsnitlige antal chancer, holdet skal skabe for at vinde.
    * **Store Chancer:** Indikerer minimumskravet til offensive gennembrud i kampe, der ender med 3 point.
    """)
else:
    st.warning("Ikke nok data tilgængelig for Hvidovre i denne sæson.")
