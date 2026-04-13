import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from data.data_load import _get_snowflake_conn

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
HVIDOVRE_SSIID = '56fa29c7-3a48-4186-9d14-dbf45fbc78d9'

def get_player_list(db_conn):
    """ Henter alle unikke Hvidovre-spillere fra fysisk data """
    sql = f"""
        SELECT DISTINCT PLAYER_NAME, "optaId" 
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_DATE >= '2025-07-01'
        ORDER BY PLAYER_NAME
    """
    return db_conn.query(sql)

def get_advanced_physical_data(player_opta_id, db_conn):
    """ Henter den avancerede data inkl. possession faser """
    sql = f"""
    WITH hvidovre_ids AS (
        SELECT DISTINCT
            m.MATCH_SSIID, 
            f.value:"optaId"::string AS opta_id
        FROM {DB}.SECONDSPECTRUM_GAME_METADATA m,
        LATERAL FLATTEN(input => CASE 
            WHEN m.HOME_SSIID = '{HVIDOVRE_SSIID}' THEN m.HOME_PLAYERS 
            ELSE m.AWAY_PLAYERS 
        END) f
        WHERE m.HOME_SSIID = '{HVIDOVRE_SSIID}' 
           OR m.AWAY_SSIID = '{HVIDOVRE_SSIID}'
    )
    SELECT 
        p.MATCH_DATE, p.MATCH_TEAMS, p.PLAYER_NAME, p.MINUTES,
        p.DISTANCE, p.AVERAGE_SPEED, p.TOP_SPEED,
        p.WALKING, p.JOGGING, p.RUNNING, 
        p."HIGH SPEED RUNNING" AS DISTANCE_HSR,
        p.SPRINTING AS DISTANCE_SPRINT,
        p.NO_OF_HIGH_INTENSITY_RUNS AS HI_RUNS_TOTAL,
        p.DISTANCE_TIP, p.HSR_DISTANCE_TIP, p.SPRINT_DISTANCE_TIP, p.NO_OF_HIGH_INTENSITY_RUNS_TIP AS HI_RUNS_TIP,
        p.DISTANCE_OTIP, p.HSR_DISTANCE_OTIP, p.SPRINT_DISTANCE_OTIP, p.NO_OF_HIGH_INTENSITY_RUNS_OTIP AS HI_RUNS_OTIP,
        p.DISTANCE_BOP, p.HSR_DISTANCE_BOP, p.SPRINT_DISTANCE_BOP, p.NO_OF_HIGH_INTENSITY_RUNS_BOP AS HI_RUNS_BOP,
        p.MATCH_SSIID
    FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS p
    INNER JOIN hvidovre_ids h 
        ON p.MATCH_SSIID = h.MATCH_SSIID 
        AND p."optaId" = h.opta_id
    WHERE p."optaId" = '{player_opta_id}'
      AND p.MATCH_DATE >= '2025-07-01'
    ORDER BY p.MATCH_DATE DESC
    """
    return db_conn.query(sql)

