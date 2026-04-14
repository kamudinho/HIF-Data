import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from mplsoccer import Pitch
import matplotlib.pyplot as plt
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7')"

@st.cache_data(ttl=600)
def get_physical_splits(player_name, player_opta_id, match_date, _conn):
    """Henter minut-for-minut data med korrekte kolonnenavne"""
    # Vi fjerner anførselstegn for at undgå Case-sensitivity fejl i Snowflake
    sql = f"""
        SELECT MINUTE_SPLIT, PHYSICAL_METRIC_TYPE, PHYSICAL_METRIC_VALUE
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SPLITS_PLAYERS
        WHERE (PLAYER_OPTAID = '{player_opta_id}' OR PLAYER_NAME ILIKE '%{player_name}%')
          AND MATCH_DATE = '{match_date}'
        ORDER BY MINUTE_SPLIT
    """
    return _conn.query(sql)

@st.cache_data(ttl=600)
def get_physical_summary(player_name, player_opta_uuid, valgt_hold_navn, _conn):
    target_ssiid = TEAMS.get(valgt_hold_navn, {}).get('ssid')
    # Matcher præcis dine kolonnenavne fra skema-oversigten
    sql = f"""
        SELECT 
            MATCH_DATE, MATCH_TEAMS, MINUTES, DISTANCE,
            "HIGH SPEED RUNNING" as HSR, SPRINTING, TOP_SPEED,
            NO_OF_HIGH_INTENSITY_RUNS as HI_RUNS,
            DISTANCE_TIP, HSR_DISTANCE_TIP as HSR_TIP, NO_OF_HIGH_INTENSITY_RUNS_TIP as HI_RUNS_TIP,
            DISTANCE_OTIP, HSR_DISTANCE_OTIP as HSR_OTIP, NO_OF_HIGH_INTENSITY_RUNS_OTIP as HI_RUNS_OTIP
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE (PLAYER_NAME ILIKE '%{player_name}%' OR "optaId" = '{player_opta_uuid}')
          AND MATCH_DATE >= '2025-07-01'
          AND MATCH_SSIID IN (
              SELECT MATCH_SSIID FROM {DB}.SECONDSPECTRUM_GAME_METADATA
              WHERE HOME_SSIID = '{target_ssiid}' OR AWAY_SSIID = '{target_ssiid}'
          )
        ORDER BY MATCH_DATE DESC
    """
    return _conn.query(sql)

def draw_static_pitch(val, title, color):
    pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD', line_zorder=2)
    fig, ax = pitch.draw(figsize=(8, 6))
    fig.patch.set_alpha(0)
    ax.text(50, 50, f"{int(val)}", color=color, fontsize=50, fontweight='bold', ha='center', va='center', alpha=0.2)
    ax.set_title(title, fontsize=12, pad=10, fontweight='bold')
    return fig

def vis_side():
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 24px !important; font-weight: bold !important; color: #cc0000; }
        .stTabs [aria-selected="true"] { background-color: #cc0000 !important; color: white !important; }
        </style>
    """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn: return

    # --- FILTRERING ---
    sql_teams = f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}"
    df_teams_raw = conn.query(sql_teams)
    mapping_lookup = {str(info['opta_uuid']).lower().replace('t', ''): name for name, info in TEAMS.items() if 'opta_uuid' in info}
    
    valid_teams = {mapping_lookup[str(r['CONTESTANTHOME_OPTAUUID']).lower().replace('t','')]: r['CONTESTANTHOME_OPTAUUID'] 
                   for _, r in df_teams_raw.iterrows() if str(r['CONTESTANTHOME_OPTAUUID']).lower().replace('t','') in mapping_lookup}

    c1, c2 = st.columns(2)
    if not valid_teams:
        st.warning("Ingen hold fundet for de valgte ligaer.")
        return
        
    valgt_hold = c1.selectbox("Hold", sorted(list(valid_teams.keys())))
    
    sql_spillere = f"SELECT DISTINCT TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as NAVN, e.PLAYER_OPTAUUID FROM {DB}.OPTA_EVENTS e JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valid_teams[valgt_hold]}' AND e.EVENT_TIMESTAMP >= '2025-07-01'"
    df_pl = conn.query(sql_spillere)
    if df_pl is None or df_pl.empty: return
    valgt_spiller = c2.selectbox("Spiller", sorted(df_pl['NAVN'].tolist()))
    valgt_player_uuid = df_pl[df_pl['NAVN'] == valgt_spiller]['PLAYER_OPTAUUID'].iloc[0]
    clean_player_id = str(valgt_player_uuid).lower().replace('p', '').strip()

    # --- DATA LOAD ---
    df_sum = get_physical_summary(valgt_spiller, clean_player_id, valgt_hold, conn)

    if df_sum is not None and not df_sum.empty:
        latest = df_sum.iloc[0]
        
        m = st.columns(4)
        m[0].metric("Distance", f"{round(latest['DISTANCE']/1000, 2)} km")
        m[1].metric("HSR", f"{int(latest['HSR'])} m")
        m[2].metric("Sprint", f"{int(latest['SPRINTING'])} m")
        m[3].metric("HI Runs", int(latest['HI_RUNS']))

        # Faner uden ikoner
        t_pitch, t_minute, t_trend = st.tabs(["Baneoversigt", "Minut-analyse", "Saeson-trend"])

        with t_pitch:
            st.write("### Højintensive aktioner (TIP vs OTIP)")
            col_a, col_b = st.columns(2)
            with col_a: st.pyplot(draw_static_pitch(latest['HI_RUNS_TIP'], "Ved boldbesiddelse (TIP)", "#2ecc71"))
            with col_b: st.pyplot(draw_static_pitch(latest['HI_RUNS_OTIP'], "Modstander har bold (OTIP)", "#e74c3c"))

        with t_minute:
            df_splits = get_physical_splits(valgt_spiller, clean_player_id, latest['MATCH_DATE'], conn)
            if df_splits is not None and not df_splits.empty:
                df_dist = df_splits[df_splits['PHYSICAL_METRIC_TYPE'] == 'Total Distance']
                fig_min = go.Figure()
                fig_min.add_trace(go.Bar(x=df_dist['MINUTE_SPLIT'], y=df_dist['PHYSICAL_METRIC_VALUE'], marker_color='#cc0000'))
                fig_min.update_layout(title=f"Meter løbet pr. minut-interval", xaxis_title="Minut", yaxis_title="Meter", plot_bgcolor="white")
                st.plotly_chart(fig_min, use_container_width=True)
            else:
                st.info("Ingen minut-data fundet for denne kamp.")

        with t_trend:
            df_trend = df_sum.sort_values('MATCH_DATE')
            fig_t = go.Figure()
            fig_t.add_trace(go.Scatter(x=df_trend['MATCH_DATE'], y=df_trend['HSR'], name="HSR", line=dict(color='#cc0000', width=3)))
            fig_t.update_layout(title="HSR udvikling over sæsonen", plot_bgcolor="white")
            st.plotly_chart(fig_t, use_container_width=True)
    else:
        st.info("Ingen fysiske data fundet.")

if __name__ == "__main__":
    vis_side()
