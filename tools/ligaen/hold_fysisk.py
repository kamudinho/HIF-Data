import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data.data_load import _get_snowflake_conn

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
SEASON_START = "2025-07-01"
LIGA_OPTA_ID = "148"  # 1. Division / NordicBet Liga

@st.cache_resource
def get_cached_conn():
    return _get_snowflake_conn()

def vis_side():
    st.set_page_config(page_title="Hvidovre IF - Liga Benchmark", layout="wide")
    
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 24px !important; font-weight: bold !important; }
        </style>
    """, unsafe_allow_html=True)

    conn = get_cached_conn()
    
    # 1. SQL: Henter fysiske data og joiner på 1. division via OptaID 148
    sql = f"""
        SELECT 
            P.MATCH_TEAMS,
            P.DISTANCE,
            P."HIGH SPEED RUNNING" as HSR,
            P.NO_OF_HIGH_INTENSITY_RUNS as HI_RUNS,
            P.TOP_SPEED
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS P
        JOIN {DB}.SECONDSPECTRUM_SEASON_METADATA M ON P.MATCH_SSIID = M.MATCH_SSIID
        WHERE M.COMPETITION_OPTAID = '{LIGA_OPTA_ID}'
          AND M.DATE >= '{SEASON_START}'
    """
    
    df_raw = conn.query(sql)

    if df_raw is None or df_raw.empty:
        st.error(f"Ingen data fundet for turnering ID {LIGA_OPTA_ID} (1. Division).")
        return

    # Sørg for ensartede kolonnenavne
    df_raw.columns = [c.upper() for c in df_raw.columns]

    # RENSNING: Samler holdnavne (f.eks. "HVI-KIF" -> "HVI")
    df_raw['HOLDNAVN'] = df_raw['MATCH_TEAMS'].apply(
        lambda x: str(x).split('-')[0].split(':')[0].strip()
    )
    
    # AGGREGERING: Sæson-gennemsnit pr. hold
    df_liga = df_raw.groupby('HOLDNAVN').agg({
        'DISTANCE': 'mean',
        'HSR': 'mean',
        'HI_RUNS': 'mean',
        'TOP_SPEED': 'mean'
    }).reset_index()

    # --- DROPDOWNS PLACERET PÅ SIDEN ---
    st.title("Fysisk Ligabenchmark: 1. Division")
    
    c1, c2 = st.columns(2)
    with c1:
        valgt_hold = st.selectbox("Vælg dit hold", sorted(df_liga['HOLDNAVN'].unique()))
    
    with c2:
        metric_map = {
            "HI Løb (Antal)": "HI_RUNS",
            "High Speed Running (m)": "HSR",
            "Total Distance (m)": "DISTANCE"
        }
        valgt_metric_label = st.selectbox("Vælg parameter på X-aksen", list(metric_map.keys()))
        valgt_x_col = metric_map[valgt_metric_label]

    st.divider()

    # --- DISPLAY METRICS ---
    hold_data = df_liga[df_liga['HOLDNAVN'] == valgt_hold].iloc[0]
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Gns. Distance", f"{round(hold_data['DISTANCE']/1000, 1)} km")
    m2.metric("Gns. HSR", f"{int(hold_data['HSR'])} m")
    m3.metric("Gns. HI løb", f"{int(hold_data['HI_RUNS'])}")
    m4.metric("Gns. Topfart", f"{round(hold_data['TOP_SPEED'], 1)} km/t")

    st.divider()

    # --- SCATTER PLOT LOGIK (INGEN DOBBELT-PRIK) ---
    st.subheader(f"Analyse: {valgt_metric_label} vs. Topfart")

    # Split i to grupper for at undgå overlap
    df_others = df_liga[df_liga['HOLDNAVN'] != valgt_hold]
    df_highlight = df_liga[df_liga['HOLDNAVN'] == valgt_hold]

    # 1. Placer de "grå" hold
    fig = px.scatter(
        df_others, 
        x=valgt_x_col, 
        y='TOP_SPEED',
        text='HOLDNAVN',
        labels={
            valgt_x_col: valgt_metric_label,
            'TOP_SPEED': 'Topfart (km/t)'
        }
    )

    fig.update_traces(
        marker=dict(size=14, opacity=0.4, color='grey'),
        textposition='top center'
    )

    # 2. Placer det valgte hold som et rødt lag ovenpå
    fig.add_trace(go.Scatter(
        x=df_highlight[valgt_x_col],
        y=df_highlight['TOP_SPEED'],
        mode='markers+text',
        marker=dict(size=22, color='#cc0000', line=dict(width=2, color='white')),
        text=df_highlight['HOLDNAVN'],
        textposition="top center",
        showlegend=False
    ))

    # 3. Liga gennemsnit (linjer)
    liga_avg_x = df_liga[valgt_x_col].mean()
    liga_avg_y = df_liga['TOP_SPEED'].mean()

    fig.add_vline(x=liga_avg_x, line_dash="dash", line_color="grey", opacity=0.6)
    fig.add_hline(y=liga_avg_y, line_dash="dash", line_color="grey", opacity=0.6)

    fig.update_layout(
        height=650,
        template="plotly_white",
        xaxis=dict(showgrid=True, gridcolor='#f0f0f0'),
        yaxis=dict(showgrid=True, gridcolor='#f0f0f0')
    )

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    vis_side()
