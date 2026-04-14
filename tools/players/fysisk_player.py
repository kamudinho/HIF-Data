import streamlit as st
import pandas as pd
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

def query_db(sql):
    conn = get_cached_conn()
    return conn.query(sql)

@st.cache_data(ttl=600)
def get_player_full_package(player_name, team_ssiid):
    # Vi bruger en mere fleksibel navnesøgning igen for at sikre match
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

def vis_side():
    # CSS fra før (Tabs styling)
    st.markdown("""
        <style>
        .stTabs [data-baseweb="tab-list"] { gap: 8px; border-bottom: 1px solid #eee; background-color: white; }
        .stTabs [data-baseweb="tab"] { height: 45px; background-color: white !important; border: none !important; color: #666 !important; font-weight: 400 !important; padding: 0px 20px !important; }
        .stTabs [aria-selected="true"] { color: #cc0000 !important; border-bottom: 3px solid #cc0000 !important; font-weight: 700 !important; }
        div[data-testid="stMetricValue"] { font-size: 24px !important; font-weight: 700; }
        </style>
    """, unsafe_allow_html=True)

    # 1. Hent Hold
    df_teams = query_db(f"SELECT DISTINCT CONTESTANTHOME_NAME as NAME, CONTESTANTHOME_OPTAUUID as UUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS} ORDER BY 1")
    
    col1, col2 = st.columns(2)
    v_hold = col1.selectbox("Vælg Hold", df_teams['NAME'].unique(), label_visibility="collapsed")
    
    h_uuid = df_teams[df_teams['NAME'] == v_hold]['UUID'].iloc[0]
    h_ssid = TEAMS.get(v_hold, {}).get('ssid')

    # 2. Hent kun spillere fra det valgte hold, der har fysisk data i denne sæson
    # Vi joiner OPTA_PLAYERS med SECONDSPECTRUM for at få de rigtige navne
    sql_spillere = f"""
        SELECT DISTINCT p.FIRST_NAME || ' ' || p.LAST_NAME as NAVN
        FROM {DB}.OPTA_PLAYERS p
        JOIN {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS s ON s.PLAYER_NAME ILIKE '%' || p.LAST_NAME || '%'
        JOIN {DB}.SECONDSPECTRUM_GAME_METADATA m ON s.MATCH_SSIID = m.MATCH_SSIID
        WHERE p.PLAYER_OPTAUUID IN (
            SELECT DISTINCT PLAYER_OPTAUUID FROM {DB}.OPTA_EVENTS WHERE EVENT_CONTESTANT_OPTAUUID = '{h_uuid}'
        )
        AND m.MATCH_DATE >= '{SEASON_START}'
        AND (m.HOME_SSIID = '{h_ssid}' OR m.AWAY_SSIID = '{h_ssid}')
        ORDER BY 1
    """
    df_pl = query_db(sql_spillere)
    
    # Fallback: Hvis den avancerede query fejler, så vis alle fra holdet (som før)
    if df_pl.empty:
        df_pl = query_db(f"SELECT DISTINCT FIRST_NAME || ' ' || LAST_NAME as NAVN FROM {DB}.OPTA_PLAYERS WHERE PLAYER_OPTAUUID IN (SELECT DISTINCT PLAYER_OPTAUUID FROM {DB}.OPTA_EVENTS WHERE EVENT_CONTESTANT_OPTAUUID = '{h_uuid}') ORDER BY 1")

    v_spiller = col2.selectbox("Vælg Spiller", df_pl['NAVN'].tolist(), label_visibility="collapsed")

    # 3. Hent data
    df = get_player_full_package(v_spiller, h_ssid)

    if not df.empty:
        latest = df.iloc[0]
        st.write(f"**{latest['MATCH_TEAMS']}** | {latest['MATCH_DATE']}")
        
        # Metrics række
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Distance", f"{round(latest['DISTANCE']/1000, 2)} km")
        m2.metric("HSR", f"{int(latest['HIGH SPEED RUNNING'])} m")
        m3.metric("Top Speed", f"{round(latest['TOP_SPEED'], 1)} km/h")
        mins = str(latest['MINUTES']).split(':')[0] if ':' in str(latest['MINUTES']) else latest['MINUTES']
        m4.metric("Minutter", f"{int(mins)}")

        # Tabs (Nu med unikke keys for at undgå fejlen fra før)
        t_fase, t_int, t_split, t_trend = st.tabs(["Fase-overblik", "Intensitets Profil", "Minut Splits", "Sæson Trend"])

        with t_fase:
            c_a, c_b = st.columns(2)
            c_a.pyplot(draw_pitch_stat(latest['HSR_DISTANCE_TIP'], "Angreb (TIP)", "#2ecc71"))
            c_b.pyplot(draw_pitch_stat(latest['HSR_DISTANCE_OTIP'], "Forsvar (OTIP)", "#e74c3c"))

        with t_int:
            # Vi bruger l_name logik her for at sikre match i F53A tabellen
            l_name = v_spiller.split(' ')[-1]
            df_p = query_db(f"SELECT * FROM {DB}.SECONDSPECTRUM_F53A_GAME_PLAYER WHERE MATCH_SSIID = '{latest['MATCH_SSIID']}' AND PLAYER_NAME ILIKE '%{l_name}%' LIMIT 1")
            if not df_p.empty:
                r = df_p.iloc[0]
                z_labels = ['Stående', 'Gående', 'Jogging', 'LSR', 'HSR', 'Sprint']
                z_vals = [r['PERCENTDISTANCESTANDING'], r['PERCENTDISTANCEWALKING'], r['PERCENTDISTANCEJOGGING'], r['PERCENTDISTANCELOWSPEEDRUNNING'], r['PERCENTDISTANCEHIGHSPEEDRUNNING'], r['PERCENTDISTANCEHIGHSPEEDSPRINTING']]
                fig = go.Figure(go.Bar(x=z_vals, y=z_labels, orientation='h', marker_color='#cc0000'))
                fig.update_layout(plot_bgcolor="white", height=300, margin=dict(l=0, r=0, t=0, b=0), xaxis=dict(showgrid=False))
                st.plotly_chart(fig, use_container_width=True, key=f"int_{v_spiller}")

        with t_split:
            df_s = query_db(f"SELECT MINUTE_SPLIT, UPPER(PHYSICAL_METRIC_TYPE) as METRIC, SUM(PHYSICAL_METRIC_VALUE) as VAL FROM {DB}.SECONDSPECTRUM_PHYSICAL_SPLITS_PLAYERS WHERE MATCH_SSIID = '{latest['MATCH_SSIID']}' AND PLAYER_NAME ILIKE '%{l_name}%' GROUP BY 1, 2 ORDER BY 1 ASC")
            if not df_s.empty:
                metrics = df_s['METRIC'].unique().tolist()
                s_tabs = st.tabs([m.replace(' DISTANCE', '').title() for m in metrics])
                for i, m in enumerate(metrics):
                    with s_tabs[i]:
                        d_m = df_s[df_s['METRIC'] == m]
                        fig_s = go.Figure(go.Scatter(x=d_m['MINUTE_SPLIT'], y=d_m['VAL'], fill='tozeroy', line=dict(color='#cc0000', width=2)))
                        fig_s.update_layout(plot_bgcolor="white", height=300, margin=dict(t=20), xaxis=dict(dtick=10, showgrid=False))
                        st.plotly_chart(fig_s, use_container_width=True, key=f"split_{m}_{v_spiller}")

        with t_trend:
            df_t = df.sort_values('MATCH_DATE')
            fig_t = go.Figure(go.Scatter(x=df_t['MATCH_DATE'], y=df_t['HIGH SPEED RUNNING'], mode='lines+markers', line=dict(color='#cc0000')))
            fig_t.update_layout(plot_bgcolor="white", height=350, xaxis=dict(showgrid=False))
            st.plotly_chart(fig_t, use_container_width=True, key=f"trend_{v_spiller}")
    else:
        st.info("Vælg en spiller for at se fysisk data.")

if __name__ == "__main__":
    vis_side()
