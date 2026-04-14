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
LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '328', '329', '43319', '331')"
HIF_SSIID = '56fa29c7-3a48-4186-9d14-dbf45fbc78d9'

def convert_time_to_minutes(time_val):
    """Konverterer '97:58' til 97.96 eller returnerer tallet hvis det allerede er float/int"""
    if isinstance(time_val, str) and ":" in time_val:
        try:
            m, s = map(float, time_val.split(':'))
            return m + (s / 60.0)
        except:
            return 0.0
    return pd.to_numeric(time_val, errors='coerce')

@st.cache_data(ttl=600)
def get_physical_summary(player_opta_uuid, _conn):
    # Vi renser ID'et for 'p', så det matcher "optaId" i Second Spectrum tabellen
    clean_id = str(player_opta_uuid).lower().replace('p', '').strip()
    
    sql_player = f"""
    WITH hvidovre_ids AS (
        SELECT DISTINCT
            m.MATCH_SSIID, 
            REPLACE(LOWER(f.value:"optaId"::string), 'p', '') AS clean_opta_id
        FROM {DB}.SECONDSPECTRUM_GAME_METADATA m,
        LATERAL FLATTEN(input => CASE 
            WHEN m.HOME_SSIID = '{HIF_SSIID}' THEN m.HOME_PLAYERS 
            ELSE m.AWAY_PLAYERS 
        END) f
        WHERE m.HOME_SSIID = '{HIF_SSIID}' 
           OR m.AWAY_SSIID = '{HIF_SSIID}'
    )
    SELECT 
        p.MATCH_DATE,
        p.MATCH_TEAMS,
        p.PLAYER_NAME,
        p.MINUTES,
        p.DISTANCE,
        p.AVERAGE_SPEED,
        p.TOP_SPEED,
        p."HIGH SPEED RUNNING" AS HSR,
        p.SPRINTING AS SPRINTING,
        p.NO_OF_HIGH_INTENSITY_RUNS AS HI_RUNS,
        p.DISTANCE_TIP,
        p.HSR_DISTANCE_TIP AS HSR_TIP,
        p.NO_OF_HIGH_INTENSITY_RUNS_TIP AS HI_RUNS_TIP,
        p.DISTANCE_OTIP,
        p.HSR_DISTANCE_OTIP AS HSR_OTIP,
        p.NO_OF_HIGH_INTENSITY_RUNS_OTIP AS HI_RUNS_OTIP,
        p.DISTANCE_BOP,
        p.MATCH_SSIID
    FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS p
    INNER JOIN hvidovre_ids h 
        ON p.MATCH_SSIID = h.MATCH_SSIID 
        AND REPLACE(LOWER(p."optaId"), 'p', '') = h.clean_opta_id
    WHERE h.clean_opta_id = '{clean_id}'
      AND p.MATCH_DATE >= '2025-07-01'
    ORDER BY p.MATCH_DATE DESC
    """
    return _conn.query(sql_player)

def draw_phase_pitch(val, title, color):
    pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD', line_zorder=2)
    fig, ax = pitch.draw(figsize=(8, 6))
    fig.patch.set_alpha(0)
    try:
        display_val = int(float(val)) if pd.notnull(val) else 0
    except:
        display_val = 0
    ax.text(50, 50, f"{display_val}", color=color, fontsize=60, 
            fontweight='bold', ha='center', va='center', alpha=0.15)
    ax.set_title(title, fontsize=14, pad=10, fontweight='bold', color='#333333')
    return fig

