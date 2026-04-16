import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
SEASON_START = "2025-07-01"
LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '328', '329', '43319', '331', '1305')"

@st.cache_resource
def get_cached_conn():
    return _get_snowflake_conn()

def vis_side():
    st.markdown("""<style>
        [data-testid="stMetricValue"] { font-size: 26px !important; font-weight: bold !important; color: #333; }
    </style>""", unsafe_allow_html=True)

    conn = get_cached_conn()
    
    # 1. HENT HOLDLISTE (Bruger DB prefix)
    df_teams = conn.query(f"""
        SELECT DISTINCT CONTESTANTHOME_NAME as NAME 
        FROM {DB}.OPTA_MATCHINFO 
        WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS} 
        ORDER BY 1
    """)
    
    if df_teams is None or df_teams.empty:
        st.error("Kunne ikke hente hold-data.")
        return

    c1, c2 = st.columns(2)
    valgt_hold = c1.selectbox("Vælg Hold", df_teams['NAME'].unique())
    target_ssiid = TEAMS.get(valgt_hold, {}).get('ssid')

    # 2. HENT KAMPE FOR HOLDET (Bruger DB prefix)
    df_matches = conn.query(f"""
        SELECT DISTINCT 
            MATCH_SSIID, 
            DATE as CALC_DATE,
            DESCRIPTION as MATCH_NAME
        FROM {DB}.SECONDSPECTRUM_SEASON_METADATA
        WHERE (HOME_SSIID = '{target_ssiid}' OR AWAY_SSIID = '{target_ssiid}')
          AND DATE >= '{SEASON_START}'
          AND DATE <= CURRENT_DATE()
        ORDER BY DATE DESC
    """)

    if df_matches is None or df_matches.empty:
        st.warning("Ingen spillede kampe fundet.")
        return

    df_matches['DATO_STR'] = pd.to_datetime(df_matches['CALC_DATE']).dt.strftime('%d/%m')
    df_matches['SELECT_LABEL'] = df_matches['DATO_STR'] + " - " + df_matches['MATCH_NAME']
    valgt_kamp_label = c2.selectbox("Vælg Kamp", df_matches['SELECT_LABEL'].tolist())
    valgt_match_ssiid = df_matches[df_matches['SELECT_LABEL'] == valgt_kamp_label]['MATCH_SSIID'].iloc[0]

    # 3. HOLD-DATA AGGREGERING (Totaler for hele holdet i kampen)
    # Her bruger vi DB prefix på alle tabeller
    df_hold_summary = conn.query(f"""
        SELECT 
            SUM(DISTANCE) as TOTAL_DIST,
            SUM("HIGH SPEED RUNNING") as TOTAL_HSR,
            SUM(SPRINTING) as TOTAL_SPRINT,
            SUM(NO_OF_HIGH_INTENSITY_RUNS) as TOTAL_HI,
            SUM(HSR_DISTANCE_TIP) as HSR_TIP,
            SUM(HSR_DISTANCE_OTIP) as HSR_OTIP
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_SSIID = '{valgt_match_ssiid}'
    """)

    if df_hold_summary is not None and not df_hold_summary.empty:
        hold = df_hold_summary.iloc[0]
        
        # Metrics række
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Distance", f"{round(hold['TOTAL_DIST']/1000, 1)} km")
        m2.metric("HSR Distance", f"{int(hold['TOTAL_HSR'])} m")
        m3.metric("Sprint Distance", f"{int(hold['TOTAL_SPRINT'])} m")
        m4.metric("HI Aktiviteter", f"{int(hold['TOTAL_HI'])}")

        st.divider()

        # 4. GRAFER: TIP vs OTIP (Holdets intensitet med/uden bold)
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("Fysisk Fase-fordeling")
            fig_pie = go.Figure(data=[go.Pie(
                labels=['Med bold (TIP)', 'Uden bold (OTIP)'],
                values=[hold['HSR_TIP'], hold['HSR_OTIP']],
                hole=.4,
                marker_colors=['#cc0000', '#333333']
            )])
            fig_pie.update_layout(height=350, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_right:
            # 5. PERIODE ANALYSE (Interval-data)
            df_splits = conn.query(f"""
                SELECT MINUTE_SPLIT, SUM(PHYSICAL_METRIC_VALUE) as VAL
                FROM {DB}.SECONDSPECTRUM_PHYSICAL_SPLITS_PLAYERS
                WHERE MATCH_SSIID = '{valgt_match_ssiid}'
                  AND PHYSICAL_METRIC_TYPE = 'Distance'
                GROUP BY 1 ORDER BY 1 ASC
            """)
            
            if df_splits is not None and not df_splits.empty:
                st.subheader("Intensitet over tid (Distance)")
                fig_line = go.Figure()
                fig_line.add_trace(go.Bar(
                    x=df_splits['MINUTE_SPLIT'], 
                    y=df_splits['VAL'], 
                    marker_color='#cc0000'
                ))
                fig_line.update_layout(height=350, xaxis_title="Minutter", yaxis_title="Meter")
                st.plotly_chart(fig_line, use_container_width=True)

    # 6. SPILLER LISTE (Top 10 i kampen)
    st.subheader("Spiller-performance i kampen")
    df_players = conn.query(f"""
        SELECT PLAYER_NAME, DISTANCE, "HIGH SPEED RUNNING", SPRINTING, TOP_SPEED
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_SSIID = '{valgt_match_ssiid}'
        ORDER BY DISTANCE DESC
    """)
    if df_players is not None:
        st.dataframe(df_players, use_container_width=True, hide_index=True)
