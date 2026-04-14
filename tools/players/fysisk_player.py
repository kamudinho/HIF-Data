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
LIGA_IDS = "('335', '328', '329', '43319', '331')"

def get_physical_data_with_splits(player_name, player_opta_uuid, valgt_hold_navn, db_conn):
    """Henter fysisk data inklusiv TIP/OTIP/BOP splits"""
    target_ssiid = TEAMS.get(valgt_hold_navn, {}).get('ssid', '56fa29c7-3a48-4186-9d14-dbf45fbc78d9')
    clean_id = str(player_opta_uuid).lower().replace('p', '').strip()
    navne_dele = [n.strip() for n in player_name.split(' ') if len(n.strip()) > 2]
    name_conditions = " OR ".join([f"PLAYER_NAME ILIKE '%{n}%'" for n in navne_dele])

    sql = f"""
        SELECT 
            p.MATCH_DATE,
            ANY_VALUE(p.MATCH_TEAMS) as MATCH_TEAMS,
            MAX(p.MINUTES) as MINUTES,
            SUM(p.DISTANCE) as DISTANCE,
            SUM(p."HIGH SPEED RUNNING") as HSR,
            SUM(p.SPRINTING) as SPRINTING,
            MAX(p.TOP_SPEED) as TOP_SPEED,
            SUM(p.NO_OF_HIGH_INTENSITY_RUNS) as HI_RUNS,
            -- SPLITS
            SUM(p.DISTANCE_TIP) as DISTANCE_TIP,
            SUM(p.DISTANCE_OTIP) as DISTANCE_OTIP,
            SUM(p.DISTANCE_BOP) as DISTANCE_BOP,
            SUM(p.HSR_DISTANCE_TIP) as HSR_TIP,
            SUM(p.HSR_DISTANCE_OTIP) as HSR_OTIP,
            SUM(p.NO_OF_HIGH_INTENSITY_RUNS_TIP) as HI_RUNS_TIP,
            SUM(p.NO_OF_HIGH_INTENSITY_RUNS_OTIP) as HI_RUNS_OTIP
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS p
        WHERE (({name_conditions}) OR ("optaId" LIKE '%{clean_id}%'))
          AND p.MATCH_DATE >= '2025-07-01'
          AND p.MATCH_SSIID IN (
              SELECT MATCH_SSIID FROM {DB}.SECONDSPECTRUM_GAME_METADATA
              WHERE HOME_SSIID = '{target_ssiid}' OR AWAY_SSIID = '{target_ssiid}'
          )
        GROUP BY p.MATCH_DATE, p.PLAYER_NAME
        ORDER BY p.MATCH_DATE DESC
    """
    return db_conn.query(sql)

def vis_side():
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 18px !important; font-weight: bold !important; color: #cc0000; }
        [data-testid="stMetricLabel"] { font-size: 11px !important; }
        .player-header { font-size: 22px; font-weight: bold; margin-bottom: 15px; }
        </style>
    """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn: return

    # --- TOP MENU (INGEN SIDEBAR) ---
    col_h1, col_h2 = st.columns(2)
    
    # 1. Holdvalg
    hold_liste = sorted(list(TEAMS.keys()))
    valgt_hold = col_h1.selectbox("Vælg Hold", hold_liste)
    valgt_uuid_hold = TEAMS[valgt_hold].get('opta_uuid')

    # 2. Spillervalg
    sql_spillere = f"""
        SELECT DISTINCT TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as NAVN, e.PLAYER_OPTAUUID
        FROM {DB}.OPTA_EVENTS e
        JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
        WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid_hold}' 
        AND e.EVENT_TIMESTAMP >= '2025-07-01'
    """
    df_pl = conn.query(sql_spillere)
    
    if df_pl is None or df_pl.empty:
        st.warning("Ingen spillere fundet.")
        return

    valgt_spiller = col_h2.selectbox("Vælg Spiller", sorted(df_pl['NAVN'].tolist()))
    valgt_player_uuid = df_pl[df_pl['NAVN'] == valgt_spiller]['PLAYER_OPTAUUID'].iloc[0]

    st.markdown("---")

    # --- DATA LOAD ---
    df = get_physical_data_with_splits(valgt_spiller, valgt_player_uuid, valgt_hold, conn)

    if df is not None and not df.empty:
        latest = df.iloc[0]
        
        # HOVEDMETRICS
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Distance", f"{round(latest['DISTANCE']/1000, 2)} km")
        m2.metric("HSR (Z4+5)", f"{int(latest['HSR'])} m")
        m3.metric("Sprint (Z6)", f"{int(latest['SPRINTING'])} m")
        m4.metric("Topfart", f"{round(latest['TOP_SPEED'], 1)} km/t")

        # SPLIT ANALYSE
        st.subheader("Possession Splits (TIP vs OTIP)")
        
        c_left, c_right = st.columns(2)
        
        with c_left:
            # Distance Split cirkeldiagram
            fig_pie = go.Figure(data=[go.Pie(
                labels=['Med bold (TIP)', 'Modstander med bold (OTIP)', 'Bold ude (BOP)'],
                values=[latest['DISTANCE_TIP'], latest['DISTANCE_OTIP'], latest['DISTANCE_BOP']],
                hole=.4,
                marker_colors=['#2ecc71', '#e74c3c', '#95a5a6']
            )])
            fig_pie.update_layout(title="Distance Fordeling", height=350, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig_pie, use_container_width=True)

        with c_right:
            # HSR og HI Runs Split
            st.write("**Intensitet i faser (Seneste kamp)**")
            split_data = pd.DataFrame({
                'Fase': ['TIP (Med bold)', 'OTIP (Uden bold)'],
                'HSR Meter': [latest['HSR_TIP'], latest['HSR_OTIP']],
                'HI Runs': [latest['HI_RUNS_TIP'], latest['HI_RUNS_OTIP']]
            })
            st.table(split_data)
            
            # Kort summary
            hsr_total = latest['HSR_TIP'] + latest['HSR_OTIP']
            if hsr_total > 0:
                pct_otip = (latest['HSR_OTIP'] / hsr_total) * 100
                st.info(f"💡 {int(pct_otip)}% af spillerens HSR foregår i den defensive fase (OTIP).")

        # TREND OVER TID
        st.subheader("Sæsonudvikling: Intensitet")
        df_trend = df.sort_values('MATCH_DATE')
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(x=df_trend['MATCH_DATE'], y=df_trend['HSR'], name="HSR Total", line=dict(color='#cc0000', width=3)))
        fig_trend.add_trace(go.Scatter(x=df_trend['MATCH_DATE'], y=df_trend['HSR_OTIP'], name="HSR Uden bold (OTIP)", line=dict(color='#333', dash='dot')))
        
        fig_trend.update_layout(plot_bgcolor="white", height=300, margin=dict(t=20, b=0, l=0, r=0), hovermode="x unified")
        st.plotly_chart(fig_trend, use_container_width=True)

        with st.expander("Se alle kampsplit (Rå data)"):
            st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.warning(f"Ingen fysisk data fundet for {valgt_spiller}.")

if __name__ == "__main__":
    vis_side()
