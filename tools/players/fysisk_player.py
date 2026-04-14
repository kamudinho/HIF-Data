import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from mplsoccer import Pitch
from matplotlib import patheffects
from data.data_load import _get_snowflake_conn 
from data.utils.team_mapping import TEAMS

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
# Sæsonstart 2025/2026
SEASON_START = "2025-07-01"
LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '328', '329', '43319', '331', '1305')"

@st.cache_resource
def get_cached_conn():
    return _get_snowflake_conn()

def query_db(sql):
    conn = get_cached_conn()
    return conn.query(sql)

@st.cache_data(ttl=600)
def get_player_full_package(player_name, team_ssiid):
    dele = player_name.strip().split(' ')
    l_name = dele[-1].replace('å', '_').replace('ø', '_').replace('æ', '_')
    sql = f"""
        SELECT s.*, m.HOME_SSIID, m.AWAY_SSIID
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS s
        JOIN {DB}.SECONDSPECTRUM_GAME_METADATA m ON s.MATCH_SSIID = m.MATCH_SSIID
        WHERE s.PLAYER_NAME ILIKE '%{l_name}%'
          AND (m.HOME_SSIID = '{team_ssiid}' OR m.AWAY_SSIID = '{team_ssiid}')
          AND s.MATCH_DATE >= '{SEASON_START}'
        ORDER BY s.MATCH_DATE DESC
    """
    return query_db(sql)

def draw_pitch_stat(val, title, color):
    pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
    fig, ax = pitch.draw(figsize=(6, 4))
    ax.scatter(50, 50, s=2000, color=color, alpha=0.1)
    txt = ax.text(50, 50, f"{int(val)}m", color=color, fontsize=35, fontweight='bold', ha='center', va='center')
    txt.set_path_effects([patheffects.withStroke(linewidth=2, foreground='white')])
    ax.set_title(title, fontsize=12, fontweight='bold')
    return fig

