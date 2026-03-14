import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from data.utils.team_mapping import TEAMS

# --- KONSTANTER (HIF Identitet) ---
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b' 
DZ_COLOR = '#1f77b4'

def vis_side(dp):
    # --- 1. DATA INDLÆSNING & LOGO SETUP ---
    opta_data = dp.get('opta', {})
    logo_map = dp.get("logo_map", {})
    df_skud = opta_data.get('league_shotevents', pd.DataFrame()).copy()

    if df_skud.empty:
        st.info("Ingen liga-skuddata fundet.")
        return
    
    df_skud.columns = [c.upper() for c in df_skud.columns]
    col_team_uuid = 'EVENT_CONTESTANT_OPTAUUID'

    # Mapping til klubnavne
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}

    # --- 2. CSS STYLING ---
    st.markdown(f"""
        <style>
            .stat-box {{ background-color: #f8f9fa; padding: 10px; border-radius: 8px; border-left: 5px solid {HIF_RED}; margin-bottom: 10px; }}
            .stat-label {{ font-size: 0.8rem; text-transform: uppercase; color: #666; font-weight: bold; display: flex; align-items: center; gap: 8px; }}
            .stat-value {{ font-size: 1.5rem; font-weight: 800; color: #1a1a1a; margin-top: 2px; }}
            .legend-dot {{ height: 12px; width: 12px; border-radius: 50%; display: inline-block; vertical-align: middle; }}
            .liga-table {{ width: 100%; border-collapse: collapse; font-size: 14px; margin-bottom: 30px; }}
            .liga-table th {{ background-color: #f2f2f2; padding: 10px; text-align: center; border-bottom: 2px solid #ddd; }}
            .liga-table td {{ padding: 10px; border-bottom: 1px solid #eee; text-align: center; }}
            .liga-table td.left {{ text-align: left; }}
        </style>
    """, unsafe_allow_html=True)

    # --- 3. ZONE DEFINITIONER ---
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

    def map_to_zone(r):
        mx, my = r['EVENT_X'] * (P_L / 100), r['EVENT_Y'] * (P_W / 100)
        for z, b in ZONE_BOUNDARIES.items():
            if b["y_min"] <= mx <= b["y_max"] and b["x_min"] <= my <= b["x_max"]:
                return z
        return "Zone 8"

    df_skud['Zone'] = df_skud.apply(map_to_zone, axis=1)
    df_skud['IS_DZ_GEO'] = (df_skud['EVENT_X'] >= 88.5) & (df_skud['EVENT_Y'] >= 37.0) & (df_skud['EVENT_Y'] <= 63.0)

    # --- 4. TABS ---
    tabs = st.tabs(["SPILLEROVERSIGT", "AFSLUTNINGER", "DZ-AFSLUTNINGER", "AFSLUTNINGSZONER", "MÅLZONER"])

    # --- TAB 0: SPILLEROVERSIGT (TOP 20) ---
    with tabs[0]:
        stats = []
        for p in df_skud['PLAYER_NAME'].unique():
            d = df_skud[df_skud['PLAYER_NAME'] == p]
            t_uuid = str(d[col_team_uuid].iloc[0]).upper()
            dz = d[d['IS_DZ_GEO']]
            s, m = len(d), len(d[d['EVENT_TYPEID'] == 16])
            dzs, dzm = len(dz), len(dz[dz['EVENT_TYPEID'] == 16])
            
            stats.append({
                "UUID": t_uuid,
                "Spiller": p, 
                "Klub": uuid_to_name.get(t_uuid, "Ukendt"),
                "Skud": s, "Mål": m, 
                "Konv%": (m/s*100) if s > 0 else 0,
                "DZ-S": dzs, "DZ-Andel": (dzs/s*100) if s > 0 else 0
            })
        
        df_f = pd.DataFrame(stats).sort_values("Mål", ascending=False).head(20).reset_index(drop=True)
        
        html_table = '<table class="liga-table"><thead><tr><th>#</th><th></th><th class="left">Spiller</th><th class="left">Klub</th><th>S</th><th>M</th><th>K%</th><th>DZ-S</th><th>DZ-Andel</th></tr></thead><tbody>'
        for i, row in df_f.iterrows():
            # Logo Logik
            wy_id = next((info.get('team_wyid') for k, info in TEAMS.items() if info.get('opta_uuid') == row['UUID']), None)
            logo_url = logo_map.get(wy_id, next((v['logo'] for k, v in TEAMS.items() if v.get('opta_uuid') == row['UUID']), ""))
            logo_img = f'<img src="{logo_url}" width="22">' if logo_url else ""
            
            html_table += f"""
            <tr>
                <td>{i+1}</td>
                <td>{logo_img}</td>
                <td class="left"><b>{row['Spiller']}</b></td>
                <td class="left">{row['Klub']}</td>
                <td>{row['Skud']}</td>
                <td style="color:{HIF_RED}; font-weight:800;">{row['Mål']}</td>
                <td>{row['Konv%']:.1f}%</td>
                <td>{row['DZ-S']}</td>
                <td><div style="background:#eee; width:50px; height:8px; display:inline-block;"><div style="background:{HIF_RED}; width:{row['DZ-Andel']}%; height:100%;"></div></div> {row['DZ-Andel']:.0f}%</td>
            </tr>"""
        html_table += "</tbody></table>"
        st.markdown(html_table, unsafe_allow_html=True)

    # --- HJÆLPEFUNKTION TIL DROPDOWNS (RETTET) ---
    def get_filtered_data(key_suffix):
        # 1. Liste over alle hold baseret på UUIDs i data
        uuids_in_data = df_skud[col_team_uuid].unique()
        available_teams = sorted([uuid_to_name[str(u).upper()] for u in uuids_in_data if str(u).upper() in uuid_to_name])
        
        c_left, c_right = st.columns(2)
        with c_left:
            sel_team = st.selectbox("Vælg Hold", ["ALLE HOLD"] + available_teams, key=f"t_{key_suffix}")
        
        # 2. Find spillere baseret på holdvalg
        if sel_team == "ALLE HOLD":
            player_list = sorted(df_skud['PLAYER_NAME'].unique())
            d_filtered = df_skud.copy()
        else:
            team_uuid = next(v['opta_uuid'].upper() for k, v in TEAMS.items() if k == sel_team)
            d_filtered = df_skud[df_skud[col_team_uuid].str.upper() == team_uuid]
            player_list = sorted(d_filtered['PLAYER_NAME'].unique())
            
        with c_right:
            sel_p = st.selectbox("Vælg Spiller", ["HELE HOLDET"] + player_list, key=f"p_{key_suffix}")
        
        if sel_p != "HELE HOLDET":
            d_filtered = d_filtered[d_filtered['PLAYER_NAME'] == sel_p]
            
        return d_filtered

    # --- TAB 1: AFSLUTNINGER ---
    with tabs[1]:
        d_v = get_filtered_data("afsl")
        c1, c2 = st.columns([2, 1])
        with c2:
            s_cnt, m_cnt = len(d_v), len(d_v[d_v["EVENT_TYPEID"]==16])
            konv = (m_cnt/s_cnt*100) if s_cnt > 0 else 0
            st.markdown(f'<div class="stat-box"><div class="stat-label">Skud</div><div class="stat-value">{s_cnt}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Mål</div><div class="stat-value">{m_cnt}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box" style="border-left-color:{HIF_GOLD}"><div class="stat-label">Konvertering</div><div class="stat-value">{konv:.2f}%</div></div>', unsafe_allow_html=True)
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            colors = (d_v['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
            pitch.scatter(d_v['EVENT_X'], d_v['EVENT_Y'], s=80, c=colors, edgecolors=HIF_RED, linewidth=1, ax=ax)
            st.pyplot(fig)

    # --- TAB 2: DZ-AFSLUTNINGER ---
    with tabs[2]:
        d_v = get_filtered_data("dz")
        c1, c2 = st.columns([2, 1])
        with c2:
            dz_d = d_v[d_v['IS_DZ_GEO']]
            m_alt = len(d_v[d_v["EVENT_TYPEID"]==16])
            m_dz = len(dz_d[dz_d["EVENT_TYPEID"]==16])
            st.markdown(f'<div class="stat-box" style="border-left-color:{HIF_RED}"><div class="stat-label">DZ Skud</div><div class="stat-value">{len(dz_d)}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box" style="border-left-color:{HIF_RED}"><div class="stat-label">DZ Mål</div><div class="stat-value">{m_dz}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box" style="border-left-color:{HIF_GOLD}"><div class="stat-label">Andel af mål fra DZ</div><div class="stat-value">{(m_dz/m_alt*100 if m_alt > 0 else 0):.1f}%</div></div>', unsafe_allow_html=True)
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            ax.add_patch(patches.Rectangle((37, 88.5), 26, 11.5, color=DZ_COLOR, alpha=0.15))
            colors = (dz_d['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
            pitch.scatter(dz_d['EVENT_X'], dz_d['EVENT_Y'], s=80, c=colors, edgecolors=HIF_RED, ax=ax)
            st.pyplot(fig)

    # --- TAB 3 & 4: ZONER ---
    def zone_plot_enhanced(is_m, suffix):
        d_v = get_filtered_data(suffix)
        col_viz, col_ctrl = st.columns([1.8, 1])
        
        data_to_plot = d_v[d_v['EVENT_TYPEID'] == 16] if is_m else d_v
        zone_stats = {}
        for zone, b in ZONE_BOUNDARIES.items():
            z_data = data_to_plot[data_to_plot['Zone'] == zone]
            cnt = len(z_data)
            top_p = z_data['PLAYER_NAME'].mode().iloc[0].split()[-1] if cnt > 0 else "-"
            zone_stats[zone] = {'cnt': cnt, 'top': top_p}

        with col_ctrl:
            st.markdown(f"**{'MÅL' if is_m else 'SKUD'} PER ZONE**")
            z_df = pd.DataFrame([{'Zone': k, 'Antal': v['cnt'], 'Top': v['top']} for k, v in zone_stats.items() if k != "Zone 8"]).sort_values("Antal", ascending=False)
            st.dataframe(z_df, hide_index=True, use_container_width=True)

        with col_viz:
            pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='grey')
            fig, ax = pitch.draw(figsize=(8, 10))
            ax.set_ylim(55, 105)
            max_v = max([v['cnt'] for k, v in zone_stats.items() if k != "Zone 8"]) if len(data_to_plot) > 0 else 1
            cmap = plt.cm.YlOrRd if is_m else plt.cm.Blues

            for name, b in ZONE_BOUNDARIES.items():
                if b["y_max"] <= 55: continue
                y_draw_min = max(b["y_min"], 55)
                stats = zone_stats[name]
                face_color = cmap(stats['cnt']/max_v) if stats['cnt'] > 0 else '#f9f9f9'
                rect = patches.Rectangle((b["x_min"], y_draw_min), b["x_max"]-b["x_min"], b["y_max"]-y_draw_min, facecolor=face_color, alpha=0.7, edgecolor='black', linestyle='--')
                ax.add_patch(rect)
                if stats['cnt'] > 0:
                    ax.text(b["x_min"] + (b["x_max"] - b["x_min"])/2, y_draw_min + (b["y_max"]-y_draw_min)/2, f"{stats['cnt']}\n{stats['top']}", ha='center', va='center', fontsize=8)
            st.pyplot(fig)

    with tabs[3]: zone_plot_enhanced(False, "z_s")
    with tabs[4]: zone_plot_enhanced(True, "z_m")
