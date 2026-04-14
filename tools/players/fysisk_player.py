import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from mplsoccer import Pitch
import matplotlib.pyplot as plt
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS, TEAM_COLORS

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
# Omfatter nu alle relevante ligaer (1. Div, 2. Div, 3. Div, Pokal, U19)
LIGA_IDS = "('328', '329', '43319', '331', '1305', '6ifaeunfdele')"

@st.cache_data(ttl=600)
def get_physical_summary(player_name, player_opta_uuid, _conn):
    """Henter fysisk data for spilleren på tværs af alle kampe i databasen"""
    clean_id = str(player_opta_uuid).lower().replace('p', '').strip()
    
    # Vi søger både på OptaID og Navne-matches for at sikre data-complete
    navne_dele = [n.strip() for n in player_name.split(' ') if len(n.strip()) > 2]
    name_conditions = " OR ".join([f"PLAYER_NAME ILIKE '%{n}%'" for n in navne_dele])

    sql = f"""
        SELECT 
            MATCH_DATE, 
            MATCH_TEAMS, 
            MINUTES, 
            DISTANCE,
            "HIGH SPEED RUNNING" as HSR, 
            SPRINTING, 
            TOP_SPEED,
            NO_OF_HIGH_INTENSITY_RUNS as HI_RUNS,
            DISTANCE_TIP, 
            HSR_DISTANCE_TIP as HSR_TIP, 
            NO_OF_HIGH_INTENSITY_RUNS_TIP as HI_RUNS_TIP,
            DISTANCE_OTIP, 
            HSR_DISTANCE_OTIP as HSR_OTIP, 
            NO_OF_HIGH_INTENSITY_RUNS_OTIP as HI_RUNS_OTIP,
            DISTANCE_BOP, 
            HSR_DISTANCE_BOP as HSR_BOP
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE (({name_conditions}) OR ("optaId" = '{clean_id}'))
          AND MATCH_DATE >= '2025-07-01'
        ORDER BY MATCH_DATE DESC
    """
    return _conn.query(sql)

def draw_phase_pitch(val, title, color):
    """Visualisering af banefaser"""
    pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD', line_zorder=2)
    fig, ax = pitch.draw(figsize=(8, 6))
    fig.patch.set_alpha(0)
    
    # Centreret tekst-overlay af værdien
    ax.text(50, 50, f"{int(val)}", color=color, fontsize=60, 
            fontweight='bold', ha='center', va='center', alpha=0.15)
    
    ax.set_title(title, fontsize=14, pad=10, fontweight='bold', color='#333333')
    return fig

def vis_side():
    # Fjernet ikoner i tabs og styling af knapper/metrics
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 24px !important; font-weight: bold !important; color: #cc0000; }
        .stTabs [data-baseweb="tab"] { font-weight: bold; }
        div.block-container { padding-top: 2rem; }
        </style>
    """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn: 
        st.error("Kunne ikke oprette forbindelse til Snowflake")
        return

    # --- 1. HENT ALLE HOLD FRA DE VALGTE LIGAER ---
    # Vi henter alle unikke holdnavne og deres UUIDs fra OPTA_MATCHINFO
    sql_all_teams = f"""
        SELECT DISTINCT CONTESTANTHOME_NAME as TEAM_NAME, CONTESTANTHOME_OPTAUUID as TEAM_UUID
        FROM {DB}.OPTA_MATCHINFO 
        WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}
        ORDER BY TEAM_NAME
    """
    df_teams = conn.query(sql_all_teams)
    
    if df_teams is None or df_teams.empty:
        st.warning("Ingen hold fundet i de valgte turneringer.")
        return

    # --- VALG AF HOLD OG SPILLER ---
    col_h1, col_h2 = st.columns(2)
    
    hold_navne = df_teams['TEAM_NAME'].tolist()
    valgt_hold_navn = col_h1.selectbox("Vælg Hold", hold_navne)
    
    valgt_hold_uuid = df_teams[df_teams['TEAM_NAME'] == valgt_hold_navn]['TEAM_UUID'].iloc[0]

    # Hent spillere for det valgte hold
    sql_spillere = f"""
        SELECT DISTINCT TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as NAVN, e.PLAYER_OPTAUUID
        FROM {DB}.OPTA_EVENTS e
        JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
        WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_hold_uuid}' 
          AND e.EVENT_TIMESTAMP >= '2025-07-01'
        ORDER BY NAVN
    """
    df_pl = conn.query(sql_spillere)
    
    if df_pl is None or df_pl.empty:
        st.info(f"Ingen spillere fundet med events for {valgt_hold_navn} i denne sæson.")
        return

    valgt_spiller = col_h2.selectbox("Vælg Spiller", df_pl['NAVN'].tolist())
    valgt_player_uuid = df_pl[df_pl['NAVN'] == valgt_spiller]['PLAYER_OPTAUUID'].iloc[0]

    st.markdown("---")

    # --- DATA-LOAD OG VISUALISERING ---
    df = get_physical_summary(valgt_spiller, valgt_player_uuid, conn)

    if df is not None and not df.empty:
        latest = df.iloc[0]
        
        # Farvevalg baseret på hold (hvis findes i team_mapping), ellers standard HIF-rød
        primary_color = TEAM_COLORS.get(valgt_hold_navn, {}).get('primary', '#cc0000')
        
        # Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Distance", f"{round(latest['DISTANCE']/1000, 2)} km")
        m2.metric("HSR", f"{int(latest['HSR'])} m")
        m3.metric("Sprint", f"{int(latest['SPRINTING'])} m")
        m4.metric("HI Runs", int(latest['HI_RUNS']))

        # Tabs uden ikoner i titlerne
        tabs = st.tabs(["Bane-overblik", "Sæson-trend", "Kamp-data"])

        with tabs[0]:
            st.write(f"### Fordeling af HI Runs for {valgt_spiller}")
            c_a, c_b = st.columns(2)
            with c_a:
                st.pyplot(draw_phase_pitch(latest['HI_RUNS_TIP'], "TIP (I Besiddelse)", "#2ecc71"))
            with c_b:
                st.pyplot(draw_phase_pitch(latest['HI_RUNS_OTIP'], "OTIP (Modstander i Besiddelse)", "#e74c3c"))

        with tabs[1]:
            df_trend = df.sort_values('MATCH_DATE')
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_trend['MATCH_DATE'], y=df_trend['HSR'], name="Total HSR", line=dict(color=primary_color, width=3)))
            fig.add_trace(go.Scatter(x=df_trend['MATCH_DATE'], y=df_trend['HSR_TIP'], name="TIP HSR (Offensiv)", line=dict(color='#2ecc71', dash='dot')))
            fig.add_trace(go.Scatter(x=df_trend['MATCH_DATE'], y=df_trend['HSR_OTIP'], name="OTIP HSR (Defensiv)", line=dict(color='#e74c3c', dash='dot')))
            
            fig.update_layout(
                title=f"HSR Udvikling - {valgt_spiller}",
                plot_bgcolor="white", 
                height=450, 
                hovermode="x unified",
                margin=dict(t=50, b=20, l=10, r=10)
            )
            st.plotly_chart(fig, use_container_width=True)

        with tabs[2]:
            st.subheader("Alle kampe i databasen")
            st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info(f"Ingen Second Spectrum data fundet for {valgt_spiller}. Tjek om spilleren har spillet i de dækkede ligaer.")

if __name__ == "__main__":
    vis_side()
