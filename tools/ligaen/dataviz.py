import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

# --- 1. DATA LOADING & TABEL-BEREGNING ---

@st.cache_data(ttl=3600)
def get_league_data():
    conn = _get_snowflake_conn()
    db = "KLUB_HVIDOVREIF.AXIS"
    
    # Hent både kampresultater (til tabel) og advanced stats (til performance)
    # Vi fokuserer på Grundspillet (Runde 1-22)
    query = f"""
        SELECT 
            tm.TEAM_WYID, tm.GAMEWEEK,
            m.MATCHLABEL,
            adv.XG, adv.GOALS, adv.SHOTS,
            -- Beregn point direkte i SQL eller i Pandas efterfølgende
            CASE 
                WHEN (tm.TEAM_WYID = m.WINNERID) THEN 3
                WHEN (m.WINNERID = 0) THEN 1
                ELSE 0
            END as POINTS,
            (adv.GOALS - adv.GOALSAGAINST) as GD
        FROM {db}.WYSCOUT_TEAMMATCHES tm
        JOIN {db}.WYSCOUT_MATCHES m ON tm.MATCH_WYID = m.MATCH_WYID
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv 
            ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID
        WHERE tm.COMPETITION_WYID = 328
          AND tm.GAMEWEEK <= 22
          AND m.SEASON_WYID = (SELECT SEASON_WYID FROM {db}.WYSCOUT_SEASONS WHERE SEASONNAME = '2025/2026' LIMIT 1)
    """
    df = conn.query(query)
    
    # 1. Beregn Tabellen (X-akse position)
    tabel = df.groupby('TEAM_WYID').agg({
        'POINTS': 'sum',
        'GD': 'sum',
        'XG': 'mean',
        'GOALS': 'mean',
        'SHOTS': 'mean'
    }).sort_values(['POINTS', 'GD'], ascending=False).reset_index()
    
    # Tilføj 'RANK' (1 til 12)
    tabel['RANK'] = tabel.index + 1
    
    return tabel

# --- 2. POSITION VIZ FUNKTION ---

def draw_rank_performance_plot(df, metric_col, label):
    """
    X-akse: Tabelplacering (1-12)
    Y-akse: Performance Metric
    """
    fig = go.Figure()

    # Tilføj logoer
    for i, row in df.iterrows():
        team_id = int(row['TEAM_WYID'])
        team_info = next((info for name, info in TEAMS.items() if info.get('wyid') == team_id), {})
        logo_url = team_info.get('logo', "")
        
        if logo_url:
            fig.add_layout_image(
                dict(
                    source=logo_url,
                    xref="x", yref="y",
                    x=row['RANK'], y=row[metric_col],
                    sizex=0.6, sizey=row[metric_col] * 0.1, # Skaleres efter y-værdi
                    xanchor="center", yanchor="middle"
                )
            )

    # Usynlige punkter for interaktivitet
    fig.add_trace(go.Scatter(
        x=df['RANK'],
        y=df[metric_col],
        mode='markers',
        marker=dict(size=25, opacity=0),
        hovertext=[next((name for name, info in TEAMS.items() if info.get('wyid') == int(tid)), "Ukendt") for tid in df['TEAM_WYID']],
        hovertemplate="<b>%{hovertext}</b><br>Placering: %{x}<br>Værdi: %{y:.2f}<extra></extra>"
    ))

    fig.update_layout(
        title=f"Tabelplacering vs. {label}",
        xaxis=dict(
            title="Tabelplacering (1 = Top)",
            tickmode='linear',
            range=[0.5, 12.5],
            autorange="reversed", # Valgfrit: Vend aksen så 1 er til højre, eller behold 1 til venstre
            gridcolor="#eee"
        ),
        yaxis=dict(title=label, gridcolor="#eee"),
        height=500,
        plot_bgcolor='white'
    )
    
    st.plotly_chart(fig, use_container_width=True)

# --- 3. EXECUTION ---

def vis_side():
    st.subheader("Performance vs. Tabelplacering (Runde 1-22)")
    
    df_liga = get_league_data()
    
    if df_liga.empty:
        st.error("Ingen data fundet.")
        return

    # Dropdown til Y-aksen
    metrics = {
        'Expected Goals (Avg)': 'XG',
        'Mål (Avg)': 'GOALS',
        'Skud (Avg)': 'SHOTS'
    }
    
    selected_label = st.selectbox("Vælg performance parameter (Y-akse)", list(metrics.keys()))
    selected_metric = metrics[selected_label]
    
    draw_rank_performance_plot(df_liga, selected_metric, selected_label)
    
    # Vis rå tabel underneden for reference
    with st.expander("Se Tabel-data"):
        st.dataframe(df_liga[['RANK', 'TEAM_WYID', 'POINTS', 'GD', 'XG']].rename(columns={'TEAM_WYID': 'ID'}))

if __name__ == "__main__":
    vis_side()
