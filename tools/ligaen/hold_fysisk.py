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
    
    # 1. SQL: Henter data og joiner på 1. division via OptaID 148
    # Vi udelader AVG_HI kolonnen i SQL og beregner den i Pandas for at undgå fejl
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
        st.error(f"Ingen data fundet for turnering ID {LIGA_OPTA_ID}.")
        return

    # Sørg for ensartede kolonnenavne (UPPERCASE)
    df_raw.columns = [c.upper() for c in df_raw.columns]

    # RENSNING: Splitter "HVI-KIF" eller "HEL - FRA" til rent holdnavn
    df_raw['HOLDNAVN'] = df_raw['MATCH_TEAMS'].apply(
        lambda x: str(x).split('-')[0].split(':')[0].strip()
    )
    
    # AGGREGERING: Ét punkt pr. hold (sæson-gennemsnit)
    df_liga = df_raw.groupby('HOLDNAVN').agg({
        'DISTANCE': 'mean',
        'HSR': 'mean',
        'HI_RUNS': 'mean',
        'TOP_SPEED': 'mean'
    }).reset_index()

    # Navngivning til selector
    metric_map = {
        "HI Løb (Antal)": "HI_RUNS",
        "High Speed Running (m)": "HSR",
        "Total Distance (m)": "DISTANCE"
    }

    # --- SIDEBAR / KONTROL ---
    st.sidebar.header("Indstillinger")
    valgt_hold = st.sidebar.selectbox("Vælg dit hold", sorted(df_liga['HOLDNAVN'].unique()))
    valgt_metric_label = st.sidebar.selectbox("Vælg X-akse metric", list(metric_map.keys()))
    valgt_x_col = metric_map[valgt_metric_label]

    # --- DISPLAY METRICS ---
    hold_data = df_liga[df_liga['HOLDNAVN'] == valgt_hold].iloc[0]
    
    st.title(f"Fysisk Profil: {valgt_hold}")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Gns. Distance", f"{round(hold_data['DISTANCE']/1000, 1)} km")
    m2.metric("Gns. HSR", f"{int(hold_data['HSR'])} m")
    m3.metric("Gns. HI løb", f"{int(hold_data['HI_RUNS'])}")
    m4.metric("Gns. Topfart", f"{round(hold_data['TOP_SPEED'], 1)} km/t")

    st.divider()

    # --- SCATTER PLOT LOGIK (Undgå dobbeltvisning) ---
    st.subheader(f"Benchmark: {valgt_metric_label} vs. Topfart")

    # Split datasæt: Andre hold vs. Valgt hold
    df_others = df_liga[df_liga['HOLDNAVN'] != valgt_hold]
    df_highlight = df_liga[df_liga['HOLDNAVN'] == valgt_hold]

    # 1. Tegn de andre hold (grå)
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
        marker=dict(size=12, opacity=0.4, color='grey'),
        textposition='top center'
    )

    # 2. Tilføj det valgte hold som et rødt lag (ingen dobbelt-prik)
    fig.add_trace(go.Scatter(
        x=df_highlight[valgt_x_col],
        y=df_highlight['TOP_SPEED'],
        mode='markers+text',
        marker=dict(size=20, color='#cc0000', line=dict(width=2, color='white')),
        text=df_highlight['HOLDNAVN'],
        textposition="top center",
        showlegend=False
    ))

    # 3. Gennemsnitslinjer for hele ligaen
    liga_avg_x = df_liga[valgt_x_col].mean()
    liga_avg_y = df_liga['TOP_SPEED'].mean()

    fig.add_vline(x=liga_avg_x, line_dash="dash", line_color="grey", opacity=0.5)
    fig.add_hline(y=liga_avg_y, line_dash="dash", line_color="grey", opacity=0.5)

    fig.update_layout(
        height=600,
        template="plotly_white",
        xaxis=dict(showgrid=True, gridcolor='#f0f0f0'),
        yaxis=dict(showgrid=True, gridcolor='#f0f0f0')
    )

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    vis_side()
