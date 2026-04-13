import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS
import requests
from PIL import Image
from io import BytesIO

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
CURRENT_SEASON = "2025/2026"

# --- HJÆLPEFUNKTIONER ---
@st.cache_data(ttl=3600)
def get_logo_img(opta_uuid):
    if not opta_uuid: return None
    uuid_clean = str(opta_uuid).lower().replace('t', '')
    url = next((info['logo'] for name, info in TEAMS.items() if str(info.get('opta_uuid', '')).lower().replace('t','') == uuid_clean), None)
    if not url: return None
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except: return None

def get_physical_summary(player_name, player_opta_uuid, db_conn):
    """ Henter overordnet kamp-statistik """
    clean_id = str(player_opta_uuid).lower().replace('p', '').strip()
    sql = f"""
        SELECT 
            MATCH_DATE, MATCH_TEAMS, MATCH_SSIID,
            CAST(MINUTES AS FLOAT) as MINUTES, 
            DISTANCE, "HIGH SPEED RUNNING" as HSR, 
            SPRINTING, TOP_SPEED, NO_OF_HIGH_INTENSITY_RUNS as HI_RUNS
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE ("optaId" = '{clean_id}' OR PLAYER_NAME ILIKE '%{player_name}%')
          AND MATCH_DATE >= '2025-07-01'
        ORDER BY MATCH_DATE DESC
    """
    return db_conn.query(sql)

def get_physical_splits(player_opta_uuid, match_ssiid, db_conn):
    """ Henter minut-for-minut data for en specifik kamp """
    clean_id = str(player_opta_uuid).lower().replace('p', '').strip()
    sql = f"""
        SELECT 
            MINUTE_SPLIT,
            PHYSICAL_METRIC_TYPE,
            PHYSICAL_METRIC_VALUE
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SPLITS_PLAYERS
        WHERE "PLAYER_OPTAID" = '{clean_id}'
          AND MATCH_SSIID = '{match_ssiid}'
        ORDER BY MINUTE_SPLIT ASC
    """
    return db_conn.query(sql)

