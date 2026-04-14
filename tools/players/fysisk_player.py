import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from mplsoccer import Pitch
from matplotlib import patheffects
from data.utils.team_mapping import TEAMS

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '328', '329', '43319', '331', '1305')"

# --- DATA INDLÆSNING (OPTIMERET) ---
conn = st.connection("snowflake")

@st.cache_data(ttl=600)
def get_player_data(player_name, player_uuid, team_ssiid):
    clean_id = str(player_uuid).lower().replace('p', '').strip()
    dele = player_name.strip().split(' ')
    f_name, l_name = dele[0], dele[-1].replace('å', '_').replace('ø', '_').replace('æ', '_')

    sql = f"""
        SELECT 
            s.MATCH_DATE, s.MATCH_TEAMS, s.PLAYER_NAME, s.MATCH_SSIID,
            TRY_TO_NUMBER(SPLIT_PART(s.MINUTES, ':', 1)) as MINS,
            s.DISTANCE, s."HIGH SPEED RUNNING" as HSR, s.SPRINTING, s.TOP_SPEED,
            s.HSR_DISTANCE_TIP as HSR_TIP, s.HSR_DISTANCE_OTIP as HSR_OTIP
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS s
        JOIN {DB}.SECONDSPECTRUM_GAME_METADATA m ON s.MATCH_SSIID = m.MATCH_SSIID
        WHERE (s."optaId" = '{clean_id}' OR (s.PLAYER_NAME ILIKE '%{f_name}%' AND s.PLAYER_NAME ILIKE '%{l_name}%'))
          AND (m.HOME_SSIID = '{team_ssiid}' OR m.AWAY_SSIID = '{team_ssiid}')
          AND s.MATCH_DATE >= '2025-07-01'
        ORDER BY s.MATCH_DATE DESC
    """
    return conn.query(sql)

@st.cache_data(ttl=600)
def get_f53a_data(match_ssiid, player_name):
    dele = player_name.strip().split(' ')
    l_name = dele[-1].replace('å', '_').replace('ø', '_').replace('æ', '_')
    return conn.query(f"SELECT * FROM {DB}.SECONDSPECTRUM_F53A_GAME_PLAYER WHERE MATCH_SSIID = '{match_ssiid}' AND PLAYER_NAME ILIKE '%{l_name}%' LIMIT 1")

@st.cache_data(ttl=600)
def get_splits_data(match_ssiid, player_name):
    dele = player_name.strip().split(' ')
    l_name = dele[-1].replace('å', '_').replace('ø', '_').replace('æ', '_')
    return conn.query(f"SELECT MINUTE_SPLIT, UPPER(PHYSICAL_METRIC_TYPE) as METRIC, SUM(PHYSICAL_METRIC_VALUE) as VAL FROM {DB}.SECONDSPECTRUM_PHYSICAL_SPLITS_PLAYERS WHERE MATCH_SSIID = '{match_ssiid}' AND PLAYER_NAME ILIKE '%{l_name}%' GROUP BY 1, 2 ORDER BY 1 ASC")

# --- HJÆLPEFUNKTIONER ---
def draw_pitch_stat(val, title, color):
    pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
    fig, ax = pitch.draw(figsize=(8, 6))
    ax.scatter(50, 50, s=3000, color=color, alpha=0.1)
    txt = ax.text(50, 50, f"{int(val)}m", color=color, fontsize=45, fontweight='bold', ha='center', va='center')
    txt.set_path_effects([patheffects.withStroke(linewidth=3, foreground='white')])
    ax.set_title(title, fontsize=16, fontweight='bold')
    return fig

