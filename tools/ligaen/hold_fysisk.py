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

@st.cache_resource
def get_cached_conn():
    return _get_snowflake_conn()

def vis_side():
    st.markdown("""<style>
        [data-testid="stMetricValue"] { font-size: 26px !important; font-weight: bold !important; color: #333; }
    </style>""", unsafe_allow_html=True)

    conn = get_cached_conn()
    
    # 1. SQL: AGGREGERING TIL HOLDNIVEAU (Fjerner kamp-niveauet)
    # Her beregner vi gennemsnittet for alle kampe i sæsonen pr. hold
    sql_liga = f"""
        SELECT 
            MATCH_TEAMS as HOLDNAVN,
            AVG(TOTAL_HI) as AVG_HI,
            AVG(PEAK_SPEED) as AVG_PEAK_SPEED,
            AVG(TOTAL_DIST) as AVG_DIST,
            AVG(TOTAL_HSR) as AVG_HSR
        FROM (
            SELECT 
                MATCH_SSIID,
                MATCH_TEAMS,
                SUM(NO_OF_HIGH_INTENSITY_RUNS) as TOTAL_HI,
                MAX(TOP_SPEED) as PEAK_SPEED,
                SUM(DISTANCE) as TOTAL_DIST,
                SUM("HIGH SPEED RUNNING") as TOTAL_HSR
            FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
            WHERE MATCH_DATE >= '{SEASON_START}'
            GROUP BY 1, 2
        )
        GROUP BY 1
    """
    df_liga = conn.query(sql_liga)

    if df_liga is None or df_liga.empty:
        st.error("Kunne ikke hente data.")
        return

    # 2. VALG AF HOLD
    valgt_hold = st.selectbox("Vælg Hold", df_liga['HOLDNAVN'].unique())
    hold_stats = df_liga[df_liga['HOLDNAVN'] == valgt_hold].iloc[0]
    liga_snit = df_liga.mean(numeric_only=True)

    # 3. METRIKKER (Sæson-gennemsnit)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Gns. Distance", f"{round(hold_stats['AVG_DIST']/1000, 1)} km")
    m2.metric("Gns. HSR", f"{int(hold_stats['AVG_HSR'])} m")
    m3.metric("Gns. HI Aktiviteter", f"{int(hold_stats['AVG_HI'])}")
    m4.metric("Gns. Topfart", f"{round(hold_stats['AVG_PEAK_SPEED'], 1)} km/t")

    st.divider()

    # 4. SCATTER PLOT (Kun én prik per hold)
    st.subheader("Holdets placering i ligaen (Sæson-gennemsnit)")
    
    fig = px.scatter(
        df_liga, 
        x='AVG_HI', 
        y='AVG_PEAK_SPEED',
        text='HOLDNAVN',
        labels={
            'AVG_HI': 'HI Aktiviteter (Gns. per kamp)',
            'AVG_PEAK_SPEED': 'Peak Sprint Velocity (km/t)'
        }
    )

    # Farv alle hold grå og det valgte hold rødt
    fig.update_traces(
        marker=dict(size=12, opacity=0.4, color='grey'),
        textposition='top center'
    )

    # Highlight det valgte hold
    highlight = df_liga[df_liga['HOLDNAVN'] == valgt_hold]
    fig.add_trace(go.Scatter(
        x=highlight['AVG_HI'],
        y=highlight['AVG_PEAK_SPEED'],
        mode='markers+text',
        marker=dict(size=20, color='#cc0000', line=dict(width=2, color='white')),
        text=[valgt_hold],
        textposition="top center",
        showlegend=False
    ))

    # Liga gennemsnitslinjer
    fig.add_vline(x=liga_snit['AVG_HI'], line_dash="dash", line_color="grey")
    fig.add_hline(y=liga_snit['AVG_PEAK_SPEED'], line_dash="dash", line_color="grey")

    fig.update_layout(height=600, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    vis_side()
