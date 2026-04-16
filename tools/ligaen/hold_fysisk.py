import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from data.data_load import _get_snowflake_conn

# SkillCorner Viz imports
try:
    from skillcornerviz.standard_plots import bar_plot as bar
    from skillcornerviz.standard_plots import radar_plot as rad
    SKILLCORNER_AVAILABLE = True
except:
    SKILLCORNER_AVAILABLE = False

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
SEASON_START = "2025-07-01"
LIGA_OPTA_ID = "148"

@st.cache_resource
def get_cached_conn():
    return _get_snowflake_conn()

def vis_side():
    st.set_page_config(page_title="Hvidovre IF - Fysisk Analyse", layout="wide")
    conn = get_cached_conn()
    
    # 1. DATA INDLÆSNING (Hold-totaler pr. kamp)
    sql = f"""
        SELECT P.MATCH_SSIID, P.MATCH_TEAMS, P.DISTANCE, P."HIGH SPEED RUNNING" as HSR,
               P.NO_OF_HIGH_INTENSITY_RUNS as HI_RUNS, P.TOP_SPEED
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS P
        JOIN {DB}.SECONDSPECTRUM_SEASON_METADATA M ON P.MATCH_SSIID = M.MATCH_SSIID
        WHERE M.COMPETITION_OPTAID = '{LIGA_OPTA_ID}' AND M.DATE >= '{SEASON_START}'
    """
    df_raw = conn.query(sql)
    df_raw.columns = [c.upper() for c in df_raw.columns]
    df_raw['HOLDNAVN'] = df_raw['MATCH_TEAMS'].apply(lambda x: str(x).split('-')[0].split(':')[0].strip())

    # Aggregering: Kamp-totaler og derefter Sæson-gennemsnit
    df_kampe = df_raw.groupby(['MATCH_SSIID', 'HOLDNAVN']).agg({
        'DISTANCE': 'sum', 'HSR': 'sum', 'HI_RUNS': 'sum', 'TOP_SPEED': 'max'
    }).reset_index()

    df_liga = df_kampe.groupby('HOLDNAVN').agg({
        'DISTANCE': 'mean', 'HSR': 'mean', 'HI_RUNS': 'mean', 'TOP_SPEED': 'mean'
    }).reset_index()

    # --- UI KONTROLLER ---
    st.title("Fysisk Ligabenchmark")
    
    t1, t2, t3 = st.columns([2, 2, 2])
    with t1:
        valgt_hold = st.selectbox("Vælg dit hold", sorted(df_liga['HOLDNAVN'].unique()))
    with t2:
        valgt_metric = st.selectbox("Vælg Metric (Bar Chart)", ["HI_RUNS", "HSR", "DISTANCE", "TOP_SPEED"])
    with t3:
        visning = st.radio("Vælg graf-visning", ["Scatterplot", "SkillCorner Bar Chart", "SkillCorner Radar"], horizontal=True)

    st.divider()

    # --- VISNINGS LOGIK ---

    if visning == "Scatterplot":
        # Det interaktive plot du havde før
        fig = px.scatter(df_liga[df_liga['HOLDNAVN'] != valgt_hold], x='DISTANCE', y=valgt_metric, text='HOLDNAVN')
        fig.add_trace(go.Scatter(x=df_liga[df_liga['HOLDNAVN'] == valgt_hold]['DISTANCE'], 
                                 y=df_liga[df_liga['HOLDNAVN'] == valgt_hold][valgt_metric],
                                 mode='markers+text', marker=dict(size=20, color='red'), text=valgt_hold))
        st.plotly_chart(fig, use_container_width=True)

    elif visning == "SkillCorner Bar Chart" and SKILLCORNER_AVAILABLE:
        # SkillCorner Bar Chart (Top 10 hold)
        df_sorted = df_liga.sort_values(valgt_metric, ascending=False).head(10).copy()
        df_sorted['plot_id'] = range(len(df_sorted)) # ID til biblioteket
        
        fig, ax = bar.plot_bar_chart(
            df=df_sorted,
            metric=valgt_metric,
            label=f"Top 10: {valgt_metric}",
            unit="",
            primary_highlight_group=df_sorted[df_sorted['HOLDNAVN'] == valgt_hold]['plot_id'].tolist(),
            primary_highlight_color='#cc0000',
            data_point_id='plot_id',
            data_point_label='HOLDNAVN',
            plot_title=f"Benchmark: {valgt_metric}"
        )
        st.pyplot(fig)

    elif visning == "SkillCorner Radar" and SKILLCORNER_AVAILABLE:
        # SkillCorner Radar (Percentiler)
        radar_metrics = {'HI_RUNS': 'HI Runs', 'TOP_SPEED': 'Top Speed', 'HSR': 'HSR', 'DISTANCE': 'Volume'}
        radar_df = df_liga.copy()
        for m in radar_metrics.keys():
            radar_df[m] = radar_df[m].rank(pct=True) * 100

        fig, ax = rad.plot_radar(
            radar_df,
            data_point_id='HOLDNAVN',
            label=valgt_hold,
            metrics=list(radar_metrics.keys()),
            metric_labels=radar_metrics,
            plot_title=f"Fysisk Profil | {valgt_hold}",
            add_sample_info=False
        )
        st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
