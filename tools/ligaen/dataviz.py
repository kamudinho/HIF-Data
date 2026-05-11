import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

# --- 1. DATA LOADING ---

@st.cache_data(ttl=3600)
def get_team_viz_data():
    conn = _get_snowflake_conn()
    # Henter gennemsnitlige hold-metrics
    query = """
        SELECT t.TEAMNAME, t.TEAM_WYID,
               AVG(adv.SHOTS) as SHOTS, AVG(adv.GOALS) as GOALS, AVG(adv.XG) as XG,
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
    df = conn.query(query)
    # Tving kolonnenavne til upper for konsistens
    df.columns = [c.upper() for c in df.columns]
    return df

def get_logo_url_by_name(team_name):
    # Matcher navnet mod din TEAMS dictionary
    for name, info in TEAMS.items():
        if name.lower() in team_name.lower() or team_name.lower() in name.lower():
            return info.get('logo', "")
    return ""

# --- 2. HOVEDFUNKTION ---

def vis_side():
    df = get_team_viz_data()
    
    if df is None or df.empty:
        st.error("Kunne ikke hente data til visualiseringen.")
        return

    # --- FILTRE ---
    col1, col2 = st.columns([1, 1])
    
    with col1:
        metric_map = {
            'Mål': 'GOALS',
            'Expected Goals (xG)': 'XG',
            'Skud': 'SHOTS',
            'Interceptions': 'INTERCEPTIONS',
            'Tacklinger': 'TACKLES',
            'Afleveringer': 'PASSES',
            'Progressive Afleveringer': 'PROGRESSIVEPASSES'
        }
        selected_label = st.selectbox("Vælg Kategori", list(metric_map.keys()))
        selected_col = metric_map[selected_label]

    # Sortering så det bedste hold er øverst
    df_plot = df.sort_values(selected_col, ascending=True)

    # --- PLOTLY SETUP ---
    fig = go.Figure()

    # Søjler
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

    # Tilføj Logoer som layout images på y-aksen
    for i, row in df_plot.iterrows():
        url = get_logo_url_by_name(row['TEAMNAME'])
        if url:
            fig.add_layout_image(
                dict(
                    source=url,
                    xref="paper", yref="y",
                    x=-0.01, y=row['TEAMNAME'],
                    sizex=0.8, sizey=0.8,
                    xanchor="right", yanchor="middle"
                )
            )

    fig.update_layout(
        height=700,
        margin=dict(l=160, r=60, t=40, b=40),
        plot_bgcolor='white',
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

if __name__ == "__main__":
    vis_side()