def vis_side():
    st.markdown("""
        <style>
        .stTabs [data-baseweb="tab-list"] { gap: 8px; border-bottom: 1px solid #eee; background-color: white; }
        .stTabs [data-baseweb="tab"] { 
            height: 45px; background-color: white !important; border: none !important; 
            color: #666 !important; font-weight: 400 !important; padding: 0px 20px !important;
        }
        .stTabs [aria-selected="true"] { 
            color: #cc0000 !important; border-bottom: 3px solid #cc0000 !important; font-weight: 700 !important;
        }
        div[data-testid="stMetricValue"] { font-size: 24px !important; font-weight: 700; }
        </style>
    """, unsafe_allow_html=True)

    # 1. Hent Hold (Kun dem der er aktive i de valgte ligaer)
    df_teams = query_db(f"SELECT DISTINCT CONTESTANTHOME_NAME as NAME, CONTESTANTHOME_OPTAUUID as UUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS} ORDER BY 1")
    
    col1, col2 = st.columns(2)
    v_hold = col1.selectbox("Vælg Hold", df_teams['NAME'].unique(), label_visibility="collapsed")
    h_uuid = df_teams[df_teams['NAME'] == v_hold]['UUID'].iloc[0]
    h_ssid = TEAMS.get(v_hold, {}).get('ssid')

    # 2. Hent Spillere (RETTET: Kun spillere med events i den aktuelle sæson)
    sql_spillere = f"""
        SELECT DISTINCT TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as NAVN, p.PLAYER_OPTAUUID 
        FROM {DB}.OPTA_PLAYERS p
        JOIN {DB}.OPTA_EVENTS e ON p.PLAYER_OPTAUUID = e.PLAYER_OPTAUUID
        WHERE e.EVENT_CONTESTANT_OPTAUUID = '{h_uuid}'
          AND e.EVENT_TIMESTAMP >= '{SEASON_START}'
        ORDER BY 1
    """
    df_pl = query_db(sql_spillere)
    v_spiller = col2.selectbox("Vælg Spiller", df_pl['NAVN'].tolist(), label_visibility="collapsed")
    p_uuid = df_pl[df_pl['NAVN'] == v_spiller]['PLAYER_OPTAUUID'].iloc[0]

    df = get_player_full_package(v_spiller, h_ssid)

    if not df.empty:
        latest = df.iloc[0]
        st.write(f"**{latest['MATCH_TEAMS']}** | {latest['MATCH_DATE']}")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Distance", f"{round(latest['DISTANCE']/1000, 2)} km")
        m2.metric("HSR", f"{int(latest['HIGH SPEED RUNNING'])} m")
        m3.metric("Top Speed", f"{round(latest['TOP_SPEED'], 1)} km/h")
        mins = str(latest['MINUTES']).split(':')[0] if ':' in str(latest['MINUTES']) else latest['MINUTES']
        m4.metric("Minutter", f"{int(mins)}")

        t_fase, t_int, t_split, t_trend = st.tabs(["Fase-overblik", "Intensitets Profil", "Minut Splits", "Sæson Trend"])

        with t_fase:
            c_a, c_b = st.columns(2)
            c_a.pyplot(draw_pitch_stat(latest['HSR_DISTANCE_TIP'], "Angreb (TIP)", "#2ecc71"))
            c_b.pyplot(draw_pitch_stat(latest['HSR_DISTANCE_OTIP'], "Forsvar (OTIP)", "#e74c3c"))

        with t_int:
            df_p = query_db(f"SELECT * FROM {DB}.SECONDSPECTRUM_F53A_GAME_PLAYER WHERE MATCH_SSIID = '{latest['MATCH_SSIID']}' AND PLAYER_NAME ILIKE '%{v_spiller.split(' ')[-1]}%' LIMIT 1")
            if not df_p.empty:
                r = df_p.iloc[0]
                z_labels = ['Stående', 'Gående', 'Jogging', 'LSR', 'HSR', 'Sprint']
                z_vals = [r['PERCENTDISTANCESTANDING'], r['PERCENTDISTANCEWALKING'], r['PERCENTDISTANCEJOGGING'], r['PERCENTDISTANCELOWSPEEDRUNNING'], r['PERCENTDISTANCEHIGHSPEEDRUNNING'], r['PERCENTDISTANCEHIGHSPEEDSPRINTING']]
                fig = go.Figure(go.Bar(x=z_vals, y=z_labels, orientation='h', marker_color='#cc0000'))
                fig.update_layout(plot_bgcolor="white", height=300, margin=dict(l=0, r=0, t=0, b=0), xaxis=dict(showgrid=False))
                st.plotly_chart(fig, use_container_width=True, key=f"int_profile_{p_uuid}_{latest['MATCH_SSIID']}")

        with t_split:
            df_s = query_db(f"SELECT MINUTE_SPLIT, UPPER(PHYSICAL_METRIC_TYPE) as METRIC, SUM(PHYSICAL_METRIC_VALUE) as VAL FROM {DB}.SECONDSPECTRUM_PHYSICAL_SPLITS_PLAYERS WHERE MATCH_SSIID = '{latest['MATCH_SSIID']}' AND PLAYER_NAME ILIKE '%{v_spiller.split(' ')[-1]}%' GROUP BY 1, 2 ORDER BY 1 ASC")
            if not df_s.empty:
                metrics = df_s['METRIC'].unique().tolist()
                s_tabs = st.tabs([m.replace(' DISTANCE', '').title() for m in metrics])
                for i, m in enumerate(metrics):
                    with s_tabs[i]:
                        d_m = df_s[df_s['METRIC'] == m]
                        fig_s = go.Figure(go.Scatter(x=d_m['MINUTE_SPLIT'], y=d_m['VAL'], fill='tozeroy', line=dict(color='#cc0000', width=2)))
                        fig_s.update_layout(plot_bgcolor="white", height=300, margin=dict(t=20), xaxis=dict(dtick=10, showgrid=False))
                        st.plotly_chart(fig_s, use_container_width=True, key=f"split_{m}_{p_uuid}_{latest['MATCH_SSIID']}")

        with t_trend:
            df_trend = df.sort_values('MATCH_DATE')
            fig_t = go.Figure(go.Scatter(x=df_trend['MATCH_DATE'], y=df_trend['HIGH SPEED RUNNING'], mode='lines+markers', line=dict(color='#cc0000')))
            fig_t.update_layout(plot_bgcolor="white", height=350, xaxis=dict(showgrid=False))
            st.plotly_chart(fig_t, use_container_width=True, key=f"trend_{p_uuid}")
    else:
        st.warning("Ingen fysisk data fundet for spilleren i denne sæson.")

if __name__ == "__main__":
    vis_side()
