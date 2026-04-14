import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from mplsoccer import Pitch
import matplotlib.pyplot as plt
from matplotlib import patheffects
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '328', '329', '43319', '331', '1305')"

@st.cache_data(ttl=600)
def get_extended_player_data(player_name, player_opta_uuid, target_team_ssiid, _conn):
    """Henter fysisk data med forbedret navne-matching"""
    clean_id = str(player_opta_uuid).lower().replace('p', '').strip()
    
    navne_dele = player_name.strip().split(' ')
    f_name = navne_dele[0]
    l_name = navne_dele[-1].replace('å', '_').replace('ø', '_').replace('æ', '_')

    sql = f"""
        SELECT 
            s.MATCH_DATE, s.MATCH_TEAMS, s.PLAYER_NAME,
            CASE 
                WHEN s.MINUTES LIKE '%:%' THEN 
                    TRY_TO_NUMBER(SPLIT_PART(s.MINUTES, ':', 1)) + (TRY_TO_NUMBER(SPLIT_PART(s.MINUTES, ':', 2)) / 60)
                ELSE TRY_TO_NUMBER(s.MINUTES) 
            END AS MINUTES_DECIMAL,
            s.DISTANCE, s."HIGH SPEED RUNNING" as HSR, s.SPRINTING, s.TOP_SPEED,
            s.HSR_DISTANCE_TIP as HSR_TIP, s.HSR_DISTANCE_OTIP as HSR_OTIP,
            s.MATCH_SSIID,
            s."optaId"
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS s
        JOIN {DB}.SECONDSPECTRUM_GAME_METADATA m ON s.MATCH_SSIID = m.MATCH_SSIID
        WHERE (s."optaId" = '{clean_id}' OR (s.PLAYER_NAME ILIKE '%{f_name}%' AND s.PLAYER_NAME ILIKE '%{l_name}%'))
          AND (m.HOME_SSIID = '{target_team_ssiid}' OR m.AWAY_SSIID = '{target_team_ssiid}')
          AND s.MATCH_DATE >= '2025-07-01'
        ORDER BY s.MATCH_DATE DESC
    """
    return _conn.query(sql)

@st.cache_data(ttl=600)
def get_f53a_percentages(match_ssiid, player_name, _conn):
    """Henter procenter med de præcise kolonnenavne fra din tabel"""
    navne_dele = player_name.strip().split(' ')
    f_name = navne_dele[0]
    l_name = navne_dele[-1].replace('å', '_').replace('ø', '_').replace('æ', '_')
    
    sql = f"""
        SELECT 
            PERCENTDISTANCESTANDING as STANDING_PCT, 
            PERCENTDISTANCEWALKING as WALKING_PCT,
            PERCENTDISTANCEJOGGING as JOGGING_PCT, 
            PERCENTDISTANCELOWSPEEDRUNNING as LSR_PCT,
            PERCENTDISTANCEHIGHSPEEDRUNNING as HSR_PCT, 
            PERCENTDISTANCEHIGHSPEEDSPRINTING as SPRINT_PCT
        FROM {DB}.SECONDSPECTRUM_F53A_GAME_PLAYER
        WHERE MATCH_SSIID = '{match_ssiid}' 
          AND (PLAYER_NAME ILIKE '%{f_name}%' AND PLAYER_NAME ILIKE '%{l_name}%')
        LIMIT 1
    """
    return _conn.query(sql)

@st.cache_data(ttl=600)
def get_minute_splits(match_ssiid, player_name, _conn):
    """Henter ALLE tilgængelige minut-splits for spilleren"""
    navne_dele = player_name.split(' ')
    f_name = navne_dele[0]
    l_name = navne_dele[-1].replace('å', '_').replace('ø', '_').replace('æ', '_')
    
    sql = f"""
        SELECT 
            MINUTE_SPLIT, 
            UPPER(PHYSICAL_METRIC_TYPE) as METRIC_TYPE, 
            SUM(PHYSICAL_METRIC_VALUE) as VALUE
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SPLITS_PLAYERS
        WHERE MATCH_SSIID = '{match_ssiid}' 
          AND (PLAYER_NAME ILIKE '%{f_name}%' AND PLAYER_NAME ILIKE '%{l_name}%')
        GROUP BY MINUTE_SPLIT, PHYSICAL_METRIC_TYPE
        ORDER BY MINUTE_SPLIT ASC
    """
    return _conn.query(sql)

def draw_phase_pitch(val, title, color):
    pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD', line_zorder=2)
    fig, ax = pitch.draw(figsize=(8, 6))
    fig.patch.set_alpha(0)
    display_val = int(val) if pd.notnull(val) else 0
    ax.scatter(50, 50, s=3000, color=color, alpha=0.1, zorder=1)
    txt = ax.text(50, 50, f"{display_val}m", color=color, fontsize=45, fontweight='bold', ha='center', va='center', zorder=3)
    txt.set_path_effects([patheffects.withStroke(linewidth=3, foreground='white')])
    ax.set_title(title, fontsize=16, pad=15, fontweight='bold', color='#333333')
    return fig

