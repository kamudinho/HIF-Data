import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

# --- 1. DATA & LOGO LOGIK ---

@st.cache_data(ttl=3600)
def get_viz_data():
    conn = _get_snowflake_conn()
    # Vi henter metrics aggregeret pr. hold fra Wyscout
    query = """
        SELECT t.TEAMNAME, t.TEAM_WYID,
               AVG(adv.SHOTS) as SHOTS, AVG(adv.GOALS) as GOALS, 
               AVG(md.INTERCEPTIONS) as INTERCEPTIONS, AVG(md.TACKLES) as TACKLES, 
               AVG(mp.PASSES) as PASSES, AVG(mp.PROGRESSIVEPASSES) as PROGRESSIVEPASSES
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMMATCHES tm 
        JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMS t ON tm.TEAM_WYID = t.TEAM_WYID 
        LEFT JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID 
        LEFT JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_MATCHADVANCEDSTATS_DEFENCE md ON tm.MATCH_WYID = md.MATCH_WYID AND tm.TEAM_WYID = md.TEAM_WYID 
        LEFT JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_MATCHADVANCEDSTATS_PASSES mp ON tm.MATCH_WYID = mp.MATCH_WYID AND tm.TEAM_WYID = mp.TEAM_WYID 
        WHERE tm.COMPETITION_WYID = 328
        GROUP BY t.TEAMNAME, t.TEAM_WYID
    """
    return conn.query(query)

def get_logo_url_by_name(team_name):
    # Matcher teamnavn fra DB med din TEAM_mapping
    for name, info in TEAMS.items():
        if name.lower() in team_name.lower() or team_name.lower() in name.lower():
            return info.get('logo', "")
    return ""

# --- 2. UI & VISUALISERING ---

def draw_position_viz():
    df = get_viz_data()
    
    col1, col2 = st.columns(2)
    
    with col1:
        metric_options = {
            'Afslutninger': 'SHOTS',
            'Mål': 'GOALS',
            'Interceptions': 'INTERCEPTIONS',
            'Tacklinger': 'TACKLES',
            'Afleveringer': 'PASSES',
            'Progressive afleveringer': 'PROGRESSIVEPASSES'
        }
        selected_label = st.selectbox("Vælg Metric", list(metric_options.keys()))
        selected_metric = metric_options[selected_label]

    # Sortér data efter den valgte metric
    df_sorted = df.sort_values(selected_metric, ascending=True)

    fig = go.Figure()

    # Tilføj bar chart
    fig.add_trace(go.Bar(
        x=df_sorted[selected_metric],
        y=df_sorted['TEAMNAME'],
        orientation='h',
        marker_color=[TEAM_COLORS.get(name, {}).get("primary", "#1b365d") for name in df_sorted['TEAMNAME']],
        text=df_sorted[selected_metric].round(2),
        textposition='outside',
        cliponaxis=False
    ))

    # Tilføj Logoer ved siden af holdnavne
    for i, row in df_sorted.iterrows():
        logo_url = get_logo_url_by_name(row['TEAMNAME'])
        if logo_url:
            fig.add_layout_image(
                dict(
                    source=logo_url,
                    xref="paper", yref="y",
                    x=-0.02, y=row['TEAMNAME'],
                    sizex=0.8, sizey=0.8,
                    xanchor="right", yanchor="middle"
                )
            )

    fig.update_layout(
        title=f"Hold-sammenligning: {selected_label}",
        height=600,
        margin=dict(l=150, r=50, t=50, b=50),
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=True, gridcolor='lightgrey'),
        yaxis=dict(showgrid=False)
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

if __name__ == "__main__":
    draw_position_viz()