def vis_side():
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 24px !important; font-weight: bold !important; color: #cc0000; }
        .stTabs [aria-selected="true"] { background-color: #cc0000 !important; color: white !important; }
        div.block-container { padding-top: 2rem; }
        </style>
    """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn: return

    # --- HOLD OG SPILLERVALG ---
    sql_teams = f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}"
    df_teams_raw = conn.query(sql_teams)
    mapping_lookup = {str(info['opta_uuid']).lower().replace('t', ''): name for name, info in TEAMS.items() if 'opta_uuid' in info}
    
    valid_teams = {}
    if df_teams_raw is not None:
        for _, r in df_teams_raw.iterrows():
            uuid_clean = str(r['CONTESTANTHOME_OPTAUUID']).lower().replace('t','')
            if uuid_clean in mapping_lookup:
                valid_teams[mapping_lookup[uuid_clean]] = r['CONTESTANTHOME_OPTAUUID']

    col_h1, col_h2 = st.columns(2)
    valgt_hold = col_h1.selectbox("Vælg Hold", sorted(list(valid_teams.keys())))
    valgt_uuid_hold = valid_teams[valgt_hold]

    sql_spillere = f"""
        SELECT DISTINCT TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as NAVN, e.PLAYER_OPTAUUID
        FROM {DB}.OPTA_EVENTS e
        JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
        WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid_hold}' AND e.EVENT_TIMESTAMP >= '2025-07-01'
    """
    df_pl = conn.query(sql_spillere)
    if df_pl is None or df_pl.empty: return

    valgt_spiller = col_h2.selectbox("Vælg Spiller", sorted(df_pl['NAVN'].tolist()))
    valgt_player_uuid = df_pl[df_pl['NAVN'] == valgt_spiller]['PLAYER_OPTAUUID'].iloc[0]

    st.markdown("---")

    # --- DATA HANDLING ---
    df = get_physical_summary(valgt_player_uuid, conn)

    if df is not None and not df.empty:
        # Konverter minutter fra "97:58" til numerisk
        df['MINUTES_NUM'] = df['MINUTES'].apply(convert_time_to_minutes)
        
        # Konverter resten til tal
        numeric_cols = ['DISTANCE', 'HSR', 'SPRINTING', 'TOP_SPEED', 'HI_RUNS', 
                        'HI_RUNS_TIP', 'HI_RUNS_OTIP', 'HSR_TIP', 'HSR_OTIP']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        latest = df.iloc[0]
        m_mins = float(latest['MINUTES_NUM']) if latest['MINUTES_NUM'] > 0 else 1.0
        
        # p90 Beregninger
        dist_90 = round((latest['DISTANCE'] / m_mins) * 90 / 1000, 2)
        hsr_90 = int((latest['HSR'] / m_mins) * 90)
        sprint_90 = int((latest['SPRINTING'] / m_mins) * 90)

        # Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Distance", f"{round(latest['DISTANCE']/1000, 2)} km", f"{dist_90} p90")
        m2.metric("HSR", f"{int(latest['HSR'])} m", f"{hsr_90} p90")
        m3.metric("Sprint", f"{int(latest['SPRINTING'])} m", f"{sprint_90} p90")
        m4.metric("HI Runs", int(latest['HI_RUNS']))

        tabs = st.tabs(["📍 Bane-overblik", "📈 Sæson-trend", "📋 Kamp-data"])

        with tabs[0]:
            st.write("### Fordeling af Højintensive løb (HI Runs)")
            c_a, c_b = st.columns(2)
            with c_a:
                st.pyplot(draw_phase_pitch(latest['HI_RUNS_TIP'], "TIP (Offensiv fase)", "#2ecc71"))
            with c_b:
                st.pyplot(draw_phase_pitch(latest['HI_RUNS_OTIP'], "OTIP (Defensiv fase)", "#e74c3c"))
            st.write(f"**Topfart i seneste kamp:** {latest['TOP_SPEED']} km/h")

        with tabs[1]:
            df_trend = df.sort_values('MATCH_DATE')
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_trend['MATCH_DATE'], y=df_trend['HSR'], name="Total HSR", line=dict(color='#cc0000', width=3)))
            fig.add_trace(go.Scatter(x=df_trend['MATCH_DATE'], y=df_trend['HSR_TIP'], name="TIP HSR", line=dict(color='#2ecc71', dash='dot')))
            fig.add_trace(go.Scatter(x=df_trend['MATCH_DATE'], y=df_trend['HSR_OTIP'], name="OTIP HSR", line=dict(color='#e74c3c', dash='dot')))
            fig.update_layout(title="HSR volumen over tid", plot_bgcolor="white", height=400)
            st.plotly_chart(fig, use_container_width=True)

        with tabs[2]:
            st.dataframe(
                df[['MATCH_DATE', 'MATCH_TEAMS', 'MINUTES', 'DISTANCE', 'HSR', 'SPRINTING', 'TOP_SPEED']], 
                use_container_width=True, 
                hide_index=True,
                column_config={"MINUTES": "Minutter", "MATCH_DATE": "Dato"}
            )
    else:
        st.info(f"Ingen fysiske data fundet for {valgt_spiller}.")

if __name__ == "__main__":
    vis_side()
