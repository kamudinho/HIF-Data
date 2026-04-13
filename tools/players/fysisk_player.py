import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS
import requests
from PIL import Image
from io import BytesIO

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
HVIDOVRE_SSIID = '56fa29c7-3a48-4186-9d14-dbf45fbc78d9'
CURRENT_SEASON = "2025/2026"

def get_advanced_physical_data(player_name, player_opta_uuid, db_conn):
    """ 
    Henter avanceret fysisk data inkl. TIP (Team in Possession), 
    OTIP (Opponent in Possession) og BOP (Ball out of Play).
    """
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
      AND p.MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'
    ORDER BY p.MATCH_DATE DESC
    """
    return db_conn.query(sql)

def vis_side(dp=None):
    st.markdown("<style>.metric-card { background: #f8f9fa; padding: 10px; border-radius: 5px; }</style>", unsafe_allow_html=True)
    
    conn = _get_snowflake_conn()
    if not conn or dp is None:
        st.error("Ingen spiller valgt.")
        return

    valgt_spiller = dp['spiller_navn']
    valgt_player_uuid = dp['spiller_uuid']

    df = get_advanced_physical_data(valgt_spiller, valgt_player_uuid, conn)

    if df is None or df.empty:
        st.warning(f"Ingen avancerede fysiske data fundet for {valgt_spiller}.")
        return

    # --- KAMPVALG ---
    df['Display'] = df['MATCH_DATE'].astype(str) + " : " + df['MATCH_TEAMS']
    valgt_kamp = st.selectbox("Vælg kamp", df['Display'].tolist())
    row = df[df['Display'] == valgt_kamp].iloc[0]

    # --- TOP KPI'ER ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Dist", f"{round(row['DISTANCE']/1000, 2)} km")
    m2.metric("HSR", f"{int(row['DISTANCE_HSR'])} m")
    m3.metric("Sprint", f"{int(row['DISTANCE_SPRINT'])} m")
    m4.metric("Topfart", f"{round(row['TOP_SPEED'], 1)} km/t")

    st.markdown("---")

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Possession Context (Distance)")
        # TIP vs OTIP vs BOP
        labels = ['Med bold (TIP)', 'Mod bold (OTIP)', 'Bold ude (BOP)']
        values = [row['DISTANCE_TIP'], row['DISTANCE_OTIP'], row['DISTANCE_BOP']]
        
        fig_pos = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4, marker_colors=['#00CC96', '#EF553B', '#636EFA'])])
        fig_pos.update_layout(height=350, margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig_pos, use_container_width=True)

    with col_right:
        st.subheader("Intensitets-zoner (Meter)")
        # Zone opdeling
        zones = ['Walking', 'Jogging', 'Running', 'HSR', 'Sprinting']
        z_values = [row['WALKING'], row['JOGGING'], row['RUNNING'], row['DISTANCE_HSR'], row['DISTANCE_SPRINT']]
        
        fig_zones = go.Figure(data=[go.Bar(x=zones, y=z_values, marker_color='#cc0000')])
        fig_zones.update_layout(height=350, margin=dict(t=20, b=20, l=20, r=20), plot_bgcolor='white')
        st.plotly_chart(fig_zones, use_container_width=True)

    # --- HIGH INTENSITY BREAKDOWN ---
    st.subheader("Høj-intensitetsløb (HI Runs)")
    c1, c2, c3 = st.columns(3)
    c1.metric("HI Runs (Total)", int(row['HI_RUNS_TOTAL']))
    c2.metric("HI Runs (Med bold)", int(row['HI_RUNS_TIP']))
    c3.metric("HI Runs (Mod bold)", int(row['HI_RUNS_OTIP']))

    # --- HISTORIK ---
    with st.expander("Se fuld sæsonoversigt"):
        st.dataframe(df[['MATCH_DATE', 'MATCH_TEAMS', 'DISTANCE', 'DISTANCE_HSR', 'DISTANCE_SPRINT', 'TOP_SPEED', 'HI_RUNS_TOTAL']], 
                     hide_index=True, use_container_width=True)

if __name__ == "__main__":
    vis_side()
