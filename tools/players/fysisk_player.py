import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from mplsoccer import Pitch
from data.data_load import _get_snowflake_conn

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7')"

@st.cache_data(ttl=600)
def get_physical_splits(player_opta_id, match_ssiid, _conn):
    """Henter minut-splits"""
    clean_id = str(player_opta_id).lower().replace('p', '').strip()
    sql = f"""
        SELECT 
            MINUTE_SPLIT, PHYSICAL_METRIC_TYPE, PHYSICAL_METRIC_VALUE, PERIOD
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SPLITS_PLAYERS
        WHERE PLAYER_OPTAID = '{clean_id}'
          AND MATCH_SSIID = '{match_ssiid}'
        ORDER BY PERIOD, MINUTE_SPLIT
    """
    return _conn.query(sql)

@st.cache_data(ttl=600)
def get_physical_summary(player_name, player_opta_uuid, _conn):
    """Henter sæson-historik"""
    clean_id = str(player_opta_uuid).lower().replace('p', '').strip()
    sql = f"""
        SELECT 
            MATCH_DATE, MATCH_TEAMS, MATCH_SSIID, MINUTES, DISTANCE,
            "HIGH SPEED RUNNING" as HSR, SPRINTING, TOP_SPEED,
            NO_OF_HIGH_INTENSITY_RUNS as HI_RUNS,
            DISTANCE_TIP, HSR_DISTANCE_TIP as HSR_TIP, NO_OF_HIGH_INTENSITY_RUNS_TIP as HI_RUNS_TIP,
            DISTANCE_OTIP, HSR_DISTANCE_OTIP as HSR_OTIP, NO_OF_HIGH_INTENSITY_RUNS_OTIP as HI_RUNS_OTIP
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE (PLAYER_NAME ILIKE '%{player_name}%' OR "optaId" = '{clean_id}')
          AND MATCH_DATE >= '2025-07-01'
        ORDER BY MATCH_DATE DESC
    """
    return _conn.query(sql)

def draw_static_pitch(val, title, color):
    pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD', line_zorder=2)
    fig, ax = pitch.draw(figsize=(8, 6))
    fig.patch.set_alpha(0)
    ax.text(50, 50, f"{int(val)}", color=color, fontsize=50, fontweight='bold', ha='center', va='center', alpha=0.2)
    ax.set_title(title, fontsize=14, pad=10, fontweight='bold')
    return fig

def vis_side():
    st.markdown("<style>[data-testid='stMetricValue'] { color: #cc0000; font-weight: bold; }</style>", unsafe_allow_html=True)
    conn = _get_snowflake_conn()
    if not conn: return

    # --- 1. FIND HOLD ---
    # Vi bruger MATCHINFO til at finde holdnavne i de rigtige ligaer
    sql_teams = f"""
        SELECT DISTINCT CONTESTANTHOME_NAME 
        FROM {DB}.OPTA_MATCHINFO 
        WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}
    """
    df_teams = conn.query(sql_teams)
    if df_teams is None or df_teams.empty:
        st.error("Ingen hold fundet.")
        return

    c1, c2 = st.columns(2)
    valgt_hold = c1.selectbox("Hold", sorted(df_teams['CONTESTANTHOME_NAME'].tolist()))
    
    # --- 2. FIND SPILLERE VIA SUMMARY TABELLEN (Mere robust) ---
    # Vi henter spillere der rent faktisk har fysiske data for det valgte hold
    sql_spillere = f"""
        SELECT DISTINCT PLAYER_NAME, "optaId" as PLAYER_OPTAUUID
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_TEAMS LIKE '%{valgt_hold}%'
    """
    df_pl = conn.query(sql_spillere)
    
    if df_pl is None or df_pl.empty:
        st.warning(f"Ingen fysiske data fundet for spillere på {valgt_hold}")
        return

    valgt_spiller = c2.selectbox("Spiller", sorted(df_pl['PLAYER_NAME'].tolist()))
    valgt_id = df_pl[df_pl['PLAYER_NAME'] == valgt_spiller]['PLAYER_OPTAUUID'].iloc[0]

    # --- 3. VIS DATA ---
    df_sum = get_physical_summary(valgt_spiller, valgt_id, conn)

    if df_sum is not None and not df_sum.empty:
        latest = df_sum.iloc[0]
        st.subheader(f"Analyse: {valgt_spiller}")
        
        m = st.columns(4)
        m[0].metric("Distance", f"{round(latest['DISTANCE']/1000, 2)} km")
        m[1].metric("HSR", f"{int(latest['HSR'])} m")
        m[2].metric("Sprint", f"{int(latest['SPRINTING'])} m")
        m[3].metric("Topfart", f"{latest['TOP_SPEED']} km/h")

        t1, t2, t3 = st.tabs(["Minut-for-minut", "Bane", "Trend"])

        with t1:
            df_splits = get_physical_splits(valgt_id, latest['MATCH_SSIID'], conn)
            if not df_splits.empty:
                metrikker = sorted(df_splits['PHYSICAL_METRIC_TYPE'].unique())
                valgt_m = st.selectbox("Metrik", metrikker, index=0)
                df_plot = df_splits[df_splits['PHYSICAL_METRIC_TYPE'] == valgt_m]
                
                fig = go.Figure(go.Bar(x=df_plot['MINUTE_SPLIT'], y=df_plot['PHYSICAL_METRIC_VALUE'], marker_color='#cc0000'))
                fig.update_layout(title=f"{valgt_m} pr. minut", plot_bgcolor="white")
                st.plotly_chart(fig, use_container_width=True)

        with t2:
            st.write("Højintensive aktioner (HI Runs)")
            ca, cb = st.columns(2)
            with ca: st.pyplot(draw_static_pitch(latest['HI_RUNS_TIP'] or 0, "Med bold (TIP)", "#2ecc71"))
            with cb: st.pyplot(draw_static_pitch(latest['HI_RUNS_OTIP'] or 0, "Uden bold (OTIP)", "#e74c3c"))

        with t3:
            df_trend = df_sum.sort_values('MATCH_DATE')
            fig_t = go.Figure(go.Scatter(x=df_trend['MATCH_DATE'], y=df_trend['HSR'], line=dict(color='#cc0000', width=3)))
            fig_t.update_layout(title="HSR udvikling", plot_bgcolor="white")
            st.plotly_chart(fig_t, use_container_width=True)

if __name__ == "__main__":
    vis_side()
