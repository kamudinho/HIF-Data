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

# --- KONFIGURATION (Hvidovre-app værdier) ---
HIF_RED = '#cc0000'
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o"

# --- ZONE DEFINITIONER (105x68 m) ---
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

def to_metric(val, total_m):
    return val * (total_m / 100)

def map_to_zone(r):
    mx, my = to_metric(r['EVENT_X'], 105), to_metric(r['EVENT_Y'], 68)
    for z, b in ZONE_BOUNDARIES.items():
        if b["y_min"] <= mx <= b["y_max"] and b["x_min"] <= my <= b["x_max"]: return z
    return "Zone 8"

def draw_logo_on_pitch(ax, logo_img):
    if logo_img:
        ax_logo = ax.inset_axes([0.02, 0.89, 0.12, 0.10], transform=ax.transAxes)
        ax_logo.imshow(logo_img)
        ax_logo.axis('off')

# --- MAIN APP ---
def vis_side(dp=None):
    st.markdown("""
    <style>
        header {visibility: hidden;}
        .main .block-container { padding-top: 0.5rem !important; padding-bottom: 3rem !important; }
        [data-testid="stVerticalBlock"] { gap: 0rem !important; }
        .stTabs { margin-top: 10px !important; }
        .stat-box { 
            background-color: #f8f9fa; padding: 15px !important; border-radius: 8px; 
            border-left: 5px solid #cc0000; margin-bottom: 12px !important; 
        }
        .stat-label { font-size: 0.8rem; text-transform: uppercase; color: #666; font-weight: bold; }
        .stat-value { font-size: 1.6rem; font-weight: 800; color: #1a1a1a; margin-top: 4px; }
    </style>
    """, unsafe_allow_html=True)

    df_all = load_league_data()
    if df_all.empty: return

    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['EVENT_CONTESTANT_OPTAUUID'].str.upper().map(uuid_to_name)
    teams = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])

    c_h1, c_h2 = st.columns([2, 1])
    with c_h2:
        t_sel = st.selectbox("Hold", teams, index=teams.index("Hvidovre") if "Hvidovre" in teams else 0, label_visibility="collapsed")
    
    t_color = TEAM_COLORS.get(t_sel, {}).get('primary', HIF_RED)
    t_logo = get_logo_img(TEAMS.get(t_sel, {}).get('logo'))
    
    df_team = df_all[df_all['KLUB_NAVN'] == t_sel].copy()
    df_team['X_M'] = df_team['EVENT_X'].apply(lambda x: to_metric(x, 105))
    df_team['Y_M'] = df_team['EVENT_Y'].apply(lambda y: to_metric(y, 68))
    df_team['Zone'] = df_team.apply(map_to_zone, axis=1)
    
    # DZ Definition: 88.5m til 105m (mållinje)
    df_team['IS_DZ'] = (df_team['X_M'] >= 94.5) & (df_team['Y_M'] >= 25.16) & (df_team['Y_M'] <= 42.84)

    tabs = st.tabs(["SPILLEROVERSIGT", "AFSLUTNINGER", "DZ-ANALYSE", "SKUDZONER", "MÅLZONER"])
    pitch_cfg = {"half": True, "pitch_type": 'custom', "pitch_length": 105, "pitch_width": 68, "line_color": '#cccccc'}

    # TAB 0: SPILLEROVERSIGT
    with tabs[0]:
        # TAB 0: SPILLEROVERSIGT (OPDATERET LOGIK)
        p_stats = []
        for p, d in df_team.groupby('PLAYER_NAME'):
            s, m = len(d), len(d[d['EVENT_TYPEID']==16])
            dz_d = d[d['IS_DZ']]
            dz_s, dz_m = len(dz_d), len(dz_d[dz_d['EVENT_TYPEID']==16])
            
            p_stats.append({
                "Spiller": p, 
                "Skud": s, 
                "Mål": m, 
                "Konv.%": (m/s*100 if s > 0 else 0),
                "DZ-Skud": dz_s,
                "DZ-Mål": dz_m,
                "DZ-Konv.%": (dz_m/dz_s*100 if dz_s > 0 else 0),
                # Ganger med 100 her, så tallet er f.eks. 100 eller 85
                "DZ-Andel": (dz_s / s * 100 if s > 0 else 0) 
            })

        df_display = pd.DataFrame(p_stats).sort_values("Konv.%", ascending=False)
        
        # Beregn højde: ca. 35px per række + 40px til header
        dynamic_height = (len(df_display) + 1) * 35 + 40

        st.dataframe(
            df_display,
            use_container_width=True, 
            hide_index=True,
            height=dynamic_height, # Her fjernes scroll-baren
            column_config={
                "DZ-Andel": st.column_config.ProgressColumn(
                    "DZ-Andel", 
                    help="Andel af skud foretaget i Danger Zone",
                    format="%d%%", 
                    min_value=0, 
                    max_value=100
                ),
                "Konv.%": st.column_config.NumberColumn("Konv.%", format="%.1f%%"),
                "DZ-Konv.%": st.column_config.NumberColumn("DZ-Konv.%", format="%.1f%%")
            }
        )
        
    # TAB 1: AFSLUTNINGER
    with tabs[1]:
        c1, c2 = st.columns([2, 1])
        with c2:
            p_sel = st.selectbox("Spiller", ["Alle spillere"] + sorted(df_team['PLAYER_NAME'].unique()))
            d_v = df_team if p_sel == "Alle spillere" else df_team[df_team['PLAYER_NAME'] == p_sel]
            s, m = len(d_v), len(d_v[d_v["EVENT_TYPEID"]==16])
            st.markdown(f'<div class="stat-box"><div class="stat-label">Skud</div><div class="stat-value">{s}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Mål</div><div class="stat-value">{m}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Konvertering</div><div class="stat-value">{(m/s*100 if s>0 else 0):.1f}%</div></div>', unsafe_allow_html=True)
        with c1:
            pitch = VerticalPitch(**pitch_cfg)
            fig, ax = pitch.draw(figsize=(8, 10)); ax.set_ylim(55, 105)
            pitch.scatter(d_v['X_M'], d_v['Y_M'], s=100, c=(d_v['EVENT_TYPEID']==16).map({True: t_color, False: 'white'}), edgecolors=t_color, ax=ax, zorder=3)
            draw_logo_on_pitch(ax, t_logo); st.pyplot(fig)

    # TAB 2: DZ-ANALYSE
    with tabs[2]:
        c1, c2 = st.columns([2, 1])
        dz_d = df_team[df_team['IS_DZ']]
        with c2:
            s_dz, m_dz = len(dz_d), len(dz_d[dz_d["EVENT_TYPEID"]==16])
            st.markdown(f'<div class="stat-box"><div class="stat-label">DZ Skud</div><div class="stat-value">{s_dz}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">DZ Mål</div><div class="stat-value">{m_dz}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">DZ Konv.</div><div class="stat-value">{(m_dz/s_dz*100 if s_dz>0 else 0):.1f}%</div></div>', unsafe_allow_html=True)
        with c1:
            pitch = VerticalPitch(**pitch_cfg)
            fig, ax = pitch.draw(figsize=(8, 10)); ax.set_ylim(55, 105)
            ax.add_patch(patches.Rectangle((25.16, 88.5), 17.68, 16.5, color=t_color, alpha=0.15, zorder=1))
            pitch.scatter(dz_d['X_M'], dz_d['Y_M'], s=100, c=(dz_d['EVENT_TYPEID']==16).map({True: t_color, False: 'white'}), edgecolors=t_color, ax=ax, zorder=3)
            draw_logo_on_pitch(ax, t_logo); st.pyplot(fig)

    # TAB 3 & 4: ZONER
    for i, is_goal in enumerate([False, True]):
        with tabs[i+3]:
            c1, c2 = st.columns([1.6, 1])
            plot_df = df_team[df_team['EVENT_TYPEID'] == 16] if is_goal else df_team
            total_count = len(plot_df)
            with c2:
                st.write(f"**Zone-stats ({'Mål' if is_goal else 'Skud'})**")
                z_summary = []
                for z, b in ZONE_BOUNDARIES.items():
                    z_d = plot_df[plot_df['Zone'] == z]
                    if len(z_d) > 0:
                        top_p = z_d['PLAYER_NAME'].value_counts().idxmax()
                        z_summary.append({"Zone": z, "Antal": len(z_d), "Andel": (len(z_d)/total_count if total_count > 0 else 0), "Topscorer": top_p})
                st.dataframe(pd.DataFrame(z_summary).sort_values("Antal", ascending=False), hide_index=True, use_container_width=True, column_config={"Andel": st.column_config.NumberColumn(format="%.1f%%")})
            with c1:
                pitch = VerticalPitch(**pitch_cfg)
                fig, ax = pitch.draw(figsize=(8, 10)); ax.set_ylim(55, 105)
                max_v = plot_df['Zone'].value_counts().max() if not plot_df.empty else 1
                for z, b in ZONE_BOUNDARIES.items():
                    if b["y_max"] <= 55: continue
                    cnt = len(plot_df[plot_df['Zone']==z])
                    alpha = (cnt/max_v)*0.6 if cnt > 0 else 0.05
                    ax.add_patch(patches.Rectangle((b["x_min"], max(b["y_min"], 55)), b["x_max"]-b["x_min"], b["y_max"]-max(b["y_min"], 55), facecolor=t_color, alpha=alpha, edgecolor='black', ls='--'))
                    if cnt > 0: ax.text(b["x_min"]+(b["x_max"]-b["x_min"])/2, max(b["y_min"], 55)+(b["y_max"]-max(b["y_min"], 55))/2, f"{cnt}", ha='center', va='center', fontweight='bold')
                draw_logo_on_pitch(ax, t_logo); st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
