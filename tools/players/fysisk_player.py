import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from mplsoccer import Pitch
import matplotlib.pyplot as plt
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

# --- KONFIGURATION (OPDATERET) ---
DB = "KLUB_HVIDOVREIF.AXIS"
# Vi bruger din præcise liste og sikrer, at Superliga (335) evt. kan fjernes herfra hvis ønsket.
# Jeg har beholdt din streng, men SQL-kaldet vil nu kun vise hold fra disse ID'er.
LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '328', '329', '43319', '331')"
CURRENT_SEASON = "2025/2026"

def get_physical_data_with_splits(player_name, player_opta_uuid, valgt_hold_navn, db_conn):
    target_ssiid = TEAMS.get(valgt_hold_navn, {}).get('ssid', '56fa29c7-3a48-4186-9d14-dbf45fbc78d9')
    clean_id = str(player_opta_uuid).lower().replace('p', '').strip()
    navne_dele = [n.strip() for n in player_name.split(' ') if len(n.strip()) > 2]
    name_conditions = " OR ".join([f"PLAYER_NAME ILIKE '%{n}%'" for n in navne_dele])

    sql = f"""
        SELECT 
            p.MATCH_DATE,
            ANY_VALUE(p.MATCH_TEAMS) as MATCH_TEAMS,
            MAX(p.MINUTES) as MINUTES,
            SUM(p.DISTANCE) as DISTANCE,
            SUM(p."HIGH SPEED RUNNING") as HSR,
            SUM(p.SPRINTING) as SPRINTING,
            MAX(p.TOP_SPEED) as TOP_SPEED,
            SUM(p.NO_OF_HIGH_INTENSITY_RUNS) as HI_RUNS,
            SUM(p.DISTANCE_TIP) as DISTANCE_TIP,
            SUM(p.DISTANCE_OTIP) as DISTANCE_OTIP,
            SUM(p.DISTANCE_BOP) as DISTANCE_BOP,
            SUM(p.HSR_DISTANCE_TIP) as HSR_TIP,
            SUM(p.HSR_DISTANCE_OTIP) as HSR_OTIP,
            SUM(p.NO_OF_HIGH_INTENSITY_RUNS_TIP) as HI_RUNS_TIP,
            SUM(p.NO_OF_HIGH_INTENSITY_RUNS_OTIP) as HI_RUNS_OTIP
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS p
        WHERE (({name_conditions}) OR ("optaId" LIKE '%{clean_id}%'))
          AND p.MATCH_DATE >= '2025-07-01'
          AND p.MATCH_SSIID IN (
              SELECT MATCH_SSIID FROM {DB}.SECONDSPECTRUM_GAME_METADATA
              WHERE HOME_SSIID = '{target_ssiid}' OR AWAY_SSIID = '{target_ssiid}'
          )
        GROUP BY p.MATCH_DATE, p.PLAYER_NAME
        ORDER BY p.MATCH_DATE DESC
    """
    return db_conn.query(sql)

def draw_intensity_pitch(val, title, color):
    """Tegner banen korrekt med Matplotlib til Streamlit"""
    pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD', line_zorder=2)
    fig, ax = pitch.draw(figsize=(6, 4))
    fig.set_facecolor('none')
    
    # Centreret tekst-overlay for at illustrere volumen i zonen
    ax.text(50, 50, f"{int(val)}", color=color, fontsize=40, 
            fontweight='bold', ha='center', va='center', alpha=0.2)
    
    ax.set_title(title, fontsize=14, pad=10, color='#333333', fontweight='bold')
    return fig