# --- HOVEDSIDE ---
def vis_side():
    # CSS til at matche dine screenshots (Tabs styling)
    st.markdown("""
        <style>
        .stTabs [data-baseweb="tab-list"] { gap: 24px; border-bottom: 1px solid #f0f0f0; }
        .stTabs [data-baseweb="tab"] { height: 50px; background-color: transparent !important; border: none !important; color: #666 !important; font-weight: 500 !important; }
        .stTabs [aria-selected="true"] { color: #cc0000 !important; border-bottom: 2px solid #cc0000 !important; }
        [data-testid="stMetricValue"] { font-size: 28px !important; color: #333; }
        </style>
    """, unsafe_allow_html=True)

    # Vælgere
    df_teams = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME as NAME, CONTESTANTHOME_OPTAUUID as UUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS} ORDER BY 1")
    
    col1, col2 = st.columns(2)
    v_hold = col1.selectbox("Vælg Hold", df_teams['NAME'].unique())
    h_uuid = df_teams[df_teams['NAME'] == v_hold]['UUID'].iloc[0]
    h_ssid = TEAMS.get(v_hold, {}).get('ssid')

    df_pl = conn.query(f"SELECT DISTINCT TRIM(FIRST_NAME) || ' ' || TRIM(LAST_NAME) as NAVN, PLAYER_OPTAUUID FROM {DB}.OPTA_PLAYERS WHERE PLAYER_OPTAUUID IN (SELECT DISTINCT PLAYER_OPTAUUID FROM {DB}.OPTA_EVENTS WHERE EVENT_CONTESTANT_OPTAUUID = '{h_uuid}') ORDER BY 1")
    v_spiller = col2.selectbox("Vælg Spiller", df_pl['NAVN'].tolist())
    p_uuid = df_pl[df_pl['NAVN'] == v_spiller]['PLAYER_OPTAUUID'].iloc[0]

    # Data Hentning
    df = get_player_data(v_spiller, p_uuid, h_ssid)

    if not df.empty:
        latest = df.iloc[0]
        st.subheader(f"Seneste Kamp: {latest['MATCH_TEAMS']} ({latest['MATCH_DATE']})")
        
        # Metrics række
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Distance", f"{round(latest['DISTANCE']/1000, 2)} km")
        m2.metric("HSR (>19.8 km/h)", f"{int(latest['HSR'])} m")
        m3.metric("Top Speed", f"{round(latest['TOP_SPEED'], 1)} km/h")
        m4.metric("Spilletid", f"{int(latest['MINS'])} min")

        # Hoved Tabs
        t_fase, t_int, t_split, t_trend = st.tabs(["Fase-overblik", "Intensitets Profil", "Minut Splits", "Sæson Trend"])

        with t_fase:
            c_a, c_b = st.columns(2)
            c_a.pyplot(draw_pitch_stat(latest['HSR_TIP'], "Angreb (TIP)", "#2ecc71"))
            c_b.pyplot(draw_pitch_stat(latest['HSR_OTIP'], "Forsvar (OTIP)", "#e74c3c"))

        with t_int:
            df_p = get_f53a_data(latest['MATCH_SSIID'], v_spiller)
            if not df_p.empty:
                row = df_p.iloc[0]
                z_labels = ['Stående', 'Gående', 'Jogging', 'LSR', 'HSR', 'Sprint']
                z_vals = [row['PERCENTDISTANCESTANDING'], row['PERCENTDISTANCEWALKING'], row['PERCENTDISTANCEJOGGING'], 
                          row['PERCENTDISTANCELOWSPEEDRUNNING'], row['PERCENTDISTANCEHIGHSPEEDRUNNING'], row['PERCENTDISTANCEHIGHSPEEDSPRINTING']]
                fig = go.Figure(go.Bar(x=z_vals, y=z_labels, orientation='h', marker_color='#cc0000', text=[f"{round(v,1)}%" for v in z_vals], textposition='outside'))
                fig.update_layout(plot_bgcolor="white", height=350, margin=dict(l=0, r=0, t=0, b=0), xaxis=dict(showticklabels=False, showgrid=False))
                st.plotly_chart(fig, use_container_width=True)

        with t_split:
            df_s = get_splits_data(latest['MATCH_SSIID'], v_spiller)
            if not df_s.empty:
                metrics = df_s['METRIC'].unique().tolist()
                s_tabs = st.tabs([m.replace(' DISTANCE', '').title() for m in metrics])
                for i, m in enumerate(metrics):
                    with s_tabs[i]:
                        d_m = df_s[df_s['METRIC'] == m]
                        fig_s = go.Figure(go.Scatter(x=d_m['MINUTE_SPLIT'], y=d_m['VAL'], fill='tozeroy', line=dict(color='#cc0000', width=3)))
                        fig_s.update_layout(plot_bgcolor="white", height=350, margin=dict(t=20, b=20), xaxis=dict(dtick=5))
                        st.plotly_chart(fig_s, use_container_width=True)

        with t_trend:
            fig_t = go.Figure(go.Scatter(x=df['MATCH_DATE'], y=df['HSR'], mode='lines+markers', line=dict(color='#cc0000')))
            fig_t.update_layout(plot_bgcolor="white", title="HSR Trend over sæsonen")
            st.plotly_chart(fig_t, use_container_width=True)

if __name__ == "__main__":
    vis_side()
