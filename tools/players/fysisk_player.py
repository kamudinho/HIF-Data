import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from mplsoccer import Pitch
from matplotlib import patheffects
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
SEASON_START = "2025-07-01"
LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '328', '329', '43319', '331', '1305')"

# --- OPTIMERET FORBINDELSE ---
@st.cache_resource
def get_cached_conn():
    """Genbruger forbindelsen for at øge hastigheden markant"""
    return _get_snowflake_conn()

# --- DATA FUNKTIONER ---
@st.cache_data(ttl=600)
def get_extended_player_data(player_name, player_opta_uuid, target_team_ssiid):
    conn = get_cached_conn()
    clean_id = str(player_opta_uuid).lower().replace('p', '').strip()
    navne_dele = player_name.strip().split(' ')
    f_name, l_name = navne_dele[0], navne_dele[-1].replace('å', '_').replace('ø', '_').replace('æ', '_')

    sql = f"""
        SELECT 
            s.MATCH_DATE, s.MATCH_TEAMS, s.PLAYER_NAME, s.MATCH_SSIID,
            CASE WHEN s.MINUTES LIKE '%:%' THEN TRY_TO_NUMBER(SPLIT_PART(s.MINUTES, ':', 1)) ELSE TRY_TO_NUMBER(s.MINUTES) END AS MINS,
            s.DISTANCE, s."HIGH SPEED RUNNING" as HSR, s.SPRINTING, s.TOP_SPEED,
            s.HSR_DISTANCE_TIP as HSR_TIP, s.HSR_DISTANCE_OTIP as HSR_OTIP
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS s
        JOIN {DB}.SECONDSPECTRUM_GAME_METADATA m ON s.MATCH_SSIID = m.MATCH_SSIID
        WHERE (s."optaId" = '{clean_id}' OR (s.PLAYER_NAME ILIKE '%{f_name}%' AND s.PLAYER_NAME ILIKE '%{l_name}%'))
          AND (m.HOME_SSIID = '{target_team_ssiid}' OR m.AWAY_SSIID = '{target_team_ssiid}')
          AND s.MATCH_DATE >= '{SEASON_START}'
        ORDER BY s.MATCH_DATE DESC
    """
    return conn.query(sql)

def draw_phase_pitch(val, title, color):
    pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
    fig, ax = pitch.draw(figsize=(8, 6))
    fig.patch.set_alpha(0)
    ax.scatter(50, 50, s=3000, color=color, alpha=0.1)
    txt = ax.text(50, 50, f"{int(val)}m", color=color, fontsize=45, fontweight='bold', ha='center', va='center')
    txt.set_path_effects([patheffects.withStroke(linewidth=3, foreground='white')])
    ax.set_title(title, fontsize=16, fontweight='bold')
    return fig

