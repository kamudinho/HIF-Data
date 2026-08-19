import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import base64

# --- IMPORT DYNAMISKE KONSTANTER OG MAPPINGS ---
from data.utils.team_mapping import (
    SEASONS,
    COMPETITIONS,
    SEASON_LEAGUE_MAPPER,
    TEAMS,
    COMPETITION_NAME as DEFAULT_COMP,
    TOURNAMENTCALENDAR_NAME as DEFAULT_SEASON
)
from data.data_load import _get_snowflake_conn

# --- 1. HJÆLPEFUNKTIONER ---

@st.cache_data(ttl=86400)
def get_base64_image(url):
    try:
        if not url: return ""
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            encoded_str = base64.b64encode(response.content).decode("utf-8")
            return f"data:image/png;base64,{encoded_str}"
    except: 
        return url
    return url

def safe_int(val):
    try:
        if pd.isnull(val): return 0
        return int(float(val))
    except: return 0

@st.cache_data(ttl=3600)
def load_match_level_data(tournament_opta_uuid, team_opta_uuid, team_wyid, comp_wyid, season_start_year=2026):
    conn = _get_snowflake_conn()
    db = "KLUB_HVIDOVREIF.AXIS"
    
    query = f"""
        WITH MatchBase AS (
            SELECT 
                MATCH_OPTAUUID, 
                TO_CHAR(MATCH_DATE_FULL, 'YYYY-MM-DD') AS MATCH_DATE,
                CONTESTANTHOME_OPTAUUID, 
                CONTESTANTAWAY_OPTAUUID,
                TOTAL_HOME_SCORE, 
                TOTAL_AWAY_SCORE
            FROM {db}.OPTA_MATCHINFO
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{tournament_opta_uuid}'
        ),
        MatchStatsPivot AS (
            SELECT 
                MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
                MAX(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN CAST(STAT_TOTAL AS FLOAT) END) AS TOTALSCORINGATT,
                MAX(CASE WHEN STAT_TYPE = 'ontargetScoringAtt' THEN CAST(STAT_TOTAL AS FLOAT) END) AS ONTARGETSCORINGATT,
                MAX(CASE WHEN STAT_TYPE = 'shotOffTarget' THEN CAST(STAT_TOTAL AS FLOAT) END) AS SHOTOFFTARGET,
                MAX(CASE WHEN STAT_TYPE = 'blockedScoringAtt' THEN CAST(STAT_TOTAL AS FLOAT) END) AS BLOCKEDSCORINGATT,
                MAX(CASE WHEN STAT_TYPE = 'subsGoals' THEN CAST(STAT_TOTAL AS FLOAT) END) AS SUBSGOALS,
                MAX(CASE WHEN STAT_TYPE = 'totalPass' THEN CAST(STAT_TOTAL AS FLOAT) END) AS TOTALPASS,
                MAX(CASE WHEN STAT_TYPE = 'accuratePass' THEN CAST(STAT_TOTAL AS FLOAT) END) AS ACCURATEPASS,
                MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN CAST(STAT_TOTAL AS FLOAT) END) AS POSSESSIONPERCENTAGE,
                MAX(CASE WHEN STAT_TYPE = 'wonCorners' THEN CAST(STAT_TOTAL AS FLOAT) END) AS WONCORNERS,
                MAX(CASE WHEN STAT_TYPE = 'lostCorners' THEN CAST(STAT_TOTAL AS FLOAT) END) AS LOSTCORNERS,
                MAX(CASE WHEN STAT_TYPE = 'totalTackle' THEN CAST(STAT_TOTAL AS FLOAT) END) AS TOTALTACKLE,
                MAX(CASE WHEN STAT_TYPE = 'wonTackle' THEN CAST(STAT_TOTAL AS FLOAT) END) AS WONTACKLE,
                MAX(CASE WHEN STAT_TYPE = 'totalClearance' THEN CAST(STAT_TOTAL AS FLOAT) END) AS TOTALCLEARANCE,
                MAX(CASE WHEN STAT_TYPE = 'outfielderBlock' THEN CAST(STAT_TOTAL AS FLOAT) END) AS OUTFIELDERBLOCK,
                MAX(CASE WHEN STAT_TYPE = 'fkFoulWon' THEN CAST(STAT_TOTAL AS FLOAT) END) AS FKFOULWON,
                MAX(CASE WHEN STAT_TYPE = 'fkFoulLost' THEN CAST(STAT_TOTAL AS FLOAT) END) AS FKFOULLOST,
                MAX(CASE WHEN STAT_TYPE = 'saves' THEN CAST(STAT_TOTAL AS FLOAT) END) AS SAVES,
                MAX(CASE WHEN STAT_TYPE = 'goalsConceded' THEN CAST(STAT_TOTAL AS FLOAT) END) AS GOALSCONCEDED,
                MAX(CASE WHEN STAT_TYPE = 'cleanSheet' THEN CAST(STAT_TOTAL AS FLOAT) END) AS CLEANSHEET
            FROM {db}.OPTA_MATCHSTATS
            WHERE MATCH_OPTAUUID IN (SELECT MATCH_OPTAUUID FROM MatchBase)
            GROUP BY 1, 2
        ),
        ExpectedGoalsPivot AS (
            SELECT 
                MATCH_ID AS MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
                SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS EXPECTEDGOALS
            FROM {db}.OPTA_MATCHEXPECTEDGOALS
            WHERE MATCH_ID IN (SELECT MATCH_OPTAUUID FROM MatchBase)
            GROUP BY 1, 2
        ),
        WyscoutDefense AS (
            SELECT 
                TO_CHAR(tm.DATE, 'YYYY-MM-DD') AS MATCH_DATE,
                md.PPDA
            FROM {db}.WYSCOUT_TEAMMATCHES tm
            LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_DEFENCE md 
                ON tm.MATCH_WYID = md.MATCH_WYID AND tm.TEAM_WYID = md.TEAM_WYID
            WHERE tm.COMPETITION_WYID = {comp_wyid} AND tm.TEAM_WYID = {team_wyid}
        ),
        FullTournamentData AS (
            SELECT 
                mb.MATCH_OPTAUUID,
                mb.MATCH_DATE,
                sp.CONTESTANT_OPTAUUID AS TEAM_OPTAUUID,
                
                CASE WHEN sp.CONTESTANT_OPTAUUID = mb.CONTESTANTHOME_OPTAUUID THEN mb.TOTAL_HOME_SCORE ELSE mb.TOTAL_AWAY_SCORE END AS GOALS,
                CASE WHEN sp.CONTESTANT_OPTAUUID = mb.CONTESTANTHOME_OPTAUUID THEN mb.TOTAL_AWAY_SCORE ELSE mb.TOTAL_HOME_SCORE END AS GOALS_AGAINST,
                
                mb.CONTESTANTHOME_OPTAUUID,
                mb.CONTESTANTAWAY_OPTAUUID,

                sp.TOTALSCORINGATT,
                sp.ONTARGETSCORINGATT,
                sp.SHOTOFFTARGET,
                sp.BLOCKEDSCORINGATT,
                sp.SUBSGOALS,
                sp.TOTALPASS,
                sp.ACCURATEPASS,
                sp.POSSESSIONPERCENTAGE,
                sp.WONCORNERS,
                sp.LOSTCORNERS,
                sp.TOTALTACKLE,
                sp.WONTACKLE,
                sp.TOTALCLEARANCE,
                sp.OUTFIELDERBLOCK,
                sp.FKFOULWON,
                sp.FKFOULLOST,
                sp.SAVES,
                sp.GOALSCONCEDED,
                sp.CLEANSHEET,
                xg.EXPECTEDGOALS,
                wd.PPDA,
                
                AVG(xg.EXPECTEDGOALS) OVER() AS LIGA_AVG_EXPECTEDGOALS,
                AVG(sp.TOTALSCORINGATT) OVER() AS LIGA_AVG_TOTALSCORINGATT,
                AVG(sp.ONTARGETSCORINGATT) OVER() AS LIGA_AVG_ONTARGETSCORINGATT,
                AVG(sp.TOTALPASS) OVER() AS LIGA_AVG_TOTALPASS,
                AVG(sp.ACCURATEPASS) OVER() AS LIGA_AVG_ACCURATEPASS,
                AVG(sp.POSSESSIONPERCENTAGE) OVER() AS LIGA_AVG_POSSESSIONPERCENTAGE,
                AVG(sp.WONCORNERS) OVER() AS LIGA_AVG_WONCORNERS,
                AVG(sp.LOSTCORNERS) OVER() AS LIGA_AVG_LOSTCORNERS,
                AVG(sp.TOTALTACKLE) OVER() AS LIGA_AVG_TOTALTACKLE,
                AVG(wd.PPDA) OVER() AS LIGA_AVG_PPDA

            FROM MatchBase mb
            JOIN MatchStatsPivot sp ON mb.MATCH_OPTAUUID = sp.MATCH_OPTAUUID
            LEFT JOIN ExpectedGoalsPivot xg ON sp.MATCH_OPTAUUID = xg.MATCH_OPTAUUID AND sp.CONTESTANT_OPTAUUID = xg.CONTESTANT_OPTAUUID
            LEFT JOIN WyscoutDefense wd ON mb.MATCH_DATE = wd.MATCH_DATE 
        )
        SELECT * 
        FROM FullTournamentData
        WHERE TEAM_OPTAUUID = '{team_opta_uuid}'
        ORDER BY MATCH_DATE ASC
    """
    df = conn.query(query)
    if not df.empty:
        df.columns = [c.upper() for c in df.columns]
    return df

