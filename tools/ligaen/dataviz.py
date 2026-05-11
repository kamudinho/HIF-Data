import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

# --- 1. DATA LOADING (DIN SPECIFIKKE SQL) ---

@st.cache_data(ttl=3600)
def get_hvidovre_performance():
    conn = _get_snowflake_conn()
    db = "KLUB_HVIDOVREIF.AXIS"
    # Din query optimeret til Snowflake i Streamlit
    query = f"""
        SELECT 
            m.MATCHLABEL, tm.SEASON_WYID, tm.TEAM_WYID, tm.MATCH_WYID, 
            tm.DATE, tm.STATUS, tm.COMPETITION_WYID, tm.GAMEWEEK,
            c.COMPETITIONNAME AS COMPETITION_NAME, 
            adv.XG, adv.GOALS, adv.SHOTS, adv.XGPERSHOT
        FROM {db}.WYSCOUT_TEAMMATCHES tm
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv 
            ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID
        JOIN {db}.WYSCOUT_MATCHES m ON tm.MATCH_WYID = m.MATCH_WYID
        JOIN {db}.WYSCOUT_SEASONS s ON m.SEASON_WYID = s.SEASON_WYID
        JOIN {db}.WYSCOUT_COMPETITIONS c ON tm.COMPETITION_WYID = c.COMPETITION_WYID
        WHERE tm.COMPETITION_WYID = 328
            AND s.SEASONNAME = '2025/2026'
        ORDER BY tm.GAMEWEEK ASC
    """
    return conn.query(query)

# --- 2. LOGO POSITION CHART FUNKTION ---

def draw_gameweek_performance_chart(df, metric, label):
    """
    Viser holdenes præstation på x-aksen. 
    Bruger gennemsnit for de runder der er spillet indtil nu (1-22).
    """
    # Gruppér per hold for at få gennemsnitlig præstation i grundspillet
    df_agg = df[df['GAMEWEEK'] <= 22].groupby('TEAM_WYID').agg({
        metric: 'mean',
        'MATCHLABEL': 'last' # Bruges bare til at finde holdnavne via mapping
    }).reset_index()
    
    df_agg = df_agg.sort_values(metric).reset_index()
    
    fig = go.Figure()
    y_values = np.linspace(0.2, 0.8, len(df_agg))

    for i, row in df_agg.iterrows():
        # Find logo og info via TEAM_WYID
        team_id = int(row['TEAM_WYID'])
        team_info = next((info for name, info in TEAMS.items() if info.get('wyid') == team_id), {})
        logo_url = team_info.get('logo', "")
        
        if logo_url:
            fig.add_layout_image(dict(
                source=logo_url, xref="x", yref="y",
                x=row[metric], y=y_values[i],
                sizex=0.07 * (df_agg[metric].max() - df_agg[metric].min() if len(df_agg) > 1 else 1), 
                sizey=0.2, xanchor="center", yanchor="middle"
            ))

    fig.add_trace(go.Scatter(
        x=df_agg[metric], y=y_values, mode='markers',
        marker=dict(size=25, opacity=0),
        hovertext=[next((name for name, info in TEAMS.items() if info.get('wyid') == int(tid)), "Ukendt") for tid in df_agg['TEAM_WYID']],
        hovertemplate="<b>%{hovertext}</b><br>Snit (Runde 1-22): %{x:.2f}<extra></extra>"
    ))

    fig.update_layout(
        height=250, margin=dict(t=40, b=40, l=10, r=10),
        xaxis=dict(showgrid=True, gridcolor="#eee", title=f"Gennemsnitlig {label} (Grundspil)"),
        yaxis=dict(showticklabels=False, showgrid=False, range=[0, 1]),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig, use_container_width=True)

# --- 3. HOVEDFUNKTION ---

def vis_side():
    st.title("Hvidovre IF - Grundspils Performance")
    
    df_perf = get_hvidovre_performance()
    
    if df_perf is None or df_perf.empty:
        st.error("Kunne ikke hente data. Tjek din SQL-forbindelse.")
        return

    # Tabs til at skifte visning
    t1, t2 = st.tabs(["Logo Positioner (1-22)", "Runde-for-runde"])

    with t1:
        st.info("Placering af alle hold baseret på gennemsnit i de første 22 runder.")
        metric_choice = st.selectbox("Vælg Metric", ["XG", "GOALS", "SHOTS"])
        draw_gameweek_performance_chart(df_perf, metric_choice, metric_choice)

    with t2:
        # Linjediagram for Hvidovre specifikt gennem runderne
        hif_df = df_perf[df_perf['TEAM_WYID'] == 7490].copy()
        
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(
            x=hif_df['GAMEWEEK'], y=hif_df['XG'],
            mode='lines+markers',
            name='xG',
            line=dict(color='#df003b', width=3)
        ))
        
        fig_line.update_layout(
            title="Hvidovre xG udvikling (Runde 1-22)",
            xaxis=dict(title="Gameweek", tickmode='linear', range=[1, 22]),
            yaxis=dict(title="xG Værdi"),
            plot_bgcolor='white'
        )
        st.plotly_chart(fig_line, use_container_width=True)

if __name__ == "__main__":
    vis_side()