def vis_side(dp=None):
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 18px !important; font-weight: bold; }
        .match-card { border: 1px solid #eee; padding: 15px; border-radius: 10px; background: #f9f9f9; }
        </style>
    """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn or dp is None:
        st.error("Kunne ikke forbinde til database eller ingen spiller valgt.")
        return

    # Data fra 'dp' (som sendes med fra hovedmenuen)
    valgt_spiller = dp['spiller_navn']
    valgt_player_uuid = dp['spiller_uuid']
    valgt_hold_uuid = dp['hold_uuid']
    hold_logo = get_logo_img(valgt_hold_uuid)

    st.title(f"Fysisk Analyse: {valgt_spiller}")

    # 1. Hent Summary Data
    df_phys = get_physical_summary(valgt_spiller, valgt_player_uuid, conn)

    if df_phys is None or df_phys.empty:
        st.warning(f"Ingen fysisk data fundet for {valgt_spiller} i sæsonen {CURRENT_SEASON}")
        return

    # --- TOP METRICS (Sæson gennemsnit) ---
    avg_col = st.columns(4)
    avg_col[0].metric("Gns. Distance", f"{round(df_phys['DISTANCE'].mean()/1000, 2)} km")
    avg_col[1].metric("Gns. HSR", f"{int(df_phys['HSR'].mean())} m")
    avg_col[2].metric("Max Topfart", f"{round(df_phys['TOP_SPEED'].max(), 1)} km/t")
    avg_col[3].metric("Gns. HI Runs", int(df_phys['HI_RUNS'].mean()))

    st.markdown("---")

    # --- KAMP SELEKTOR ---
    df_phys['Dato_Modstander'] = df_phys['MATCH_DATE'].dt.strftime('%d/%m') + " - " + df_phys['MATCH_TEAMS']
    valgt_kamp_str = st.selectbox("Vælg kamp for detaljeret minut-analyse", df_phys['Dato_Modstander'].tolist())
    
    selected_match = df_phys[df_phys['Dato_Modstander'] == valgt_kamp_str].iloc[0]
    match_ssiid = selected_match['MATCH_SSIID']

    # --- KAMP SPECIFIKKE METRICS ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Distance", f"{round(selected_match['DISTANCE']/1000, 2)} km")
    m2.metric("HSR", f"{int(selected_match['HSR'])} m")
    m3.metric("Sprint", f"{int(selected_match['SPRINTING'])} m")
    m4.metric("Minutter", int(selected_match['MINUTES']))

    # --- SPLITS ANALYSE (MINUT FOR MINUT) ---
    st.subheader("Intensitet over tid (Minut-splits)")
    
    df_splits = get_physical_splits(valgt_player_uuid, match_ssiid, conn)

    if df_splits is not None and not df_splits.empty:
        # Pivot data så vi har metrikker som kolonner
        df_pivoted = df_splits.pivot(index='MINUTE_SPLIT', columns='PHYSICAL_METRIC_TYPE', values='PHYSICAL_METRIC_VALUE').reset_index()
        
        # Omdøb for læsbarhed
        rename_map = {
            'distance': 'Distance (m)',
            'high_speed_running': 'HSR (m)',
            'sprinting': 'Sprint (m)'
        }
        df_pivoted = df_pivoted.rename(columns=rename_map)

        # Plotly figur
        fig = go.Figure()
        
        # Tilføj Distance som bar i baggrunden
        fig.add_trace(go.Bar(
            x=df_pivoted['MINUTE_SPLIT'],
            y=df_pivoted['Distance (m)'],
            name='Total Distance',
            marker_color='rgba(200, 200, 200, 0.3)',
            yaxis='y2'
        ))

        # Tilføj HSR som linje
        fig.add_trace(go.Scatter(
            x=df_pivoted['MINUTE_SPLIT'],
            y=df_pivoted['HSR (m)'],
            name='High Speed Running',
            line=dict(color='#cc0000', width=3),
            mode='lines'
        ))

        fig.update_layout(
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis=dict(title="HSR Meter pr. minut", side="left"),
            yaxis2=dict(title="Total Meter pr. minut", side="right", overlaying='y', showgrid=False),
            xaxis=dict(title="Minut", dtick=5),
            height=400,
            margin=dict(l=20, r=20, t=30, b=20),
            plot_bgcolor='white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Ingen minut-for-minut splits tilgængelige for denne kamp.")

    # --- HISTORISK UDVIKLING ---
    st.subheader("Sæsonudvikling")
    df_hist = df_phys.sort_values('MATCH_DATE')
    
    tab_dist, tab_hsr, tab_speed = st.tabs(["Distance", "HSR", "Topfart"])
    
    with tab_dist:
        fig_dist = px.line(df_hist, x='MATCH_DATE', y='DISTANCE', points="all", 
                           labels={'DISTANCE': 'Meter'}, color_discrete_sequence=['#333'])
        fig_dist.update_layout(plot_bgcolor='white')
        st.plotly_chart(fig_dist, use_container_width=True)

    with tab_hsr:
        fig_hsr = px.bar(df_hist, x='MATCH_DATE', y='HSR', 
                         color='HSR', color_continuous_scale='Reds')
        fig_hsr.update_layout(plot_bgcolor='white')
        st.plotly_chart(fig_hsr, use_container_width=True)

    with tab_speed:
        fig_speed = px.scatter(df_hist, x='MATCH_DATE', y='TOP_SPEED', size='HI_RUNS', 
                               trendline="lowess", title="Topfart vs Antal HI-løb (størrelse)")
        st.plotly_chart(fig_speed, use_container_width=True)

if __name__ == "__main__":
    # Test-mock hvis kørt direkte
    vis_side()
