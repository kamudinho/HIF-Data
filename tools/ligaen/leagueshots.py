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

# --- CONFIG ---
HIF_RED = '#cc0000'
HIF_GOLD = '#FFD700'
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o"

# --- ZONE DEFINITIONER (ALLE NUANCER) ---
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
def load_data():
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    sql = f"""
        SELECT e.*, q.QUALIFIER_VALUE as XG_RAW FROM {DB}.OPTA_EVENTS e 
        LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID AND q.QUALIFIER_QID = 321
        WHERE e.EVENT_TYPEID IN (13,14,15,16) 
        AND e.MATCH_OPTAUUID IN (SELECT DISTINCT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}')
    """
    df = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
    df.columns = [c.upper() for c in df.columns]
    return df

def get_zone(r):
    x_m, y_m = r['EVENT_X'] * (105/100), r['EVENT_Y'] * (68/100)
    for z, b in ZONE_BOUNDARIES.items():
        if b["y_min"] <= x_m <= b["y_max"] and b["x_min"] <= y_m <= b["x_max"]: return z
    return "Zone 8"

def draw_zone_pitch(df_plot, df_total, t_color, title):
    pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='grey')
    fig, ax = pitch.draw(figsize=(8, 10))
    ax.set_ylim(55, 105)
    
    z_counts = df_plot['Zone'].value_counts()
    max_v = z_counts.max() if not z_counts.empty else 1
    
    for z, b in ZONE_BOUNDARIES.items():
        if b["y_max"] <= 55: continue
        count = z_counts.get(z, 0)
        pct = (count / len(df_total) * 100) if len(df_total) > 0 else 0
        alpha = (count/max_v)*0.6 if count > 0 else 0.05
        
        ax.add_patch(patches.Rectangle((b["x_min"], max(b["y_min"], 55)), b["x_max"]-b["x_min"], b["y_max"]-max(b["y_min"], 55), 
                                      facecolor=t_color, alpha=alpha, edgecolor='black', ls='--'))
        if count > 0:
            ax.text(b["x_min"]+(b["x_max"]-b["x_min"])/2, max(b["y_min"], 55)+(b["y_max"]-max(b["y_min"], 55))/2, 
                    f"{count}\n({pct:.1f}%)", ha='center', va='center', fontsize=9, fontweight='bold')
    return fig

# --- MAIN APP ---
def vis_side(dp=None):
    df_all = load_data()
    if df_all.empty: return

    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['EVENT_CONTESTANT_OPTAUUID'].str.upper().map(uuid_to_name)
    teams = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])

    # Layout: Dropdown altid til højre
    c_t1, c_t2 = st.columns([2, 1])
    with c_t2:
        t_sel = st.selectbox("Vælg hold", teams, index=teams.index("Hvidovre") if "Hvidovre" in teams else 0)
    
    t_color = TEAM_COLORS.get(t_sel, {}).get('primary', HIF_RED)
    df_team = df_all[df_all['KLUB_NAVN'] == t_sel].copy()
    df_team['Zone'] = df_team.apply(get_zone, axis=1)
    df_team['IS_DZ'] = (df_team['EVENT_X'] >= 88.5) & (df_team['EVENT_Y'] >= 37.0) & (df_team['EVENT_Y'] <= 63.0)

    tabs = st.tabs(["SPILLEROVERSIGT", "SKUDZONER", "MÅLZONER", "DZ-ANALYSE"])

    # --- TAB 0: SPILLEROVERSIGT (UDVIDET DATA) ---
    with tabs[0]:
        p_stats = []
        for p, d in df_team.groupby('PLAYER_NAME'):
            s, m = len(d), len(d[d['EVENT_TYPEID']==16])
            dz_d = d[d['IS_DZ']]
            dz_s, dz_m = len(dz_d), len(dz_d[dz_d['EVENT_TYPEID']==16])
            p_stats.append({
                "Spiller": p, "Skud": s, "Mål": m, "Konv.%": (m/s*100 if s>0 else 0),
                "DZ-Skud": dz_s, "DZ-Mål": dz_m, "DZ-Konv.%": (dz_m/dz_s*100 if dz_s>0 else 0)
            })
        st.dataframe(pd.DataFrame(p_stats).sort_values("Skud", ascending=False), use_container_width=True, hide_index=True)

    # --- TAB 1 & 2: ZONE ANALYSE ---
    for i, is_goal in enumerate([False, True]):
        with tabs[i+1]:
            c1, c2 = st.columns([2, 1])
            plot_df = df_team[df_team['EVENT_TYPEID'] == 16] if is_goal else df_team
            
            with c2:
                st.write(f"**Data per zone ({'Mål' if is_goal else 'Skud'})**")
                z_summary = []
                for z in ZONE_BOUNDARIES.keys():
                    z_d = plot_df[plot_df['Zone'] == z]
                    if len(z_d) > 0:
                        top_p = z_d['PLAYER_NAME'].value_counts().idxmax()
                        z_summary.append({"Zone": z, "Antal": len(z_d), "%": f"{(len(z_d)/len(df_team)*100):.1f}%", "Topscorer": top_p})
                st.table(pd.DataFrame(z_summary).sort_values("Antal", ascending=False))
            
            with c1:
                st.pyplot(draw_zone_pitch(plot_df, df_team, t_color, "Zoner"))

    # --- TAB 3: DZ ANALYSE ---
    with tabs[3]:
        c1, c2 = st.columns([2, 1])
        dz_data = df_team[df_team['IS_DZ']]
        with c2:
            s, m = len(dz_data), len(dz_data[dz_data['EVENT_TYPEID']==16])
            st.metric("DZ Skud", s)
            st.metric("DZ Mål", m)
            st.metric("DZ Konvertering", f"{(m/s*100 if s>0 else 0):.1f}%")
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw()
            ax.add_patch(patches.Rectangle((37, 88.5), 26, 11.5, color=t_color, alpha=0.2))
            pitch.scatter(dz_data['EVENT_X'], dz_data['EVENT_Y'], c=(dz_data['EVENT_TYPEID']==16).map({True: t_color, False: 'white'}), edgecolors=t_color, ax=ax)
            st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
