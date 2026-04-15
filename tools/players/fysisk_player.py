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

    # --- 3. VÆLG SPILLER (KUN DIT HOLD) ---
    df_pl = conn.query(f"""
        SELECT DISTINCT PLAYER_NAME 
        FROM {DB}.SECONDSPECTRUM_F53A_GAME_PLAYER 
        WHERE MATCH_SSIID = '{valgt_match_ssiid}'
          AND TEAM_SSIID = '{target_ssiid}'
        ORDER BY 1
    """)
    
    if df_pl is None or df_pl.empty:
        st.warning("Ingen spillere fundet for det valgte hold i denne kamp.")
        return

    valgt_spiller = c3.selectbox("Vælg Spiller", df_pl['PLAYER_NAME'].tolist(), label_visibility="collapsed")

    # --- 4. HENT OG VIS DATA (KUN HVIS SPILLER ER VALGT) ---
    if valgt_spiller:
        spiller_safe = valgt_spiller.replace("'", "''")
        
        # Hent data fra begge tabeller
        df_f53a = conn.query(f"SELECT * FROM {DB}.SECONDSPECTRUM_F53A_GAME_PLAYER WHERE MATCH_SSIID = '{valgt_match_ssiid}' AND PLAYER_NAME = '{spiller_safe}'")
        df_sum = conn.query(f"SELECT * FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS WHERE MATCH_SSIID = '{valgt_match_ssiid}' AND PLAYER_NAME = '{spiller_safe}'")

        if not df_f53a.empty and not df_sum.empty:
            p_f = df_f53a.iloc[0]
            p_s = df_sum.iloc[0]

            # Top Metrics
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Distance", f"{round(p_f['DISTANCE']/1000, 2)} km")
            m2.metric("Speed Runs", int(p_f['SPEEDRUNS']))
            m3.metric("Top Speed", f"{round(p_f['TOP_SPEED'], 1)} km/h")
            mins = p_s.get('MINUTES', '0').split(':')[0] if isinstance(p_s.get('MINUTES'), str) else '0'
            m4.metric("Minutter", f"{mins}'")

            tabs = st.tabs(["Fase-overblik", "Intensitets Profil", "Minut Splits", "Sæson Trend"])

            with tabs[0]:
                col_a, col_b = st.columns(2)
                col_a.pyplot(draw_phase_pitch(p_s.get('HSR_DISTANCE_TIP', 0), "Angreb (TIP)", "#2ecc71"))
                col_b.pyplot(draw_phase_pitch(p_s.get('HSR_DISTANCE_OTIP', 0), "Forsvar (OTIP)", "#e74c3c"))

            with tabs[1]:
                z_data = {
                    'Sprint': p_f['PERCENTDISTANCEHIGHSPEEDSPRINTING'],
                    'HSR': p_f['PERCENTDISTANCEHIGHSPEEDRUNNING'],
                    'LSR': p_f['PERCENTDISTANCELOWSPEEDRUNNING'],
                    'Jogging': p_f['PERCENTDISTANCEJOGGING'],
                    'Gående': p_f['PERCENTDISTANCEWALKING']
                }
                fig = go.Figure(go.Bar(x=list(z_data.values()), y=list(z_data.keys()), orientation='h', marker_color='#cc0000'))
                fig.update_layout(height=350, margin=dict(t=20, b=20), xaxis=dict(ticksuffix="%"), yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig, use_container_width=True)

            with tabs[2]:
                df_ms = conn.query(f"""
                    SELECT MINUTE_SPLIT, UPPER(PHYSICAL_METRIC_TYPE) as METRIC, SUM(PHYSICAL_METRIC_VALUE) as VAL 
                    FROM {DB}.SECONDSPECTRUM_PHYSICAL_SPLITS_PLAYERS 
                    WHERE MATCH_SSIID = '{valgt_match_ssiid}' AND PLAYER_NAME = '{spiller_safe}'
                    GROUP BY 1, 2 ORDER BY 1 ASC
                """)
                if df_ms is not None and not df_ms.empty:
                    sel_m = st.selectbox("Metrik", df_ms['METRIC'].unique())
                    d_curr = df_ms[df_ms['METRIC'] == sel_m]
                    fig_l = go.Figure(go.Scatter(x=d_curr['MINUTE_SPLIT'], y=d_curr['VAL'], mode='lines+markers', line=dict(color='#cc0000')))
                    st.plotly_chart(fig_l, use_container_width=True)

            with tabs[3]:
                df_trend = conn.query(f"""
                    SELECT MATCH_DATE, DISTANCE FROM {DB}.SECONDSPECTRUM_F53A_GAME_PLAYER
                    WHERE PLAYER_NAME = '{spiller_safe}' AND SEASONLABEL = '2025/2026'
                    ORDER BY MATCH_DATE ASC
                """)
                if not df_trend.empty:
                    st.line_chart(df_trend.set_index('MATCH_DATE')['DISTANCE'])
        else:
            st.info("Kunne ikke finde fuldstændig data for denne spiller.")

if __name__ == "__main__":
    vis_side()
