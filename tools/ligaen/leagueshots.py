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

# --- CONFIG & CSS ---
HIF_RED = '#cc0000'
ASSIST_BLUE = '#1e90ff'
HIF_GOLD = '#FFD700'
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o"

def set_design():
    st.markdown(f"""
        <style>
            .stat-box {{ background-color: #f8f9fa; padding: 12px; border-radius: 8px; border-left: 5px solid {HIF_RED}; margin-bottom: 10px; }}
            .stat-label {{ font-size: 0.75rem; text-transform: uppercase; color: #666; font-weight: bold; }}
            .stat-value {{ font-size: 1.4rem; font-weight: 800; color: #1a1a1a; margin-top: 2px; }}
            [data-testid="stDataFrame"] td {{ text-align: center !important; }}
            .stTabs {{ margin-top: -20px; }}
        </style>
    """, unsafe_allow_html=True)

# --- DATA ---
@st.cache_data(ttl=3600)
def load_data():
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    match_id_sql = f"SELECT DISTINCT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"
    sql = f"""
        SELECT e.*, q.QUALIFIER_VALUE as XG_RAW FROM {DB}.OPTA_EVENTS e 
        LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID AND q.QUALIFIER_QID = 321
        WHERE e.EVENT_TYPEID IN (13,14,15,16) AND e.MATCH_OPTAUUID IN ({match_id_sql})
    """
    df = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
    df.columns = [c.upper() for c in df.columns]
    return df

@st.cache_data(ttl=3600)
def get_logo(url):
    try: return Image.open(BytesIO(requests.get(url, timeout=5).content))
    except: return None

# --- ZONE DEFINITIONER (FULDE NUANCER) ---
P_L, P_W = 105.0, 68.0
X_MID_L, X_MID_R = (P_W - 18.32) / 2, (P_W + 18.32) / 2
X_INN_L, X_INN_R = (P_W - 40.2) / 2, (P_W + 40.2) / 2
Y_GOAL, Y_6YD, Y_PK, Y_18YD, Y_MID = 105.0, 99.5, 94.0, 88.5, 75.0

ZONE_BOUNDARIES = {
    "Zone 1": {"y_min": Y_6YD, "y_max": Y_GOAL, "x_min": X_MID_L, "x_max": X_MID_R},
    "Zone 2": {"y_min": Y_PK, "y_max": Y_6YD, "x_min": X_MID_L, "x_max": X_MID_R},
    "Zone 3": {"y_min": Y_18YD, "y_max": Y_PK, "x_min": X_MID_L, "x_max": X_MID_R},
    "Zone 4A": {"y_min": Y_6YD, "y_max": Y_GOAL, "x_min": X_MID_R, "x_max": X_INN_R},
    "Zone 4B": {"y_min": Y_6YD, "y_max": Y_GOAL, "x_min": X_INN_L, "x_max": X_MID_L},
    "Zone 5A": {"y_min": Y_18YD, "y_max": Y_6YD, "x_min": X_MID_R, "x_max": X_INN_R},
    "Zone 5B": {"y_min": Y_18YD, "y_max": Y_6YD, "x_min": X_INN_L, "x_max": X_MID_L},
    "Zone 6A": {"y_min": Y_18YD, "y_max": Y_GOAL, "x_min": X_INN_R, "x_max": P_W},
    "Zone 6B": {"y_min": Y_18YD, "y_max": Y_GOAL, "x_min": 0, "x_max": X_INN_L},
    "Zone 7C": {"y_min": Y_MID, "y_max": Y_18YD, "x_min": 0, "x_max": X_MID_L},
    "Zone 7B": {"y_min": Y_MID, "y_max": Y_18YD, "x_min": X_MID_L, "x_max": X_MID_R},
    "Zone 7A": {"y_min": Y_MID, "y_max": Y_18YD, "x_min": X_MID_R, "x_max": P_W},
    "Zone 8":  {"y_min": 0, "y_max": Y_MID, "x_min": 0, "x_max": P_W}
}

