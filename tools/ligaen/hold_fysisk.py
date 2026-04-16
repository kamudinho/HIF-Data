import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from data.data_load import _get_snowflake_conn

# --- EKSTREMT ROBUST IMPORT ---
# Vi importerer de specifikke funktioner for at undgå 'module not defined'
try:
    from skillcornerviz.standard_plots.bar_plot import plot_bar_chart
    from skillcornerviz.standard_plots.radar_plot import plot_radar
    SKILLCORNER_READY = True
except Exception as e:
    SKILLCORNER_READY = False
    SC_ERROR_MSG = str(e)

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
SEASON_START = "2025-07-01"
LIGA_OPTA_ID = "148"

@st.cache_resource
def get_cached_conn():
    return _get_snowflake_conn()

def vis_side():
    st.title("Hvidovre IF - Physical Performance")
    
    if not SKILLCORNER_READY:
        st.error(f"SkillCorner-modulerne kunne ikke indlæses: {SC_ERROR_MSG}")
        st.info("Tjek at 'skillcornerviz' er stavet korrekt i din requirements.txt")

    conn = get_cached_conn()
    
    # 1. DATA SQL
    sql = f"""
        SELECT P.MATCH_SSIID, P.MATCH_TEAMS, P.DISTANCE, P."HIGH SPEED RUNNING" as HSR,
               P.NO_OF_HIGH_INTENSITY_RUNS as HI_RUNS, P.TOP_SPEED
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS P
        JOIN {DB}.SECONDSPECTRUM_SEASON_METADATA M ON P.MATCH_SSIID = M.MATCH_SSIID
        WHERE M.COMPETITION_OPTAID = '{LIGA_OPTA_ID}' AND M.DATE >= '{SEASON_START}'
    """
    df_raw = conn.query(sql)
    
    if df_raw is None or df_raw.empty:
        st.warning("Venter på data fra Snowflake...")
        return

    df_raw.columns = [c.upper() for c in df_raw.columns]
    df_raw['HOLDNAVN'] = df_raw['MATCH_TEAMS'].apply(lambda x: str(x).split('-')[0].split(':')[0].strip())

    # 2. AGGREGERING (Hold-fokus)
    df_kampe = df_raw.groupby(['MATCH_SSIID', 'HOLDNAVN']).agg({
        'DISTANCE': 'sum', 'HSR': 'sum', 'HI_RUNS': 'sum', 'TOP_SPEED': 'max'
    }).reset_index()

    df_liga = df_kampe.groupby('HOLDNAVN').agg({
        'DISTANCE': 'mean', 'HSR': 'mean', 'HI_RUNS': 'mean', 'TOP_SPEED': 'mean'
    }).reset_index()

    # --- UI ---
    valgt_hold = st.selectbox("Vælg dit hold", sorted(df_liga['HOLDNAVN'].unique()), index=0)
    
    col1, col2 = st.columns([1, 1])

    # --- GRAF 1: SKILLCORNER BAR CHART (HI RUNS) ---
    with col1:
        st.subheader("High Intensity Ranking")
        if SKILLCORNER_READY:
            df_bar = df_liga.sort_values('HI_RUNS', ascending=False).copy()
            df_bar['id_col'] = range(len(df_bar))
            h_idx = df_bar[df_bar['HOLDNAVN'] == valgt_hold]['id_col'].tolist()
            
            try:
                fig1, ax1 = plot_bar_chart(
                    df=df_bar, metric='HI_RUNS', label='HI Aktioner',
                    primary_highlight_group=h_idx, primary_highlight_color='#cc0000',
                    data_point_id='id_col', data_point_label='HOLDNAVN'
                )
                st.pyplot(fig1)
            except Exception as e:
                st.write(f"Bar Chart fejl: {e}")

    # --- GRAF 2: SKILLCORNER RADAR (PERCENTILER) ---
    with col2:
        st.subheader("Fysisk Power-Profil")
        if SKILLCORNER_READY:
            radar_metrics = {'HI_RUNS': 'HI Runs', 'TOP_SPEED': 'Top Speed', 'HSR': 'HSR', 'DISTANCE': 'Volume'}
            radar_df = df_liga.copy()
            for m in radar_metrics.keys():
                radar_df[m] = radar_df[m].rank(pct=True) * 100
            
            try:
                fig2, ax2 = plot_radar(
                    radar_df, data_point_id='HOLDNAVN', label=valgt_hold,
                    metrics=list(radar_metrics.keys()), metric_labels=radar_metrics,
                    add_sample_info=False
                )
                st.pyplot(fig2)
            except Exception as e:
                st.write(f"Radar fejl: {e}")

    # --- GRAF 3: INTERAKTIVT SCATTER (PLOTLY) ---
    st.divider()
    st.subheader("Sammenligning: Distance vs. Intensitet")
    
    fig3 = px.scatter(df_liga, x='DISTANCE', y='HI_RUNS', text='HOLDNAVN',
                     color_discrete_sequence=['grey'], opacity=0.5)
    
    # Highlight det valgte hold i rød
    highlight_df = df_liga[df_liga['HOLDNAVN'] == valgt_hold]
    fig3.add_trace(go.Scatter(
        x=highlight_df['DISTANCE'], y=highlight_df['HI_RUNS'],
        mode='markers+text', marker=dict(size=15, color='#cc0000'),
        text=valgt_hold, textposition="top center", showlegend=False
    ))
    
    fig3.update_layout(template="plotly_white", height=500)
    st.plotly_chart(fig3, use_container_width=True)

if __name__ == "__main__":
    vis_side()
