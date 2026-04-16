import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
SEASON_START = "2025-07-01"
LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '328', '329', '43319', '331', '1305')"

@st.cache_resource
def get_cached_conn():
    return _get_snowflake_conn()

def vis_side():
    st.markdown("""<style>
        [data-testid="stMetricValue"] { font-size: 26px !important; font-weight: bold !important; color: #333; }
    </style>""", unsafe_allow_html=True)

    conn = get_cached_conn()
    
    # 1. HENT ALLE HOLD-STATS FOR SÆSONEN (Aggregeret på holdniveau)
    sql_all_teams = f"""
        SELECT 
            MATCH_TEAMS,
            AVG(HOLD_DIST) as AVG_DIST,
            AVG(HOLD_HSR) as AVG_HSR,
            AVG(HOLD_SPRINT) as AVG_SPRINT,
            MAX(TOP_SPEED_KAMP) as PEAK_SPEED,
            AVG(HOLD_HSR_TIP) as AVG_HSR_TIP,
            AVG(HOLD_HSR_OTIP) as AVG_HSR_OTIP
        FROM (
            SELECT 
                MATCH_SSIID,
                MATCH_TEAMS,
                SUM(DISTANCE) as HOLD_DIST,
                SUM("HIGH SPEED RUNNING") as HOLD_HSR,
                SUM(SPRINTING) as HOLD_SPRINT,
                SUM(NO_OF_HIGH_INTENSITY_RUNS) as HOLD_HI,
                MAX(TOP_SPEED) as TOP_SPEED_KAMP,
                SUM(HSR_DISTANCE_TIP) as HOLD_HSR_TIP,
                SUM(HSR_DISTANCE_OTIP) as HOLD_HSR_OTIP
            FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
            WHERE MATCH_DATE >= '{SEASON_START}'
            GROUP BY 1, 2
        )
        GROUP BY 1
    """
    df_all_teams = conn.query(sql_all_teams)

    if df_all_teams is None or df_all_teams.empty:
        st.error("Kunne ikke hente hold-data fra Snowflake.")
        return

    # 2. VALG AF HOLD
    valgt_hold = st.selectbox("Vælg Hold", df_all_teams['MATCH_TEAMS'].unique())
    hold_data = df_all_teams[df_all_teams['MATCH_TEAMS'] == valgt_hold].iloc[0]
    liga_avg = df_all_teams.mean(numeric_only=True)

    # 3. OVERORDNEDE METRIKKER (Sæson-gennemsnit vs. Liga-snit)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Gns. Distance", f"{round(hold_data['AVG_DIST']/1000, 1)} km", 
              delta=f"{round((hold_data['AVG_DIST'] - liga_avg['AVG_DIST'])/1000, 1)} km")
    m2.metric("Gns. HSR", f"{int(hold_data['AVG_HSR'])} m", 
              delta=f"{int(hold_data['AVG_HSR'] - liga_avg['AVG_HSR'])} m")
    m3.metric("Gns. HI løb", f"{int(hold_data['AVG_HI'])}", 
              delta=f"{int(hold_data['AVG_HI'] - liga_avg['AVG_HI'])}")
    m4.metric("Peak Speed", f"{round(hold_data['PEAK_SPEED'], 1)} km/t")

    st.divider()

    # 4. LIGA BENCHMARK (SCATTER PLOT)
    st.subheader("Sæson-benchmark: Intensitet vs. Topfart")
    
    fig_scatter = px.scatter(
        df_all_teams, 
        x='AVG_HI', 
        y='PEAK_SPEED',
        text='MATCH_TEAMS',
        labels={
            'AVG_HI': 'HI Aktiviteter (Sæson-gennemsnit)',
            'PEAK_SPEED': 'Topfart registreret (km/t)'
        }
    )

    fig_scatter.update_traces(marker=dict(size=12, opacity=0.4, color='grey'), textposition='top center')

    # Fremhæv det valgte hold
    fig_scatter.add_trace(go.Scatter(
        x=[hold_data['AVG_HI']],
        y=[hold_data['PEAK_SPEED']],
        mode='markers+text',
        marker=dict(size=20, color='#cc0000', line=dict(width=2, color='white')),
        text=[valgt_hold],
        textposition="top center",
        showlegend=False
    ))

    # Gennemsnitslinjer for ligaen
    fig_scatter.add_vline(x=liga_avg['AVG_HI'], line_dash="dash", line_color="grey")
    fig_scatter.add_hline(y=liga_avg['PEAK_SPEED'], line_dash="dash", line_color="grey")

    fig_scatter.update_layout(height=550, template="plotly_white")
    st.plotly_chart(fig_scatter, use_container_width=True)

    st.divider()

    # 5. HOLDETS PROFIL (Fasefordeling og Udvikling)
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Holdets profil: Med vs. Uden bold")
        fig_pie = go.Figure(data=[go.Pie(
            labels=['Angreb (TIP)', 'Forsvar (OTIP)'],
            values=[hold_data['AVG_HSR_TIP'], hold_data['AVG_HSR_OTIP']],
            hole=.4,
            marker_colors=['#cc0000', '#333333']
        )])
        fig_pie.update_layout(height=400, margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_right:
        # Sæson-udvikling for det valgte hold
        df_trend = conn.query(f"""
            SELECT MATCH_DATE, SUM("HIGH SPEED RUNNING") as HSR
            FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
            WHERE MATCH_TEAMS = '{valgt_hold}'
              AND MATCH_DATE >= '{SEASON_START}'
            GROUP BY 1 ORDER BY 1 ASC
        """)
        
        if df_trend is not None and not df_trend.empty:
            st.subheader("Udvikling i intensitet over sæsonen")
            fig_trend = px.line(df_trend, x='MATCH_DATE', y='HSR', markers=True)
            fig_trend.update_traces(line_color='#cc0000')
            fig_trend.update_layout(height=400, xaxis_title="Dato", yaxis_title="Hold-HSR (meter)")
            st.plotly_chart(fig_trend, use_container_width=True)

if __name__ == "__main__":
    vis_side()
