import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data.data_load import _get_snowflake_conn

# --- KONFIGURATION FRA DINE GEMTE VÆRDIER ---
DB = "KLUB_HVIDOVREIF.AXIS"
SEASON_START = "2025-07-01"
COMP_ID = "328" # NordicBet Liga / 1. Division

@st.cache_resource
def get_cached_conn():
    return _get_snowflake_conn()

def vis_side():
    st.markdown("""<style>
        [data-testid="stMetricValue"] { font-size: 26px !important; font-weight: bold !important; color: #333; }
    </style>""", unsafe_allow_html=True)

    conn = get_cached_conn()
    
    # SQL: Vi kobler fysisk data med sæson-metadata for at filtrere på 1. division
    # Vi bruger 'HOME_SSIID' og 'MATCH_TEAMS' logik til at sikre hold-identifikation
    sql_liga = f"""
        SELECT 
            P.MATCH_TEAMS AS "FULL_NAME",
            AVG(P.DISTANCE) AS "AVG_DIST",
            AVG(P."HIGH SPEED RUNNING") AS "AVG_HSR",
            AVG(P.TOP_SPEED) AS "AVG_PEAK_SPEED"
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS P
        JOIN {DB}.SECONDSPECTRUM_SEASON_METADATA M ON P.MATCH_SSIID = M.MATCH_SSIID
        WHERE M.SECOND_SPECTRUM_COMPETITION_ID = '{COMP_ID}'
          AND M.DATE >= '{SEASON_START}'
        GROUP BY 1
    """
    
    df_raw = conn.query(sql_liga)

    if df_raw is None or df_raw.empty:
        st.error(f"Ingen data fundet for turnering ID {COMP_ID} i denne sæson.")
        return

    # RENSNING: Vi splitter "HIK-HVI" til kun at være det første hold for at samle statistikken
    df_raw['HOLDNAVN'] = df_raw['FULL_NAME'].apply(lambda x: str(x).split('-')[0].strip())
    
    # Grupper i Pandas for at få ét rent gennemsnit pr. hold
    df_liga = df_raw.groupby('HOLDNAVN').agg({
        'AVG_DIST': 'mean',
        'AVG_HSR': 'mean',
        'AVG_PEAK_SPEED': 'mean'
    }).reset_index()

    # 1. VALG AF HOLD
    alle_hold = sorted(df_liga['HOLDNAVN'].unique())
    valgt_hold = st.selectbox("Vælg Hold (1. Division)", alle_hold)
    
    hold_stats = df_liga[df_liga['HOLDNAVN'] == valgt_hold].iloc[0]
    liga_snit = df_liga.mean(numeric_only=True)

    # 2. METRIKKER (Uden HI løb)
    m1, m2, m3 = st.columns(3)
    m1.metric("Gns. Distance", f"{round(hold_stats['AVG_DIST']/1000, 1)} km")
    m2.metric("Gns. HSR", f"{int(hold_stats['AVG_HSR'])} m")
    m3.metric("Gns. Topfart", f"{round(hold_stats['AVG_PEAK_SPEED'], 1)} km/t")

    st.divider()

    # 3. SCATTER PLOT (HSR vs Topfart)
    st.subheader("Fysisk Power-index: 1. Division")
    
    fig = px.scatter(
        df_liga, 
        x='AVG_HSR', 
        y='AVG_PEAK_SPEED',
        text='HOLDNAVN',
        labels={
            'AVG_HSR': 'High Speed Running (Gns. meter pr. kamp)',
            'AVG_PEAK_SPEED': 'Topfart (Gns. km/t)'
        }
    )

    # Style liga-punkter
    fig.update_traces(
        marker=dict(size=14, opacity=0.4, color='grey'),
        textposition='top center'
    )

    # Highlight det valgte hold
    highlight = df_liga[df_liga['HOLDNAVN'] == valgt_hold]
    fig.add_trace(go.Scatter(
        x=highlight['AVG_HSR'],
        y=highlight['AVG_PEAK_SPEED'],
        mode='markers+text',
        marker=dict(size=22, color='#df003b', line=dict(width=2, color='white')),
        text=[valgt_hold],
        textposition="top center",
        showlegend=False
    ))

    # Gennemsnitslinjer
    fig.add_vline(x=liga_snit['AVG_HSR'], line_dash="dash", line_color="grey", opacity=0.5)
    fig.add_hline(y=liga_snit['AVG_PEAK_SPEED'], line_dash="dash", line_color="grey", opacity=0.5)

    fig.update_layout(
        height=600, 
        template="plotly_white",
        xaxis=dict(showgrid=True, gridcolor='#f0f0f0'),
        yaxis=dict(showgrid=True, gridcolor='#f0f0f0')
    )
    
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    vis_side()
