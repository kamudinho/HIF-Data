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

@st.cache_data(ttl=600)
def get_extended_player_data(player_name, player_opta_uuid, target_team_ssiid):
    conn = get_cached_conn()
    navne_dele = player_name.strip().split(' ')
    f_name = navne_dele[0].replace("'", "''")
    l_name = navne_dele[-1].replace("'", "''")

    sql = f"""
        SELECT 
            s.MATCH_DATE, s.MATCH_TEAMS, s.PLAYER_NAME, s.MATCH_SSIID,
            CASE WHEN s.MINUTES LIKE '%:%' THEN TRY_TO_NUMBER(SPLIT_PART(s.MINUTES, ':', 1)) ELSE TRY_TO_NUMBER(s.MINUTES) END AS MINS,
            s.DISTANCE, s."HIGH SPEED RUNNING" as HSR, s.SPRINTING, s.TOP_SPEED,
            s.HSR_DISTANCE_TIP as HSR_TIP, s.HSR_DISTANCE_OTIP as HSR_OTIP
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS s
        JOIN {DB}.SECONDSPECTRUM_GAME_METADATA m ON s.MATCH_SSIID = m.MATCH_SSIID
        WHERE (s.PLAYER_NAME ILIKE '%{f_name}%' AND s.PLAYER_NAME ILIKE '%{l_name}%')
          AND (m.HOME_SSIID = '{target_team_ssiid}' OR m.AWAY_SSIID = '{target_team_ssiid}')
          AND s.MATCH_DATE >= '{SEASON_START}'
        ORDER BY s.MATCH_DATE DESC
    """
    raw_df = conn.query(sql)
    if raw_df is None or raw_df.empty:
        return pd.DataFrame()
    
    df = raw_df.copy()
    df['MATCH_DATE'] = pd.to_datetime(df['MATCH_DATE'])
    return df

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
    
    # 1. Hent Hold
    df_teams = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME as NAME, CONTESTANTHOME_OPTAUUID as UUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS} ORDER BY 1")
    if df_teams is None or df_teams.empty:
        st.error("Kunne ikke hente hold-data.")
        return

    c1, c2 = st.columns(2)
    valgt_hold = c1.selectbox("Vælg Hold", df_teams['NAME'].unique(), label_visibility="collapsed")
    h_uuid = df_teams[df_teams['NAME'] == valgt_hold]['UUID'].iloc[0]
    target_ssiid = TEAMS.get(valgt_hold, {}).get('ssid')

    # 2. Hent Spillere
    df_pl = conn.query(f"SELECT DISTINCT TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as NAVN, p.PLAYER_OPTAUUID FROM {DB}.OPTA_PLAYERS p JOIN {DB}.OPTA_EVENTS e ON p.PLAYER_OPTAUUID = e.PLAYER_OPTAUUID WHERE e.EVENT_CONTESTANT_OPTAUUID = '{h_uuid}' AND e.EVENT_TIMESTAMP >= '{SEASON_START}' ORDER BY 1")
    if df_pl is None or df_pl.empty:
        st.warning("Ingen spillere fundet for dette hold.")
        return

    valgt_spiller = c2.selectbox("Vælg Spiller", df_pl['NAVN'].tolist(), label_visibility="collapsed")
    p_uuid = df_pl[df_pl['NAVN'] == valgt_spiller]['PLAYER_OPTAUUID'].iloc[0]

    # --- DEFINER NAVNE HER SÅ ALLE TABS KAN SE DEM ---
    navne_dele = valgt_spiller.strip().split(' ')
    f_clean = navne_dele[0].replace("'", "''")
    l_clean = navne_dele[-1].replace("'", "''")

    # 3. Hent Fysisk Data
    df = get_extended_player_data(valgt_spiller, p_uuid, target_ssiid)

    if not df.empty:
        latest = df.iloc[0]
        match_date_str = latest['MATCH_DATE'].strftime('%d/%m/%Y')
        
        st.caption(f"Seneste Kamp: {latest['MATCH_TEAMS']} ({match_date_str})")
        
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
            st.caption("Intensitetsprofil (Beregnet ud fra kampens splits)")
            
            # Vi henter de rå værdier baseret på din liste over PHYSICAL_METRIC_TYPE
            df_calc = conn.query(f"""
                SELECT PHYSICAL_METRIC_TYPE as METRIC, SUM(PHYSICAL_METRIC_VALUE) as TOTAL_VAL
                FROM {DB}.SECONDSPECTRUM_PHYSICAL_SPLITS_PLAYERS
                WHERE MATCH_SSIID = '{latest['MATCH_SSIID']}'
                  AND (PLAYER_NAME ILIKE '%{f_clean}%' AND PLAYER_NAME ILIKE '%{l_clean}%')
                GROUP BY 1
            """)

            if df_calc is not None and not df_calc.empty:
                # Vi laver en dictionary for nem opslag
                m_dict = df_calc.set_index('METRIC')['TOTAL_VAL'].to_dict()
                
                # Vi henter totalen
                total_dist = m_dict.get('Total Distance', 1)
                
                # Her mapper vi dine eksakte navne fra listen
                # Vi bruger .get(nøgle, 0) for at undgå fejl hvis en zone er 0
                z_map = {
                    'Sprint': m_dict.get('Sprinting Distance', 0),
                    'HSR': m_dict.get('High Speed Running Distance', 0),
                    'LSR': m_dict.get('Low Speed Running Distance', 0),
                    'Jogging': m_dict.get('Jogging Distance', 0),
                    'Gående': m_dict.get('Walking Distance', 0)
                }

                # Tjek om der er en rest (hvis f.eks. 'Standing' mangler i listen)
                # Men ud fra din liste bør disse 5 zoner dække det meste.
                
                z_labels = list(z_map.keys())
                # Beregn % af total distance
                z_vals = [(v / total_dist) * 100 for v in z_map.values()]

                fig = go.Figure(go.Bar(
                    x=z_vals,
                    y=z_labels,
                    orientation='h',
                    marker_color='#cc0000',
                    text=[f"{v:.1f}%" if v > 0.05 else "" for v in z_vals], # Skjul tekst hvis v < 0.1%
                    textposition='outside',
                    hovertemplate="%{y}: %{x:.1f}%<extra></extra>"
                ))

                fig.update_layout(
                    plot_bgcolor="white",
                    height=350,
                    margin=dict(l=0, r=60, t=10, b=0),
                    xaxis=dict(
                        showticklabels=False, 
                        range=[0, max(z_vals)*1.4 if any(z_vals) else 100], 
                        showgrid=False
                    ),
                    yaxis=dict(autorange="reversed") # Sprint øverst
                )
                st.plotly_chart(fig, use_container_width=True, key=f"calc_profile_final_{p_uuid}")
            else:
                st.info("Ingen split-data fundet for denne spiller.")
                
        with tabs[2]:
            st.caption("Minut-for-minut intensitet vs. Sæson gns. pr. minut")
            df_season_splits = conn.query(f"""
                SELECT MINUTE_SPLIT, UPPER(PHYSICAL_METRIC_TYPE) as METRIC, AVG(PHYSICAL_METRIC_VALUE) as AVG_VAL,
                    CASE WHEN (PLAYER_NAME ILIKE '%{f_clean}%' AND PLAYER_NAME ILIKE '%{l_clean}%') THEN 'PLAYER' ELSE 'TEAM' END as SCOPE
                FROM {DB}.SECONDSPECTRUM_PHYSICAL_SPLITS_PLAYERS
                WHERE MATCH_DATE >= '{SEASON_START}'
                GROUP BY 1, 2, 4
            """)

            df_current_match = conn.query(f"""
                SELECT MINUTE_SPLIT, UPPER(PHYSICAL_METRIC_TYPE) as METRIC, SUM(PHYSICAL_METRIC_VALUE) as VAL 
                FROM {DB}.SECONDSPECTRUM_PHYSICAL_SPLITS_PLAYERS 
                WHERE MATCH_SSIID = '{latest['MATCH_SSIID']}' 
                  AND PLAYER_NAME ILIKE '%{f_clean}%' AND PLAYER_NAME ILIKE '%{l_clean}%'
                GROUP BY 1, 2 ORDER BY 1 ASC
            """)
            
            if df_current_match is not None and not df_current_match.empty:
                all_metrics = [m for m in df_current_match['METRIC'].unique() if 'COUNT' not in m]
                prio = ["HSR DISTANCE", "SPRINT DISTANCE", "TOTAL DISTANCE"]
                sorted_metrics = [m for m in prio if m in all_metrics] + [m for m in all_metrics if m not in prio]
                readable_options = [m.replace(' DISTANCE', '').title() for m in sorted_metrics]
                map_back = dict(zip(readable_options, sorted_metrics))
                selected_readable = st.segmented_control("Vælg metrik", options=readable_options, default=readable_options[0], key=f"split_sel_{p_uuid}")
                
                if selected_readable:
                    m_type = map_back[selected_readable]
                    div = 1000 if "TOTAL" in m_type else 1
                    suffix = "km" if "TOTAL" in m_type else "m"
                    d_current = df_current_match[df_current_match['METRIC'] == m_type].copy()
                    d_s_player = df_season_splits[(df_season_splits['METRIC'] == m_type) & (df_season_splits['SCOPE'] == 'PLAYER')].sort_values('MINUTE_SPLIT')
                    d_s_team = df_season_splits[(df_season_splits['METRIC'] == m_type) & (df_season_splits['SCOPE'] == 'TEAM')].groupby('MINUTE_SPLIT')['AVG_VAL'].mean().reset_index()

                    fig_s = go.Figure()
                    fig_s.add_trace(go.Scatter(x=d_s_team['MINUTE_SPLIT'], y=d_s_team['AVG_VAL']/div, line=dict(color="#D3D3D3", width=1.5), name="Hold Sæson Gns."))
                    fig_s.add_trace(go.Scatter(x=d_s_player['MINUTE_SPLIT'], y=d_s_player['AVG_VAL']/div, line=dict(color="black", width=1.5, dash="dash"), name="Spiller Sæson Gns."))
                    fig_s.add_trace(go.Scatter(x=d_current['MINUTE_SPLIT'], y=d_current['VAL']/div, fill='tozeroy', line=dict(color='#cc0000', width=2.5), mode='lines+markers', name="Denne kamp"))
                    fig_s.update_layout(plot_bgcolor="white", height=400, margin=dict(t=20, b=20, l=0, r=0), xaxis=dict(title="Kampminut", range=[0, 95]), yaxis=dict(title=suffix))
                    st.plotly_chart(fig_s, use_container_width=True)

        with tabs[3]:
            df_chart = df.copy().drop_duplicates(subset=['MATCH_DATE', 'MATCH_TEAMS']).sort_values('MATCH_DATE')
            cat_choice = st.segmented_control("Vælg metrik", options=["HSR (m)", "Sprint (m)", "Distance (km)", "Topfart (km/t)"], default="HSR (m)")
            mapping = {"HSR (m)": ("HSR", 1), "Sprint (m)": ("SPRINTING", 1), "Distance (km)": ("DISTANCE", 1000), "Topfart (km/t)": ("TOP_SPEED", 1)}
            col_name, div = mapping[cat_choice]

            if not df_chart.empty:
                def get_opp(teams_str, my_team):
                    parts = [p.strip() for p in str(teams_str).split('-')]
                    if len(parts) < 2: return str(teams_str)
                    return parts[1] if parts[0].lower() in my_team.lower() else parts[0]

                df_chart['Opponent'] = df_chart['MATCH_TEAMS'].apply(lambda x: get_opp(x, valgt_hold))
                df_chart['Label'] = df_chart['Opponent'] + "<br>" + df_chart['MATCH_DATE'].dt.strftime('%d/%m')
                y_vals = df_chart[col_name] / div
                fig_t = go.Figure(go.Bar(x=df_chart['Label'], y=y_vals, marker_color='#cc0000', text=y_vals.round(1), textposition='outside'))
                fig_t.update_layout(plot_bgcolor="white", height=400, yaxis=dict(range=[0, y_vals.max()*1.3]))
                st.plotly_chart(fig_t, use_container_width=True)

    else:
        st.warning("Ingen fysisk data fundet for denne spiller.")

if __name__ == "__main__":
    vis_side()
