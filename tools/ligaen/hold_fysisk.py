import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from data.data_load import _get_snowflake_conn

# Sikker import af SkillCorner-biblioteker
try:
    from skillcornerviz.standard_plots import radar_plot as rad
    SKILLCORNER_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    SKILLCORNER_AVAILABLE = False

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
SEASON_START = "2025-07-01"
LIGA_OPTA_ID = "148"  # 1. Division

@st.cache_resource
def get_cached_conn():
    return _get_snowflake_conn()

def vis_side():
    st.set_page_config(page_title="Hvidovre IF - Fysisk Benchmark", layout="wide")
    
    # CSS til at gøre metrics mere kompakte
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 18px !important; font-weight: bold !important; }
        </style>
    """, unsafe_allow_html=True)

    conn = get_cached_conn()
    
    # 1. SQL: Henter data inklusiv MINUTES til SkillCorner p90-beregning
    sql = f"""
        SELECT 
            P.MATCH_TEAMS,
            P.DISTANCE,
            P."HIGH SPEED RUNNING" as HSR,
            P.NO_OF_HIGH_INTENSITY_RUNS as HI_RUNS,
            P.TOP_SPEED,
            COALESCE(P.MINUTES, 90) as MINUTES
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS P
        JOIN {DB}.SECONDSPECTRUM_SEASON_METADATA M ON P.MATCH_SSIID = M.MATCH_SSIID
        WHERE M.COMPETITION_OPTAID = '{LIGA_OPTA_ID}'
          AND M.DATE >= '{SEASON_START}'
    """
    
    df_raw = conn.query(sql)

    if df_raw is None or df_raw.empty:
        st.error(f"Ingen data fundet for turnering ID {LIGA_OPTA_ID}.")
        return

    df_raw.columns = [c.upper() for c in df_raw.columns]

    # 2. DATABEHANDLING & NORMALISERING (SkillCorner Logic)
    df_raw['HOLDNAVN'] = df_raw['MATCH_TEAMS'].apply(
        lambda x: str(x).split('-')[0].split(':')[0].strip()
    )
    
    # Beregn per 90 minutter (p90)
    df_raw['DIST_P90'] = (df_raw['DISTANCE'] / df_raw['MINUTES']) * 90
    df_raw['HI_P90'] = (df_raw['HI_RUNS'] / df_raw['MINUTES']) * 90
    df_raw['HSR_P90'] = (df_raw['HSR'] / df_raw['MINUTES']) * 90
    
    # Gruppér til gennemsnit pr. hold
    df_liga = df_raw.groupby('HOLDNAVN').agg({
        'DIST_P90': 'mean',
        'HSR_P90': 'mean',
        'HI_P90': 'mean',
        'TOP_SPEED': 'mean'
    }).reset_index()

    # --- KONTROL PANEL ---
    st.title("Physical Performance Benchmark")
    st.caption("Data er normaliseret pr. 90 minutter (p90) jf. SkillCorner standarder")
    
    c1, c2 = st.columns(2)
    with c1:
        valgt_hold = st.selectbox("Vælg dit hold", sorted(df_liga['HOLDNAVN'].unique()))
    with c2:
        metric_map = {
            "HI Aktioner (p90)": "HI_P90",
            "High Speed Running (p90)": "HSR_P90",
            "Topfart (km/t)": "TOP_SPEED"
        }
        valgt_label = st.selectbox("Vælg intensitet (Y-akse)", list(metric_map.keys()))
        y_col = metric_map[valgt_label]

    # --- TOP METRICS ---
    hold_data = df_liga[df_liga['HOLDNAVN'] == valgt_hold].iloc[0]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Gns. Dist (p90)", f"{round(hold_data['DIST_P90']/1000, 2)} km")
    m2.metric("Gns. HI (p90)", f"{round(hold_data['HI_P90'], 1)}")
    m3.metric("Gns. HSR (p90)", f"{int(hold_data['HSR_P90'])} m")
    m4.metric("Topfart", f"{round(hold_data['TOP_SPEED'], 1)} km/t")

    st.divider()

    # --- LIGA SCATTER PLOT ---
    df_others = df_liga[df_liga['HOLDNAVN'] != valgt_hold]
    df_highlight = df_liga[df_liga['HOLDNAVN'] == valgt_hold]

    fig = px.scatter(
        df_others, x='DIST_P90', y=y_col, text='HOLDNAVN',
        labels={'DIST_P90': 'Total Distance pr. 90m', y_col: valgt_label}
    )
    fig.update_traces(marker=dict(size=14, opacity=0.4, color='grey'), textposition='top center')

    fig.add_trace(go.Scatter(
        x=df_highlight['DIST_P90'], y=df_highlight[y_col],
        mode='markers+text',
        marker=dict(size=22, color='#cc0000', line=dict(width=2, color='white')),
        text=df_highlight['HOLDNAVN'], textposition="top center", showlegend=False
    ))

    # Gennemsnitslinjer
    fig.add_vline(x=df_liga['DIST_P90'].mean(), line_dash="dash", line_color="grey", opacity=0.5)
    fig.add_hline(y=df_liga[y_col].mean(), line_dash="dash", line_color="grey", opacity=0.5)

    fig.update_layout(height=550, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

    # --- SKILLCORNER RADAR ---
    if SKILLCORNER_AVAILABLE:
        st.divider()
        st.subheader(f"Fysisk Profil | {valgt_hold}")
        
        # Beregn percentiler til radar
        radar_df = df_liga.copy()
        radar_metrics = {
            'HI_P90': 'High Intensity',
            'TOP_SPEED': 'Peak Speed',
            'HSR_P90': 'HSR',
            'DIST_P90': 'Volume'
        }
        for m in radar_metrics.keys():
            radar_df[m] = radar_df[m].rank(pct=True) * 100

        try:
            fig_radar, ax = rad.plot_radar(
                radar_df,
                data_point_id='HOLDNAVN',
                label=valgt_hold,
                metrics=list(radar_metrics.keys()),
                metric_labels=radar_metrics,
                plot_title=f"Benchmark Percentiler: {valgt_hold}",
                add_sample_info=False
            )
            # Fjern baggrundsfarven fra Matplotlib figuren for at matche Streamlit
            fig_radar.patch.set_facecolor('none')
            st.pyplot(fig_radar)
        except Exception as e:
            st.error(f"Fejl ved generering af radar: {e}")
    else:
        st.info("SkillCorner Radar er deaktiveret grundet manglende bibliotek.")

if __name__ == "__main__":
    vis_side()
