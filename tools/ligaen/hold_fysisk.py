import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from data.data_load import _get_snowflake_conn

# --- ROBUST IMPORT AF SKILLCORNER ---
try:
    import skillcornerviz.standard_plots.bar_plot as sc_bar
    import skillcornerviz.standard_plots.radar_plot as sc_rad
    SKILLCORNER_ERR = None
except Exception as e:
    SKILLCORNER_ERR = str(e)

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
SEASON_START = "2025-07-01"
LIGA_OPTA_ID = "148"

@st.cache_resource
def get_cached_conn():
    return _get_snowflake_conn()

def vis_side():
    st.set_page_config(page_title="Hvidovre IF - Physical Analytics", layout="wide")
    
    if SKILLCORNER_ERR:
        st.error(f"SkillCorner bibliotek fejler: {SKILLCORNER_ERR}")
        st.info("Prøv at genstarte appen eller tjek din requirements.txt")

    conn = get_cached_conn()
    
    # 1. HENT DATA
    sql = f"""
        SELECT P.MATCH_SSIID, P.MATCH_TEAMS, P.DISTANCE, P."HIGH SPEED RUNNING" as HSR,
               P.NO_OF_HIGH_INTENSITY_RUNS as HI_RUNS, P.TOP_SPEED
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS P
        JOIN {DB}.SECONDSPECTRUM_SEASON_METADATA M ON P.MATCH_SSIID = M.MATCH_SSIID
        WHERE M.COMPETITION_OPTAID = '{LIGA_OPTA_ID}' AND M.DATE >= '{SEASON_START}'
    """
    df_raw = conn.query(sql)
    if df_raw is None or df_raw.empty:
        st.error("Ingen data fundet.")
        return

    df_raw.columns = [c.upper() for c in df_raw.columns]
    df_raw['HOLDNAVN'] = df_raw['MATCH_TEAMS'].apply(lambda x: str(x).split('-')[0].split(':')[0].strip())

    # 2. AGGREGERING (Hold-totaler pr. kamp)
    df_kampe = df_raw.groupby(['MATCH_SSIID', 'HOLDNAVN']).agg({
        'DISTANCE': 'sum', 'HSR': 'sum', 'HI_RUNS': 'sum', 'TOP_SPEED': 'max'
    }).reset_index()

    df_liga = df_kampe.groupby('HOLDNAVN').agg({
        'DISTANCE': 'mean', 'HSR': 'mean', 'HI_RUNS': 'mean', 'TOP_SPEED': 'mean'
    }).reset_index()

    # --- UI ---
    valgt_hold = st.selectbox("Vælg dit hold", sorted(df_liga['HOLDNAVN'].unique()))
    
    # 1. INTERAKTIV SCATTER
    st.subheader("Interaktiv Oversigt (Plotly)")
    fig = px.scatter(df_liga[df_liga['HOLDNAVN'] != valgt_hold], x='DISTANCE', y='HI_RUNS', text='HOLDNAVN',
                     labels={'DISTANCE': 'Total Distance (m)', 'HI_RUNS': 'HI Aktioner'})
    fig.add_trace(go.Scatter(x=df_liga[df_liga['HOLDNAVN'] == valgt_hold]['DISTANCE'], 
                             y=df_liga[df_liga['HOLDNAVN'] == valgt_hold]['HI_RUNS'],
                             mode='markers+text', marker=dict(size=18, color='red'), text=valgt_hold))
    st.plotly_chart(fig, use_container_width=True)

    # --- 2. SKILLCORNER BAR CHART ---
    st.divider()
    st.subheader("SkillCorner Rankings (Bar Chart)")
    
    df_bar = df_liga.sort_values('HI_RUNS', ascending=False).copy()
    df_bar['SC_ID'] = range(len(df_bar))
    highlight_idx = df_bar[df_bar['HOLDNAVN'] == valgt_hold]['SC_ID'].tolist()

    if 'sc_bar' in globals() or 'sc_bar' in locals():
        try:
            # Vi kalder funktionen direkte fra det importede modul
            fig_bar, ax_bar = sc_bar.plot_bar_chart(
                df=df_bar,
                metric='HI_RUNS',
                label='HI Aktioner pr. kamp',
                unit='',
                primary_highlight_group=highlight_idx,
                primary_highlight_color='#cc0000',
                data_point_id='SC_ID',
                data_point_label='HOLDNAVN',
                plot_title="Liga Ranking: High Intensity"
            )
            st.pyplot(fig_bar)
        except Exception as e:
            st.warning(f"Kunne ikke tegne Bar Chart: {e}")

    # --- 3. SKILLCORNER RADAR ---
    st.divider()
    st.subheader("SkillCorner Profil (Radar)")
    
    if 'sc_rad' in globals() or 'sc_rad' in locals():
        radar_metrics = {'HI_RUNS': 'HI Runs', 'TOP_SPEED': 'Top Speed', 'HSR': 'HSR', 'DISTANCE': 'Volume'}
        radar_df = df_liga.copy()
        for m in radar_metrics.keys():
            radar_df[m] = radar_df[m].rank(pct=True) * 100

        try:
            fig_rad, ax_rad = sc_rad.plot_radar(
                radar_df,
                data_point_id='HOLDNAVN',
                label=valgt_hold,
                metrics=list(radar_metrics.keys()),
                metric_labels=radar_metrics,
                plot_title=f"Power Profil: {valgt_hold}",
                add_sample_info=False
            )
            st.pyplot(fig_rad)
        except Exception as e:
            st.warning(f"Kunne ikke tegne Radar: {e}")

if __name__ == "__main__":
    vis_side()
