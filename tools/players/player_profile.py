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

# --- KONFIGURATION (Fra Saved Information) ---
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '335', '328', '329', '43319', '331')"
SEASONNAME = "2025/2026"  #

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

def create_donut_chart(value, label, color="#003366"):
    fig = go.Figure(go.Pie(
        values=[value, max(0.1, 100-value) if "%" in str(label) or value <= 100 else 0],
        hole=0.7,
        marker_colors=[color, "#EEEEEE"],
        textinfo='none',
        hoverinfo='none'
    ))
    fig.update_layout(
        showlegend=False,
        margin=dict(t=5, b=5, l=5, r=5),
        height=140, # Justeret for bedre opløsning
        annotations=[dict(text=str(value), x=0.5, y=0.5, font_size=18, showarrow=False, font_family="Arial Black")]
    )
    return fig

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
              SELECT MATCH_SSIID FROM {DB}.SECONDSPECTRUM_GAME_METADATA
              WHERE HOME_SSIID = '{target_ssiid}' OR AWAY_SSIID = '{target_ssiid}'
          )
        GROUP BY p.MATCH_DATE, p.PLAYER_NAME
        ORDER BY p.MATCH_DATE DESC
    """
    return db_conn.query(sql)

def vis_side():
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 16px !important; text-align: center; font-weight: bold !important; }
        [data-testid="stMetricLabel"] { font-size: 10px !important; text-align: center; }
        .profile-card { background-color: #003366; color: white; padding: 15px; border-radius: 12px; height: 100%; }
        .donut-container { text-align: center; border: 1px solid #eee; border-radius: 8px; padding: 10px; background: white; }
        .donut-label { font-size: 11px; font-weight: bold; color: #333; margin-bottom: 5px; height: 25px; }
        </style>
        """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn: return

    # --- TOP MENU ---
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
    mapping_lookup = {str(info['opta_uuid']).lower().replace('t', ''): name for name, info in TEAMS.items() if 'opta_uuid' in info}
    team_map = {mapping_lookup[str(r['CONTESTANTHOME_OPTAUUID']).lower().replace('t','')]: r['CONTESTANTHOME_OPTAUUID'] 
                for _, r in df_teams_raw.iterrows() if str(r['CONTESTANTHOME_OPTAUUID']).lower().replace('t','') in mapping_lookup}

    col_h_hold, col_h_spiller, _ = st.columns([1.5, 1.5, 5])
    valgt_hold = col_h_hold.selectbox("Hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid_hold = team_map[valgt_hold]

    # --- HENT DATA ---
    sql = f"""
        SELECT 
            e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, 
            TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as VISNINGSNAVN, 
            e.PLAYER_OPTAUUID, e.EVENT_OUTCOME as OUTCOME,
            TO_CHAR(e.EVENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS') as EVENT_TIMESTAMP_STR,
            LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
        FROM {DB}.OPTA_EVENTS e
        JOIN (SELECT DISTINCT PLAYER_OPTAUUID, FIRST_NAME, LAST_NAME FROM {DB}.OPTA_PLAYERS WHERE FIRST_NAME IS NOT NULL) p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
        WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid_hold}' AND e.EVENT_TIMESTAMP >= '2025-07-01'
        GROUP BY 1, 2, 3, 4, 5, 6, 7
    """
    df_all = conn.query(sql)
    df_all['qual_list'] = df_all['QUALIFIERS'].fillna('').str.split(',')
    df_all['Action_Label'] = df_all.apply(get_action_label, axis=1)

    spiller_liste = sorted(df_all['VISNINGSNAVN'].unique())
    valgt_spiller = col_h_spiller.selectbox("Spiller", spiller_liste, label_visibility="collapsed")
    valgt_player_uuid = df_all[df_all['VISNINGSNAVN'] == valgt_spiller]['PLAYER_OPTAUUID'].iloc[0]
    df_spiller = df_all[df_all['VISNINGSNAVN'] == valgt_spiller].copy()

    tabs = st.tabs(["Spillerprofil", "Spilleraktioner", "Fysisk data", "Statistik"])

    # --- TAB: SPILLERPROFIL ---
    with tabs[0]:
        c1, c2 = st.columns([1, 3.5])
        with c1:
            st.markdown(f"""<div class="profile-card"><h3>{valgt_spiller}</h3><p>Position: Midtbane</p><hr>
                Kampe: 16<br>Minutter: 1423<br>Mål: 3<br>Assists: 4</div>""", unsafe_allow_html=True)
            st.write("")
            for m, v in {"Afleveringer": 29.2, "Dueller": 25.7, "Boldtab": 11.6, "Skud": 1.7, "xG": 0.3, "Pasnings %": 77.4}.items():
                st.write(f"<div style='font-size:11px;'>{m} <span style='float:right;'>{v}</span></div>", unsafe_allow_html=True)
                st.progress(min(v/100 if "Pasnings" in m else v/50, 1.0))
        
        with c2:
            st.markdown("<h4 style='text-align:center;'>Spillerstatistik</h4>", unsafe_allow_html=True)
            metrics_grid = [
                ("Afleveringer", 474), ("Pasning %", 77), ("Fremadrettet", 158), ("Progressive", 77),
                ("Lange pasninger", 22), ("Sidste 1/3", 68), ("Off. aktioner", 0), ("Off. dueller", 235),
                ("Erobringer", 87), ("Modst. halvdel", 57), ("Generobringer", 51), ("Interceptions", 31)
            ]
            for i in range(0, len(metrics_grid), 4):
                cols = st.columns(4)
                for j in range(4):
                    label, val = metrics_grid[i+j]
                    with cols[j]:
                        st.markdown(f'<div class="donut-container"><div class="donut-label">{label}</div>', unsafe_allow_html=True)
                        st.plotly_chart(create_donut_chart(val, label), use_container_width=True, config={'displayModeBar': False})
                        st.markdown('</div>', unsafe_allow_html=True)

    # --- TAB: SPILLERAKTIONER ---
    with tabs[1]:
        st.write("Her vises din tidligere 'Spillerprofil' (Pitch/Heatmap)...")

    # --- TAB: FYSISK DATA (GENOPRETTET FULD VERSION) ---
    with tabs[2]:
        df_phys = get_physical_data(valgt_spiller, valgt_player_uuid, valgt_hold, conn)
        if df_phys is not None and not df_phys.empty:
            df_phys['MATCH_DATE'] = pd.to_datetime(df_phys['MATCH_DATE'])
            latest = df_phys.iloc[0]
            avg_dist = df_phys['DISTANCE'].mean()
            avg_hsr = df_phys['HSR'].mean()

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Seneste Distance", f"{round(latest['DISTANCE']/1000, 2)} km", delta=f"{round((latest['DISTANCE'] - avg_dist)/1000, 2)} km")
            m2.metric("HSR Meter", f"{int(latest['HSR'])} m", delta=f"{int(latest['HSR'] - avg_hsr)} m")
            m3.metric("Topfart", f"{round(latest['TOP_SPEED'], 1)} km/t")
            m4.metric("Højintense Akt.", int(latest['HI_RUNS']))

            cat_choice = st.segmented_control("Vælg metrik", options=["HSR (m)", "Sprint (m)", "Distance (km)", "Topfart (km/t)"], default="HSR (m)")
            mapping = {"HSR (m)": ("HSR", 1), "Sprint (m)": ("SPRINTING", 1), "Distance (km)": ("DISTANCE", 1000), "Topfart (km/t)": ("TOP_SPEED", 1)}
            col_name, div = mapping[cat_choice]

            df_chart = df_phys.sort_values('MATCH_DATE')
            def get_opp(s, my): 
                p = s.split('-')
                return p[1].strip() if p[0].strip().lower() in my.lower() else p[0].strip()
            
            df_chart['Opponent'] = df_chart['MATCH_TEAMS'].apply(lambda x: get_opp(x, valgt_hold))
            df_chart['Label'] = df_chart['Opponent'] + "<br>" + df_chart['MATCH_DATE'].dt.strftime('%d/%m')
            y_vals = df_chart[col_name] / div

            fig = go.Figure()
            fig.add_trace(go.Bar(x=df_chart['Label'], y=y_vals, text=y_vals.apply(lambda x: f"{x:.0f}"), textposition='outside', marker_color='#cc0000'))
            fig.add_shape(type="line", x0=-0.5, x1=len(df_chart)-0.5, y0=y_vals.mean(), y1=y_vals.mean(), line=dict(color="gray", dash="dash"))
            fig.update_layout(plot_bgcolor="white", height=350, margin=dict(t=20, b=50, l=10, r=10), xaxis=dict(type='category'), showlegend=False)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            st.data_editor(df_phys, hide_index=True, use_container_width=True)

if __name__ == "__main__":
    vis_side()
