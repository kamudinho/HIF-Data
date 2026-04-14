import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '328', '329', '43319', '331')"
CURRENT_SEASON = "2025/2026"

@st.cache_data(ttl=600)
def get_physical_profile(player_name, player_opta_uuid, valgt_hold_navn, _conn):
    """Henter fysisk summary baseret på dit præcise skema"""
    target_ssiid = TEAMS.get(valgt_hold_navn, {}).get('ssid')
    clean_id = str(player_opta_uuid).lower().replace('p', '').strip()
    
    # Navne-filter logik
    navne_dele = [n.strip() for n in player_name.split(' ') if len(n.strip()) > 2]
    name_conditions = " OR ".join([f"PLAYER_NAME ILIKE '%{n}%'" for n in navne_dele])

    sql = f"""
        SELECT 
            MATCH_DATE,
            MATCH_TEAMS,
            MINUTES,
            DISTANCE,
            "HIGH SPEED RUNNING" as HSR,
            SPRINTING,
            TOP_SPEED,
            NO_OF_HIGH_INTENSITY_RUNS as HI_RUNS,
            -- TIP (Team in Possession)
            DISTANCE_TIP,
            HSR_DISTANCE_TIP as HSR_TIP,
            NO_OF_HIGH_INTENSITY_RUNS_TIP as HI_RUNS_TIP,
            -- OTIP (Opponent in Possession)
            DISTANCE_OTIP,
            HSR_DISTANCE_OTIP as HSR_OTIP,
            NO_OF_HIGH_INTENSITY_RUNS_OTIP as HI_RUNS_OTIP,
            -- BOP (Ball Out of Play)
            DISTANCE_BOP,
            HSR_DISTANCE_BOP as HSR_BOP
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE (({name_conditions}) OR ("optaId" = '{clean_id}'))
          AND MATCH_DATE >= '2025-07-01'
          AND MATCH_SSIID IN (
              SELECT MATCH_SSIID FROM {DB}.SECONDSPECTRUM_GAME_METADATA
              WHERE HOME_SSIID = '{target_ssiid}' OR AWAY_SSIID = '{target_ssiid}'
          )
        ORDER BY MATCH_DATE DESC
    """
    return _conn.query(sql)

def vis_side():
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 22px !important; font-weight: bold !important; color: #cc0000; }
        .stTabs [aria-selected="true"] { background-color: #cc0000 !important; color: white !important; }
        </style>
    """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn: return

    # --- FILTRERING (INGEN SUPERLIGA) ---
    sql_teams = f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}"
    df_teams_raw = conn.query(sql_teams)
    mapping_lookup = {str(info['opta_uuid']).lower().replace('t', ''): name for name, info in TEAMS.items() if 'opta_uuid' in info}
    
    valid_teams = {}
    if df_teams_raw is not None:
        for _, r in df_teams_raw.iterrows():
            uuid_clean = str(r['CONTESTANTHOME_OPTAUUID']).lower().replace('t','')
            if uuid_clean in mapping_lookup:
                valid_teams[mapping_lookup[uuid_clean]] = r['CONTESTANTHOME_OPTAUUID']

    c1, c2 = st.columns(2)
    valgt_hold = c1.selectbox("Vælg Hold", sorted(list(valid_teams.keys())))
    valgt_uuid_hold = valid_teams[valgt_hold]

    sql_spillere = f"""
        SELECT DISTINCT TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as NAVN, e.PLAYER_OPTAUUID
        FROM {DB}.OPTA_EVENTS e
        JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
        WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid_hold}' AND e.EVENT_TIMESTAMP >= '2025-07-01'
    """
    df_pl = conn.query(sql_spillere)
    if df_pl is None or df_pl.empty: return

    valgt_spiller = c2.selectbox("Vælg Spiller", sorted(df_pl['NAVN'].tolist()))
    valgt_player_uuid = df_pl[df_pl['NAVN'] == valgt_spiller]['PLAYER_OPTAUUID'].iloc[0]

    # --- DATA LOAD ---
    df = get_physical_profile(valgt_spiller, valgt_player_uuid, valgt_hold, conn)

    if df is not None and not df.empty:
        latest = df.iloc[0]
        st.subheader(f"Fysisk Analyse: {valgt_spiller}")
        
        # 1. Metrics Rad
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Distance", f"{round(latest['DISTANCE']/1000, 2)} km")
        m2.metric("HSR (Zone 4/5)", f"{int(latest['HSR'])} m")
        m3.metric("Sprint (Zone 6)", f"{int(latest['SPRINTING'])} m")
        m4.metric("Top Speed", f"{round(latest['TOP_SPEED'], 1)} km/t")

        # 2. Tabs
        t_phase, t_trend, t_log = st.tabs(["📊 Fase Analyse (TIP/OTIP)", "📈 Sæson Udvikling", "📋 Kamp Log"])

        with t_phase:
            col_a, col_b = st.columns(2)
            
            with col_a:
                # Donut chart for Distance
                fig_dist = go.Figure(data=[go.Pie(
                    labels=['Med bold (TIP)', 'Modstander bold (OTIP)', 'Bold ude (BOP)'],
                    values=[latest['DISTANCE_TIP'], latest['DISTANCE_OTIP'], latest['DISTANCE_BOP']],
                    hole=.4,
                    marker_colors=['#2ecc71', '#e74c3c', '#95a5a6']
                )])
                fig_dist.update_layout(title="Distance Fordeling", height=350, margin=dict(t=40, b=0, l=0, r=0))
                st.plotly_chart(fig_dist, use_container_width=True)

            with col_b:
                # Bar chart for HI Runs
                fig_hi = go.Figure(data=[
                    go.Bar(name='TIP', x=['HI Runs'], y=[latest['HI_RUNS_TIP']], marker_color='#2ecc71'),
                    go.Bar(name='OTIP', x=['HI Runs'], y=[latest['HI_RUNS_OTIP']], marker_color='#e74c3c'),
                    go.Bar(name='BOP', x=['HI Runs'], y=[latest.get('HI_RUNS_BOP', 0)], marker_color='#95a5a6')
                ])
                fig_hi.update_layout(title="Højintensive aktioner pr. fase", barmode='group', height=350)
                st.plotly_chart(fig_hi, use_container_width=True)

        with t_trend:
            df_trend = df.sort_values('MATCH_DATE')
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(x=df_trend['MATCH_DATE'], y=df_trend['HSR'], name="Total HSR", line=dict(color='#cc0000', width=3)))
            fig_trend.add_trace(go.Scatter(x=df_trend['MATCH_DATE'], y=df_trend['HSR_TIP'], name="Offensiv HSR (TIP)", line=dict(color='#2ecc71', dash='dot')))
            fig_trend.add_trace(go.Scatter(x=df_trend['MATCH_DATE'], y=df_trend['HSR_OTIP'], name="Defensiv HSR (OTIP)", line=dict(color='#e74c3c', dash='dot')))
            fig_trend.update_layout(title="HSR Udvikling over sæsonen", plot_bgcolor="white", height=400)
            st.plotly_chart(fig_trend, use_container_width=True)

        with t_log:
            st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Ingen fysiske data fundet for denne spiller.")

if __name__ == "__main__":
    vis_side()
