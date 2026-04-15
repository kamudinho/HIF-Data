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
        [data-testid="stMetricValue"] { font-size: 26px !important; font-weight: bold !important; color: #333; }
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
    
    valgt_kamp_label = c2.selectbox("Vælg Kamp", df_matches['SELECT_LABEL'].tolist(), label_visibility="collapsed")
    valgt_match_ssiid = df_matches[df_matches['SELECT_LABEL'] == valgt_kamp_label]['MATCH_SSIID'].iloc[0]

    # --- 3. VÆLG SPILLER (OPDATERET FILTRERING) ---
    # Vi henter spillere der matcher kampen. 
    # Vi prøver først med target_ssiid, og hvis det fejler, bruger vi navnet.
    df_pl = conn.query(f"""
        SELECT DISTINCT PLAYER_NAME 
        FROM {DB}.SECONDSPECTRUM_F53A_GAME_PLAYER 
        WHERE MATCH_SSIID = '{valgt_match_ssiid}'
          AND (TEAM_SSIID = '{target_ssiid}' OR TEAM_NAME ILIKE '%{valgt_hold}%')
        ORDER BY 1
    """)
    
    # Hvis den stadig er tom, så lad os hente ALLE spillere fra kampen 
    # så appen ikke går i stå, og vi kan fejlfinde.
    if df_pl is None or df_pl.empty:
        df_pl = conn.query(f"""
            SELECT DISTINCT PLAYER_NAME 
            FROM {DB}.SECONDSPECTRUM_F53A_GAME_PLAYER 
            WHERE MATCH_SSIID = '{valgt_match_ssiid}'
            ORDER BY 1
        """)
        if not df_pl.empty:
            st.info(f"Viser alle spillere for kampen (Hold-ID match fejlede for {valgt_hold})")

    if df_pl is None or df_pl.empty:
        st.warning(f"Ingen spillere fundet i F53A tabellen for kamp-ID: {valgt_match_ssiid}")
        return

    valgt_spiller = c3.selectbox("Vælg Spiller", df_pl['PLAYER_NAME'].tolist(), label_visibility="collapsed")

    # --- 4. DATA VISUALISERING ---
    # Vi henter data for den valgte spiller
    df_latest = conn.query(f"""
        SELECT *
        FROM {DB}.SECONDSPECTRUM_F53A_GAME_PLAYER 
        WHERE MATCH_SSIID = '{valgt_match_ssiid}' 
          AND PLAYER_NAME = '{valgt_spiller.replace("'", "''")}'
    """)

    if not df_latest.empty:
        latest = df_latest.iloc[0]
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Distance", f"{round(latest['DISTANCE']/1000, 2)} km")
        # Beregner HSR meter ud fra procent hvis nødvendigt, her bruger vi speedruns
        m2.metric("Speed Runs", int(latest['SPEEDRUNS']))
        m3.metric("Top Speed", f"{round(latest['TOP_SPEED'], 1)} km/h")
        m4.metric("Avg Speed", f"{round(latest['AVERAGE_SPEED'], 1)} km/h")
        
        tabs = st.tabs(["Intensitets Profil", "Minut Splits", "Sæson Trend"])

        with tabs[0]:
            # Zone-fordeling baseret på procenterne fra F53A tabellen
            z_map = {
                'Sprint': latest.get('PERCENTDISTANCEHIGHSPEEDSPRINTING', 0),
                'HSR': latest.get('PERCENTDISTANCEHIGHSPEEDRUNNING', 0),
                'LSR': latest.get('PERCENTDISTANCELOWSPEEDRUNNING', 0),
                'Jogging': latest.get('PERCENTDISTANCEJOGGING', 0),
                'Gående': latest.get('PERCENTDISTANCEWALKING', 0),
                'Stående': latest.get('PERCENTDISTANCESTANDING', 0)
            }
            
            fig = go.Figure(go.Bar(
                x=list(z_map.values()), 
                y=list(z_map.keys()), 
                orientation='h', 
                marker_color='#cc0000'
            ))
            fig.update_layout(
                height=350, 
                margin=dict(t=20, b=20), 
                yaxis=dict(autorange="reversed"),
                xaxis=dict(ticksuffix="%")
            )
            st.plotly_chart(fig, use_container_width=True)

        with tabs[1]:
            # Minut splits fra SPLITS tabellen
            df_ms = conn.query(f"""
                SELECT MINUTE_SPLIT, UPPER(PHYSICAL_METRIC_TYPE) as METRIC, SUM(PHYSICAL_METRIC_VALUE) as VAL 
                FROM {DB}.SECONDSPECTRUM_PHYSICAL_SPLITS_PLAYERS 
                WHERE MATCH_SSIID = '{valgt_match_ssiid}' 
                  AND PLAYER_NAME = '{valgt_spiller.replace("'", "''")}'
                GROUP BY 1, 2 ORDER BY 1 ASC
            """)
            
            if not df_ms.empty:
                m_list = df_ms['METRIC'].unique().tolist()
                sel_m = st.selectbox("Vælg metrik", m_list, key="ms_select_box")
                d_curr = df_ms[df_ms['METRIC'] == sel_m]
                fig_s = go.Figure(go.Scatter(x=d_curr['MINUTE_SPLIT'], y=d_curr['VAL'], mode='lines+markers', line=dict(color='#cc0000')))
                fig_s.update_layout(xaxis_title="Minut", yaxis_title="Meter", height=350)
                st.plotly_chart(fig_s, use_container_width=True)

        with tabs[2]:
            # Sæson Trend fra F53A tabellen
            df_trend = conn.query(f"""
                SELECT MATCH_DATE, DISTANCE, TOP_SPEED
                FROM {DB}.SECONDSPECTRUM_F53A_GAME_PLAYER
                WHERE PLAYER_NAME = '{valgt_spiller.replace("'", "''")}'
                  AND SEASONLABEL = '2025/2026'
                ORDER BY MATCH_DATE ASC
            """)
            if not df_trend.empty:
                df_trend['MATCH_DATE'] = pd.to_datetime(df_trend['MATCH_DATE'])
                st.line_chart(df_trend.set_index('MATCH_DATE')['DISTANCE'])
    else:
        st.warning("Ingen fysisk data fundet for denne spiller.")

if __name__ == "__main__":
    vis_side()
