import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn
from PIL import Image
import requests
from io import BytesIO

# --- KONFIGURATION ---
HIF_RED = '#cc0000'
HIF_GOLD = '#FFD700'
ASSIST_BLUE = '#1e90ff'
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o"

# --- ZONE DEFINITIONER (OPTA 0-100) ---
ZONE_BOUNDARIES = {
    "Zone 1": {"y_min": 94.8, "y_max": 100.0, "x_min": 37.0, "x_max": 63.0},
    "Zone 2": {"y_min": 88.5, "y_max": 94.8, "x_min": 37.0, "x_max": 63.0},
    "Zone 3": {"y_min": 83.0, "y_max": 88.5, "x_min": 37.0, "x_max": 63.0},
    "Zone 4A": {"y_min": 94.8, "y_max": 100.0, "x_min": 63.0, "x_max": 79.6},
    "Zone 4B": {"y_min": 94.8, "y_max": 100.0, "x_min": 20.4, "x_max": 37.0},
    "Zone 5A": {"y_min": 83.0, "y_max": 94.8, "x_min": 63.0, "x_max": 79.6},
    "Zone 5B": {"y_min": 83.0, "y_max": 94.8, "x_min": 20.4, "x_max": 37.0},
    "Zone 6A": {"y_min": 83.0, "y_max": 100.0, "x_min": 79.6, "x_max": 100.0},
    "Zone 6B": {"y_min": 83.0, "y_max": 100.0, "x_min": 0.0, "x_max": 20.4},
    "Zone 7C": {"y_min": 71.4, "y_max": 83.0, "x_min": 0.0, "x_max": 37.0},
    "Zone 7B": {"y_min": 71.4, "y_max": 83.0, "x_min": 37.0, "x_max": 63.0},
    "Zone 7A": {"y_min": 71.4, "y_max": 83.0, "x_min": 63.0, "x_max": 100.0},
    "Zone 8":  {"y_min": 0.0, "y_max": 71.4, "x_min": 0.0, "x_max": 100.0}
}

# --- DATA & UTILS ---
@st.cache_data(ttl=3600)
def load_league_data():
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    match_sql = f"SELECT DISTINCT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"
    sql = f"""
        SELECT e.*, q.QUALIFIER_VALUE as XG_RAW FROM {DB}.OPTA_EVENTS e 
        LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID AND q.QUALIFIER_QID = 321
        WHERE e.EVENT_TYPEID IN (13,14,15,16) AND e.MATCH_OPTAUUID IN ({match_sql})
    """
    df = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
    df.columns = [c.upper() for c in df.columns]
    return df

@st.cache_data(ttl=3600)
def get_logo_img(url):
    try: return Image.open(BytesIO(requests.get(url, timeout=5).content))
    except: return None

def map_to_zone(r):
    for z, b in ZONE_BOUNDARIES.items():
        if b["y_min"] <= r['EVENT_X'] <= b["y_max"] and b["x_min"] <= r['EVENT_Y'] <= b["x_max"]: return z
    return "Zone 8"

