import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from data.data_load import _get_snowflake_conn

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
    
    # SQL: Vi henter data. Snowflake vil typisk returnere disse som store bogstaver.
    sql_liga = f"""
        SELECT 
            MATCH_TEAMS,
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
        st.error("Kunne ikke hente data fra databasen.")
        return

    # --- VIGTIGT: Tving alle kolonnenavne til STORE bogstaver for at undgå 'unhashable' eller 'KeyError' ---
    df_liga.columns = [c.upper() for c in df_liga.columns]
    
    # Rens holdnavne
    df_liga['MATCH_TEAMS'] = df_liga['MATCH_TEAMS'].str.strip()

    # 1. VALG AF HOLD (Nu bruger vi store bogstaver i referencerne)
    alle_hold = sorted(df_liga['MATCH_TEAMS'].unique())
    valgt_hold = st.selectbox("Vælg Hold", alle_hold)
    
    # Filtrer data for det valgte hold
    hold_stats = df_liga[df_liga['MATCH_TEAMS'] == valgt_hold].iloc[0]
    liga_snit = df_liga.mean(numeric_only=True)

    # 2. METRIKKER (Sæson-gennemsnit)
    m1, m2, m3, m4 = st.columns(4)
    # Vi bruger de store bogstaver her:
    m1.metric("Gns. Distance", f"{round(hold_stats['AVG_DIST']/1000, 1)} km")
    m2.metric("Gns. HSR", f"{int(hold_stats['AVG_HSR'])} m")
    m3.metric("Gns. HI Aktiviteter", f"{int(hold_stats['AVG_HI'])}")
    m4.metric("Gns. Topfart", f"{round(hold_stats['AVG_PEAK_SPEED'], 1)} km/t")

    st.divider()

    # 3. SCATTER PLOT (Kun én prik pr. hold)
    st.subheader("Holdets placering i ligaen (Sæson-gennemsnit)")
    
    fig = px.scatter(
        df_liga, 
        x='AVG_HI', 
        y='AVG_PEAK_SPEED',
        text='MATCH_TEAMS',
        labels={
            'AVG_HI': 'HI Aktiviteter (Gns. per kamp)',
            'AVG_PEAK_SPEED': 'Peak Sprint Velocity (km/t)'
        }
    )

    # Styling for alle prikker
    fig.update_traces(
        marker=dict(size=12, opacity=0.4, color='grey'),
        textposition='top center'
    )

    # Fremhæv det valgte hold med en rød prik
    highlight = df_liga[df_liga['MATCH_TEAMS'] == valgt_hold]
    fig.add_trace(go.Scatter(
        x=highlight['AVG_HI'],
        y=highlight['AVG_PEAK_SPEED'],
        mode='markers+text',
        marker=dict(size=22, color='#df003b', line=dict(width=2, color='white')),
        text=[valgt_hold],
        textposition="top center",
        showlegend=False
    ))

    # Gennemsnitslinjer for ligaen
    fig.add_vline(x=liga_snit['AVG_HI'], line_dash="dash", line_color="grey")
    fig.add_hline(y=liga_snit['AVG_PEAK_SPEED'], line_dash="dash", line_color="grey")

    fig.update_layout(
        height=600, 
        template="plotly_white",
        xaxis=dict(showgrid=True, gridcolor='f0f0f0'),
        yaxis=dict(showgrid=True, gridcolor='f0f0f0')
    )
    
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    vis_side()
