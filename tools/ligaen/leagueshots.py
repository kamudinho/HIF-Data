import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# HIF Identitet & Design
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'
DZ_COLOR = '#1f77b4'

# --- KLUB MAPPING ---
KLUB_NAVNE = {
    "HVI": "Hvidovre IF",
    "KIF": "Kolding IF",
    "MID": "Middelfart",
    "HOB": "Hobro IK",
    "VFF": "Viborg FF",
    "B93": "B.93",
    "FRE": "FC Fredericia",
    "ROS": "FC Roskilde",
    "HBK": "HB Køge",
    "ESB": "Esbjerg fB",
    "OB": "OB",
    "ODN": "OB",
    "SIL": "Silkeborg IF",
    "VEN": "Vendsyssel FF",
    "HIK": "Hillerød Fodbold"
}

def get_opponent_name(description):
    """Finder modstanderen ud fra DESCRIPTION (f.eks. 'HVI - KIF')"""
    if not description or ' - ' not in description:
        return "Ukendt"
    teams = [t.strip() for t in description.split(' - ')]
    opp_code = teams[1] if teams[0] == 'HVI' else teams[0]
    return KLUB_NAVNE.get(opp_code, opp_code)

def vis_side(dp):
    # 1. DATA SETUP
    opta_data = dp.get('opta', {})
    df_all = opta_data.get('league_shotevents', pd.DataFrame()).copy()

    if df_all.empty:
        st.info("Ingen ligadata fundet.")
        return

    # Standardiser kolonner
    df_all.columns = [c.upper() for c in df_all.columns]
    
    # --- LOGIK: OVERSÆT HOLD TIL RIGTIGE NAVNE ---
    # Vi bruger DESCRIPTION til at finde ud af hvem modstanderen er i hver kamp
    def map_team_name(row):
        if row['EVENT_CONTESTANT_NAME'] == 'HVI':
            return "Hvidovre IF"
        # Hvis det ikke er HVI, er det modstanderen fra kampens beskrivelse
        return get_opponent_name(row['DESCRIPTION'])

    df_all['KLUB_DISPLAY'] = df_all.apply(map_team_name, axis=1)
    teams_in_data = sorted(df_all['KLUB_DISPLAY'].unique())

    st.markdown(f"""
        <style>
            .stat-box {{ background-color: #f8f9fa; padding: 10px; border-radius: 8px; border-left: 5px solid #cc0000; margin-bottom: 10px; }}
            .stat-label {{ font-size: 0.8rem; text-transform: uppercase; color: #666; font-weight: bold; display: flex; align-items: center; gap: 8px; }}
            .stat-value {{ font-size: 1.5rem; font-weight: 800; color: #1a1a1a; margin-top: 2px; }}
        </style>
    """, unsafe_allow_html=True)

    # --- ZONE DEFINITIONER ---
    P_L, P_W = 105.0, 68.0
    ZONE_BOUNDARIES = {
        "Zone 1": {"y_min": 99.5, "y_max": 105.0, "x_min": 24.84, "x_max": 43.16},
        "Zone 2": {"y_min": 94.0, "y_max": 99.5, "x_min": 24.84, "x_max": 43.16},
        "Zone 3": {"y_min": 88.5, "y_max": 94.0, "x_min": 24.84, "x_max": 43.16},
        "Zone 4A": {"y_min": 99.5, "y_max": 105.0, "x_min": 43.16, "x_max": 54.1},
        "Zone 4B": {"y_min": 99.5, "y_max": 105.0, "x_min": 13.9, "x_max": 24.84},
        "Zone 5A": {"y_min": 88.5, "y_max": 99.5, "x_min": 43.16, "x_max": 54.1},
        "Zone 5B": {"y_min": 88.5, "y_max": 99.5, "x_min": 13.9, "x_max": 24.84},
        "Zone 6A": {"y_min": 88.5, "y_max": 105.0, "x_min": 54.1, "x_max": 68.0},
        "Zone 6B": {"y_min": 88.5, "y_max": 105.0, "x_min": 0.0, "x_max": 13.9},
        "Zone 7C": {"y_min": 75.0, "y_max": 88.5, "x_min": 0.0, "x_max": 24.84},
        "Zone 7B": {"y_min": 75.0, "y_max": 88.5, "x_min": 24.84, "x_max": 43.16},
        "Zone 7A": {"y_min": 75.0, "y_max": 88.5, "x_min": 43.16, "x_max": 68.0},
        "Zone 8":  {"y_min": 0, "y_max": 75.0, "x_min": 0, "x_max": 68.0}
    }

    def map_to_zone(r):
        mx, my = r['EVENT_X'] * (P_L / 100), r['EVENT_Y'] * (P_W / 100)
        for z, b in ZONE_BOUNDARIES.items():
            if b["y_min"] <= mx <= b["y_max"] and b["x_min"] <= my <= b["x_max"]: return z
        return "Zone 8"

    df_all['Zone'] = df_all.apply(map_to_zone, axis=1)
    df_all['IS_DZ_GEO'] = (df_all['EVENT_X'] >= 88.5) & (df_all['EVENT_Y'] >= 37.0) & (df_all['EVENT_Y'] <= 63.0)

    tabs = st.tabs(["SPILLEROVERSIGT", "AFSLUTNINGER", "DZ-AFSLUTNINGER", "AFSLUTNINGSZONER", "MÅLZONER"])

    # --- TAB 0: SPILLEROVERSIGT ---
    with tabs[0]:
        stats = []
        for (p, klub), d in df_all.groupby(['PLAYER_NAME', 'KLUB_DISPLAY']):
            dz = d[d['IS_DZ_GEO']]
            s, m = len(d), len(d[d['EVENT_TYPEID'] == 16])
            dzs, dzm = len(dz), len(dz[dz['EVENT_TYPEID'] == 16])
            stats.append({
                "Spiller": p, "Klub": klub, "Skud": s, "Mål": m, 
                "Konvertering%": (m/s*100) if s > 0 else 0,
                "DZ-Skud": dzs, "DZ-Mål": dzm, "DZ-Andel": (dzs/s*100) if s > 0 else 0
            })
        df_f = pd.DataFrame(stats).sort_values("Skud", ascending=False)
        st.dataframe(df_f, use_container_width=True, height=(len(df_f)+1)*36, hide_index=True,
                    column_config={
                        "Konvertering%": st.column_config.NumberColumn("Konv.%", format="%.1f%%"),
                        "DZ-Andel": st.column_config.ProgressColumn("DZ-Andel", format="%.0f%%", min_value=0, max_value=100)
                    })

    # --- TAB 1: AFSLUTNINGER ---
    with tabs[1]:
        c1, c2 = st.columns([2, 1])
        with c2:
            t_sel = st.selectbox("Vælg Hold", teams_in_data, key="t_afsl")
            df_t = df_all[df_all['KLUB_DISPLAY'] == t_sel]
            sel_p = st.selectbox("Vælg spiller", ["Hele Holdet"] + sorted(df_t['PLAYER_NAME'].unique()), key="p_afsl")
            d_v = df_t if sel_p == "Hele Holdet" else df_t[df_t['PLAYER_NAME'] == sel_p]
            
            s_cnt, m_cnt = len(d_v), len(d_v[d_v["EVENT_TYPEID"]==16])
            st.markdown(f'<div class="stat-box"><div class="stat-label">Skud</div><div class="stat-value">{s_cnt}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Mål</div><div class="stat-value">{m_cnt}</div></div>', unsafe_allow_html=True)
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            colors = (d_v['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
            pitch.scatter(d_v['EVENT_X'], d_v['EVENT_Y'], s=25, c=colors, edgecolors=HIF_RED, ax=ax)
            st.pyplot(fig)

    # --- ZONER FUNKTION ---
    def zone_plot_enhanced(data_all, is_m, key_suffix):
        col_viz, col_ctrl = st.columns([1.8, 1])
        with col_ctrl:
            t_sel = st.selectbox("Vælg Hold", teams_in_data, key=f"t_z_{key_suffix}")
            df_t = data_all[data_all['KLUB_DISPLAY'] == t_sel]
            p_sel = st.selectbox("Vælg spiller", ["Hele Holdet"] + sorted(df_t['PLAYER_NAME'].unique()), key=f"p_z_{key_suffix}")
            d_v = df_t if p_sel == "Hele Holdet" else df_t[df_t['PLAYER_NAME'] == p_sel]
            plot_data = d_v[d_v['EVENT_TYPEID'] == 16] if is_m else d_v
            z_counts = plot_data.groupby('Zone').size()
            
            z_df = pd.DataFrame([{'Zone': k, 'Antal': z_counts.get(k, 0)} for k in ZONE_BOUNDARIES.keys() if z_counts.get(k,0) > 0]).sort_values('Antal', ascending=False)
            st.dataframe(z_df, hide_index=True, use_container_width=True)

        with col_viz:
            pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='grey')
            fig, ax = pitch.draw(figsize=(8, 10))
            ax.set_ylim(55, 105)
            max_v = z_counts.max() if not z_counts.empty else 1
            cmap = plt.cm.YlOrRd if is_m else plt.cm.Blues
            for name, b in ZONE_BOUNDARIES.items():
                if b["y_max"] <= 55: continue
                cnt = z_counts.get(name, 0)
                face = cmap(cnt/max_v) if cnt > 0 else '#f9f9f9'
                ax.add_patch(patches.Rectangle((b["x_min"], max(b["y_min"], 55)), b["x_max"]-b["x_min"], b["y_max"]-max(b["y_min"], 55), facecolor=face, alpha=0.7, edgecolor='black', ls='--'))
                if cnt > 0:
                    ax.text(b["x_min"]+(b["x_max"]-b["x_min"])/2, max(b["y_min"], 55)+(b["y_max"]-max(b["y_min"], 55))/2, f"{cnt}", ha='center', va='center', fontsize=8, fontweight='bold')
            st.pyplot(fig)

    with tabs[3]: zone_plot_enhanced(df_all, False, "skud")
    with tabs[4]: zone_plot_enhanced(df_all, True, "maal")
