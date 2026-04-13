import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from mplsoccer import Pitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS
import requests
from PIL import Image
from io import BytesIO

# --- IMPORT FRA MAPPING ---
from data.utils.mapping import (
    OPTA_EVENT_TYPES, 
    OPTA_QUALIFIERS,
    get_action_label
)

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

def draw_player_info_box(ax, team_logo, player_name, season_str, category_str):
    if team_logo:
        ax_l = ax.inset_axes([0.02, 0.88, 0.07, 0.07], transform=ax.transAxes)
        ax_l.imshow(team_logo)
        ax_l.axis('off')
    ax.text(0.10, 0.92, str(player_name).upper(), transform=ax.transAxes, 
            fontsize=10, fontweight='bold', color='black', va='center')
    ax.text(0.10, 0.89, f"{season_str} | {category_str}", transform=ax.transAxes, 
            fontsize=8, color='#666666', va='center')

def get_physical_data(player_name, player_opta_uuid, valgt_hold_navn, db_conn):
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
            SUM(p.NO_OF_HIGH_INTENSITY_RUNS) as HI_RUNS
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS p
        WHERE (({name_conditions}) OR ("optaId" LIKE '%{clean_id}%'))
          AND p.MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'
          AND p.MATCH_SSIID IN (
              SELECT MATCH_SSIID 
              FROM {DB}.SECONDSPECTRUM_GAME_METADATA
              WHERE HOME_SSIID = '{target_ssiid}' 
                 OR AWAY_SSIID = '{target_ssiid}'
          )
        GROUP BY p.MATCH_DATE, p.PLAYER_NAME
        ORDER BY p.MATCH_DATE DESC
    """
    return db_conn.query(sql)

def vis_side(dp=None):
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 18px !important; font-weight: bold !important; color: #cc0000; }
        [data-testid="stMetricLabel"] { font-size: 11px !important; }
        .main-header { font-size: 24px; font-weight: bold; margin-bottom: 20px; }
        </style>
        """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn: return

    # --- SIDEBAR FILTRE ---
    st.sidebar.title("Fysisk Filter")
    
    # 1. Hent hold
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
    mapping_lookup = {str(info['opta_uuid']).lower().replace('t', ''): name for name, info in TEAMS.items() if 'opta_uuid' in info}

    team_map = {}
    if df_teams_raw is not None:
        for _, r in df_teams_raw.iterrows():
            uuid_clean = str(r['CONTESTANTHOME_OPTAUUID']).lower().replace('t','')
            if uuid_clean in mapping_lookup:
                team_map[mapping_lookup[uuid_clean]] = r['CONTESTANTHOME_OPTAUUID']

    valgt_hold = st.sidebar.selectbox("Vælg Hold", sorted(list(team_map.keys())))
    valgt_uuid_hold = team_map[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid_hold)

    # 2. Hent spillere for valgte hold
    sql_spillere = f"""
        SELECT DISTINCT TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as NAVN, e.PLAYER_OPTAUUID
        FROM {DB}.OPTA_EVENTS e
        JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
        WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid_hold}' 
        AND e.EVENT_TIMESTAMP >= '2025-07-01'
    """
    df_pl = conn.query(sql_spillere)
    
    if df_pl is None or df_pl.empty:
        st.sidebar.warning("Ingen spillere fundet.")
        return

    spiller_navne = sorted(df_pl['NAVN'].tolist())
    valgt_spiller = st.sidebar.selectbox("Vælg Spiller", spiller_navne)
    valgt_player_uuid = df_pl[df_pl['NAVN'] == valgt_spiller]['PLAYER_OPTAUUID'].iloc[0]

    # --- HOVEDINDHOLD ---
    st.markdown(f'<div class="main-header">Fysisk Profil: {valgt_spiller}</div>', unsafe_allow_html=True)

    df_phys = get_physical_data(valgt_spiller, valgt_player_uuid, valgt_hold, conn)

    if df_phys is not None and not df_phys.empty:
        df_phys['MATCH_DATE'] = pd.to_datetime(df_phys['MATCH_DATE'])
        latest = df_phys.iloc[0]
        avg_dist = df_phys['DISTANCE'].mean()
        avg_hsr = df_phys['HSR'].mean()

        # Quick Stats Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Seneste Distance", f"{round(latest['DISTANCE']/1000, 2)} km", delta=f"{round((latest['DISTANCE'] - avg_dist)/1000, 2)} km")
        m2.metric("Seneste HSR", f"{int(latest['HSR'])} m", delta=f"{int(latest['HSR'] - avg_hsr)} m")
        m3.metric("Sæson Topfart", f"{round(df_phys['TOP_SPEED'].max(), 1)} km/t")
        m4.metric("HI Akt. (Gns)", int(df_phys['HI_RUNS'].mean()))

        st.markdown("---")

        t_charts, t_data = st.tabs(["📊 Performance Grafer", "📋 Kamp-log"])

        with t_charts:
            cat_choice = st.segmented_control("Vælg metrik", options=["HSR (m)", "Sprint (m)", "Distance (km)", "Topfart (km/t)"], default="HSR (m)")
            mapping = {"HSR (m)": ("HSR", 1, "m"), "Sprint (m)": ("SPRINTING", 1, "m"), "Distance (km)": ("DISTANCE", 1000, "km"), "Topfart (km/t)": ("TOP_SPEED", 1, "km/t")}
            col, div, suffix = mapping[cat_choice]

            df_chart = df_phys.copy().sort_values('MATCH_DATE')
            df_chart['Opponent'] = df_chart['MATCH_TEAMS'].apply(lambda x: x.replace(valgt_hold, '').replace('-', '').strip())
            df_chart['Label'] = df_chart['Opponent'] + "<br>" + df_chart['MATCH_DATE'].dt.strftime('%d/%m')
            
            y_vals = df_chart[col] / div
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df_chart['Label'], y=y_vals,
                text=y_vals.apply(lambda x: f"{x:.1f}" if x < 50 else f"{int(x)}"),
                textposition='outside', marker_color='#cc0000'
            ))
            
            # Gennemsnitslinje
            fig.add_shape(type="line", x0=-0.5, x1=len(df_chart)-0.5, y0=y_vals.mean(), y1=y_vals.mean(),
                         line=dict(color="gray", width=2, dash="dash"))

            fig.update_layout(
                plot_bgcolor="white", height=400, margin=dict(t=20, b=80, l=10, r=10),
                xaxis=dict(tickangle=-45, type='category'),
                yaxis=dict(showgrid=True, gridcolor='#f0f0f0', showticklabels=False, range=[0, y_vals.max() * 1.3]),
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        with t_data:
            st.dataframe(df_phys[['MATCH_DATE', 'MATCH_TEAMS', 'MINUTES', 'DISTANCE', 'HSR', 'TOP_SPEED', 'HI_RUNS']], 
                         hide_index=True, use_container_width=True)
    else:
        st.info("Ingen fysisk data fundet for denne spiller i den valgte periode.")

if __name__ == "__main__":
    vis_side()
