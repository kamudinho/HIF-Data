import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
HVIDOVRE_SSIID = '56fa29c7-3a48-4186-9d14-dbf45fbc78d9'
LIGA_IDS = "('335', '328', '329', '43319', '331')" # Standard liga IDs

def get_advanced_physical_data(player_name, player_opta_uuid, db_conn):
    """ Henter avanceret fysisk data inkl. TIP, OTIP og BOP baseret på din SQL """
    clean_id = str(player_opta_uuid).lower().replace('p', '').strip()
    
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
    WHERE (p."optaId" = '{clean_id}' OR p.PLAYER_NAME ILIKE '%{player_name}%')
      AND p.MATCH_DATE >= '2025-07-01'
    ORDER BY p.MATCH_DATE DESC
    """
    return db_conn.query(sql)

def vis_side(dp=None):
    st.set_page_config(layout="wide")
    conn = _get_snowflake_conn()
    
    if not conn:
        st.error("Kunne ikke forbinde til Snowflake.")
        return

    # --- MANUEL SPILLERVÆLGER (HVIS DP ER NONE) ---
    if dp is None:
        st.info("Ingen spiller sendt fra oversigten. Vælg en spiller manuelt herunder:")
        c1, c2 = st.columns(2)
        
        # Hent spillere fra Hvidovre (baseret på dit SSID)
        sql_players = f"""
            SELECT DISTINCT PLAYER_NAME, "optaId" 
            FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
            WHERE MATCH_DATE >= '2025-07-01'
            ORDER BY PLAYER_NAME
        """
        df_all_players = conn.query(sql_players)
        
        if df_all_players is not None:
            valgt_navn = c1.selectbox("Spiller", df_all_players['PLAYER_NAME'].tolist())
            valgt_id = df_all_players[df_all_players['PLAYER_NAME'] == valgt_navn]['optaId'].iloc[0]
            player_info = {'spiller_navn': valgt_navn, 'spiller_uuid': valgt_id}
        else:
            st.error("Kunne ikke hente spillerliste.")
            return
    else:
        player_info = dp

    # --- HENT DATA ---
    df = get_advanced_physical_data(player_info['spiller_navn'], player_info['spiller_uuid'], conn)

    if df is None or df.empty:
        st.warning(f"Ingen avanceret fysisk data fundet for {player_info['spiller_navn']}.")
        return

    st.title(f"Fysisk Analyse: {player_info['spiller_navn']}")

    # --- KAMPVALG ---
    df['Display'] = df['MATCH_DATE'].astype(str) + " : " + df['MATCH_TEAMS']
    valgt_kamp = st.selectbox("Vælg kamp for detaljer", df['Display'].tolist())
    row = df[df['Display'] == valgt_kamp].iloc[0]

    # --- OVERORDNEDE METRICS ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Distance", f"{round(row['DISTANCE']/1000, 2)} km")
    m2.metric("HSR (High Speed)", f"{int(row['DISTANCE_HSR'])} m")
    m3.metric("Sprint", f"{int(row['DISTANCE_SPRINT'])} m")
    m4.metric("Topfart", f"{round(row['TOP_SPEED'], 1)} km/t")

    st.markdown("---")

    # --- VISUALISERING AF POSSESSION CONTEXT ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Arbejdsrate pr. fase (Distance)")
        labels = ['Eget hold i besiddelse (TIP)', 'Modstander i besiddelse (OTIP)', 'Bold ude af spil (BOP)']
        values = [row['DISTANCE_TIP'], row['DISTANCE_OTIP'], row['DISTANCE_BOP']]
        
        fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4, marker_colors=['#2ecc71', '#e74c3c', '#95a5a6'])])
        fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=300)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        st.subheader("Højintensive løb (HI Runs)")
        # Bar chart for HI Runs i de forskellige faser
        hi_labels = ['Total', 'Med bold (TIP)', 'Mod bold (OTIP)', 'Ude af spil (BOP)']
        hi_values = [row['HI_RUNS_TOTAL'], row['HI_RUNS_TIP'], row['HI_RUNS_OTIP'], row['HI_RUNS_BOP']]
        
        fig_hi = go.Figure(data=[go.Bar(x=hi_labels, y=hi_values, marker_color='#cc0000')])
        fig_hi.update_layout(yaxis_title="Antal aktioner", plot_bgcolor='white', height=300)
        st.plotly_chart(fig_hi, use_container_width=True)

    # --- INTENSITETSZONER ---
    st.subheader("Distance i Intensitetszoner (m)")
    zones = ['Walking', 'Jogging', 'Running', 'HSR', 'Sprinting']
    z_values = [row['WALKING'], row['JOGGING'], row['RUNNING'], row['DISTANCE_HSR'], row['DISTANCE_SPRINT']]
    
    fig_zones = go.Figure(data=[go.Bar(x=zones, y=z_values, text=z_values, textposition='auto', marker_color='#34495e')])
    fig_zones.update_layout(plot_bgcolor='white', height=350)
    st.plotly_chart(fig_zones, use_container_width=True)

    # --- TABEL ---
    with st.expander("Se rådata for sæsonen"):
        st.dataframe(df.drop(columns=['Display']), hide_index=True)

if __name__ == "__main__":
    vis_side()
