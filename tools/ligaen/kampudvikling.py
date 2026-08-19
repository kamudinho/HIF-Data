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
    """Sikker konvertering af værdier til int, der håndterer NaN og None."""
    try:
        if pd.isnull(val):
            return 0
        return int(float(val))
    except:
        return 0

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
        )
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
            
            AVG(xg.EXPECTEDGOALS) OVER() AS AVG_EXPECTEDGOALS,
            AVG(sp.TOTALSCORINGATT) OVER() AS AVG_TOTALSCORINGATT,
            AVG(sp.TOTALPASS) OVER() AS AVG_TOTALPASS,
            AVG(sp.ACCURATEPASS) OVER() AS AVG_ACCURATEPASS,
            AVG(sp.POSSESSIONPERCENTAGE) OVER() AS AVG_POSSESSIONPERCENTAGE,
            AVG(sp.WONCORNERS) OVER() AS AVG_WONCORNERS,
            AVG(sp.TOTALTACKLE) OVER() AS AVG_TOTALTACKLE,
            AVG(sp.TOTALCLEARANCE) OVER() AS AVG_TOTALCLEARANCE,
            AVG(wd.PPDA) OVER() AS AVG_PPDA

        FROM MatchBase mb
        JOIN MatchStatsPivot sp ON mb.MATCH_OPTAUUID = sp.MATCH_OPTAUUID
        LEFT JOIN ExpectedGoalsPivot xg ON sp.MATCH_OPTAUUID = xg.MATCH_OPTAUUID AND sp.CONTESTANT_OPTAUUID = xg.CONTESTANT_OPTAUUID
        LEFT JOIN WyscoutDefense wd ON mb.MATCH_DATE = wd.MATCH_DATE 
        
        WHERE sp.CONTESTANT_OPTAUUID = '{team_opta_uuid}'
        ORDER BY mb.MATCH_DATE ASC
    """
    df = conn.query(query)
    
    if not df.empty:
        df.columns = [c.upper() for c in df.columns]
    
    return df

def draw_match_trend_chart(df_matches, metric, label, team_name):
    if df_matches is None or df_matches.empty:
        st.warning("Ingen kampdata tilgængelig for dette hold i den valgte sæson/turnering.")
        return

    fig = go.Figure()
    df_matches[metric] = pd.to_numeric(df_matches[metric], errors='coerce')
    
    df_matches['MATCH_NUM'] = range(1, len(df_matches) + 1)
    
    y_vals = df_matches[metric].dropna()
    has_data = not y_vals.empty

    if has_data:
        y_min = y_vals.min()
        y_max = y_vals.max()
        y_span = y_max - y_min if y_max != y_min else 1.0
        snit_vaerdi = y_vals.mean()
    else:
        y_span = 1.0
        snit_vaerdi = 0.0

    avg_col = f"AVG_{metric}"
    if avg_col in df_matches.columns and not df_matches[avg_col].dropna().empty:
        ligasnit = df_matches[avg_col].dropna().iloc[0]
    else:
        ligasnit = y_vals.mean() if has_data else 0.0

    opp_names = []
    opp_logos = []
    hover_texts = []

    for _, row in df_matches.iterrows():
        home_uuid = row.get('CONTESTANTHOME_OPTAUUID')
        away_uuid = row.get('CONTESTANTAWAY_OPTAUUID')
        current_team_uuid = row.get('TEAM_OPTAUUID')
        
        opp_uuid = away_uuid if current_team_uuid == home_uuid else home_uuid
        
        o_name, o_logo = "Modstander", ""
        for name, info in TEAMS.items():
            if info.get('opta_uuid') == opp_uuid:
                o_name, o_logo = name, info.get('logo', '')
                break

        opp_names.append(o_name)
        opp_logos.append(o_logo)
        
        g_for = safe_int(row.get('GOALS'))
        g_imod = safe_int(row.get('GOALS_AGAINST'))
        dato = str(row.get('MATCH_DATE', ''))[:10]
        
        hover_texts.append(
            f"<b>Kamp {int(row['MATCH_NUM'])} vs. {o_name}</b><br>"
            f"Dato: {dato}<br>"
            f"Resultat: {g_for} - {g_imod}<br>"
            f"{label}: {row.get(metric, 0):.2f}"
        )

    df_matches['OPP_NAME'] = opp_names
    df_matches['OPP_LOGO'] = opp_logos
    df_matches['HOVER_TEXT'] = hover_texts

    # --- FORSTØRREDE LOGO-DIMENSIONER ---
    logo_size_x = 0.65  # Tidligere 0.40 (gør dem bredere)
    logo_size_y = y_span * 0.20 if y_span > 0.5 else 0.25  # Gjort markant højere

    for _, row in df_matches.iterrows():
        if pd.notnull(row[metric]) and row.get('OPP_LOGO'):
            b64_logo = get_base64_image(row['OPP_LOGO'])
            fig.add_layout_image(dict(
                source=b64_logo, 
                xref="x", 
                yref="y",
                x=row['MATCH_NUM'], 
                y=row[metric],
                sizex=logo_size_x, 
                sizey=logo_size_y,
                xanchor="center", 
                yanchor="middle"
            ))

    is_reversed = "PPDA" in label.upper() or "IMOD" in label.upper()

    if len(df_matches) > 1:
        for i in range(len(df_matches) - 1):
            y0 = df_matches[metric].iloc[i]
            y1 = df_matches[metric].iloc[i+1]
            x0 = df_matches['MATCH_NUM'].iloc[i]
            x1 = df_matches['MATCH_NUM'].iloc[i+1]
            
            if pd.notnull(y0) and pd.notnull(y1):
                if is_reversed:
                    is_up = y1 < y0
                else:
                    is_up = y1 > y0
                
                seg_color = '#2ECC71' if is_up else '#E74C3C' if y1 != y0 else '#95A5A6'
                
                fig.add_trace(go.Scatter(
                    x=[x0, x1],
                    y=[y0, y1],
                    mode='lines',
                    line=dict(color=seg_color, width=2, dash='dot'),
                    showlegend=False,
                    hoverinfo='skip'
                ))

    fig.add_trace(go.Scatter(
        x=df_matches['MATCH_NUM'], 
        y=df_matches[metric], 
        mode='markers',
        marker=dict(size=40, opacity=0), 
        hovertext=df_matches['HOVER_TEXT'],
        hoverinfo='text',
        showlegend=False
    ))

    overlap_threshold = y_span * 0.10
    if abs(snit_vaerdi - ligasnit) < overlap_threshold:
        if snit_vaerdi >= ligasnit:
            team_pos = "top right"
            liga_pos = "bottom right"
        else:
            team_pos = "bottom right"
            liga_pos = "top right"
    else:
        team_pos = "top right"
        liga_pos = "bottom right"

    if has_data:
        fig.add_hline(
            y=snit_vaerdi, 
            line_dash="solid", 
            line_color="black", 
            line_width=1.5,
            annotation_text=f"(Gennemsnit: {team_name})", 
            annotation_position=team_pos
        )

    fig.add_hline(
        y=ligasnit, 
        line_dash="dash", 
        line_color="gray", 
        line_width=1.5,
        annotation_text=f"(Gennemsnit: {DEFAULT_COMP})", 
        annotation_position=liga_pos
    )

    yaxis_config = dict(
        title=f"<b>{label} pr. kamp</b>", 
        gridcolor="#f0f0f0", 
        linecolor='black',
        autorange="reversed" if is_reversed else True
    )

    fig.update_layout(
        height=550, 
        margin=dict(t=50, b=60, l=60, r=40),
        xaxis=dict(
            title="<b>Kampnummer</b>", 
            tickmode='linear', 
            dtick=1,
            gridcolor="#f0f0f0", 
            linecolor='black'
        ),
        yaxis=yaxis_config,
        plot_bgcolor='white',
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

# --- 3. HOVEDFUNKTION ---

def vis_side():
    tilgængelige_hold = SEASON_LEAGUE_MAPPER.get("2026/2027", {}).get(DEFAULT_COMP, list(TEAMS.keys()))
    
    default_team_name = "Hvidovre" if "Hvidovre" in tilgængelige_hold else tilgængelige_hold[0]
    default_team_info = TEAMS.get(default_team_name, {})
    default_team_wyid = default_team_info.get("team_wyid", 7490)
    default_team_opta_uuid = default_team_info.get("opta_uuid", '8gxd9ry2580pu1b1dd5ny9ymy')

    tournament_opta_map = {
        "NordicBet Liga": "2mb332vncy4450vu14paj8844",
        "Superliga": "29actv1ohj8r10kd9hu0jnb0n"
    }
    current_opta_uuid = tournament_opta_map.get(DEFAULT_COMP, "2mb332vncy4450vu14paj8844")
    comp_wyid = COMPETITIONS.get(DEFAULT_COMP, {}).get("wyid", 328)

    try:
        season_start_year = int(DEFAULT_SEASON.split('/')[0])
    except:
        season_start_year = 2026

    col_title, col_t, col_m = st.columns([1.8, 1.2, 1.0])
    
    with col_t:
        valgt_hold = st.selectbox("Vælg hold:", tilgængelige_hold, index=tilgængelige_hold.index(default_team_name) if default_team_name in tilgængelige_hold else 0)
        valgt_team_info = TEAMS.get(valgt_hold, {})
        valgt_team_wyid = valgt_team_info.get("team_wyid", default_team_wyid)
        valgt_team_opta_uuid = valgt_team_info.get("opta_uuid", default_team_opta_uuid)

    with col_m:
        metric_map = {
            "xG": "EXPECTEDGOALS", 
            "Mål": "GOALS", 
            "Mål imod": "GOALS_AGAINST", 
            "Skud": "TOTALSCORINGATT", 
            "Afleveringer": "TOTALPASS", 
            "PPDA": "PPDA",
            "Hjørnespark": "wonCorners",
            "Hjørnespark, mod": "lostCorners",
        }
        sel_metric = st.selectbox("Parameter:", list(metric_map.keys()))

    with col_title:
        st.subheader(f"{valgt_hold} – Kampoversigt")
        st.caption(f"Udvikling i {DEFAULT_COMP} ({DEFAULT_SEASON})")

    df_matches = load_match_level_data(
        tournament_opta_uuid=current_opta_uuid,
        team_opta_uuid=valgt_team_opta_uuid,
        team_wyid=valgt_team_wyid,
        comp_wyid=comp_wyid,
        season_start_year=season_start_year
    )
    draw_match_trend_chart(df_matches, metric_map[sel_metric], sel_metric, valgt_hold)

if __name__ == "__main__":
    vis_side()
