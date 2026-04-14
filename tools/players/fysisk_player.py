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
    """Henter fysisk overblik med robust navne-matching for at håndtere 'Kiel', 'Lien' og 'å/a'"""
    clean_id = str(player_opta_uuid).lower().replace('p', '').strip()
    
    # Split navn for at finde fornavn og efternavn (ignorerer mellemnavne)
    navne_dele = player_name.split(' ')
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
            COALESCE(f.PERCENTDISTANCESTANDING, 0) as STANDING_PCT, 
            COALESCE(f.PERCENTDISTANCEWALKING, 0) as WALKING_PCT,
            COALESCE(f.PERCENTDISTANCEJOGGING, 0) as JOGGING_PCT, 
            COALESCE(f.PERCENTDISTANCELOWSPEEDRUNNING, 0) as LSR_PCT,
            COALESCE(f.PERCENTDISTANCEHIGHSPEEDRUNNING, 0) as HSR_PCT, 
            COALESCE(f.PERCENTDISTANCEHIGHSPEEDSPRINTING, 0) as SPRINT_PCT,
            s.MATCH_SSIID
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS s
        JOIN {DB}.SECONDSPECTRUM_GAME_METADATA m ON s.MATCH_SSIID = m.MATCH_SSIID
        LEFT JOIN {DB}.SECONDSPECTRUM_F53A_GAME_PLAYER f 
            ON s.MATCH_SSIID = f.MATCH_SSIID 
            AND (f.PLAYER_NAME ILIKE '%{f_name}%' AND f.PLAYER_NAME ILIKE '%{l_name}%')
        WHERE (s."optaId" = '{clean_id}' OR (s.PLAYER_NAME ILIKE '%{f_name}%' AND s.PLAYER_NAME ILIKE '%{l_name}%'))
          AND (m.HOME_SSIID = '{target_team_ssiid}' OR m.AWAY_SSIID = '{target_team_ssiid}')
          AND s.MATCH_DATE >= '2025-07-01'
        ORDER BY s.MATCH_DATE DESC
    """
    return _conn.query(sql)

@st.cache_data(ttl=600)
def get_minute_splits(match_ssiid, player_name, _conn):
    """Henter minut-splits med robust matching og summering af perioder"""
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
          AND UPPER(PHYSICAL_METRIC_TYPE) IN ('TOTAL DISTANCE', 'HIGH SPEED RUNNING DISTANCE')
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
        
        st.write(f"### Seneste Kamp: {latest['MATCH_TEAMS']} ({latest['MATCH_DATE']})")
        
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
            st.write("### Distancefordeling pr. hastighedszone (%)")
            z_labels = ['Stående', 'Gående', 'Jogging', 'LSR', 'HSR', 'Sprint']
            z_vals = [latest['STANDING_PCT'], latest['WALKING_PCT'], latest['JOGGING_PCT'], latest['LSR_PCT'], latest['HSR_PCT'], latest['SPRINT_PCT']]
            
            fig = go.Figure(go.Bar(
                x=z_vals, 
                y=z_labels, 
                orientation='h', 
                marker_color='#cc0000', 
                text=[f"{round(v,1)}%" for v in z_vals], 
                textposition='outside'
            ))
            fig.update_layout(xaxis=dict(range=[0, max(z_vals) + 10] if any(z_vals) else [0, 100]), height=400)
            st.plotly_chart(fig, use_container_width=True)

        with tabs[2]:
            st.write("### Intensitet minut-for-minut (HSR)")
            df_splits = get_minute_splits(latest['MATCH_SSIID'], valgt_spiller, conn)
            
            if not df_splits.empty:
                df_hsr = df_splits[df_splits['METRIC_TYPE'] == 'HIGH SPEED RUNNING DISTANCE']
                
                if not df_hsr.empty:
                    fig_s = go.Figure(go.Scatter(
                        x=df_hsr['MINUTE_SPLIT'], 
                        y=df_hsr['VALUE'], 
                        fill='tozeroy', 
                        line_color='#cc0000',
                        mode='lines+markers',
                        name="HSR Meter"
                    ))
                    fig_s.update_layout(
                        xaxis=dict(tickmode='linear', tick0=0, dtick=5),
                        xaxis_title="Minut",
                        yaxis_title="Meter pr. split",
                        hovermode="x unified"
                    )
                    st.plotly_chart(fig_s, use_container_width=True)
                else:
                    st.info("Ingen HSR-data fundet i splits.")
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
