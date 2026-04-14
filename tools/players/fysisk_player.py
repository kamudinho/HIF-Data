import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from mplsoccer import Pitch
import matplotlib.pyplot as plt
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS, TEAM_COLORS

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '328', '329', '43319', '331', '1305')"

@st.cache_data(ttl=600)
def get_extended_player_data(player_name, player_opta_uuid, _conn):
    """Henter udvidet fysisk data inkl. faser, procenter og metadata"""
    clean_id = str(player_opta_uuid).lower().replace('p', '').strip()
    navne_dele = [n.strip() for n in player_name.split(' ') if len(n.strip()) > 2]
    name_conditions = " OR ".join([f"s.PLAYER_NAME ILIKE '%{n}%'" for n in navne_dele])

    sql = f"""
        SELECT 
            s.MATCH_DATE, s.MATCH_TEAMS, s.PLAYER_NAME,
            CASE 
                WHEN s.MINUTES LIKE '%:%' THEN 
                    TRY_TO_NUMBER(SPLIT_PART(s.MINUTES, ':', 1)) + (TRY_TO_NUMBER(SPLIT_PART(s.MINUTES, ':', 2)) / 60)
                ELSE TRY_TO_NUMBER(s.MINUTES) 
            END AS MINUTES_DECIMAL,
            s.DISTANCE, s."HIGH SPEED RUNNING" as HSR, s.SPRINTING, s.TOP_SPEED,
            s.NO_OF_HIGH_INTENSITY_RUNS as HI_RUNS,
            s.HSR_DISTANCE_TIP as HSR_TIP, s.SPRINT_DISTANCE_TIP as SPRINT_TIP,
            s.HSR_DISTANCE_OTIP as HSR_OTIP, s.SPRINT_DISTANCE_OTIP as SPRINT_OTIP,
            s.HSR_DISTANCE_BOP as HSR_BOP,
            f.PERCENTDISTANCESTANDING as STANDING_PCT, f.PERCENTDISTANCEWALKING as WALKING_PCT,
            f.PERCENTDISTANCEJOGGING as JOGGING_PCT, f.PERCENTDISTANCELOWSPEEDRUNNING as LSR_PCT,
            f.PERCENTDISTANCEHIGHSPEEDRUNNING as HSR_PCT, f.PERCENTDISTANCEHIGHSPEEDSPRINTING as SPRINT_PCT,
            sea.SEASONLABEL, sea.COMPETITIONLABEL, s.MATCH_SSIID
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS s
        LEFT JOIN {DB}.SECONDSPECTRUM_F53A_GAME_PLAYER f 
            ON s.MATCH_SSIID = f.MATCH_SSIID AND s.PLAYER_NAME = f.PLAYER_NAME
        LEFT JOIN {DB}.SECONDSPECTRUM_SEASON_METADATA sea
            ON s.MATCH_SSIID = sea.MATCH_SSIID
        WHERE (({name_conditions}) OR (s."optaId" = '{clean_id}'))
          AND s.MATCH_DATE >= '2025-07-01'
        ORDER BY s.MATCH_DATE DESC
    """
    return _conn.query(sql)

@st.cache_data(ttl=600)
def get_minute_splits(match_ssiid, player_name, _conn):
    """Henter minut-for-minut data for en specifik kamp og spiller"""
    sql = f"""
        SELECT MINUTE_SPLIT, PHYSICAL_METRIC_TYPE, PHYSICAL_METRIC_VALUE
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SPLITS_PLAYERS
        WHERE MATCH_SSIID = '{match_ssiid}' 
          AND PLAYER_NAME = '{player_name}'
          AND PHYSICAL_METRIC_TYPE IN ('distance', 'high_speed_running_distance')
        ORDER BY MINUTE_SPLIT ASC
    """
    return _conn.query(sql)

def draw_phase_pitch(val, title, color):
    pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD', line_zorder=2)
    fig, ax = pitch.draw(figsize=(8, 6))
    fig.patch.set_alpha(0)
    ax.text(50, 50, f"{int(val)}m", color=color, fontsize=50, fontweight='bold', ha='center', va='center', alpha=0.2)
    ax.set_title(title, fontsize=14, pad=10, fontweight='bold', color='#333333')
    return fig

