import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data.data_load import _get_snowflake_conn

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
SEASON_START = "2025-07-01"
# Dine Opta UUIDs for 1. division (NordicBet Liga)
LIGA_UUIDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7')"

@st.cache_resource
def get_cached_conn():
    return _get_snowflake_conn()

def vis_side():
    st.markdown("""<style>
        [data-testid="stMetricValue"] { font-size: 26px !important; font-weight: bold !important; color: #333; }
    </style>""", unsafe_allow_html=True)

    conn = get_cached_conn()
    
    # SQL: Vi henter de rå kampsummeringer og joiner på metadata for at ramme turneringen
    # Vi omdøber kolonnerne direkte i SQL for at undgå navne-fejl
    sql = f"""
        SELECT 
            P.MATCH_TEAMS,
            P.DISTANCE,
            P."HIGH SPEED RUNNING" as HSR,
            P.NO_OF_HIGH_INTENSITY_RUNS as HI_RUNS,
            P.TOP_SPEED
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS P
        JOIN {DB}.SECONDSPECTRUM_SEASON_METADATA M ON P.MATCH_SSIID = M.MATCH_SSIID
        WHERE M.COMPETITION_OPTAUUID IN {LIGA_UUIDS}
          AND M.DATE >= '{SEASON_START}'
    """
    
    df_raw = conn.query(sql)

    if df_raw is None or df_raw.empty:
        st.error("Kunne ikke hente data for den valgte turnering.")
        return

    # Tving store bogstaver for konsistens
    df_raw.columns = [c.upper() for c in df_raw.columns]

    # RENSNING: Split "HVI-ACH" til "HVI"
    df_raw['HOLDNAVN'] = df_raw['MATCH_TEAMS'].apply(lambda x: str(x).split('-')[0].strip())
    
    # AGGREGERING: Vi samler alle rækker pr. hold og beregner gennemsnittet
    # Dette sikrer at vi får ÉN prik pr. hold
    df_liga = df_raw.groupby('HOLDNAVN').agg({
        'DISTANCE': 'mean',
        'HSR': 'mean',
        'HI_RUNS': 'mean',
        'TOP_SPEED': 'mean'
    }).reset_index()

    # Omdøb for at matche dine plots (og undgå 'AVG_HI' KeyError)
    df_liga.rename(columns={
        'DISTANCE': 'AVG_DIST',
        'HSR': 'AVG_HSR',
        'HI_RUNS': 'AVG_HI',
        'TOP_SPEED': 'AVG_PEAK_SPEED'
    }, inplace=True)

    # 1. VALG AF HOLD
    valgt_hold = st.selectbox("Vælg Hold", sorted(df_liga['HOLDNAVN'].unique()))
    
    hold_stats = df_liga[df_liga['HOLDNAVN'] == valgt_hold].iloc[0]
    liga_snit = df_liga.mean(numeric_only=True)

    # 2. TOP METRIKKER
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Gns. Distance", f"{round(hold_stats['AVG_DIST']/1000, 1)} km")
    m2.metric("Gns. HSR", f"{int(hold_stats['AVG_HSR'])} m")
    m3.metric("Gns. HI løb", f"{int(hold_stats['AVG_HI'])}")
    m4.metric("Gns. Topfart", f"{round(hold_stats['AVG_PEAK_SPEED'], 1)} km/t")

    st.divider()

    # 3. SCATTER PLOT
    st.subheader("Hold-benchmark (Sæson-gennemsnit)")
    
    fig = px.scatter(
        df_liga, 
        x='AVG_HI', 
        y='AVG_PEAK_SPEED',
        text='HOLDNAVN',
        labels={'AVG_HI': 'HI Aktiviteter (Gns. pr. kamp)', 'AVG_PEAK_SPEED': 'Topfart (km/t)'}
    )

    fig.update_traces(marker=dict(size=14, opacity=0.4, color='grey'), textposition='top center')

    # Fremhæv det valgte hold
    highlight = df_liga[df_liga['HOLDNAVN'] == valgt_hold]
    fig.add_trace(go.Scatter(
        x=highlight['AVG_HI'], y=highlight['AVG_PEAK_SPEED'],
        mode='markers+text',
        marker=dict(size=22, color='#cc0000', line=dict(width=2, color='white')),
        text=[valgt_hold], textposition="top center", showlegend=False
    ))

    # Gennemsnitslinjer
    fig.add_vline(x=liga_snit['AVG_HI'], line_dash="dash", line_color="grey", opacity=0.5)
    fig.add_hline(y=liga_snit['AVG_PEAK_SPEED'], line_dash="dash", line_color="grey", opacity=0.5)

    fig.update_layout(height=600, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    vis_side()