def vis_side():
    st.markdown("""<style>
        [data-testid="stMetricValue"] { font-size: 24px !important; font-weight: bold !important; color: #cc0000; }
        .stTabs [data-baseweb="tab"] { font-weight: bold; }
        div.block-container { padding-top: 1rem; }
    </style>""", unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn: return

    # --- DROP-DOWNS ---
    sql_teams = f"SELECT DISTINCT CONTESTANTHOME_NAME as TEAM_NAME, CONTESTANTHOME_OPTAUUID as TEAM_UUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS} ORDER BY TEAM_NAME"
    df_teams_raw = conn.query(sql_teams)
    
    c1, c2 = st.columns(2)
    valgt_hold = c1.selectbox("Vælg Hold", df_teams_raw['TEAM_NAME'].unique())
    target_ssiid = TEAMS.get(valgt_hold, {}).get('ssid')
    valgt_uuid_hold = df_teams_raw[df_teams_raw['TEAM_NAME'] == valgt_hold]['TEAM_UUID'].iloc[0]

    sql_spillere = f"SELECT DISTINCT TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as NAVN, e.PLAYER_OPTAUUID FROM {DB}.OPTA_EVENTS e JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid_hold}' AND e.EVENT_TIMESTAMP >= '2025-07-01' ORDER BY NAVN"
    df_pl = conn.query(sql_spillere)
    valgt_spiller = c2.selectbox("Vælg Spiller", df_pl['NAVN'].tolist())
    valgt_player_uuid = df_pl[df_pl['NAVN'] == valgt_spiller]['PLAYER_OPTAUUID'].iloc[0]

    # --- DATA ---
    df = get_extended_player_data(valgt_spiller, valgt_player_uuid, target_ssiid, conn)

    if df is not None and not df.empty:
        df = df.fillna(0)
        latest = df.iloc[0]
        
        st.caption(f"Seneste Kamp: {latest['MATCH_TEAMS']} ({latest['MATCH_DATE']})")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Distance", f"{round(latest['DISTANCE']/1000, 2)} km")
        m2.metric("HSR (>19.8 km/h)", f"{int(latest['HSR'])} m")
        m3.metric("Top Speed", f"{round(latest['TOP_SPEED'], 1)} km/h")
        m4.metric("Spilletid", f"{int(latest['MINUTES_DECIMAL'])} min")

        tabs = st.tabs(["Fase-overblik", "Intensitets Profil", "Minut Splits", "Sæson Trend"])

        with tabs[0]:
            col_a, col_b = st.columns(2)
            col_a.pyplot(draw_phase_pitch(latest['HSR_TIP'], "Angreb (TIP)", "#2ecc71"))
            col_b.pyplot(draw_phase_pitch(latest['HSR_OTIP'], "Forsvar (OTIP)", "#e74c3c"))

        with tabs[1]:
            st.caption("Distancefordeling pr. hastighedszone (%)")
            df_pct = get_f53a_percentages(latest['MATCH_SSIID'], valgt_spiller, conn)
            
            if df_pct is not None and not df_pct.empty:
                pcts = df_pct.iloc[0]
                z_labels = ['Stående', 'Gående', 'Jogging', 'LSR', 'HSR', 'Sprint']
                z_vals = [
                    float(pcts['STANDING_PCT']), float(pcts['WALKING_PCT']), 
                    float(pcts['JOGGING_PCT']), float(pcts['LSR_PCT']), 
                    float(pcts['HSR_PCT']), float(pcts['SPRINT_PCT'])
                ]
                
                fig = go.Figure(go.Bar(
                    x=z_vals, 
                    y=z_labels, 
                    orientation='h', 
                    marker_color='#cc0000', 
                    text=[f"{round(v,1)}%" for v in z_vals], 
                    textposition='outside'
                ))
                
                max_v = max(z_vals) if any(z_vals) else 100
                fig.update_layout(
                    xaxis=dict(range=[0, max_v + 15]), 
                    height=400,
                    margin=dict(l=20, r=20, t=20, b=20)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"Ingen hastighedszone-data fundet for {valgt_spiller} i denne kamp.")

        with tabs[2]:
            st.caption("Minut-for-minut intensitet")
            df_splits = get_minute_splits(latest['MATCH_SSIID'], valgt_spiller, conn)
            
            if not df_splits.empty:
                metrics = df_splits['METRIC_TYPE'].unique().tolist()
                tab_titles = [m.replace(' DISTANCE', '').title() for m in metrics]
                sub_tabs = st.tabs(tab_titles)
                
                for i, metric in enumerate(metrics):
                    with sub_tabs[i]:
                        df_plot = df_splits[df_splits['METRIC_TYPE'] == metric]
                        if not df_plot.empty:
                            fig_s = go.Figure()
                            fig_s.add_trace(go.Scatter(
                                x=df_plot['MINUTE_SPLIT'], 
                                y=df_plot['VALUE'], 
                                fill='tozeroy', 
                                line=dict(color='#cc0000', width=3),
                                mode='lines+markers',
                                name=metric
                            ))
                            fig_s.update_layout(
                                plot_bgcolor="white", height=400,
                                margin=dict(t=20, b=40, l=10, r=10),
                                xaxis=dict(title="Minut", tickmode='linear', tick0=0, dtick=5, showgrid=False),
                                yaxis=dict(title="Meter pr. split", showgrid=True, gridcolor='#f0f0f0'),
                                hovermode="x unified"
                            )
                            st.plotly_chart(fig_s, use_container_width=True, config={'displayModeBar': False})
            else:
                st.info(f"Ingen minut-splits fundet for {valgt_spiller}.")

        with tabs[3]:
            df_trend = df.sort_values('MATCH_DATE')
            fig_t = go.Figure(go.Scatter(x=df_trend['MATCH_DATE'], y=df_trend['HSR'], line=dict(color='#cc0000', width=3), mode='lines+markers'))
            fig_t.update_layout(xaxis_title="Dato", yaxis_title="HSR Distance (m)")
            st.plotly_chart(fig_t, use_container_width=True)
    else:
        st.warning(f"Ingen kampdata fundet for {valgt_spiller} hos {valgt_hold}.")

if __name__ == "__main__":
    vis_side()
