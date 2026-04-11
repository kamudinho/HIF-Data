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
    target_ssiid = TEAMS.get(valgt_hold_navn, {}).get('ssid')
    if not target_ssiid:
        target_ssiid = '56fa29c7-3a48-4186-9d14-dbf45fbc78d9'

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
        [data-testid="stMetricValue"] { font-size: 16px !important; text-align: center; font-weight: bold !important; width: 100%; }
        [data-testid="stMetricLabel"] { font-size: 10px !important; text-align: center; width: 100%; }
        [data-testid="stMetric"] { display: flex; flex-direction: column; align-items: center; }
        .player-header { font-size: 20px; font-weight: bold; margin-bottom: 10px; color: #1E1E1E; }
        </style>
        """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn: return

    # 1. HOLDVALG
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
    mapping_lookup = {str(info['opta_uuid']).lower().replace('t', ''): name for name, info in TEAMS.items() if 'opta_uuid' in info}
    
    team_map = {}
    if df_teams_raw is not None:
        for _, r in df_teams_raw.iterrows():
            uuid_clean = str(r['CONTESTANTHOME_OPTAUUID']).lower().replace('t','')
            if uuid_clean in mapping_lookup:
                team_map[mapping_lookup[uuid_clean]] = r['CONTESTANTHOME_OPTAUUID']

    col_spacer_top, col_h_hold, col_h_spiller = st.columns([2, 1.2, 1.2])
    valgt_hold = col_h_hold.selectbox("Hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid_hold = team_map[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid_hold)

    # 2. HENT DATA
    with st.spinner("Henter spillerdata..."):
        sql = f"""
            SELECT 
                e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, 
                TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as VISNINGSNAVN, 
                e.PLAYER_OPTAUUID, e.EVENT_OUTCOME as OUTCOME,
                TO_CHAR(e.EVENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS') as EVENT_TIMESTAMP_STR,
                LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
            FROM {DB}.OPTA_EVENTS e
            JOIN (SELECT DISTINCT PLAYER_OPTAUUID, FIRST_NAME, LAST_NAME FROM {DB}.OPTA_PLAYERS WHERE FIRST_NAME IS NOT NULL) p 
                ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
            LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid_hold}' 
            AND e.EVENT_TIMESTAMP >= '2025-07-01'
            GROUP BY 1, 2, 3, 4, 5, 6, 7
        """
        df_all = conn.query(sql)
        if df_all is None or df_all.empty:
            st.warning("Ingen hændelsesdata fundet.")
            return
        
        df_all = df_all.dropna(subset=['VISNINGSNAVN'])
        df_all['EVENT_TIMESTAMP'] = pd.to_datetime(df_all['EVENT_TIMESTAMP_STR'])
        df_all['qual_list'] = df_all['QUALIFIERS'].fillna('').str.split(',')
        df_all['Action_Label'] = df_all.apply(get_action_label, axis=1)

    # FILTRERING: Kun spillere aktive i 2026
    spiller_liste = sorted(df_all[df_all['EVENT_TIMESTAMP'] >= '2026-01-01']['VISNINGSNAVN'].unique())
    if not spiller_liste:
        spiller_liste = sorted(df_all['VISNINGSNAVN'].unique())
        
    valgt_spiller = col_h_spiller.selectbox("Spiller", spiller_liste, label_visibility="collapsed")
    
    valgt_player_uuid = df_all[df_all['VISNINGSNAVN'] == valgt_spiller]['PLAYER_OPTAUUID'].iloc[0]
    df_spiller = df_all[df_all['VISNINGSNAVN'] == valgt_spiller].copy()

    t_pitch, t_phys, t_stats, t_compare = st.tabs(["Spillerprofil", "Fysisk Data", "Statistik & Grafer", "Sammenligning"])

    # --- TAB: FYSISK DATA ---
    with t_phys:
        df_phys = get_physical_data(valgt_spiller, valgt_player_uuid, valgt_hold, conn)
        
        if df_phys is not None and not df_phys.empty:
            df_phys['MATCH_DATE'] = pd.to_datetime(df_phys['MATCH_DATE'])
            df_phys = df_phys.sort_values('MATCH_DATE', ascending=False)
            
            avg_dist = df_phys['DISTANCE'].mean()
            avg_hsr = df_phys['HSR'].mean()
            latest = df_phys.iloc[0]

            # Overordnede Metrics
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Seneste Dist", f"{round(latest['DISTANCE']/1000, 2)} km", 
                      delta=f"{round((latest['DISTANCE'] - avg_dist)/1000, 2)} km")
            m2.metric("HSR Meter", f"{int(latest['HSR'])} m", 
                      delta=f"{int(latest['HSR'] - avg_hsr)} m")
            m3.metric("Top Speed", f"{round(latest['TOP_SPEED'], 1)} km/t")
            m4.metric("HI Akt.", int(latest['HI_RUNS']))

            t_sub_log, t_sub_charts, t_sub_kpi = st.tabs(["Kampoversigt", "Performance Grafer", "Fysiske KPI'er"])

            with t_sub_log:
                st.data_editor(df_phys, hide_index=True, use_container_width=True, disabled=True)

            with t_sub_charts:
                cat_choice = st.segmented_control(
                    "Vælg metrik", 
                    options=["HSR (m)", "Sprint (m)", "Distance (km)", "Top Speed (km/t)"], 
                    default="HSR (m)", 
                    key="phys_graph_control"
                )
                
                # --- KONFIGURATION AF SUFFIX OG MAPPING ---
                mapping = {
                    "HSR (m)": ("HSR", 1, "m"), 
                    "Sprint (m)": ("SPRINTING", 1, "m"), 
                    "Distance (km)": ("DISTANCE", 1000, "km"), 
                    "Top Speed (km/t)": ("TOP_SPEED", 1, "km/t")
                }
                col, div, suffix = mapping[cat_choice]

                # Sorter: Sidste dato til højre
                df_chart = df_phys.head(32).copy().sort_values('MATCH_DATE', ascending=True)
                
                # Udtræk modstander
                def get_opponent(teams_str, my_team):
                    if not teams_str: return "?"
                    parts = [p.strip() for p in teams_str.split('-')]
                    return parts[1] if parts[0].lower() in my_team.lower() else parts[0]

                df_chart['Opponent'] = df_chart['MATCH_TEAMS'].apply(lambda x: get_opponent(x, valgt_hold))
                df_chart['Label'] = df_chart['Opponent'] + "<br>" + df_chart['MATCH_DATE'].dt.strftime('%d/%m')
                
                y_vals = df_chart[col] / div
                season_avg = y_vals.mean()

                # --- PLOTLY FIGUR ---
                fig = go.Figure()
                
                # Bar trace med dynamisk suffix
                fig.add_trace(go.Bar(
                    x=df_chart['Label'], 
                    y=y_vals,
                    text=y_vals.apply(lambda x: f"{x:.1f} {suffix}" if x < 50 else f"{int(x)} {suffix}"),
                    textposition='outside', 
                    marker_color='#cc0000',
                    textfont=dict(size=10, color="black")
                ))
                
                # Underspillet gennemsnitslinje (lysegrå og tyndere)
                fig.add_shape(
                    type="line", 
                    x0=-0.5, x1=len(df_chart)-0.5, 
                    y0=season_avg, y1=season_avg, 
                    line=dict(color="#D3D3D3", width=1.5, dash="dash")
                )
                
                fig.update_layout(
                    plot_bgcolor="white", 
                    height=380, 
                    margin=dict(t=40, b=0, l=0, r=0),
                    xaxis=dict(showgrid=False, tickfont=dict(size=10)),
                    yaxis=dict(showgrid=False, showticklabels=False, zeroline=False, range=[0, y_vals.max() * 1.2]),
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

            with t_sub_kpi:
                st.caption("Sæson KPI")
                # (Din KPI logik...)

    # --- TAB: STATISTIK ---
    with t_stats:
        if not df_spiller.empty:
            df_spiller['DATO'] = df_spiller['EVENT_TIMESTAMP'].dt.date
            st.line_chart(df_spiller.groupby('DATO').size())

if __name__ == "__main__":
    vis_side()
