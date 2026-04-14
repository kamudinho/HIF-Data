import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from mplsoccer import Pitch
import matplotlib.pyplot as plt
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
# NordicBet, 2. div, 3. div og Pokal (Superliga 335 er udeladt)
LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '328', '329', '43319', '331')"
CURRENT_SEASON = "2025/2026"

@st.cache_data(ttl=600)
def get_physical_summary(player_name, player_opta_uuid, valgt_hold_navn, _conn):
    """Henter de aggregerede sæsondata og splits"""
    target_ssiid = TEAMS.get(valgt_hold_navn, {}).get('ssid')
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
            SUM(p.DISTANCE_TIP) as DISTANCE_TIP,
            SUM(p.DISTANCE_OTIP) as DISTANCE_OTIP,
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
    return _conn.query(sql)

@st.cache_data(ttl=600)
def get_detailed_run_data(player_name, player_opta_uuid, valgt_hold_navn, _conn):
    """Henter koordinater for de enkelte løb (HSR/Sprint)"""
    target_ssiid = TEAMS.get(valgt_hold_navn, {}).get('ssid')
    clean_id = str(player_opta_uuid).lower().replace('p', '').strip()
    navne_dele = [n.strip() for n in player_name.split(' ') if len(n.strip()) > 2]
    name_conditions = " OR ".join([f"PLAYER_NAME ILIKE '%{n}%'" for n in navne_dele])

    sql = f"""
        SELECT START_X, START_Y, END_X, END_Y, PHASE, SPEED_CATEGORY, MATCH_DATE
        FROM {DB}.SECONDSPECTRUM_RUN_EVENTS
        WHERE (({name_conditions}) OR ("optaId" LIKE '%{clean_id}%'))
          AND MATCH_DATE >= '2025-07-01'
          AND MATCH_SSIID IN (
              SELECT MATCH_SSIID FROM {DB}.SECONDSPECTRUM_GAME_METADATA
              WHERE HOME_SSIID = '{target_ssiid}' OR AWAY_SSIID = '{target_ssiid}'
          )
    """
    return _conn.query(sql)

def draw_run_pitch(df_runs, phase, color, title):
    """Tegner banen med pile for løbsretninger"""
    pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD', line_zorder=2)
    fig, ax = pitch.draw(figsize=(10, 8))
    fig.set_facecolor('none')
    
    phase_data = df_runs[df_runs['PHASE'] == phase].copy()
    
    if not phase_data.empty:
        pitch.arrows(phase_data.START_X, phase_data.START_Y, 
                     phase_data.END_X, phase_data.END_Y, 
                     width=2, headwidth=4, headlength=4, 
                     color=color, ax=ax, alpha=0.7)
        pitch.scatter(phase_data.START_X, phase_data.START_Y, 
                      s=20, color=color, edgecolors='white', linewidth=0.5, alpha=0.8, ax=ax)
    else:
        ax.text(50, 50, "Ingen data for denne fase", ha='center', va='center', alpha=0.5)

    ax.set_title(title, fontsize=14, pad=15, fontweight='bold')
    return fig

def vis_side():
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 20px !important; font-weight: bold !important; color: #cc0000; }
        .stTabs [aria-selected="true"] { background-color: #cc0000 !important; color: white !important; }
        </style>
    """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn: return

    # --- FILTRERING ---
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

    # --- DATA ---
    df_sum = get_physical_summary(valgt_spiller, valgt_player_uuid, valgt_hold, conn)
    df_runs = get_detailed_run_data(valgt_spiller, valgt_player_uuid, valgt_hold, conn)

    if df_sum is not None and not df_sum.empty:
        latest = df_sum.iloc[0]
        st.subheader(f"Fysisk Profil: {valgt_spiller}")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Distance", f"{round(latest['DISTANCE']/1000, 2)} km")
        m2.metric("HSR", f"{int(latest['HSR'])} m")
        m3.metric("Sprint", f"{int(latest['SPRINTING'])} m")
        m4.metric("Topfart", f"{round(latest['TOP_SPEED'], 1)} km/t")

        t_runs, t_trend, t_data = st.tabs(["🚀 Løbsretninger (TIP/OTIP)", "📈 Sæsonudvikling", "📋 Kamp-log"])

        with t_runs:
            if df_runs is not None and not df_runs.empty:
                col_a, col_b = st.columns(2)
                with col_a:
                    st.pyplot(draw_run_pitch(df_runs, 'TIP', '#2ecc71', "Offensive løb (TIP)"))
                with col_b:
                    st.pyplot(draw_run_pitch(df_runs, 'OTIP', '#e74c3c', "Defensive løb (OTIP)"))
            else:
                st.info("Ingen detaljerede løbskoordinater tilgængelige.")

        with t_trend:
            df_trend = df_sum.sort_values('MATCH_DATE')
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_trend['MATCH_DATE'], y=df_trend['HSR'], name="Total HSR", line=dict(color='#cc0000', width=3)))
            fig.add_trace(go.Scatter(x=df_trend['MATCH_DATE'], y=df_trend['HSR_TIP'], name="HSR TIP", line=dict(color='#2ecc71', dash='dot')))
            fig.add_trace(go.Scatter(x=df_trend['MATCH_DATE'], y=df_trend['HSR_OTIP'], name="HSR OTIP", line=dict(color='#e74c3c', dash='dot')))
            fig.update_layout(plot_bgcolor="white", height=400, margin=dict(t=20, b=20, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)

        with t_data:
            st.dataframe(df_sum, use_container_width=True, hide_index=True)
    else:
        st.warning("Ingen data fundet.")

if __name__ == "__main__":
    vis_side()
