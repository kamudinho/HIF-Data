import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from mplsoccer import Pitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_IDS = "('335', '328', '329', '43319', '331')"

def get_physical_data_with_splits(player_name, player_opta_uuid, valgt_hold_navn, db_conn):
    """Henter fysisk data inklusiv TIP/OTIP/BOP splits"""
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
            -- POSSESSION SPLITS
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

def draw_intensity_pitch(val, title, cmap_color):
    """Hjælpefunktion til at tegne en bane med intensitets-markeringer"""
    pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD', line_zorder=2)
    fig, ax = pitch.draw(figsize=(6, 4))
    
    # Da vi arbejder med aggregerede tal per kamp, illustrerer vi her 
    # intensiteten som en visualisering af spillerens volumen i fasen
    ax.text(50, 50, f"{int(val)}", color=cmap_color, fontsize=30, 
            fontweight='bold', ha='center', va='center', alpha=0.3)
    ax.set_title(title, fontsize=12, pad=10)
    return fig

def vis_side():
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 18px !important; font-weight: bold !important; color: #cc0000; }
        [data-testid="stMetricLabel"] { font-size: 11px !important; }
        .stTabs [data-baseweb="tab-list"] { gap: 24px; }
        .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #f0f2f6; border-radius: 4px 4px 0 0; gap: 1px; padding-top: 10px; padding-bottom: 10px; }
        .stTabs [aria-selected="true"] { background-color: #cc0000; color: white; }
        </style>
    """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn: return

    # --- TOP MENU ---
    col_h1, col_h2 = st.columns(2)
    
    hold_liste = sorted(list(TEAMS.keys()))
    valgt_hold = col_h1.selectbox("Vælg Hold", hold_liste)
    valgt_uuid_hold = TEAMS[valgt_hold].get('opta_uuid')

    sql_spillere = f"""
        SELECT DISTINCT TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as NAVN, e.PLAYER_OPTAUUID
        FROM {DB}.OPTA_EVENTS e
        JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
        WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid_hold}' 
        AND e.EVENT_TIMESTAMP >= '2025-07-01'
    """
    df_pl = conn.query(sql_spillere)
    
    if df_pl is None or df_pl.empty:
        st.warning("Ingen spillere fundet.")
        return

    valgt_spiller = col_h2.selectbox("Vælg Spiller", sorted(df_pl['NAVN'].tolist()))
    valgt_player_uuid = df_pl[df_pl['NAVN'] == valgt_spiller]['PLAYER_OPTAUUID'].iloc[0]

    st.markdown("---")

    # --- DATA LOAD ---
    df = get_physical_data_with_splits(valgt_spiller, valgt_player_uuid, valgt_hold, conn)

    if df is not None and not df.empty:
        latest = df.iloc[0]
        
        # 1. OVERORDNEDE METRICS
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Distance", f"{round(latest['DISTANCE']/1000, 2)} km")
        m2.metric("HSR (Zone 4+5)", f"{int(latest['HSR'])} m")
        m3.metric("Sprint (Zone 6)", f"{int(latest['SPRINTING'])} m")
        m4.metric("HI Runs (Total)", int(latest['HI_RUNS']))

        st.markdown("<br>", unsafe_allow_html=True)

        # 2. ZONE & SPLIT ANALYSE
        t_zones, t_trends, t_raw = st.tabs(["📍 Intensitets-Zoner", "📈 Udvikling", "📄 Rå Data"])

        with t_zones:
            st.subheader("Hvor foregår de højintensive løb?")
            st.write("Visualisering af HI-Runs fordelt på spillets faser (TIP vs OTIP).")
            
            z_col1, z_col2 = st.columns(2)
            
            # TIP Bane (Offensiv)
            with z_col1:
                fig_tip = draw_intensity_pitch(latest['HI_RUNS_TIP'], "HI Runs: TIP (Med bold)", "#2ecc71")
                st.pyplot(fig_tip)
                st.markdown(f"<center><b>{int(latest['HI_RUNS_TIP'])}</b> højintensive aktioner</center>", unsafe_allow_html=True)

            # OTIP Bane (Defensiv)
            with z_col2:
                fig_otip = draw_intensity_pitch(latest['HI_RUNS_OTIP'], "HI Runs: OTIP (Uden bold)", "#e74c3c")
                st.pyplot(fig_otip)
                st.markdown(f"<center><b>{int(latest['HI_RUNS_OTIP'])}</b> højintensive aktioner</center>", unsafe_allow_html=True)

            st.markdown("---")
            
            # Cirkeldiagram for Distance-splits
            st.subheader("Distance Fordeling")
            fig_pie = go.Figure(data=[go.Pie(
                labels=['Med bold (TIP)', 'Modstander med bold (OTIP)', 'Bold ude (BOP)'],
                values=[latest['DISTANCE_TIP'], latest['DISTANCE_OTIP'], latest['DISTANCE_BOP']],
                hole=.4,
                marker_colors=['#2ecc71', '#e74c3c', '#95a5a6']
            )])
            fig_pie.update_layout(height=400, margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig_pie, use_container_width=True)

        with t_trends:
            st.subheader("Sæsonudvikling: Fysisk Output")
            df_trend = df.sort_values('MATCH_DATE')
            
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(x=df_trend['MATCH_DATE'], y=df_trend['HSR'], name="Total HSR", line=dict(color='#cc0000', width=3)))
            fig_trend.add_trace(go.Scatter(x=df_trend['MATCH_DATE'], y=df_trend['HSR_TIP'], name="HSR i TIP", line=dict(color='#2ecc71', dash='dot')))
            fig_trend.add_trace(go.Scatter(x=df_trend['MATCH_DATE'], y=df_trend['HSR_OTIP'], name="HSR i OTIP", line=dict(color='#e74c3c', dash='dot')))
            
            fig_trend.update_layout(plot_bgcolor="white", height=400, hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_trend, use_container_width=True)

        with t_raw:
            st.dataframe(df, hide_index=True, use_container_width=True)
            
    else:
        st.info(f"Ingen fysiske data fundet for {valgt_spiller} i denne sæson.")

if __name__ == "__main__":
    vis_side()
