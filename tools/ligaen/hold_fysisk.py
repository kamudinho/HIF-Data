import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
SEASON_START = "2025-07-01"
LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '328', '329', '43319', '331', '1305')"

@st.cache_resource
def get_cached_conn():
    return _get_snowflake_conn()

def vis_liga_benchmark(conn, valgt_hold_navn):
    """Genererer scatter plot over hele ligaens fysiske profil"""
    
    # Hent gennemsnit for alle hold i sæsonen
    sql_liga = f"""
        SELECT 
            MATCH_TEAMS,
            AVG(HOLD_HI) as AVG_HI,
            MAX(MAX_SPEED) as PEAK_SPEED
        FROM (
            SELECT 
                MATCH_SSIID,
                MATCH_TEAMS,
                SUM(NO_OF_HIGH_INTENSITY_RUNS) as HOLD_HI,
                MAX(TOP_SPEED) as MAX_SPEED
            FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
            WHERE MATCH_DATE >= '{SEASON_START}'
            GROUP BY 1, 2
        )
        GROUP BY 1
    """
    df_liga = conn.query(sql_liga)

    if df_liga is not None and not df_liga.empty:
        st.subheader("Liga-benchmark: Intensitet vs. Topfart")
        
        # Opret scatter plot
        fig = px.scatter(
            df_liga, 
            x='AVG_HI', 
            y='PEAK_SPEED',
            text='MATCH_TEAMS',
            labels={{
                'AVG_HI': 'HI Aktiviteter (Gns. per kamp)',
                'PEAK_SPEED': 'Peak Sprint Velocity (km/t)'
            }}
        )

        # Grundlæggende styling
        fig.update_traces(
            marker=dict(size=12, opacity=0.4, color='grey'),
            textposition='top center'
        )

        # Fremhæv det valgte hold
        highlight = df_liga[df_liga['MATCH_TEAMS'].str.contains(valgt_hold_navn, case=False, na=False)]
        if not highlight.empty:
            fig.add_trace(go.Scatter(
                x=highlight['AVG_HI'],
                y=highlight['PEAK_SPEED'],
                mode='markers+text',
                marker=dict(size=18, color='#cc0000', line=dict(width=2, color='white')),
                text=[valgt_hold_navn],
                textposition="top center",
                showlegend=False
            ))

        # Gennemsnitslinjer
        avg_hi = df_liga['AVG_HI'].mean()
        avg_speed = df_liga['PEAK_SPEED'].mean()
        fig.add_vline(x=avg_hi, line_dash="dash", line_color="grey")
        fig.add_hline(y=avg_speed, line_dash="dash", line_color="grey")

        fig.update_layout(height=500, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

def vis_side():
    st.markdown("""<style>
        [data-testid="stMetricValue"] { font-size: 26px !important; font-weight: bold !important; color: #333; }
    </style>""", unsafe_allow_html=True)

    conn = get_cached_conn()
    
    # 1. VALG AF HOLD
    df_teams = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME as NAME FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS} ORDER BY 1")
    
    if df_teams is None or df_teams.empty:
        st.error("Kunne ikke hente hold-data.")
        return

    c1, c2 = st.columns(2)
    valgt_hold = c1.selectbox("Vælg Hold", df_teams['NAME'].unique())
    target_ssiid = TEAMS.get(valgt_hold, {{}}).get('ssid')

    # 2. VALG AF KAMP
    df_matches = conn.query(f"""
        SELECT DISTINCT 
            MATCH_SSIID, 
            DATE as CALC_DATE,
            DESCRIPTION as MATCH_NAME
        FROM {DB}.SECONDSPECTRUM_SEASON_METADATA
        WHERE (HOME_SSIID = '{target_ssiid}' OR AWAY_SSIID = '{target_ssiid}')
          AND DATE >= '{SEASON_START}'
          AND DATE <= CURRENT_DATE()
        ORDER BY DATE DESC
    """)

    if df_matches is None or df_matches.empty:
        st.warning("Ingen spillede kampe fundet.")
        # Vi viser stadig liga-benchmarket selvom der ikke er valgt en specifik kamp
        vis_liga_benchmark(conn, valgt_hold)
        return

    df_matches['DATO_STR'] = pd.to_datetime(df_matches['CALC_DATE']).dt.strftime('%d/%m')
    df_matches['SELECT_LABEL'] = df_matches['DATO_STR'] + " - " + df_matches['MATCH_NAME']
    valgt_kamp_label = c2.selectbox("Vælg Kamp", df_matches['SELECT_LABEL'].tolist())
    valgt_match_ssiid = df_matches[df_matches['SELECT_LABEL'] == valgt_kamp_label]['MATCH_SSIID'].iloc[0]

    # 3. KAMP-OPSUMMERING (HOLDNIVEAU)
    df_hold_summary = conn.query(f"""
        SELECT 
            SUM(DISTANCE) as TOTAL_DIST,
            SUM("HIGH SPEED RUNNING") as TOTAL_HSR,
            SUM(SPRINTING) as TOTAL_SPRINT,
            SUM(NO_OF_HIGH_INTENSITY_RUNS) as TOTAL_HI,
            SUM(HSR_DISTANCE_TIP) as HSR_TIP,
            SUM(HSR_DISTANCE_OTIP) as HSR_OTIP
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_SSIID = '{valgt_match_ssiid}'
    """)

    if df_hold_summary is not None and not df_hold_summary.empty:
        hold = df_hold_summary.iloc[0]
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Distance", f"{{round(hold['TOTAL_DIST']/1000, 1)}} km")
        m2.metric("HSR Distance", f"{{int(hold['TOTAL_HSR'])}} m")
        m3.metric("Sprint Distance", f"{{int(hold['TOTAL_SPRINT'])}} m")
        m4.metric("HI Aktiviteter", f"{{int(hold['TOTAL_HI'])}}")

        st.divider()

        # 4. LIGA BENCHMARK (SCATTER PLOT)
        vis_liga_benchmark(conn, valgt_hold)

        st.divider()

        # 5. FASEFORDELING OG SPLITS
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("Fysisk Fase-fordeling")
            fig_pie = go.Figure(data=[go.Pie(
                labels=['Med bold (TIP)', 'Uden bold (OTIP)'],
                values=[hold['HSR_TIP'], hold['HSR_OTIP']],
                hole=.4,
                marker_colors=['#cc0000', '#333333']
            )])
            fig_pie.update_layout(height=400)
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_right:
            df_splits = conn.query(f"""
                SELECT MINUTE_SPLIT, SUM(PHYSICAL_METRIC_VALUE) as VAL
                FROM {DB}.SECONDSPECTRUM_PHYSICAL_SPLITS_PLAYERS
                WHERE MATCH_SSIID = '{valgt_match_ssiid}'
                  AND PHYSICAL_METRIC_TYPE = 'Distance'
                GROUP BY 1 ORDER BY 1 ASC
            """)
            
            if df_splits is not None and not df_splits.empty:
                st.subheader("Intensitet over tid")
                fig_bar = px.bar(df_splits, x='MINUTE_SPLIT', y='VAL', color_discrete_sequence=['#cc0000'])
                fig_bar.update_layout(height=400, xaxis_title="Minutter", yaxis_title="Meter")
                st.plotly_chart(fig_bar, use_container_width=True)

    # 6. SPILLER TABEL
    st.subheader("Individuelle præstationer i kampen")
    df_players = conn.query(f"""
        SELECT PLAYER_NAME, DISTANCE, "HIGH SPEED RUNNING", SPRINTING, TOP_SPEED
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_SSIID = '{valgt_match_ssiid}'
        ORDER BY DISTANCE DESC
    """)
    if df_players is not None:
        st.dataframe(df_players, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    vis_side()