def vis_side():
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 20px !important; font-weight: bold !important; color: #cc0000; }
        .stTabs [aria-selected="true"] { background-color: #cc0000 !important; color: white !important; }
        </style>
    """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn: return

    # --- FILTRERING AF HOLD (INGEN SUPERLIGA) ---
    sql_teams = f"""
        SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID 
        FROM {DB}.OPTA_MATCHINFO 
        WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}
    """
    df_teams_raw = conn.query(sql_teams)
    
    mapping_lookup = {str(info['opta_uuid']).lower().replace('t', ''): name 
                     for name, info in TEAMS.items() if 'opta_uuid' in info}

    valid_teams = {}
    if df_teams_raw is not None:
        for _, r in df_teams_raw.iterrows():
            uuid_clean = str(r['CONTESTANTHOME_OPTAUUID']).lower().replace('t','')
            if uuid_clean in mapping_lookup:
                valid_teams[mapping_lookup[uuid_clean]] = r['CONTESTANTHOME_OPTAUUID']

    # --- TOP VALG ---
    c1, c2 = st.columns(2)
    valgt_hold = c1.selectbox("Vælg Hold", sorted(list(valid_teams.keys())))
    valgt_uuid_hold = valid_teams[valgt_hold]

    sql_spillere = f"""
        SELECT DISTINCT TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as NAVN, e.PLAYER_OPTAUUID
        FROM {DB}.OPTA_EVENTS e
        JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
        WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid_hold}' 
        AND e.EVENT_TIMESTAMP >= '2025-07-01'
    """
    df_pl = conn.query(sql_spillere)
    
    if df_pl is None or df_pl.empty:
        st.warning("Ingen spillere fundet for det valgte hold.")
        return

    valgt_spiller = c2.selectbox("Vælg Spiller", sorted(df_pl['NAVN'].tolist()))
    valgt_player_uuid = df_pl[df_pl['NAVN'] == valgt_spiller]['PLAYER_OPTAUUID'].iloc[0]

    st.markdown("---")

    # --- DATA VISUALISERING ---
    df = get_physical_data_with_splits(valgt_spiller, valgt_player_uuid, valgt_hold, conn)

    if df is not None and not df.empty:
        latest = df.iloc[0]
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Distance", f"{round(latest['DISTANCE']/1000, 2)} km")
        m2.metric("HSR (Z4+5)", f"{int(latest['HSR'])} m")
        m3.metric("Sprint (Z6)", f"{int(latest['SPRINTING'])} m")
        m4.metric("HI Runs", int(latest['HI_RUNS']))

        t_pitch, t_trend, t_data = st.tabs(["📍 Bane-overblik (TIP/OTIP)", "📈 Udvikling", "📋 Kamp-log"])

        with t_pitch:
            st.write("### Højintensiv indsats fordelt på faser")
            p_col1, p_col2 = st.columns(2)
            
            with p_col1:
                fig1 = draw_intensity_pitch(latest['HI_RUNS_TIP'], "TIP (Med bold)", "#2ecc71")
                st.pyplot(fig1)
                st.caption(f"HI Runs i offensiv fase: {int(latest['HI_RUNS_TIP'])}")

            with p_col2:
                fig2 = draw_intensity_pitch(latest['HI_RUNS_OTIP'], "OTIP (Modstander med bold)", "#e74c3c")
                st.pyplot(fig2)
                st.caption(f"HI Runs i defensiv fase: {int(latest['HI_RUNS_OTIP'])}")

        with t_trend:
            df_trend = df.sort_values('MATCH_DATE')
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(x=df_trend['MATCH_DATE'], y=df_trend['HSR'], name="Total HSR", line=dict(color='#cc0000', width=3)))
            fig_trend.add_trace(go.Scatter(x=df_trend['MATCH_DATE'], y=df_trend['HSR_TIP'], name="TIP HSR", line=dict(color='#2ecc71', dash='dot')))
            fig_trend.add_trace(go.Scatter(x=df_trend['MATCH_DATE'], y=df_trend['HSR_OTIP'], name="OTIP HSR", line=dict(color='#e74c3c', dash='dot')))
            fig_trend.update_layout(plot_bgcolor="white", height=400, margin=dict(t=20, b=20, l=10, r=10))
            st.plotly_chart(fig_trend, use_container_width=True)

        with t_data:
            st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Ingen fysisk data fundet for denne spiller.")

if __name__ == "__main__":
    vis_side()
