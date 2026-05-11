import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.utils.team_mapping import TEAMS, TEAM_COLORS, COMPETITIONS, TOURNAMENTCALENDAR_NAME
from data.data_load import _get_snowflake_conn

# --- 1. DATA LOADING ---

@st.cache_data(ttl=3600)
def get_team_viz_data():
    conn = _get_snowflake_conn()
    wyid = COMPETITIONS["1. Division"]["wyid"]
    season = TOURNAMENTCALENDAR_NAME # "2025/2026" fra din mapping
    
    # Vi filtrerer specifikt på NordicBet Liga (328) og den aktuelle sæson
    query = f"""
        SELECT t.TEAMNAME, t.TEAM_WYID,
               AVG(adv.SHOTS) as SHOTS, AVG(adv.GOALS) as GOALS, AVG(adv.XG) as XG,
               AVG(md.INTERCEPTIONS) as INTERCEPTIONS, AVG(md.TACKLES) as TACKLES, 
               AVG(mp.PASSES) as PASSES, AVG(mp.PROGRESSIVEPASSES) as PROGRESSIVEPASSES
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMMATCHES tm 
        JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMS t ON tm.TEAM_WYID = t.TEAM_WYID 
        LEFT JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID 
        LEFT JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_MATCHADVANCEDSTATS_DEFENCE md ON tm.MATCH_WYID = md.MATCH_WYID AND tm.TEAM_WYID = md.TEAM_WYID 
        LEFT JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_MATCHADVANCEDSTATS_PASSES mp ON tm.MATCH_WYID = mp.MATCH_WYID AND tm.TEAM_WYID = mp.TEAM_WYID 
        WHERE tm.COMPETITION_WYID = {wyid}
        AND tm.SEASONNAME = '{season}'
        GROUP BY t.TEAMNAME, t.TEAM_WYID
    """
    df = conn.query(query)
    if df is not None:
        df.columns = [c.upper() for c in df.columns]
    return df

def get_logo_url_by_name(team_name):
    # Direkte opslag i din TEAMS dictionary
    for name, info in TEAMS.items():
        if name.lower() in team_name.lower() or team_name.lower() in name.lower():
            return info.get('logo', "")
    return ""

# --- 2. HOVEDFUNKTION ---

def vis_side():
    df = get_team_viz_data()
    
    if df is None or df.empty:
        st.warning(f"Ingen data fundet for 1. Division i sæsonen {TOURNAMENTCALENDAR_NAME}.")
        return

    # --- DROP-DOWN FILTRERING ---
    metric_map = {
        'Expected Goals (xG)': 'XG',
        'Mål': 'GOALS',
        'Skud': 'SHOTS',
        'Interceptions': 'INTERCEPTIONS',
        'Tacklinger': 'TACKLES',
        'Afleveringer': 'PASSES',
        'Progressive Afleveringer': 'PROGRESSIVEPASSES'
    }
    
    selected_label = st.selectbox("Vælg Metric", list(metric_map.keys()))
    selected_col = metric_map[selected_label]

    # Sortering (Lavest til højest for horisontal bar chart)
    df_plot = df.sort_values(selected_col, ascending=True)

    # --- PLOTLY GRAF ---
    fig = go.Figure()

    # Søjlerne
    fig.add_trace(go.Bar(
        x=df_plot[selected_col],
        y=df_plot['TEAMNAME'],
        orientation='h',
        marker_color=[TEAM_COLORS.get(name, {}).get("primary", "#1b365d") for name in df_plot['TEAMNAME']],
        text=df_plot[selected_col].round(2),
        textposition='outside',
        textfont=dict(size=12, weight='bold'),
        cliponaxis=False
    ))

    # Tilføj Logoer på Y-aksen
    for i, row in df_plot.iterrows():
        url = get_logo_url_by_name(row['TEAMNAME'])
        if url:
            fig.add_layout_image(
                dict(
                    source=url,
                    xref="paper", yref="y",
                    x=-0.01, y=row['TEAMNAME'],
                    sizex=0.7, sizey=0.7,
                    xanchor="right", yanchor="middle"
                )
            )

    fig.update_layout(
        title=dict(
            text=f"1. Division {TOURNAMENTCALENDAR_NAME} - {selected_label}", 
            font=dict(size=18)
        ),
        height=700,
        margin=dict(l=160, r=60, t=60, b=40),
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            title=selected_label,
            showgrid=True,
            gridcolor='rgba(200, 200, 200, 0.3)',
            zeroline=False
        ),
        yaxis=dict(
            title=None,
            showgrid=False
        ),
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
