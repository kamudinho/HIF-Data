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
    st.set_page_config(page_title="Hvidovre IF - Fysisk Analyse", layout="wide")
    
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 24px !important; font-weight: bold !important; }
        </style>
    """, unsafe_allow_html=True)

    conn = get_cached_conn()
    
    # 1. SQL: Henter data
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
        st.error(f"Ingen data fundet for 1. Division (ID {LIGA_OPTA_ID}).")
        return

    df_raw.columns = [c.upper() for c in df_raw.columns]

    # RENSNING: Samler holdnavne
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

    # --- DROPDOWNS ØVERST PÅ SIDEN ---
    st.title("Fysisk Analyse: Distance vs. Intensitet")
    
    c1, c2 = st.columns(2)
    with c1:
        valgt_hold = st.selectbox("Vælg dit hold", sorted(df_liga['HOLDNAVN'].unique()))
    
    with c2:
        metric_map = {
            "HI Løb (Antal)": "HI_RUNS",
            "High Speed Running (m)": "HSR",
            "Topfart (km/t)": "TOP_SPEED"
        }
        valgt_metric_label = st.selectbox("Vælg intensitet (Y-akse)", list(metric_map.keys()))
        valgt_y_col = metric_map[valgt_metric_label]

    st.divider()

    # --- DISPLAY METRICS ---
    hold_data = df_liga[df_liga['HOLDNAVN'] == valgt_hold].iloc[0]
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Gns. Distance", f"{round(hold_data['DISTANCE']/1000, 2)} km")
    m2.metric("Gns. HI løb", f"{int(hold_data['HI_RUNS'])}")
    m3.metric("Gns. HSR", f"{int(hold_data['HSR'])} m")
    m4.metric("Gns. Topfart", f"{round(hold_data['TOP_SPEED'], 1)} km/t")

    st.divider()

    # --- SCATTER PLOT: DISTANCE PÅ X, VALGT METRIC PÅ Y ---
    st.subheader(f"Analyse: Total Distance vs. {valgt_metric_label}")

    # Split i to grupper for at undgå overlap (KIF vises kun én gang som rød)
    df_others = df_liga[df_liga['HOLDNAVN'] != valgt_hold]
    df_highlight = df_liga[df_liga['HOLDNAVN'] == valgt_hold]

    # 1. Tegn ligaen (grå prikker)
    fig = px.scatter(
        df_others, 
        x='DISTANCE', 
        y=valgt_y_col,
        text='HOLDNAVN',
        labels={
            'DISTANCE': 'Total Distance (Meter)',
            valgt_y_col: valgt_metric_label
        }
    )

    fig.update_traces(
        marker=dict(size=14, opacity=0.4, color='grey'),
        textposition='top center'
    )

    # 2. Tegn det valgte hold (rød prik)
    fig.add_trace(go.Scatter(
        x=df_highlight['DISTANCE'],
        y=df_highlight[valgt_y_col],
        mode='markers+text',
        marker=dict(size=22, color='#cc0000', line=dict(width=2, color='white')),
        text=df_highlight['HOLDNAVN'],
        textposition="top center",
        showlegend=False
    ))

    # 3. Liga gennemsnitslinjer
    avg_dist = df_liga['DISTANCE'].mean()
    avg_y = df_liga[valgt_y_col].mean()

    fig.add_vline(x=avg_dist, line_dash="dash", line_color="grey", opacity=0.6)
    fig.add_hline(y=avg_y, line_dash="dash", line_color="grey", opacity=0.6)

    fig.update_layout(
        height=650,
        template="plotly_white",
        xaxis=dict(showgrid=True, gridcolor='#f0f0f0', title="Total Distance (Meter)"),
        yaxis=dict(showgrid=True, gridcolor='#f0f0f0')
    )

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    vis_side()