def vis_side(dp=None):
    set_design()
    df_all = load_data()
    if df_all.empty: return

    # Mapping
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['EVENT_CONTESTANT_OPTAUUID'].str.upper().map(uuid_to_name)
    teams_in_data = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])

    # --- TOPBAR ---
    c_t1, c_t2 = st.columns([2, 1])
    with c_t2:
        t_sel = st.selectbox("Vælg hold", teams_in_data, index=teams_in_data.index("Hvidovre") if "Hvidovre" in teams_in_data else 0)
    
    t_color = TEAM_COLORS.get(t_sel, {}).get('primary', HIF_RED)
    t_logo = get_logo(TEAMS.get(t_sel, {}).get('logo'))
    
    df_team = df_all[df_all['KLUB_NAVN'] == t_sel].copy()
    df_team['IS_DZ'] = (df_team['EVENT_X'] >= 88.5) & (df_team['EVENT_Y'] >= 37.0) & (df_team['EVENT_Y'] <= 63.0)
    df_team['Zone'] = df_team.apply(lambda r: next((z for z, b in ZONE_BOUNDARIES.items() if b["y_min"] <= r['EVENT_X']*(105/100) <= b["y_max"] and b["x_min"] <= r['EVENT_Y']*(68/100) <= b["x_max"]), "Zone 8"), axis=1)

    tabs = st.tabs(["SPILLEROVERSIGT", "AFSLUTNINGER", "DZ-ANALYSE", "ZONESTATS"])

    # --- TAB 1: AFSLUTNINGER ---
    with tabs[1]:
        c1, c2 = st.columns([2, 1])
        with c2:
            p_sel = st.selectbox("Vælg spiller", ["Hele Holdet"] + sorted(df_team['PLAYER_NAME'].unique()))
            d_v = df_team if p_sel == "Hele Holdet" else df_team[df_team['PLAYER_NAME'] == p_sel]
            s, m = len(d_v), len(d_v[d_v['EVENT_TYPEID']==16])
            st.markdown(f'<div class="stat-box"><div class="stat-label">Skud</div><div class="stat-value">{s}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Mål</div><div class="stat-value">{m}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box" style="border-left-color:{HIF_GOLD}"><div class="stat-label">Konvertering</div><div class="stat-value">{(m/s*100 if s>0 else 0):.1f}%</div></div>', unsafe_allow_html=True)
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            pitch.scatter(d_v['EVENT_X'], d_v['EVENT_Y'], s=80, c=(d_v['EVENT_TYPEID']==16).map({True: t_color, False: 'white'}), edgecolors=t_color, ax=ax)
            if t_logo: ax.inset_axes([0.05, 0.88, 0.12, 0.12], transform=ax.transAxes).imshow(t_logo); ax.axis('off')
            st.pyplot(fig)

    # --- TAB 2: DZ-ANALYSE (GENINDSAT KONVERTERING) ---
    with tabs[2]:
        c1, c2 = st.columns([2, 1])
        with c2:
            dz_d = df_team[df_team['IS_DZ']]
            dz_s, dz_m = len(dz_d), len(dz_d[dz_d['EVENT_TYPEID']==16])
            st.markdown(f'<div class="stat-box" style="border-left-color:{ASSIST_BLUE}"><div class="stat-label">DZ Skud</div><div class="stat-value">{dz_s}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">DZ Mål</div><div class="stat-value">{dz_m}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box" style="border-left-color:{HIF_GOLD}"><div class="stat-label">DZ Konvertering</div><div class="stat-value">{(dz_m/dz_s*100 if dz_s>0 else 0):.1f}%</div></div>', unsafe_allow_html=True)
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            ax.add_patch(patches.Rectangle((37, 88.5), 26, 11.5, color=t_color, alpha=0.15))
            pitch.scatter(dz_d['EVENT_X'], dz_d['EVENT_Y'], s=100, c=(dz_d['EVENT_TYPEID']==16).map({True: t_color, False: 'white'}), edgecolors=t_color, ax=ax)
            st.pyplot(fig)

    # --- TAB 3: ZONESTATS (NUANCER + TOPSCORERE) ---
    with tabs[3]:
        c1, c2 = st.columns([1.8, 1])
        z_stats = []
        for z, b in ZONE_BOUNDARIES.items():
            z_data = df_team[df_team['Zone'] == z]
            if len(z_data) > 0:
                top_p = z_data[z_data['EVENT_TYPEID']==16]['PLAYER_NAME'].mode().iloc[0] if len(z_data[z_data['EVENT_TYPEID']==16]) > 0 else "-"
                z_stats.append({"Zone": z, "Skud": len(z_data), "Mål": len(z_data[z_data['EVENT_TYPEID']==16]), "Topscorer": top_p})
        
        with c2:
            st.dataframe(pd.DataFrame(z_stats).sort_values("Skud", ascending=False), hide_index=True, use_container_width=True)

        with c1:
            pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='grey')
            fig, ax = pitch.draw(figsize=(8, 10))
            ax.set_ylim(55, 105)
            max_s = max([s['Skud'] for s in z_stats]) if z_stats else 1
            for z, b in ZONE_BOUNDARIES.items():
                if b["y_max"] <= 55: continue
                s_val = next((s['Skud'] for s in z_stats if s['Zone']==z), 0)
                pct = (s_val / len(df_team) * 100) if len(df_team)>0 else 0
                alpha = (s_val/max_s)*0.6 if s_val > 0 else 0.05
                ax.add_patch(patches.Rectangle((b["x_min"], max(b["y_min"], 55)), b["x_max"]-b["x_min"], b["y_max"]-max(b["y_min"], 55), facecolor=t_color, alpha=alpha, edgecolor='black', ls='--'))
                if s_val > 0:
                    ax.text(b["x_min"]+(b["x_max"]-b["x_min"])/2, max(b["y_min"], 55)+(b["y_max"]-max(b["y_min"], 55))/2, f"{s_val}\n({pct:.1f}%)", ha='center', va='center', fontsize=9, fontweight='bold')
            st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