def vis_side():
    # CSS til de rigtige tabs (Screenshot-stil)
    st.markdown("""<style>
        .stTabs [data-baseweb="tab-list"] { gap: 8px; border-bottom: 1px solid #eee; }
        .stTabs [data-baseweb="tab"] { height: 45px; background-color: white !important; color: #666 !important; }
        .stTabs [aria-selected="true"] { color: #cc0000 !important; border-bottom: 3px solid #cc0000 !important; font-weight: bold !important; }
        [data-testid="stMetricValue"] { font-size: 26px !important; font-weight: bold !important; color: #333; }
    </style>""", unsafe_allow_html=True)

    conn = get_cached_conn()
    
    # Dropdowns
    c1, c2 = st.columns(2)
    df_teams = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME as NAME, CONTESTANTHOME_OPTAUUID as UUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS} ORDER BY 1")
    valgt_hold = c1.selectbox("Vælg Hold", df_teams['NAME'].unique(), label_visibility="collapsed")
    
    h_uuid = df_teams[df_teams['NAME'] == valgt_hold]['UUID'].iloc[0]
    target_ssiid = TEAMS.get(valgt_hold, {}).get('ssid')

    df_pl = conn.query(f"SELECT DISTINCT TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as NAVN, p.PLAYER_OPTAUUID FROM {DB}.OPTA_PLAYERS p JOIN {DB}.OPTA_EVENTS e ON p.PLAYER_OPTAUUID = e.PLAYER_OPTAUUID WHERE e.EVENT_CONTESTANT_OPTAUUID = '{h_uuid}' AND e.EVENT_TIMESTAMP >= '{SEASON_START}' ORDER BY 1")
    valgt_spiller = c2.selectbox("Vælg Spiller", df_pl['NAVN'].tolist(), label_visibility="collapsed")
    p_uuid = df_pl[df_pl['NAVN'] == valgt_spiller]['PLAYER_OPTAUUID'].iloc[0]

    df = get_extended_player_data(valgt_spiller, p_uuid, target_ssiid)

    if not df.empty:
        latest = df.iloc[0]
        st.caption(f"Seneste Kamp: {latest['MATCH_TEAMS']} ({latest['MATCH_DATE']})")
        
        # Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Distance", f"{round(latest['DISTANCE']/1000, 2)} km")
        m2.metric("HSR", f"{int(latest['HSR'])} m")
        m3.metric("Top Speed", f"{round(latest['TOP_SPEED'], 1)} km/h")
        m4.metric("Spilletid", f"{int(latest['MINS'])} min")

        tabs = st.tabs(["Fase-overblik", "Intensitets Profil", "Minut Splits", "Sæson Trend"])

        with tabs[0]:
            col_a, col_b = st.columns(2)
            col_a.pyplot(draw_phase_pitch(latest['HSR_TIP'], "Angreb (TIP)", "#2ecc71"))
            col_b.pyplot(draw_phase_pitch(latest['HSR_OTIP'], "Forsvar (OTIP)", "#e74c3c"))

        with tabs[1]:
            # Hent F53A kun når fanen åbnes
            df_pct = conn.query(f"SELECT PERCENTDISTANCESTANDING, PERCENTDISTANCEWALKING, PERCENTDISTANCEJOGGING, PERCENTDISTANCELOWSPEEDRUNNING, PERCENTDISTANCEHIGHSPEEDRUNNING, PERCENTDISTANCEHIGHSPEEDSPRINTING FROM {DB}.SECONDSPECTRUM_F53A_GAME_PLAYER WHERE MATCH_SSIID = '{latest['MATCH_SSIID']}' AND PLAYER_NAME ILIKE '%{valgt_spiller.split(' ')[-1]}%' LIMIT 1")
            if not df_pct.empty:
                r = df_pct.iloc[0]
                z_labels = ['Stående', 'Gående', 'Jogging', 'LSR', 'HSR', 'Sprint']
                z_vals = [r[0], r[1], r[2], r[3], r[4], r[5]]
                fig = go.Figure(go.Bar(x=z_vals, y=z_labels, orientation='h', marker_color='#cc0000', text=[f"{round(v,1)}%" for v in z_vals], textposition='outside'))
                fig.update_layout(plot_bgcolor="white", height=350, margin=dict(l=0, r=20, t=0, b=0))
                st.plotly_chart(fig, use_container_width=True, key=f"int_{p_uuid}")

        with tabs[2]:
            df_splits = conn.query(f"SELECT MINUTE_SPLIT, UPPER(PHYSICAL_METRIC_TYPE) as METRIC, SUM(PHYSICAL_METRIC_VALUE) as VAL FROM {DB}.SECONDSPECTRUM_PHYSICAL_SPLITS_PLAYERS WHERE MATCH_SSIID = '{latest['MATCH_SSIID']}' AND PLAYER_NAME ILIKE '%{valgt_spiller.split(' ')[-1]}%' GROUP BY 1, 2 ORDER BY 1 ASC")
            if not df_splits.empty:
                metrics = df_splits['METRIC'].unique().tolist()
                sub_tabs = st.tabs([m.replace(' DISTANCE', '').title() for m in metrics])
                for i, m in enumerate(metrics):
                    with sub_tabs[i]:
                        d_m = df_splits[df_splits['METRIC'] == m]
                        fig_s = go.Figure(go.Scatter(x=d_m['MINUTE_SPLIT'], y=d_m['VAL'], fill='tozeroy', line=dict(color='#cc0000', width=3)))
                        fig_s.update_layout(plot_bgcolor="white", height=350, xaxis=dict(dtick=10))
                        st.plotly_chart(fig_s, use_container_width=True, key=f"split_{m}_{p_uuid}")

        with tabs[3]:
            df_trend = df.sort_values('MATCH_DATE')
            fig_t = go.Figure(go.Scatter(x=df_trend['MATCH_DATE'], y=df_trend['HSR'], mode='lines+markers', line=dict(color='#cc0000')))
            fig_t.update_layout(plot_bgcolor="white", height=350)
            st.plotly_chart(fig_t, use_container_width=True, key=f"trend_{p_uuid}")
    else:
        st.warning("Ingen fysisk data fundet.")

if __name__ == "__main__":
    vis_side()