def draw_match_trend_chart(df_matches, metric, label, team_name):
    if df_matches is None or df_matches.empty:
        st.warning("Ingen kampdata tilgængelig.")
        return

    fig = go.Figure()
    df_matches[metric] = pd.to_numeric(df_matches[metric], errors='coerce')
    df_matches['MATCH_NUM'] = range(1, len(df_matches) + 1)
    
    y_vals = df_matches[metric].dropna()
    snit_vaerdi = y_vals.mean() if not y_vals.empty else 0.0
    liga_avg_col = f"LIGA_AVG_{metric}"
    ligasnit = df_matches[liga_avg_col].iloc[0] if liga_avg_col in df_matches.columns else snit_vaerdi

    is_reversed = "PPDA" in label.upper() or "IMOD" in label.upper()
    
    # --- LOGIK FOR PLACERING (TOP = OVER LINJEN, BOTTOM = UNDER LINJEN) ---
    # Hvis Reversed: Lavere tal er højere oppe visuelt.
    # Hvis Normal: Højere tal er højere oppe visuelt.
    
    if is_reversed:
        # Lavere tal er øverst
        if snit_vaerdi < ligasnit: # Holdet er øverst (bedre)
            team_pos, liga_pos = "top right", "bottom right"
        else: # Liga er øverst
            team_pos, liga_pos = "bottom right", "top right"
    else:
        # Højere tal er øverst
        if snit_vaerdi >= ligasnit: # Holdet er øverst
            team_pos, liga_pos = "top right", "bottom right"
        else: # Liga er øverst
            team_pos, liga_pos = "bottom right", "top right"

    # Tegn data
    fig.add_trace(go.Scatter(x=df_matches['MATCH_NUM'], y=df_matches[metric], mode='markers', marker=dict(size=40, opacity=0), showlegend=False))
    
    # Gennemsnitslinjer
    fig.add_hline(y=snit_vaerdi, line_dash="solid", line_color="black", line_width=1.5, annotation_text=f"Snit: {team_name}", annotation_position=team_pos)
    fig.add_hline(y=ligasnit, line_dash="dash", line_color="gray", line_width=1.5, annotation_text=f"Snit: {DEFAULT_COMP}", annotation_position=liga_pos)

    fig.update_layout(height=550, plot_bgcolor='white', yaxis=dict(title=f"<b>{label} pr. kamp</b>", autorange="reversed" if is_reversed else True, gridcolor="#f0f0f0"))
    st.plotly_chart(fig, use_container_width=True)

def vis_side():
    valgt_saeson = "2026/2027"
    tilgængelige_hold = SEASON_LEAGUE_MAPPER.get(valgt_saeson, {}).get(DEFAULT_COMP, list(TEAMS.keys()))
    default_team_name = "Hvidovre" if "Hvidovre" in tilgængelige_hold else tilgængelige_hold[0]
    
    valgt_hold = st.selectbox("Vælg hold:", tilgængelige_hold, index=tilgængelige_hold.index(default_team_name))
    valgt_team_info = TEAMS.get(valgt_hold, {})
    
    metric_map = {"xG": "EXPECTEDGOALS", "Mål": "GOALS", "Mål imod": "GOALS_AGAINST", "Skud": "TOTALSCORINGATT", "PPDA": "PPDA"}
    sel_metric = st.selectbox("Parameter:", list(metric_map.keys()))

    df = load_match_level_data(
        "2mb332vncy4450vu14paj8844", 
        valgt_team_info.get("opta_uuid"), 
        valgt_team_info.get("team_wyid"), 
        COMPETITIONS.get(DEFAULT_COMP, {}).get("wyid")
    )
    draw_match_trend_chart(df, metric_map[sel_metric], sel_metric, valgt_hold)

if __name__ == "__main__":
    vis_side()
