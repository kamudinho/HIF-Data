import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data.data_load import _get_snowflake_conn

def vis_side():
    """Hovedfunktion der kaldes fra hif_dash.py"""
    
    # Hent forbindelse (bruger din eksisterende funktion)
    conn = _get_snowflake_conn()
    
    # 1. DATA FETCHING
    # Vi henter både summary (totaler) og splits (interval-data)
    @st.cache_data(ttl=3600)
    def load_physical_team_data():
        query_summary = """
        SELECT MATCH_SSIID, MATCH_DATE, MATCH_TEAMS, PLAYER_NAME, 
               DISTANCE, RUNNING, "HIGH SPEED RUNNING", SPRINTING, 
               NO_OF_HIGH_INTENSITY_RUNS, TOP_SPEED,
               HSR_DISTANCE_TIP, HSR_DISTANCE_OTIP
        FROM SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        """
        query_splits = """
        SELECT MATCH_SSIID, MINUTE_SPLIT, PHYSICAL_METRIC_TYPE, PHYSICAL_METRIC_VALUE
        FROM SECONDSPECTRUM_PHYSICAL_SPLITS_PLAYERS
        WHERE PHYSICAL_METRIC_TYPE = 'DISTANCE'
        """
        df_sum = conn.query(query_summary)
        df_spl = conn.query(query_splits)
        return df_sum, df_spl

    df_summary, df_splits = load_physical_team_data()

    if df_summary.empty:
        st.warning("Ingen fysiske data fundet i databasen.")
        return

    # 2. FILTRERING (Vælg kamp)
    alle_kampe = df_summary['MATCH_TEAMS'].unique().tolist()
    valgt_kamp = st.selectbox("Vælg Kamp", alle_kampe, index=len(alle_kampe)-1)
    
    # Filtrer data for den valgte kamp
    match_df = df_summary[df_summary['MATCH_TEAMS'] == valgt_kamp]
    match_id = match_df['MATCH_SSIID'].iloc[0]
    
    # Aggreger til hold-totaler for den valgte kamp
    team_total = match_df.agg({
        'DISTANCE': 'sum',
        'HIGH SPEED RUNNING': 'sum',
        'SPRINTING': 'sum',
        'NO_OF_HIGH_INTENSITY_RUNS': 'sum'
    })

    # 3. KPI OVERBLIK
    # Beregn liga-gennemsnit for at give kontekst (delta)
    liga_avg = df_summary.groupby('MATCH_SSIID').agg({'DISTANCE': 'sum'}).mean()['DISTANCE']
    
    c1, c2, c3, c4 = st.columns(4)
    with st.container(border=True):
        c1.metric("Total Distance", f"{team_total['DISTANCE']/1000:.1f} km", 
                  delta=f"{(team_total['DISTANCE'] - liga_avg)/1000:.1f} km vs liga-snit")
        c2.metric("HSR (20-25 km/t)", f"{team_total['HIGH SPEED RUNNING']:.0f} m")
        c3.metric("Sprint (>25 km/t)", f"{team_total['SPRINTING']:.0f} m")
        c4.metric("HI Aktiviteter", f"{team_total['NO_OF_HIGH_INTENSITY_RUNS']:.0f}")

    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        # 4. PERIODE ANALYSE (Hvor i kampen løber vi mest?)
        st.subheader("⏱️ Intensitet per 15 min.")
        kamp_splits = df_splits[df_splits['MATCH_SSIID'] == match_id].copy()
        kamp_splits['INTERVAL'] = (kamp_splits['MINUTE_SPLIT'] // 15) * 15
        period_data = kamp_splits.groupby('INTERVAL')['PHYSICAL_METRIC_VALUE'].sum().reset_index()
        
        # Omdøb interval til læsbare navne
        interval_map = {0: "0-15'", 15: "15-30'", 30: "30-45'", 45: "45-60'", 60: "60-75'", 75: "75-90'", 90: "90+'"}
        period_data['Minutter'] = period_data['INTERVAL'].map(interval_map)

        fig_period = px.bar(period_data, x='Minutter', y='PHYSICAL_METRIC_VALUE',
                            title="Total distance fordelt på tid",
                            color_discrete_sequence=['#df003b'])
        st.plotly_chart(fig_period, use_container_width=True)

    with col_right:
        # 5. TIP vs OTIP (Med bold vs Uden bold)
        st.subheader("⚽ Boldbesiddelse & Løb")
        tip_hsr = match_df['HSR_DISTANCE_TIP'].sum()
        otip_hsr = match_df['HSR_DISTANCE_OTIP'].sum()
        
        fig_pos = go.Figure(data=[go.Pie(labels=['Med bold (TIP)', 'Uden bold (OTIP)'], 
                                         values=[tip_hsr, otip_hsr], 
                                         hole=.3,
                                         marker_colors=['#df003b', '#333'])])
        fig_pos.update_layout(title="HSR Distance fordelt på boldbesiddelse")
        st.plotly_chart(fig_pos, use_container_width=True)

    # 6. SPILLER TOPLISTE
    st.subheader("🔝 Top 5 Performere (Distance)")
    top_players = match_df.sort_values('DISTANCE', ascending=False).head(5)
    
    # Vi viser spillerne i en tabel med en lille bar-chart ved siden af
    st.dataframe(
        top_players[['PLAYER_NAME', 'DISTANCE', 'HIGH SPEED RUNNING', 'SPRINTING', 'TOP_SPEED']],
        column_config={
            "DISTANCE": st.column_config.NumberColumn("Distance (m)", format="%d m"),
            "TOP_SPEED": st.column_config.NumberColumn("Topfart (km/t)", format="%.1f km/t")
        },
        use_container_width=True,
        hide_index=True
    )
