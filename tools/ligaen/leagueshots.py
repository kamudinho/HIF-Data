import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch, Pitch
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn
from PIL import Image
import requests
from io import BytesIO

# --- KONFIGURATION & DESIGN ---
HIF_RED = '#cc0000'
ASSIST_BLUE = '#1e90ff'
HIF_GOLD = '#FFD700'
DZ_COLOR = '#cc0000'
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o"

OPTA_MAP_DK = {
    1: "Aflevering", 2: "Aflevering", 3: "Dribling", 4: "Tackling", 
    5: "Frispark", 6: "Hjørnespark", 7: "Tackling", 8: "Interception",
    10: "Redning", 12: "Skud", 13: "Skud", 14: "Skud", 15: "Skud", 
    16: "MÅL", 43: "Frispark", 44: "Indkast", 49: "Opsamling", 50: "Opsnapning",
    107: "Restart"
}

# --- DATA LOADING ---
@st.cache_data(ttl=3600)
def load_league_data():
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    
    match_id_subquery = f"SELECT DISTINCT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"
    sql = f"""
        SELECT e.*, q.QUALIFIER_VALUE as XG_RAW 
        FROM {DB}.OPTA_EVENTS e 
        LEFT JOIN {DB}.OPTA_QUALIFIERS q 
            ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID AND q.QUALIFIER_QID = 321
        WHERE e.EVENT_TYPEID IN (13,14,15,16) 
        AND e.MATCH_OPTAUUID IN ({match_id_subquery})
    """
    df = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
    return df

@st.cache_data(ttl=3600)
def get_logo_img(url):
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except: return None

def get_team_style(team_name):
    color = HIF_RED
    logo_img = None
    if team_name in TEAM_COLORS:
        c = TEAM_COLORS[team_name]
        prim = c['primary'].lower()
        color = c.get('secondary', HIF_RED) if prim in ["#ffffff", "white", "#f9f9f9"] else c['primary']
    if team_name in TEAMS:
        url = TEAMS[team_name].get('logo')
        if url: logo_img = get_logo_img(url)
    return color, logo_img

