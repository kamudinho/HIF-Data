import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def vis_hold_fysisk(df_summary, df_splits, team_id):
    st.title("🏃 Holdets Fysiske Præstation")

    # 1. Aggregering på holdniveau (fra SUMMARY_PLAYERS)
    # Vi antager her, at vi har linket spillerne til deres hold via metadata
    match_totals = df_summary.groupby('MATCH_SSIID').agg({
        'DISTANCE': 'sum',
        'HIGH SPEED RUNNING': 'sum',
        'SPRINTING': 'sum',
        'NO_OF_HIGH_INTENSITY_RUNS': 'sum'
    }).reset_index()

    # Beregn liga-gennemsnit for kontekst
    liga_avg_dist = match_totals['DISTANCE'].mean()
    liga_avg_hsr = match_totals['HIGH SPEED RUNNING'].mean()

    # KPI Række
    c1, c2, c3, c4 = st.columns(4)
    latest_match = match_totals.iloc[-1]
    
    c1.metric("Total Distance", f"{latest_match['DISTANCE']/1000:.1f} km", 
              delta=f"{(latest_match['DISTANCE'] - liga_avg_dist)/1000:.1f} km vs Liga")
    c2.metric("HSR (20-25 km/t)", f"{latest_match['HIGH SPEED RUNNING']:.0f} m")
    c3.metric("Sprint (>25 km/t)", f"{latest_match['SPRINTING']:.0f} m")
    c4.metric("HI Aktiviteter", f"{latest_match['NO_OF_HIGH_INTENSITY_RUNS']:.0f}")

    st.divider()

    # 2. Udvikling over tid (Trend)
    st.subheader("Fysisk output over sæsonen")
    fig_trend = px.line(match_totals, x='MATCH_SSIID', y=['HIGH SPEED RUNNING', 'SPRINTING'],
                        title="High Intensity Trend", markers=True,
                        color_discrete_map={"HIGH SPEED RUNNING": "#df003b", "SPRINTING": "black"})
    st.plotly_chart(fig_trend, use_container_width=True)

    # 3. Periode-analyse (Hvor i kampen er vi bedst?)
    # Bruger PHYSICAL_SPLITS_PLAYERS (MINUTE_SPLIT)
    st.subheader("Præstation per 15-minutters interval")
    
    # Vi samler data i 15-min blokke (0-15, 15-30 osv)
    df_splits['INTERVAL'] = (df_splits['MINUTE_SPLIT'] // 15) * 15
    period_data = df_splits.groupby('INTERVAL')['PHYSICAL_METRIC_VALUE'].sum().reset_index()
    
    fig_period = px.bar(period_data, x='INTERVAL', y='PHYSICAL_METRIC_VALUE',
                        labels={'INTERVAL': 'Minut-interval', 'PHYSICAL_METRIC_VALUE': 'Værdi'},
                        title="Fysisk intensitet gennem kampens faser")
    st.plotly_chart(fig_period, use_container_width=True)

    # 4. Spiller-bidrag (Hvem trækker læsset?)
    st.subheader("Top-performere i seneste kamp")
    top_players = df_summary[df_summary['MATCH_SSIID'] == latest_match['MATCH_SSIID']].sort_values('DISTANCE', ascending=False)
    
    fig_players = px.bar(top_players.head(10), x='PLAYER_NAME', y=['RUNNING', 'HIGH SPEED RUNNING', 'SPRINTING'],
                         title="Distance fordelt på intensitetszoner", barmode='stack')
    st.plotly_chart(fig_players, use_container_width=True)