def vis_side():
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 24px !important; font-weight: bold !important; color: #cc0000; }
        .stTabs [data-baseweb="tab"] { font-weight: bold; }
        div.block-container { padding-top: 2rem; }
        </style>
    """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn: return

    # --- VALG AF HOLD OG SPILLER ---
    sql_teams = f"SELECT DISTINCT CONTESTANTHOME_NAME as TEAM_NAME, CONTESTANTHOME_OPTAUUID as TEAM_UUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS} ORDER BY TEAM_NAME"
    df_teams = conn.query(sql_teams)
    
    col_h1, col_h2 = st.columns(2)
    valgt_hold = col_h1.selectbox("Vælg Hold", df_teams['TEAM_NAME'].unique())
    valgt_uuid_hold = df_teams[df_teams['TEAM_NAME'] == valgt_hold]['TEAM_UUID'].iloc[0]

    sql_spillere = f"SELECT DISTINCT TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as NAVN, e.PLAYER_OPTAUUID FROM {DB}.OPTA_EVENTS e JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid_hold}' AND e.EVENT_TIMESTAMP >= '2025-07-01' ORDER BY NAVN"
    df_pl = conn.query(sql_spillere)
    
    valgt_spiller = col_h2.selectbox("Vælg Spiller", df_pl['NAVN'].tolist())
    valgt_player_uuid = df_pl[df_pl['NAVN'] == valgt_spiller]['PLAYER_OPTAUUID'].iloc[0]

    st.markdown("---")

    # --- DATA HENTNING ---
    df = get_extended_player_data(valgt_spiller, valgt_player_uuid, conn)

    if df is not None and not df.empty:
        latest = df.iloc[0]
        
        # Hoved-metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Distance", f"{round(latest['DISTANCE']/1000, 2)} km")
        m2.metric("HSR (>19.8 km/h)", f"{int(latest['HSR'])} m")
        m3.metric("Top Speed", f"{round(latest['TOP_SPEED'], 1)} km/h")
        m4.metric("Spilletid", f"{int(latest['MINUTES_DECIMAL'])} min")

        tabs = st.tabs(["Fase-overblik", "Intensitets Profil", "Minut Splits", "Sæson Trend"])

        with tabs[0]:
            st.write(f"### HSR Fordeling: {latest['MATCH_TEAMS']} ({latest['MATCH_DATE']})")
            c_a, c_b = st.columns(2)
            with c_a:
                st.pyplot(draw_phase_pitch(latest['HSR_TIP'], "TIP (Angreb)", "#2ecc71"))
            with c_b:
                st.pyplot(draw_phase_pitch(latest['HSR_OTIP'], "OTIP (Forsvar)", "#e74c3c"))

        with tabs[1]:
            st.write("### Distancefordeling pr. hastighedszone (%)")
            splits_data = {
                'Stående': latest['STANDING_PCT'], 'Gående': latest['WALKING_PCT'],
                'Jogging': latest['JOGGING_PCT'], 'LSR': latest['LSR_PCT'],
                'HSR': latest['HSR_PCT'], 'Sprint': latest['SPRINT_PCT']
            }
            fig_bar = go.Figure(go.Bar(
                x=list(splits_data.values()), y=list(splits_data.keys()),
                orientation='h', marker_color='#cc0000', text=[f"{v}%" for v in splits_data.values()], textposition='outside'
            ))
            fig_bar.update_layout(xaxis=dict(range=[0, max(splits_data.values()) + 10]), height=350, margin=dict(t=20, b=20))
            st.plotly_chart(fig_bar, use_container_width=True)

        with tabs[2]:
            st.write("### Intensitet minut-for-minut")
            df_splits = get_minute_splits(latest['MATCH_SSIID'], valgt_spiller, conn)
            if not df_splits.empty:
                df_hsr_splits = df_splits[df_splits['PHYSICAL_METRIC_TYPE'] == 'high_speed_running_distance']
                fig_split = go.Figure()
                fig_split.add_trace(go.Scatter(
                    x=df_hsr_splits['MINUTE_SPLIT'], y=df_hsr_splits['PHYSICAL_METRIC_VALUE'],
                    fill='tozeroy', line_color='#cc0000', name="HSR Meter"
                ))
                fig_split.update_layout(xaxis_title="Minut", yaxis_title="HSR Meter", height=400)
                st.plotly_chart(fig_split, use_container_width=True)
            else:
                st.info("Ingen split-data tilgængelig for denne kamp.")

        with tabs[3]:
            df_trend = df.sort_values('MATCH_DATE')
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(x=df_trend['MATCH_DATE'], y=df_trend['HSR'], name="Total HSR", line=dict(color='#cc0000', width=3)))
            fig_trend.add_trace(go.Scatter(x=df_trend['MATCH_DATE'], y=df_trend['HSR_TIP'], name="TIP HSR", line=dict(color='#2ecc71', dash='dot')))
            fig_trend.add_trace(go.Scatter(x=df_trend['MATCH_DATE'], y=df_trend['HSR_OTIP'], name="OTIP HSR", line=dict(color='#e74c3c', dash='dot')))
            fig_trend.update_layout(plot_bgcolor="white", height=400)
            st.plotly_chart(fig_trend, use_container_width=True)
            
    else:
        st.info("Ingen udvidede data fundet.")

if __name__ == "__main__":
    vis_side()
