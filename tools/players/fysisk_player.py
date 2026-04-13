import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS
import requests
from PIL import Image
from io import BytesIO

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '335', '328', '329', '43319', '331')"
CURRENT_SEASON = "2025/2026"

# --- HJÆLPEFUNKTIONER ---
@st.cache_data(ttl=3600)
def get_logo_img(opta_uuid):
    if not opta_uuid: return None
    uuid_clean = str(opta_uuid).lower().replace('t', '')
    url = next((info['logo'] for name, info in TEAMS.items() if str(info.get('opta_uuid', '')).lower().replace('t','') == uuid_clean), None)
    if not url: return None
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except: return None

def get_physical_summary(player_name, player_opta_uuid, db_conn):
    clean_id = str(player_opta_uuid).lower().replace('p', '').strip()
    # Vi søger bredt på navn eller ID for at sikre match
    sql = f"""
        SELECT 
            MATCH_DATE, MATCH_TEAMS, MATCH_SSIID,
            TRY_CAST(MINUTES AS FLOAT) as MIN_VAL, 
            DISTANCE, "HIGH SPEED RUNNING" as HSR, 
            SPRINTING, TOP_SPEED, NO_OF_HIGH_INTENSITY_RUNS as HI_RUNS
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE ("optaId" = '{clean_id}' OR PLAYER_NAME ILIKE '%{player_name}%')
          AND MATCH_DATE >= '2025-07-01'
        ORDER BY MATCH_DATE DESC
    """
    return db_conn.query(sql)

def get_physical_splits(player_opta_uuid, match_ssiid, db_conn):
    clean_id = str(player_opta_uuid).lower().replace('p', '').strip()
    sql = f"""
        SELECT 
            MINUTE_SPLIT,
            PHYSICAL_METRIC_TYPE,
            PHYSICAL_METRIC_VALUE
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SPLITS_PLAYERS
        WHERE ("PLAYER_OPTAID" = '{clean_id}' OR "PLAYER_OPTAID" LIKE '%{clean_id}%')
          AND MATCH_SSIID = '{match_ssiid}'
        ORDER BY MINUTE_SPLIT ASC
    """
    return db_conn.query(sql)

def vis_side(dp=None):
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 18px !important; font-weight: bold; }
        .main-header { font-size: 24px; font-weight: bold; margin-bottom: 20px; }
        </style>
    """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn:
        st.error("Ingen forbindelse til Snowflake.")
        return

    # --- HÅNDTERING AF SPILLERVALG (Input eller Manuel) ---
    if dp is None:
        # Hvis ingen spiller er sendt med, lav en vælger ligesom på profil-siden
        col1, col2 = st.columns(2)
        df_teams = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
        
        team_options = sorted(df_teams['CONTESTANTHOME_NAME'].tolist()) if df_teams is not None else []
        valgt_hold_navn = col1.selectbox("Vælg Hold", team_options)
        
        hold_uuid = df_teams[df_teams['CONTESTANTHOME_NAME'] == valgt_hold_navn]['CONTESTANTHOME_OPTAUUID'].iloc[0]
        
        df_players = conn.query(f"SELECT DISTINCT FIRST_NAME || ' ' || LAST_NAME as NAVN, PLAYER_OPTAUUID FROM {DB}.OPTA_PLAYERS WHERE TEAM_OPTAUUID = '{hold_uuid}'")
        valgt_spiller = col2.selectbox("Vælg Spiller", sorted(df_players['NAVN'].tolist()))
        valgt_player_uuid = df_players[df_players['NAVN'] == valgt_spiller]['PLAYER_OPTAUUID'].iloc[0]
    else:
        valgt_spiller = dp['spiller_navn']
        valgt_player_uuid = dp['spiller_uuid']
        hold_uuid = dp['hold_uuid']

    hold_logo = get_logo_img(hold_uuid)

    # --- HENT DATA ---
    with st.spinner("Henter fysisk data..."):
        df_phys = get_physical_summary(valgt_spiller, valgt_player_uuid, conn)

    if df_phys is None or df_phys.empty:
        st.info(f"Ingen fysisk data (Second Spectrum) fundet for {valgt_spiller}.")
        return

    # --- LAYOUT START ---
    st.markdown(f'<div class="main-header">{valgt_spiller} - Fysisk Rapport</div>', unsafe_allow_html=True)

    # Top Metrics (Gennemsnit)
    m_col = st.columns(4)
    m_col[0].metric("Gns. Distance", f"{round(df_phys['DISTANCE'].mean()/1000, 2)} km")
    m_col[1].metric("Gns. HSR", f"{int(df_phys['HSR'].mean())} m")
    m_col[2].metric("Max Topfart", f"{round(df_phys['TOP_SPEED'].max(), 1)} km/t")
    m_col[3].metric("Gns. HI Runs", int(df_phys['HI_RUNS'].mean()))

    st.markdown("---")

    # --- KAMPVALG TIL SPLITS ---
    df_phys['Display'] = df_phys['MATCH_DATE'].astype(str) + " : " + df_phys['MATCH_TEAMS']
    valgt_kamp = st.selectbox("Vælg kamp for minut-analyse", df_phys['Display'].tolist())
    
    match_row = df_phys[df_phys['Display'] == valgt_kamp].iloc[0]
    match_ssiid = match_row['MATCH_SSIID']

    # --- MINUT FOR MINUT GRAF ---
    df_splits = get_physical_splits(valgt_player_uuid, match_ssiid, conn)
    
    if df_splits is not None and not df_splits.empty:
        # Pivotér data så vi har metrikker som kolonner
        df_p = df_splits.pivot(index='MINUTE_SPLIT', columns='PHYSICAL_METRIC_TYPE', values='PHYSICAL_METRIC_VALUE').reset_index()
        
        fig = go.Figure()
        
        # Total Distance pr minut (Bar)
        if 'distance' in df_p.columns:
            fig.add_trace(go.Bar(
                x=df_p['MINUTE_SPLIT'], y=df_p['distance'],
                name='Meter/min', marker_color='rgba(180, 180, 180, 0.4)', yaxis='y2'
            ))
        
        # HSR pr minut (Linje)
        if 'high_speed_running' in df_p.columns:
            fig.add_trace(go.Scatter(
                x=df_p['MINUTE_SPLIT'], y=df_p['high_speed_running'],
                name='HSR Meter', line=dict(color='#cc0000', width=3)
            ))

        fig.update_layout(
            title=f"Intensitet i kampen: {valgt_kamp}",
            hovermode="x unified",
            yaxis=dict(title="HSR (m)"),
            yaxis2=dict(title="Total Distance (m)", overlaying='y', side='right', showgrid=False),
            xaxis=dict(title="Minut"),
            plot_bgcolor='white',
            height=350
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Der blev ikke fundet minut-splits for denne kamp.")

    # --- TABEL OVERSIGT ---
    st.subheader("Kamp-log")
    st.dataframe(
        df_phys[['MATCH_DATE', 'MATCH_TEAMS', 'MIN_VAL', 'DISTANCE', 'HSR', 'TOP_SPEED', 'HI_RUNS']],
        hide_index=True,
        use_container_width=True
    )

if __name__ == "__main__":
    vis_side()
