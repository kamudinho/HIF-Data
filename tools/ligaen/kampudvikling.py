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

def get_team_details_by_wyid(wyid_val):
    for name, info in TEAMS.items():
        if info.get('team_wyid') == wyid_val:
            return name, info.get('logo', '')
    return f"Hold {wyid_val}", ''

@st.cache_data(ttl=3600)
def load_match_level_data(wyid, team_wyid, season_start_year=2026):
    conn = _get_snowflake_conn()
    db = "KLUB_HVIDOVREIF.AXIS"
    
    start_date = f"{season_start_year}-07-01"
    end_date = f"{season_start_year + 1}-06-30"
    
    query = f"""
        SELECT 
            tm.MATCH_WYID,
            tm.TEAM_WYID,
            TO_CHAR(tm.DATE, 'YYYY-MM-DD') as MATCH_DATE,
            adv.XG,
            adv.SHOTS,
            adv.GOALS,
            opp_adv.GOALS as GOALS_AGAINST,
            md.PPDA,
            mp.PASSES,
            opp.TEAM_WYID as OPP_WYID,
            AVG(adv.XG) OVER() as AVG_XG,
            AVG(adv.GOALS) OVER() as AVG_GOALS,
            AVG(opp_adv.GOALS) OVER() as AVG_GOALS_AGAINST,
            AVG(adv.SHOTS) OVER() as AVG_SHOTS,
            AVG(mp.PASSES) OVER() as AVG_PASSES,
            AVG(md.PPDA) OVER() as AVG_PPDA
        FROM {db}.WYSCOUT_TEAMMATCHES tm 
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID 
        LEFT JOIN {db}.WYSCOUT_TEAMMATCHES opp ON tm.MATCH_WYID = opp.MATCH_WYID AND tm.TEAM_WYID <> opp.TEAM_WYID
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_GENERAL opp_adv ON opp.MATCH_WYID = opp_adv.MATCH_WYID AND opp.TEAM_WYID = opp_adv.TEAM_WYID
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_DEFENCE md ON tm.MATCH_WYID = md.MATCH_WYID AND tm.TEAM_WYID = md.TEAM_WYID 
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_PASSES mp ON tm.MATCH_WYID = mp.MATCH_WYID AND tm.TEAM_WYID = mp.TEAM_WYID
        WHERE tm.COMPETITION_WYID = {wyid} 
        AND tm.DATE >= '{start_date}' AND tm.DATE <= '{end_date}'
        ORDER BY tm.DATE ASC
    """
    df = conn.query(query)
    if not df.empty:
        df.columns = [c.upper() for c in df.columns]
    
    if df.empty or 'TEAM_WYID' not in df.columns:
        return pd.DataFrame()
        
    # Filtrer kun det valgte hold fra det samlede ligasæt
    df_team = df[df['TEAM_WYID'] == team_wyid].copy()
    return df_team

def draw_match_trend_chart(df_matches, metric, label, team_name):
    if df_matches is None or df_matches.empty:
        st.warning("Ingen kampdata tilgængelig for dette hold i den valgte sæson/turnering.")
        return

    fig = go.Figure()
    df_matches[metric] = pd.to_numeric(df_matches[metric], errors='coerce')
    
    # Tilføj kampnummer (1, 2, 3...)
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

    # Hent det beregnede ligagennemsnit fra kolonnen
    avg_col = f"AVG_{metric}"
    if avg_col in df_matches.columns and not df_matches[avg_col].dropna().empty:
        ligasnit = df_matches[avg_col].dropna().iloc[0]
    else:
        ligasnit = y_vals.mean() if has_data else 0.0

    opp_names = []
    opp_logos = []
    hover_texts = []

    for _, row in df_matches.iterrows():
        opp_wyid = row.get('OPP_WYID')
        o_name, o_logo = get_team_details_by_wyid(opp_wyid)
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

    # Logo størrelse (forbliver konsistent relativt til datapunkterne)
    logo_size_x = 0.55  
    logo_size_y = y_span * 0.32 if has_data else 0.3  

    # 1. Tilføj modstander-logoer som layout-billeder på plottet
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

    # 2. Tilføj linje og usynlige punkter for præcis hover
    fig.add_trace(go.Scatter(
        x=df_matches['MATCH_NUM'], 
        y=df_matches[metric], 
        mode='lines+markers',
        line=dict(color='#C41E3A', width=2, dash='dot'),
        marker=dict(size=40, opacity=0), 
        hovertext=df_matches['HOVER_TEXT'],
        hoverinfo='text'
    ))

    # 3. Holdets gennemsnitslinie (stiplet grå)
    if has_data:
        fig.add_hline(
            y=snit_vaerdi, 
            line_dash="dash", 
            line_color="gray", 
            annotation_text=f"Hold-snit: {snit_vaerdi:.2f}", 
            annotation_position="bottom right"
        )

    # 4. Ligagennemsnitslinie (fuld blå linje)
    fig.add_hline(
        y=ligasnit, 
        line_dash="solid", 
        line_color="blue", 
        line_width=2,
        annotation_text=f"Liga-snit: {ligasnit:.2f}", 
        annotation_position="top right"
    )

    is_reversed = "PPDA" in label.upper() or "IMOD" in label.upper()

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
            # Ingen fast range her, så Plotly automatisk zoomer ind på det faktiske antal kampe
            gridcolor="#f0f0f0", 
            linecolor='black'
        ),
        yaxis=yaxis_config,
        plot_bgcolor='white',
        showlegend=False,
        annotations=[dict(
            x=1, y=1.04, xref='paper', yref='paper',
            text=f"<b>{team_name} – Kamp-til-kamp udvikling ({DEFAULT_SEASON})</b>",
            showarrow=False, font=dict(size=13, color="#666666"),
            xanchor='right'
        )]
    )
    st.plotly_chart(fig, use_container_width=True)

# --- 3. HOVEDFUNKTION ---

def vis_side():
    default_team_name = "Hvidovre"
    default_team_wyid = TEAMS.get(default_team_name, {}).get("team_wyid", 7490)
    wyid = COMPETITIONS.get(DEFAULT_COMP, {}).get("wyid", 328)

    try:
        season_start_year = int(DEFAULT_SEASON.split('/')[0])
    except:
        season_start_year = 2026

    col_title, col_t, col_m = st.columns([1.8, 1.2, 1.0])
    
    with col_t:
        valgt_hold = st.selectbox("Vælg hold:", list(TEAMS.keys()), index=list(TEAMS.keys()).index(default_team_name) if default_team_name in TEAMS else 0)
        valgt_team_wyid = TEAMS.get(valgt_hold, {}).get("team_wyid", default_team_wyid)

    with col_m:
        metric_map = {
            "xG": "XG", 
            "Mål": "GOALS", 
            "Mål imod": "GOALS_AGAINST", 
            "Skud": "SHOTS", 
            "Afleveringer": "PASSES", 
            "PPDA": "PPDA"
        }
        sel_metric = st.selectbox("Parameter:", list(metric_map.keys()))

    with col_title:
        st.subheader(f"{valgt_hold} – Kampoversigt")
        st.caption(f"Udvikling i {DEFAULT_COMP} ({DEFAULT_SEASON})")

    df_matches = load_match_level_data(wyid, valgt_team_wyid, season_start_year=season_start_year)
    draw_match_trend_chart(df_matches, metric_map[sel_metric], sel_metric, valgt_hold)

if __name__ == "__main__":
    vis_side()
