import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from data.data_load import _get_snowflake_conn

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
HVIDOVRE_SSIID = '56fa29c7-3a48-4186-9d14-dbf45fbc78d9'

def get_hvidovre_players(db_conn):
    """Henter alle spillere der har spillet for Hvidovre i SS-data"""
    sql = f"""
        SELECT DISTINCT PLAYER_NAME, "optaId" 
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_DATE >= '2025-07-01'
        ORDER BY PLAYER_NAME
    """
    return db_conn.query(sql)

def get_advanced_physical_data(player_opta_id, db_conn):
    """Henter den fulde fysiske profil med TIP/OTIP/BOP logik"""
    sql = f"""
    WITH hvidovre_ids AS (
        SELECT DISTINCT
            m.MATCH_SSIID, 
            f.value:"optaId"::string AS opta_id
        FROM {DB}.SECONDSPECTRUM_GAME_METADATA m,
        LATERAL FLATTEN(input => CASE 
            WHEN m.HOME_SSIID = '{HVIDOVRE_SSIID}' THEN m.HOME_PLAYERS 
            ELSE m.AWAY_PLAYERS 
        END) f
        WHERE m.HOME_SSIID = '{HVIDOVRE_SSIID}' 
           OR m.AWAY_SSIID = '{HVIDOVRE_SSIID}'
    )
    SELECT 
        p.MATCH_DATE, p.MATCH_TEAMS, p.PLAYER_NAME, p.MINUTES,
        p.DISTANCE, p.TOP_SPEED, p.AVERAGE_SPEED,
        p.WALKING, p.JOGGING, p.RUNNING, 
        p."HIGH SPEED RUNNING" AS DISTANCE_HSR,
        p.SPRINTING AS DISTANCE_SPRINT,
        p.NO_OF_HIGH_INTENSITY_RUNS AS HI_RUNS_TOTAL,
        p.DISTANCE_TIP, p.HSR_DISTANCE_TIP, p.SPRINT_DISTANCE_TIP, 
        p.NO_OF_HIGH_INTENSITY_RUNS_TIP AS HI_RUNS_TIP,
        p.DISTANCE_OTIP, p.HSR_DISTANCE_OTIP, p.SPRINT_DISTANCE_OTIP, 
        p.NO_OF_HIGH_INTENSITY_RUNS_OTIP AS HI_RUNS_OTIP,
        p.DISTANCE_BOP, p.MATCH_SSIID
    FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS p
    INNER JOIN hvidovre_ids h 
        ON p.MATCH_SSIID = h.MATCH_SSIID 
        AND p."optaId" = h.opta_id
    WHERE p."optaId" = '{player_opta_id}'
      AND p.MATCH_DATE >= '2025-07-01'
    ORDER BY p.MATCH_DATE DESC
    """
    return db_conn.query(sql)

def vis_side():
    st.markdown("""
        <style>
        .stMetric { background-color: #f8f9fa; padding: 10px; border-radius: 10px; border: 1px solid #eee; }
        [data-testid="stMetricValue"] { color: #cc0000; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn:
        st.error("Databaseforbindelse fejlede.")
        return

    # --- SIDEBAR SELECTOR ---
    df_players = get_hvidovre_players(conn)
    if df_players is not None and not df_players.empty:
        valgt_navn = st.sidebar.selectbox("Vælg Spiller", df_players['PLAYER_NAME'].tolist())
        valgt_id = df_players[df_players['PLAYER_NAME'] == valgt_navn]['optaId'].iloc[0]
    else:
        st.error("Kunne ikke hente spillerliste.")
        return

    # --- DATA LOAD ---
    df = get_advanced_physical_data(valgt_id, conn)
    if df is None or df.empty:
        st.warning("Ingen fysisk data fundet for denne spiller.")
        return

    st.title(f"Fysisk Profil: {valgt_navn}")
    
    # --- OVERORDNET SÆSON-SNIT ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Gns. Distance", f"{round(df['DISTANCE'].mean()/1000, 2)} km")
    col2.metric("Gns. HSR", f"{int(df['DISTANCE_HSR'].mean())} m")
    col3.metric("Topfart (Sæson)", f"{round(df['TOP_SPEED'].max(), 1)} km/t")
    col4.metric("Gns. HI Runs", int(df['HI_RUNS_TOTAL'].mean()))

    st.markdown("---")

    # --- KAMP-VALG ---
    df['Match_Label'] = df['MATCH_DATE'].astype(str) + " : " + df['MATCH_TEAMS']
    valgt_kamp = st.selectbox("Vælg Kamp for detaljeret analyse", df['Match_Label'].tolist())
    row = df[df['Match_Label'] == valgt_kamp].iloc[0]

    # --- DETALJERET ANALYSE ---
    c_left, c_right = st.columns([1, 1])

    with c_left:
        st.subheader("Possession Breakdown")
        # Pie chart for Distance i faser
        fig_pie = go.Figure(data=[go.Pie(
            labels=['Eget hold (TIP)', 'Modstander (OTIP)', 'Bold ude (BOP)'],
            values=[row['DISTANCE_TIP'], row['DISTANCE_OTIP'], row['DISTANCE_BOP']],
            hole=.4,
            marker_colors=['#2ecc71', '#e74c3c', '#95a5a6']
        )])
        fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=300)
        st.plotly_chart(fig_pie, use_container_width=True)
        
        # HI Runs split
        st.write(f"**Højintensive aktioner (HI Runs):** {int(row['HI_RUNS_TOTAL'])}")
        st.caption(f"TIP (Med bold): {int(row['HI_RUNS_TIP'])} | OTIP (Uden bold): {int(row['HI_RUNS_OTIP'])}")

    with c_right:
        st.subheader("Intensitetszoner (m)")
        zone_data = {
            'Zone': ['Walking', 'Jogging', 'Running', 'HSR', 'Sprinting'],
            'Meter': [row['WALKING'], row['JOGGING'], row['RUNNING'], row['DISTANCE_HSR'], row['DISTANCE_SPRINT']]
        }
        fig_zones = px.bar(zone_data, x='Zone', y='Meter', color='Zone', 
                           color_discrete_sequence=px.colors.sequential.Reds_r)
        fig_zones.update_layout(showlegend=False, plot_bgcolor='white', height=300, margin=dict(t=0, b=0))
        st.plotly_chart(fig_zones, use_container_width=True)

    # --- TREND GRAF ---
    st.markdown("---")
    st.subheader("Sæsonudvikling: Distance vs. Intensitet")
    
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(x=df['MATCH_DATE'], y=df['DISTANCE'], name="Total Dist.", line=dict(color='#333', width=2)))
    fig_trend.add_trace(go.Scatter(x=df['MATCH_DATE'], y=df['DISTANCE_HSR'], name="HSR", yaxis="y2", line=dict(color='#cc0000', width=3)))
    
    fig_trend.update_layout(
        yaxis=dict(title="Total Distance (m)"),
        yaxis2=dict(title="HSR (m)", overlaying='y', side='right'),
        hovermode="x unified",
        legend=dict(orientation="h", y=1.1),
        plot_bgcolor='white'
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    with st.expander("Se kampskema (Rå data)"):
        st.dataframe(df[['MATCH_DATE', 'MATCH_TEAMS', 'MINUTES', 'DISTANCE', 'DISTANCE_HSR', 'TOP_SPEED', 'HI_RUNS_TOTAL']], 
                     hide_index=True, use_container_width=True)

if __name__ == "__main__":
    vis_side()
