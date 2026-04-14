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
    clean_id = str(player_opta_uuid).lower().replace('p', '').strip()
    # Vi bruger en mere simpel navne-søgning for at undgå fejl med specialtegn
    first_part = player_name.split(' ')[0]
    
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
            ON s.MATCH_SSIID = f.MATCH_SSIID AND s.PLAYER_NAME = f.PLAYER_NAME
        WHERE (s.PLAYER_NAME ILIKE '%{first_part}%' OR s."optaId" = '{clean_id}')
          AND (m.HOME_SSIID = '{target_team_ssiid}' OR m.AWAY_SSIID = '{target_team_ssiid}')
          AND s.MATCH_DATE >= '2025-07-01'
        ORDER BY s.MATCH_DATE DESC
    """
    return _conn.query(sql)

def draw_phase_pitch(val, title, color):
    pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD', line_zorder=2)
    fig, ax = pitch.draw(figsize=(8, 6))
    fig.patch.set_alpha(0)
    
    # Sikrer at vi har et tal
    display_val = int(val) if pd.notnull(val) else 0
    
    ax.scatter(50, 50, s=3000, color=color, alpha=0.1, zorder=1)
    txt = ax.text(50, 50, f"{display_val}m", color=color, fontsize=45, 
                  fontweight='bold', ha='center', va='center', zorder=3)
    txt.set_path_effects([patheffects.withStroke(linewidth=3, foreground='white')])
    ax.set_title(title, fontsize=16, pad=15, fontweight='bold')
    return fig

def vis_side():
    st.markdown("<style>div.block-container { padding-top: 1rem; }</style>", unsafe_allow_html=True)
    conn = _get_snowflake_conn()
    if not conn: return

    # --- 1. HOLDVALG ---
    sql_teams = f"SELECT DISTINCT CONTESTANTHOME_NAME as TEAM_NAME, CONTESTANTHOME_OPTAUUID as TEAM_UUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS} ORDER BY TEAM_NAME"
    df_teams_raw = conn.query(sql_teams)
    
    col1, col2 = st.columns(2)
    valgt_hold = col1.selectbox("Vælg Hold", df_teams_raw['TEAM_NAME'].unique())
    
    # Vigtigt: Hent SSID fra din mapping fil
    target_ssiid = TEAMS.get(valgt_hold, {}).get('ssid')
    valgt_uuid_hold = df_teams_raw[df_teams_raw['TEAM_NAME'] == valgt_hold]['TEAM_UUID'].iloc[0]

    # --- 2. SPILLERVALG ---
    sql_spillere = f"SELECT DISTINCT TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as NAVN, e.PLAYER_OPTAUUID FROM {DB}.OPTA_EVENTS e JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid_hold}' AND e.EVENT_TIMESTAMP >= '2025-07-01' ORDER BY NAVN"
    df_pl = conn.query(sql_spillere)
    valgt_spiller = col2.selectbox("Vælg Spiller", df_pl['NAVN'].tolist())
    valgt_player_uuid = df_pl[df_pl['NAVN'] == valgt_spiller]['PLAYER_OPTAUUID'].iloc[0]

    # --- 3. DATA ---
    df = get_extended_player_data(valgt_spiller, valgt_player_uuid, target_ssiid, conn)

    if df is not None and not df.empty:
        df = df.fillna(0) # Fjerner alle resterende NaN
        latest = df.iloc[0]
        
        st.subheader(f"{latest['PLAYER_NAME']} | {latest['MATCH_TEAMS']} ({latest['MATCH_DATE']})")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Distance", f"{round(latest['DISTANCE']/1000, 2)} km")
        m2.metric("HSR", f"{int(latest['HSR'])} m")
        m3.metric("Top Fart", f"{round(latest['TOP_SPEED'], 1)} km/h")
        m4.metric("Minutter", f"{int(latest['MINUTES_DECIMAL'])}")

        t1, t2 = st.tabs(["Fase Analyse", "Intensitet (%)"])
        
        with t1:
            c1, c2 = st.columns(2)
            c1.pyplot(draw_phase_pitch(latest['HSR_TIP'], "Angreb (TIP)", "#2ecc71"))
            c2.pyplot(draw_phase_pitch(latest['HSR_OTIP'], "Forsvar (OTIP)", "#e74c3c"))
            
        with t2:
            z_labels = ['Stående', 'Gående', 'Jogging', 'LSR', 'HSR', 'Sprint']
            z_vals = [latest['STANDING_PCT'], latest['WALKING_PCT'], latest['JOGGING_PCT'], latest['LSR_PCT'], latest['HSR_PCT'], latest['SPRINT_PCT']]
            
            fig = go.Figure(go.Bar(x=z_vals, y=z_labels, orientation='h', marker_color='#cc0000', text=[f"{v}%" for v in z_vals], textposition='outside'))
            fig.update_layout(xaxis=dict(range=[0, max(z_vals)+10]), height=400, margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(f"Ingen kampdata fundet for {valgt_spiller} hos {valgt_hold}.")

if __name__ == "__main__":
    vis_side()