# --- MAIN APP ---
def vis_side(dp=None):
    st.markdown(f"""
        <style>
            .stat-box {{ background-color: #f8f9fa; padding: 12px; border-radius: 8px; border-left: 5px solid {HIF_RED}; margin-bottom: 10px; }}
            .stat-label {{ font-size: 0.75rem; text-transform: uppercase; color: #666; font-weight: bold; }}
            .stat-value {{ font-size: 1.4rem; font-weight: 800; color: #1a1a1a; margin-top: 2px; }}
            .stTabs {{ margin-top: -20px; }}
        </style>
    """, unsafe_allow_html=True)

    df_all = load_league_data()
    if df_all.empty: return

    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['EVENT_CONTESTANT_OPTAUUID'].str.upper().map(uuid_to_name)
    teams = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])

    c_h1, c_h2 = st.columns([2, 1])
    with c_h2:
        t_sel = st.selectbox("Vælg hold", teams, index=teams.index("Hvidovre") if "Hvidovre" in teams else 0)
    
    t_color = TEAM_COLORS.get(t_sel, {}).get('primary', HIF_RED)
    t_logo = get_logo_img(TEAMS.get(t_sel, {}).get('logo'))
    
    df_team = df_all[df_all['KLUB_NAVN'] == t_sel].copy()
    df_team['Zone'] = df_team.apply(map_to_zone, axis=1)
    df_team['IS_DZ'] = (df_team['EVENT_X'] >= 88.5) & (df_team['EVENT_Y'] >= 37.0) & (df_team['EVENT_Y'] <= 63.0)

    tabs = st.tabs(["SPILLEROVERSIGT", "AFSLUTNINGER", "DZ-ANALYSE", "SKUDZONER", "MÅLZONER"])

    # --- TAB 0: SPILLEROVERSIGT ---
    with tabs[0]:
        p_stats = []
        for p, d in df_team.groupby('PLAYER_NAME'):
            s, m = len(d), len(d[d['EVENT_TYPEID']==16])
            p_stats.append({"Spiller": p, "Skud": s, "Mål": m, "Konv.%": (m/s*100 if s>0 else 0)})
        st.dataframe(pd.DataFrame(p_stats).sort_values("Skud", ascending=False), use_container_width=True, hide_index=True)

    # --- TAB 1: AFSLUTNINGER ---
    with tabs[1]:
        c1, c2 = st.columns([2, 1])
        with c2:
            p_sel = st.selectbox("Vælg spiller", ["Hele Holdet"] + sorted(df_team['PLAYER_NAME'].unique()), key="p_af")
            d_v = df_team if p_sel == "Hele Holdet" else df_team[df_team['PLAYER_NAME'] == p_sel]
            st.markdown(f'<div class="stat-box"><div class="stat-label">Skud</div><div class="stat-value">{len(d_v)}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Mål</div><div class="stat-value">{len(d_v[d_v["EVENT_TYPEID"]==16])}</div></div>', unsafe_allow_html=True)
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc', pad_bottom=-20)
            fig, ax = pitch.draw(figsize=(5, 5))
            pitch.scatter(d_v['EVENT_X'], d_v['EVENT_Y'], s=80, c=(d_v['EVENT_TYPEID']==16).map({True: t_color, False: 'white'}), edgecolors=t_color, ax=ax)
            if t_logo:
                ax_logo = ax.inset_axes([0.05, 0.85, 0.15, 0.15])
                ax_logo.imshow(t_logo)
                ax_logo.axis('off')
            st.pyplot(fig)

    # --- TAB 2: DZ-ANALYSE ---
    with tabs[2]:
        c1, c2 = st.columns([2, 1])
        dz_d = df_team[df_team['IS_DZ']]
        with c2:
            st.markdown(f'<div class="stat-box" style="border-left-color:{ASSIST_BLUE}"><div class="stat-label">DZ Skud</div><div class="stat-value">{len(dz_d)}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">DZ Mål</div><div class="stat-value">{len(dz_d[dz_d["EVENT_TYPEID"]==16])}</div></div>', unsafe_allow_html=True)
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc', pad_bottom=-20)
            fig, ax = pitch.draw(figsize=(5, 5))
            ax.add_patch(patches.Rectangle((37, 88.5), 26, 11.5, color=t_color, alpha=0.2))
            pitch.scatter(dz_d['EVENT_X'], dz_d['EVENT_Y'], s=100, c=(dz_d['EVENT_TYPEID']==16).map({True: t_color, False: 'white'}), edgecolors=t_color, ax=ax)
            st.pyplot(fig)

    # --- TAB 3 & 4: ZONER ---
    for i, is_goal in enumerate([False, True]):
        with tabs[i+3]:
            c1, c2 = st.columns([1.5, 1])
            plot_df = df_team[df_team['EVENT_TYPEID'] == 16] if is_goal else df_team
            with c2:
                z_summary = []
                for z in ZONE_BOUNDARIES.keys():
                    z_d = plot_df[plot_df['Zone'] == z]
                    if len(z_d) > 0:
                        z_summary.append({"Zone": z, "Antal": len(z_d), "%": f"{(len(z_d)/len(df_team)*100):.1f}%"})
                st.table(pd.DataFrame(z_summary).sort_values("Antal", ascending=False))
            with c1:
                pitch = VerticalPitch(half=True, pitch_type='opta', line_color='grey', pad_bottom=-20)
                fig, ax = pitch.draw(figsize=(5, 5))
                max_v = plot_df['Zone'].value_counts().max() if not plot_df.empty else 1
                for z, b in ZONE_BOUNDARIES.items():
                    cnt = len(plot_df[plot_df['Zone']==z])
                    alpha = (cnt/max_v)*0.6 if cnt > 0 else 0.05
                    ax.add_patch(patches.Rectangle((b["x_min"], b["y_min"]), b["x_max"]-b["x_min"], b["y_max"]-b["y_min"], facecolor=t_color, alpha=alpha, edgecolor='black', ls='--'))
                    if cnt > 0: ax.text(b["x_min"]+(b["x_max"]-b["x_min"])/2, b["y_min"]+(b["y_max"]-b["y_min"])/2, f"{cnt}", ha='center', va='center', fontweight='bold')
                st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
