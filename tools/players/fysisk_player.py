import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from mplsoccer import Pitch
import matplotlib.pyplot as plt
from data.data_load import _get_snowflake_conn

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
# Dine specifikke Opta Liga ID'er
LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7')"

@st.cache_data(ttl=600)
def get_physical_splits(player_name, player_opta_id, match_date, _conn):
    """Henter alle split-typer (Distance/Count) for den valgte kamp"""
    clean_id = str(player_opta_id).lower().replace('p', '').strip()
    sql = f"""
        SELECT MINUTE_SPLIT, PHYSICAL_METRIC_TYPE, PHYSICAL_METRIC_VALUE
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SPLITS_PLAYERS
        WHERE (PLAYER_OPTAID = '{clean_id}' OR PLAYER_NAME ILIKE '%{player_name}%')
          AND MATCH_DATE = '{match_date}'
        ORDER BY MINUTE_SPLIT
    """
    return _conn.query(sql)

@st.cache_data(ttl=600)
def get_physical_summary(player_name, player_opta_uuid, _conn):
    """Henter overordnet fysisk profil for sæsonen"""
    clean_id = str(player_opta_uuid).lower().replace('p', '').strip()
    sql = f"""
        SELECT 
            MATCH_DATE, MATCH_TEAMS, MINUTES, DISTANCE,
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
    """Tegner en fodboldbane med en central værdi"""
    pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD', line_zorder=2)
    fig, ax = pitch.draw(figsize=(8, 6))
    fig.patch.set_alpha(0)
    # Viser værdien stort i midten som en 'heatmap' erstatning
    ax.text(50, 50, f"{int(val)}", color=color, fontsize=50, fontweight='bold', ha='center', va='center', alpha=0.2)
    ax.set_title(title, fontsize=14, pad=10, fontweight='bold')
    return fig

def vis_side():
    # CSS til styling uden ikoner
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 26px !important; font-weight: bold !important; color: #cc0000; }
        .stTabs [aria-selected="true"] { background-color: #cc0000 !important; color: white !important; font-weight: bold !important; }
        .main { background-color: #f9f9f9; }
        </style>
    """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn:
        st.error("Ingen forbindelse til Snowflake.")
        return

    # --- 1. FILTER: VÆLG HOLD ---
    sql_teams = f"""
        SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID 
        FROM {DB}.OPTA_MATCHINFO 
        WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}
    """
    df_teams_raw = conn.query(sql_teams)
    
    if df_teams_raw is None or df_teams_raw.empty:
        st.error("Kunne ikke finde hold for de valgte ligaer.")
        return

    hold_dict = {row['CONTESTANTHOME_NAME']: row['CONTESTANTHOME_OPTAUUID'] for _, row in df_teams_raw.iterrows()}
    
    col_f1, col_f2 = st.columns(2)
    valgt_hold_navn = col_f1.selectbox("Hold", sorted(list(hold_dict.keys())))
    valgt_hold_uuid = hold_dict[valgt_hold_navn]

    # --- 2. FILTER: VÆLG SPILLER ---
    sql_spillere = f"""
        SELECT DISTINCT TRIM(FIRST_NAME) || ' ' || TRIM(LAST_NAME) as NAVN, PLAYER_OPTAUUID
        FROM {DB}.OPTA_PLAYERS 
        WHERE TEAM_OPTAUUID = '{valgt_hold_uuid}'
    """
    df_pl = conn.query(sql_spillere)
    
    if df_pl is None or df_pl.empty:
        st.warning(f"Ingen spillere fundet for {valgt_hold_navn}")
        return

    valgt_spiller_navn = col_f2.selectbox("Spiller", sorted(df_pl['NAVN'].tolist()))
    valgt_player_uuid = df_pl[df_pl['NAVN'] == valgt_spiller_navn]['PLAYER_OPTAUUID'].iloc[0]

    # --- 3. DATA LOAD ---
    df_sum = get_physical_summary(valgt_spiller_navn, valgt_player_uuid, conn)

    if df_sum is not None and not df_sum.empty:
        # Vi tager den seneste kamp som standardvisning
        latest = df_sum.iloc[0]
        st.markdown(f"### Fysisk Analyse: {valgt_spiller_navn}")
        st.caption(f"Seneste kamp: {latest['MATCH_TEAMS']} ({latest['MATCH_DATE']})")
        
        # Hoved-metrics
        m = st.columns(4)
        m[0].metric("Total Distance", f"{round(latest['DISTANCE']/1000, 2)} km")
        m[1].metric("HSR (>19.8 km/h)", f"{int(latest['HSR'])} m")
        m[2].metric("Sprint (>25.2 km/h)", f"{int(latest['SPRINTING'])} m")
        m[3].metric("Topfart", f"{latest['TOP_SPEED']} km/h")

        # Tabs til detaljer (Uden ikoner)
        tab_splits, tab_pitch, tab_trend = st.tabs(["Minut-for-minut", "Baneoversigt", "Saeson-trend"])

        with tab_splits:
            df_splits = get_physical_splits(valgt_spiller_navn, valgt_player_uuid, latest['MATCH_DATE'], conn)
            if not df_splits.empty:
                # Dynamisk valg af metrik fra din liste
                all_metrics = sorted(df_splits['PHYSICAL_METRIC_TYPE'].unique())
                # Sætter 'Total Distance' som standard hvis den findes
                default_idx = all_metrics.index('Total Distance') if 'Total Distance' in all_metrics else 0
                
                valgt_metrik = st.selectbox("Vælg fysisk kategori", all_metrics, index=default_idx)
                
                df_plot = df_splits[df_splits['PHYSICAL_METRIC_TYPE'] == valgt_metrik]
                
                fig_splits = go.Figure()
                fig_splits.add_trace(go.Bar(
                    x=df_plot['MINUTE_SPLIT'], 
                    y=df_plot['PHYSICAL_METRIC_VALUE'],
                    marker_color='#cc0000',
                    name=valgt_metrik
                ))
                fig_splits.update_layout(
                    title=f"Fordeling af {valgt_metrik} over kampens minutter",
                    xaxis_title="Minut",
                    yaxis_title="Værdi",
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    margin=dict(t=50, b=20, l=0, r=0)
                )
                st.plotly_chart(fig_splits, use_container_width=True)
            else:
                st.info("Ingen minut-data fundet for denne kamp.")

        with tab_pitch:
            st.markdown("#### Højintensive aktioner (HI Runs)")
            col_a, col_b = st.columns(2)
            v_tip = latest['HI_RUNS_TIP'] if pd.notnull(latest['HI_RUNS_TIP']) else 0
            v_otip = latest['HI_RUNS_OTIP'] if pd.notnull(latest['HI_RUNS_OTIP']) else 0
            
            with col_a: st.pyplot(draw_static_pitch(v_tip, "Med bold (TIP)", "#2ecc71"))
            with col_b: st.pyplot(draw_static_pitch(v_otip, "Modstander har bold (OTIP)", "#e74c3c"))

        with tab_trend:
            df_trend = df_sum.sort_values('MATCH_DATE')
            fig_trend = go.Figure()
            # Linje for HSR
            fig_trend.add_trace(go.Scatter(
                x=df_trend['MATCH_DATE'], 
                y=df_trend['HSR'], 
                name="HSR (m)",
                line=dict(color='#cc0000', width=3)
            ))
            fig_trend.update_layout(
                title="Udvikling i High Speed Running over sæsonen",
                plot_bgcolor="white",
                xaxis_title="Dato",
                yaxis_title="Meter"
            )
            st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.warning("Ingen fysiske data fundet for denne spiller i databasen.")

if __name__ == "__main__":
    vis_side()