def vis_side():
    st.set_page_config(page_title="Fysisk Spillerprofil", layout="wide")
    conn = _get_snowflake_conn()

    if not conn:
        st.error("Kunne ikke oprette forbindelse til databasen.")
        return

    # --- SIDEBAR: SPILLERVALG ---
    st.sidebar.header("Filter")
    df_players = get_player_list(conn)
    
    if df_players is not None and not df_players.empty:
        selected_player_name = st.sidebar.selectbox("Vælg Spiller", df_players['PLAYER_NAME'].unique())
        selected_player_id = df_players[df_players['PLAYER_NAME'] == selected_player_name]['optaId'].iloc[0]
    else:
        st.sidebar.warning("Ingen spillere fundet.")
        return

    # --- HENT DATA ---
    df_phys = get_advanced_physical_data(selected_player_id, conn)

    if df_phys is None or df_phys.empty:
        st.warning(f"Ingen fysisk data fundet for {selected_player_name}.")
        return

    # --- HOVEDLAYOUT ---
    st.title(f"Fysisk Profil: {selected_player_name}")
    
    # Sæson gennemsnit metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Gns. Distance", f"{round(df_phys['DISTANCE'].mean()/1000, 2)} km")
    m2.metric("Gns. HSR", f"{int(df_phys['DISTANCE_HSR'].mean())} m")
    m3.metric("Max Topfart", f"{round(df_phys['TOP_SPEED'].max(), 1)} km/t")
    m4.metric("Gns. HI Runs", f"{int(df_phys['HI_RUNS_TOTAL'].mean())}")

    st.markdown("---")

    # --- KAMP-SPECIFIK ANALYSE ---
    df_phys['Match_Label'] = df_phys['MATCH_DATE'].astype(str) + " : " + df_phys['MATCH_TEAMS']
    selected_match_label = st.selectbox("Vælg kamp for detaljeret analyse", df_phys['Match_Label'].tolist())
    row = df_phys[df_phys['Match_Label'] == selected_match_label].iloc[0]

    t1, t2 = st.tabs(["Possession Analyse", "Intensitets Zoner"])

    with t1:
        c1, c2 = st.columns([1, 1.5])
        with c1:
            st.write("**Distance fordelt på fase**")
            labels = ['TIP (Med bold)', 'OTIP (Mod bold)', 'BOP (Spilstop)']
            values = [row['DISTANCE_TIP'], row['DISTANCE_OTIP'], row['DISTANCE_BOP']]
            fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4, marker_colors=['#00cc96', '#ef553b', '#636efa'])])
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with c2:
            st.write("**Højintensive løb (HI Runs) pr. fase**")
            hi_data = {
                'Fase': ['Total', 'Med bold', 'Mod bold', 'Spilstop'],
                'Antal': [row['HI_RUNS_TOTAL'], row['HI_RUNS_TIP'], row['HI_RUNS_OTIP'], row['HI_RUNS_BOP']]
            }
            fig_hi = px.bar(hi_data, x='Fase', y='Antal', color='Fase', color_discrete_map={
                'Total': '#333', 'Med bold': '#00cc96', 'Mod bold': '#ef553b', 'Spilstop': '#636efa'
            })
            st.plotly_chart(fig_hi, use_container_width=True)

    with t2:
        st.write("**Distance i hastighedszoner (Meter)**")
        zone_labels = ['Walking', 'Jogging', 'Running', 'HSR', 'Sprinting']
        zone_values = [row['WALKING'], row['JOGGING'], row['RUNNING'], row['DISTANCE_HSR'], row['DISTANCE_SPRINT']]
        
        fig_zones = go.Figure(data=[go.Bar(
            x=zone_labels, 
            y=zone_values, 
            text=zone_values, 
            textposition='outside',
            marker_color='#1f77b4'
        )])
        fig_zones.update_layout(yaxis_title="Meter", plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_zones, use_container_width=True)

    # --- SÆSON TRENDS ---
    st.markdown("---")
    st.subheader("Sæsonudvikling: Distance & HSR")
    
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(x=df_phys['MATCH_DATE'], y=df_phys['DISTANCE'], name="Total Distance", line=dict(color="#636efa")))
    fig_trend.add_trace(go.Scatter(x=df_phys['MATCH_DATE'], y=df_phys['DISTANCE_HSR'], name="HSR", yaxis="y2", line=dict(color="#ef553b")))
    
    fig_trend.update_layout(
        yaxis=dict(title="Total Distance (m)"),
        yaxis2=dict(title="HSR (m)", overlaying="y", side="right"),
        hovermode="x unified",
        legend=dict(orientation="h", y=1.1)
    )
    st.plotly_chart(fig_trend, use_container_width=True)

if __name__ == "__main__":
    vis_side()
