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
LIGA_IDS = "('328', '329', '43319', '331', '1305', 'dyjr458hcmrcy87fsabfsy87o')"

@st.cache_resource
def get_cached_conn():
    return _get_snowflake_conn()

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
    st.markdown("""<style>
        .stTabs [data-baseweb="tab-list"] { gap: 8px; border-bottom: 1px solid #eee; }
        .stTabs [data-baseweb="tab"] { height: 45px; background-color: white !important; color: #666 !important; }
        .stTabs [aria-selected="true"] { color: #cc0000 !important; border-bottom: 3px solid #cc0000 !important; font-weight: bold !important; }
        [data-testid="stMetricValue"] { font-size: 24px !important; font-weight: bold !important; color: #333; }
    </style>""", unsafe_allow_html=True)

    conn = get_cached_conn()
    
    # --- 1. VÆLG HOLD ---
    df_teams = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME as NAME FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS} ORDER BY 1")
    if df_teams is None or df_teams.empty:
        st.error("Kunne ikke hente hold-data.")
        return

    c1, c2, c3 = st.columns(3)
    valgt_hold = c1.selectbox("Vælg Hold", df_teams['NAME'].unique(), label_visibility="collapsed")
    target_ssiid = TEAMS.get(valgt_hold, {}).get('ssid')

    # --- 2. VÆLG KAMP ---
    df_matches = conn.query(f"""
        SELECT DISTINCT MATCH_SSIID, DATE as CALC_DATE, DESCRIPTION as MATCH_NAME
        FROM {DB}.SECONDSPECTRUM_SEASON_METADATA
        WHERE (HOME_SSIID = '{target_ssiid}' OR AWAY_SSIID = '{target_ssiid}')
          AND DATE >= '{SEASON_START}' AND DATE <= CURRENT_DATE()
        ORDER BY DATE DESC
    """)

    if df_matches is None or df_matches.empty:
        st.warning(f"Ingen kampe fundet.")
        return

    df_matches['DATO_STR'] = pd.to_datetime(df_matches['CALC_DATE']).dt.strftime('%d/%m')
    df_matches['LABEL'] = df_matches['DATO_STR'] + " - " + df_matches['MATCH_NAME']
    valgt_label = c2.selectbox("Vælg Kamp", df_matches['LABEL'].tolist(), label_visibility="collapsed")
    valgt_match_ssiid = df_matches[df_matches['LABEL'] == valgt_label]['MATCH_SSIID'].iloc[0]

    # --- 3. VÆLG SPILLER (FILTRERET PÅ HOLD) ---
    df_pl = conn.query(f"""
        SELECT DISTINCT PLAYER_NAME 
        FROM {DB}.SECONDSPECTRUM_F53A_GAME_PLAYER 
        WHERE MATCH_SSIID = '{valgt_match_ssiid}'
          AND TEAM_SSIID = '{target_ssiid}'
        ORDER BY 1
    """)
    
    # Fallback hvis ID ikke matcher
    if df_pl is None or df_pl.empty:
        df_pl = conn.query(f"SELECT DISTINCT PLAYER_NAME FROM {DB}.SECONDSPECTRUM_F53A_GAME_PLAYER WHERE MATCH_SSIID = '{valgt_match_ssiid}' ORDER BY 1")

    valgt_spiller = c3.selectbox("Vælg Spiller", df_pl['PLAYER_NAME'].tolist(), label_visibility="collapsed")

    # --- 4. HENT DATA FRA BEGGE HOVEDTABELLER ---
    # F53A til procenter og speed
    p_f53a = conn.query(f"SELECT * FROM {DB}.SECONDSPECTRUM_F53A_GAME_PLAYER WHERE MATCH_SSIID = '{valgt_match_ssiid}' AND PLAYER_NAME = '{valgt_spiller.replace("'", "''")}'").iloc[0]
    
    # SUMMARY til baner (HSR_DISTANCE_TIP/OTIP)
    p_sum = conn.query(f"SELECT * FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS WHERE MATCH_SSIID = '{valgt_match_ssiid}' AND PLAYER_NAME = '{valgt_spiller.replace("'", "''")}'").iloc[0]

    # --- 5. DASHBOARD ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Distance", f"{round(p_f53a['DISTANCE']/1000, 2)} km")
    m2.metric("Speed Runs", int(p_f53a['SPEEDRUNS']))
    m3.metric("Top Speed", f"{round(p_f53a['TOP_SPEED'], 1)} km/h")
    # Vi henter minutter fra summary tabellen hvis muligt
    mins = p_sum.get('MINUTES', '0').split(':')[0] if isinstance(p_sum.get('MINUTES'), str) else '0'
    m4.metric("Minutter", f"{mins}'")

    tabs = st.tabs(["Fase-overblik", "Intensitets Profil", "Minut Splits", "Sæson Trend"])

    with tabs[0]:
        col_a, col_b = st.columns(2)
        # Bruger data fra SUMMARY_PLAYERS til banerne
        col_a.pyplot(draw_phase_pitch(p_sum.get('HSR_DISTANCE_TIP', 0), "Angreb (TIP)", "#2ecc71"))
        col_b.pyplot(draw_phase_pitch(p_sum.get('HSR_DISTANCE_OTIP', 0), "Forsvar (OTIP)", "#e74c3c"))

    with tabs[1]:
        z_data = {
            'Sprint': p_f53a['PERCENTDISTANCEHIGHSPEEDSPRINTING'],
            'HSR': p_f53a['PERCENTDISTANCEHIGHSPEEDRUNNING'],
            'LSR': p_f53a['PERCENTDISTANCELOWSPEEDRUNNING'],
            'Jogging': p_f53a['PERCENTDISTANCEJOGGING'],
            'Gående': p_f53a['PERCENTDISTANCEWALKING']
        }
        fig = go.Figure(go.Bar(x=list(z_data.values()), y=list(z_data.keys()), orientation='h', marker_color='#cc0000'))
        fig.update_layout(height=350, margin=dict(t=20, b=20), xaxis=dict(ticksuffix="%"), yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

    with tabs[2]:
        df_ms = conn.query(f"""
            SELECT MINUTE_SPLIT, UPPER(PHYSICAL_METRIC_TYPE) as METRIC, SUM(PHYSICAL_METRIC_VALUE) as VAL 
            FROM {DB}.SECONDSPECTRUM_PHYSICAL_SPLITS_PLAYERS 
            WHERE MATCH_SSIID = '{valgt_match_ssiid}' AND PLAYER_NAME = '{valgt_spiller.replace("'", "''")}'
            GROUP BY 1, 2 ORDER BY 1 ASC
        """)
        if not df_ms.empty:
            sel_m = st.selectbox("Vælg metrik", df_ms['METRIC'].unique())
            d_curr = df_ms[df_ms['METRIC'] == sel_m]
            fig_line = go.Figure(go.Scatter(x=d_curr['MINUTE_SPLIT'], y=d_curr['VAL'], mode='lines+markers', line=dict(color='#cc0000')))
            fig_line.update_layout(height=350, xaxis_title="Minut", yaxis_title="Meter")
            st.plotly_chart(fig_line, use_container_width=True)

    with tabs[3]:
        df_trend = conn.query(f"""
            SELECT MATCH_DATE, DISTANCE FROM {DB}.SECONDSPECTRUM_F53A_GAME_PLAYER
            WHERE PLAYER_NAME = '{valgt_spiller.replace("'", "''")}' AND SEASONLABEL = '2025/2026'
            ORDER BY MATCH_DATE ASC
        """)
        if not df_trend.empty:
            st.line_chart(df_trend.set_index('MATCH_DATE')['DISTANCE'])

if __name__ == "__main__":
    vis_side()
