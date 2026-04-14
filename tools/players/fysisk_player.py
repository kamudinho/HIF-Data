import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from mplsoccer import Pitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '328', '329', '43319', '331')"

@st.cache_data(ttl=600)
def get_physical_summary(player_name, player_opta_uuid, valgt_hold_navn, _conn):
    target_ssiid = TEAMS.get(valgt_hold_navn, {}).get('ssid')
    clean_id = str(player_opta_uuid).lower().replace('p', '').strip()
    navne_dele = [n.strip() for n in player_name.split(' ') if len(n.strip()) > 2]
    name_conditions = " OR ".join([f"PLAYER_NAME ILIKE '%{n}%'" for n in navne_dele])

    sql = f"""
        SELECT 
            MATCH_DATE, MATCH_TEAMS, MINUTES, DISTANCE,
            "HIGH SPEED RUNNING" as HSR, SPRINTING, TOP_SPEED,
            NO_OF_HIGH_INTENSITY_RUNS as HI_RUNS,
            DISTANCE_TIP, HSR_DISTANCE_TIP as HSR_TIP, NO_OF_HIGH_INTENSITY_RUNS_TIP as HI_RUNS_TIP,
            DISTANCE_OTIP, HSR_DISTANCE_OTIP as HSR_OTIP, NO_OF_HIGH_INTENSITY_RUNS_OTIP as HI_RUNS_OTIP
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE (({name_conditions}) OR ("optaId" = '{clean_id}'))
          AND MATCH_DATE >= '2025-07-01'
          AND MATCH_SSIID IN (
              SELECT MATCH_SSIID FROM {DB}.SECONDSPECTRUM_GAME_METADATA
              WHERE HOME_SSIID = '{target_ssiid}' OR AWAY_SSIID = '{target_ssiid}'
          )
        ORDER BY MATCH_DATE DESC
    """
    return _conn.query(sql)

def draw_phase_pitch(val, title, color):
    pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD', line_zorder=2)
    fig, ax = pitch.draw(figsize=(8, 6))
    fig.patch.set_alpha(0)
    # Sikker håndtering af værdier til banen
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
        [data-testid="stMetricValue"] { font-size: 22px !important; font-weight: bold !important; color: #cc0000; }
        .stTabs [aria-selected="true"] { background-color: #cc0000 !important; color: white !important; }
        </style>
    """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn: return

    # --- SQL TIL HOLD OG SPILLERE ---
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

    # --- DATA HANDLING ---
    df = get_physical_summary(valgt_spiller, valgt_player_uuid, valgt_hold, conn)

    if df is not None and not df.empty:
        # 1. TVING DATA TIL TAL (Løser 'str' vs 'int' og NaN fejl)
        for col in df.columns:
            if col not in ['MATCH_DATE', 'MATCH_TEAMS']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        latest = df.iloc[0]
        
        # 2. BEREGNINGER (Nu med sikre tal)
        m_mins = float(latest['MINUTES']) if latest['MINUTES'] > 0 else 1.0
        m_dist = float(latest['DISTANCE'])
        m_hsr = float(latest['HSR'])
        m_sprint = float(latest['SPRINTING'])
        
        dist_90 = round((m_dist / m_mins) * 90 / 1000, 2)
        hsr_90 = int((m_hsr / m_mins) * 90)
        sprint_90 = int((m_sprint / m_mins) * 90)
        hi_index = round(((m_hsr + m_sprint) / m_dist) * 100, 1) if m_dist > 0 else 0.0

        # 3. VISNING
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Distance", f"{round(m_dist/1000, 2)} km", f"{dist_90} p90", delta_color="off")
        m2.metric("HSR", f"{int(m_hsr)} m", f"{hsr_90} p90", delta_color="off")
        m3.metric("Sprint", f"{int(m_sprint)} m", f"{sprint_90} p90", delta_color="off")
        m4.metric("Intensitets-index", f"{hi_index}%", "HSR+Sprint load", delta_color="normal" if hi_index > 7.0 else "off")

        tabs = st.tabs(["📍 Individuel Profil", "📈 Sæson-trend", "📋 Kamp-historik"])

        with tabs[0]:
            c_left, c_right = st.columns([1, 2])
            with c_left:
                st.write("### Arbejdsrate")
                total_hi = latest['HI_RUNS_TIP'] + latest['HI_RUNS_OTIP']
                if total_hi > 0:
                    off_pct = round((latest['HI_RUNS_TIP'] / total_hi) * 100)
                    st.write(f"Offensiv (TIP): **{off_pct}%**")
                    st.progress(off_pct / 100)
                    st.write(f"Defensiv (OTIP): **{100-off_pct}%**")
                    st.progress((100-off_pct) / 100)
                st.write(f"**Topfart:** {latest['TOP_SPEED']} km/h")
            with c_right:
                ca, cb = st.columns(2)
                with ca: st.pyplot(draw_phase_pitch(latest['HI_RUNS_TIP'], "Offensiv (TIP)", "#2ecc71"))
                with cb: st.pyplot(draw_phase_pitch(latest['HI_RUNS_OTIP'], "Defensiv (OTIP)", "#e74c3c"))

        with tabs[1]:
            df_trend = df.sort_values('MATCH_DATE')
            df_trend['HSR_P90'] = (df_trend['HSR'] / df_trend['MINUTES'].replace(0,1)) * 90
            fig = go.Figure(go.Scatter(x=df_trend['MATCH_DATE'], y=df_trend['HSR_P90'], line=dict(color='#cc0000', width=3), mode='lines+markers'))
            fig.update_layout(title="HSR intensitet (p90) over tid", plot_bgcolor="white", height=400)
            st.plotly_chart(fig, use_container_width=True)

        with tabs[2]:
            st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Ingen fysiske data fundet for denne spiller.")

if __name__ == "__main__":
    vis_side()