# --- MAIN APP ---
def vis_side(dp=None):
    # Indlæs CSS fra dit ønskede layout
    st.markdown(f"""
        <style>
            .stat-box {{ background-color: #f8f9fa; padding: 10px; border-radius: 8px; border-left: 5px solid {HIF_RED}; margin-bottom: 10px; }}
            .stat-label {{ font-size: 0.8rem; text-transform: uppercase; color: #666; font-weight: bold; }}
            .stat-value {{ font-size: 1.5rem; font-weight: 800; color: #1a1a1a; margin-top: 2px; }}
            /* Centrerer dataframes */
            [data-testid="stDataFrame"] td {{ text-align: center !important; }}
            [data-testid="stTable"] td {{ text-align: center !important; }}
        </style>
    """, unsafe_allow_html=True)

    df_all = load_league_data()
    if df_all.empty:
        st.info("Ingen ligadata fundet.")
        return

    # Data Prep
    df_all.columns = [c.upper() for c in df_all.columns]
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['EVENT_CONTESTANT_OPTAUUID'].str.upper().map(uuid_to_name)
    teams_in_data = sorted([name for name in df_all['KLUB_NAVN'].unique() if pd.notna(name)])

    # Holdvalg
    hif_idx = teams_in_data.index("Hvidovre") if "Hvidovre" in teams_in_data else 0
    t_sel = st.selectbox("Vælg hold", teams_in_data, index=hif_idx)
    t_color, t_logo = get_team_style(t_sel)

    # Zone logik
    df_all['IS_DZ_GEO'] = (df_all['EVENT_X'] >= 88.5) & (df_all['EVENT_Y'] >= 37.0) & (df_all['EVENT_Y'] <= 63.0)
    
    P_L, P_W = 105.0, 68.0
    X_MID_L, X_MID_R = (P_W - 18.32) / 2, (P_W + 18.32) / 2
    Y_GOAL, Y_6YD, Y_PK, Y_18YD, Y_MID = 105.0, 99.5, 94.0, 88.5, 75.0
    ZONE_BOUNDARIES = {
        "Zone 1": {"y_min": Y_6YD, "y_max": Y_GOAL, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 2": {"y_min": Y_PK, "y_max": Y_6YD, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 3": {"y_min": Y_18YD, "y_max": Y_PK, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 8": {"y_min": 0, "y_max": Y_MID, "x_min": 0, "x_max": P_W} # Forenklet her for eksemplet
    }

    def map_to_zone(r):
        mx, my = r['EVENT_X'] * (P_L / 100), r['EVENT_Y'] * (P_W / 100)
        for z, b in ZONE_BOUNDARIES.items():
            if b["y_min"] <= mx <= b["y_max"] and b["x_min"] <= my <= b["x_max"]: return z
        return "Zone 8"

    df_all['Zone'] = df_all.apply(map_to_zone, axis=1)
    df_team = df_all[df_all['KLUB_NAVN'] == t_sel].copy()

    tabs = st.tabs(["SPILLEROVERSIGT", "AFSLUTNINGER", "DZ-AFSLUTNINGER", "AFSLUTNINGSZONER", "MÅLZONER"])

    # --- TAB 0: SPILLEROVERSIGT ---
    with tabs[0]:
        stats = []
        for p, d in df_team.groupby('PLAYER_NAME'):
            dz = d[d['IS_DZ_GEO']]
            s, m = len(d), len(d[d['EVENT_TYPEID'] == 16])
            dz_s, dz_m = len(dz), len(dz[dz['EVENT_TYPEID'] == 16])
            stats.append({
                "Spiller": p, "Skud": s, "Mål": m, "Konv.%": (m/s*100) if s > 0 else 0,
                "DZ-Skud": dz_s, "DZ-Mål": dz_m, "DZ-Andel": (dz_s/s*100) if s > 0 else 0
            })
        df_f = pd.DataFrame(stats).sort_values("Skud", ascending=False)
        st.dataframe(df_f, use_container_width=True, hide_index=True, column_config={
            "DZ-Andel": st.column_config.ProgressColumn("DZ-Andel", format="%.1f%%", min_value=0, max_value=100),
            "Konv.%": st.column_config.NumberColumn(format="%.1f%%")
        })

    # --- TAB 1: AFSLUTNINGER ---
    with tabs[1]:
        c1, c2 = st.columns([2, 1])
        with c2:
            p_sel = st.selectbox("Vælg spiller", ["Hele Holdet"] + sorted(df_team['PLAYER_NAME'].unique()))
            d_v = df_team if p_sel == "Hele Holdet" else df_team[df_team['PLAYER_NAME'] == p_sel]
            s_cnt, m_cnt = len(d_v), len(d_v[d_v['EVENT_TYPEID'] == 16])
            st.markdown(f'<div class="stat-box"><div class="stat-label">Skud</div><div class="stat-value">{s_cnt}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Mål</div><div class="stat-value">{m_cnt}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box" style="border-left-color:{HIF_GOLD}"><div class="stat-label">Konvertering</div><div class="stat-value">{(m_cnt/s_cnt*100 if s_cnt>0 else 0):.1f}%</div></div>', unsafe_allow_html=True)
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            colors = (d_v['EVENT_TYPEID'] == 16).map({True: t_color, False: 'white'})
            pitch.scatter(d_v['EVENT_X'], d_v['EVENT_Y'], s=80, c=colors, edgecolors=t_color, ax=ax)
            st.pyplot(fig)

    # --- TAB 2: DZ-AFSLUTNINGER ---
    with tabs[2]:
        c1, c2 = st.columns([2, 1])
        with c2:
            dz_d = df_team[df_team['IS_DZ_GEO']]
            st.markdown(f'<div class="stat-box" style="border-left-color:{ASSIST_BLUE}"><div class="stat-label">DZ Skud</div><div class="stat-value">{len(dz_d)}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">DZ Mål</div><div class="stat-value">{len(dz_d[dz_d["EVENT_TYPEID"]==16])}</div></div>', unsafe_allow_html=True)
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            ax.add_patch(patches.Rectangle((37, 88.5), 26, 11.5, color=t_color, alpha=0.15))
            colors = (dz_d['EVENT_TYPEID'] == 16).map({True: t_color, False: 'white'})
            pitch.scatter(dz_d['EVENT_X'], dz_d['EVENT_Y'], s=100, c=colors, edgecolors=t_color, ax=ax)
            st.pyplot(fig)
            
    # --- TAB 3 & 4: ZONER ---
    def zone_tab(is_goal):
        c1, c2 = st.columns([1.8, 1])
        df_t = df_all[df_all['KLUB_NAVN'] == t_sel]
        plot_data = df_t[df_t['EVENT_TYPEID'] == 16] if is_goal else df_t
        z_counts = plot_data.groupby('Zone').size()
        
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='grey')
            fig, ax = pitch.draw(figsize=(8, 10))
            ax.set_ylim(55, 105)
            max_v = z_counts.max() if not z_counts.empty else 1
            for name, b in ZONE_BOUNDARIES.items():
                if b["y_max"] <= 55: continue
                cnt = z_counts.get(name, 0)
                alpha = (cnt/max_v) * 0.85 if cnt > 0 else 0.05
                ax.add_patch(patches.Rectangle(
                    (b["x_min"], max(b["y_min"], 55)), 
                    b["x_max"]-b["x_min"], 
                    b["y_max"]-max(b["y_min"], 55), 
                    facecolor=t_color, alpha=alpha, edgecolor='black', ls='--', lw=0.5
                ))
                if cnt > 0:
                    display_text_color = 'black' if alpha < 0.4 else txt_color
                    ax.text(
                        b["x_min"]+(b["x_max"]-b["x_min"])/2, 
                        max(b["y_min"], 55)+(b["y_max"]-max(b["y_min"], 55))/2, 
                        f"{cnt}", ha='center', va='center', fontsize=12, fontweight='bold', color=display_text_color
                    )
            draw_logo_adjusted(ax, t_logo)
            st.pyplot(fig)

    with tabs[3]: zone_tab(False)
    with tabs[4]: zone_tab(True)
