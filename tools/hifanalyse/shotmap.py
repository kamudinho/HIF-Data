import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from data.utils.team_mapping import TEAMS

# HIF Identitet
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'
DZ_COLOR = '#1f77b4'

def vis_side(dp):
    # --- 1. DATA SETUP ---
    # Vi henter data og logo_map
    df_skud = dp.get('playerstats', pd.DataFrame()).copy()
    logo_map = dp.get("logo_map", {})
    
    if df_skud.empty:
        st.info("Ingen data fundet for det valgte hold.")
        return

    # Sikr at alle nødvendige kolonner er uppercase
    df_skud.columns = [c.upper() for c in df_skud.columns]
    
    # FIX: Definer kolonnenavnet for team ID (Opta bruger ofte 'CONTESTANTID' eller lignende)
    # I din struktur for playerstats er det ofte 'TEAM_ID' eller 'CONTESTANT_ID'
    col_team_uuid = 'EVENT_CONTESTANT_OPTAUUID' if 'EVENT_CONTESTANT_OPTAUUID' in df_skud.columns else 'TEAM_ID'

    # --- CSS STYLING ---
    st.markdown(f"""
        <style>
            .stat-box {{ background-color: #f8f9fa; padding: 10px; border-radius: 8px; border-left: 5px solid {HIF_RED}; margin-bottom: 10px; }}
            .stat-label {{ font-size: 0.8rem; text-transform: uppercase; color: #666; font-weight: bold; display: flex; align-items: center; gap: 8px; }}
            .stat-value {{ font-size: 1.5rem; font-weight: 800; color: #1a1a1a; margin-top: 2px; }}
            .hif-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
            .hif-table th {{ background: #eee; padding: 10px; border-bottom: 2px solid #ccc; }}
            .hif-table td {{ padding: 8px; border-bottom: 1px solid #eee; text-align: center; vertical-align: middle; }}
            .bar-bg {{ background: #eee; width: 100%; height: 8px; border-radius: 4px; position: relative; }}
            .bar-fill {{ background: {HIF_RED}; height: 100%; border-radius: 4px; }}
        </style>
    """, unsafe_allow_html=True)

    # --- 2. ZONE DEFINITIONER ---
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

    df_skud['ZONE'] = df_skud.apply(map_to_zone, axis=1)
    df_skud['IS_DZ_GEO'] = (df_skud['EVENT_X'] >= 88.5) & (df_skud['EVENT_Y'] >= 37.0) & (df_skud['EVENT_Y'] <= 63.0)

    tabs = st.tabs(["SPILLEROVERSIGT", "AFSLUTNINGER", "DZ-AFSLUTNINGER", "AFSLUTNINGSZONER", "MÅLZONER"])

    # --- TAB 0: SPILLEROVERSIGT (HTML med logoer og bars) ---
    with tabs[0]:
        stats_list = []
        for p in df_skud['PLAYER_NAME'].unique():
            d = df_skud[df_skud['PLAYER_NAME'] == p]
            t_uuid = str(d[col_team_uuid].iloc[0]).upper() if col_team_uuid in d.columns else ""
            dz = d[d['IS_DZ_GEO']]
            
            s, m = len(d), len(d[d['EVENT_TYPEID'] == 16])
            dzs, dzm = len(dz), len(dz[dz['EVENT_TYPEID'] == 16])
            xg = d['EXPECTED_GOALS_VALUE'].sum() if 'EXPECTED_GOALS_VALUE' in d.columns else 0
            
            stats_list.append({
                "UUID": t_uuid, "Spiller": p, "S": s, "M": m, "xG": round(xg, 2),
                "K%": (m/s*100) if s > 0 else 0, "DZ-S": dzs, "DZ-M": dzm,
                "DZ-Andel": (dzs/s*100) if s > 0 else 0
            })
        
        df_f = pd.DataFrame(stats_list).sort_values("M", ascending=False).head(20).reset_index(drop=True)
        
        html = f"""<table class="hif-table"><thead><tr><th>#</th><th></th><th style="text-align:left;">Spiller</th>
                  <th>S</th><th>M</th><th>xG</th><th>K%</th><th>DZ-S</th><th>DZ-Andel</th></tr></thead><tbody>"""
        
        for i, row in df_f.iterrows():
            wy_id = next((v['team_wyid'] for k, v in TEAMS.items() if v.get('opta_uuid', '').upper() == row['UUID']), None)
            l_url = logo_map.get(wy_id) or logo_map.get(str(wy_id), "")
            logo_img = f'<img src="{l_url}" width="25">' if l_url else ""
            
            bar = f'<div class="bar-bg"><div class="bar-fill" style="width:{row["DZ-Andel"]}%;"></div></div>'

            html += f"""<tr><td>{i+1}</td><td>{logo_img}</td><td style="text-align:left;"><b>{row['Spiller']}</b></td>
                        <td>{row['S']}</td><td style="color:{HIF_RED}; font-weight:800;">{row['M']}</td>
                        <td>{row['xG']:.2f}</td><td>{row['K%']:.1f}%</td><td>{row['DZ-S']}</td>
                        <td style="width:80px;">{bar}<span style="font-size:10px;">{int(row['DZ-Andel'])}%</span></td></tr>"""
        st.markdown(html + "</tbody></table>", unsafe_allow_html=True)

    # --- TAB 1: AFSLUTNINGER (Punktplot) ---
    with tabs[1]:
        c1, c2 = st.columns([2, 1])
        with c2:
            sel_p = st.selectbox("Vælg spiller", ["Hele Holdet"] + sorted(df_skud['PLAYER_NAME'].unique()))
            d_v = df_skud if sel_p == "Hele Holdet" else df_skud[df_skud['PLAYER_NAME'] == sel_p]
            # ... stat-boxes her ...
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            colors = (d_v['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
            pitch.scatter(d_v['EVENT_X'], d_v['EVENT_Y'], s=80, c=colors, edgecolors=HIF_RED, ax=ax)
            st.pyplot(fig)

    # --- TAB 3 & 4: ZONER (RETTET) ---
    def zone_plot_enhanced(data, is_m):
        if data.empty:
            st.warning("Ingen data at vise.")
            return

        col_viz, col_ctrl = st.columns([1.8, 1])
        total_count = len(data)

        # Beregn stats
        z_counts = data.groupby('ZONE').size()
        
        with col_viz:
            pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='grey')
            fig, ax = pitch.draw(figsize=(8, 10))
            ax.set_ylim(55, 105)

            max_v = z_counts[z_counts.index != "Zone 8"].max() if not z_counts.empty else 1
            cmap = plt.cm.YlOrRd if is_m else plt.cm.Blues

            for name, b in ZONE_BOUNDARIES.items():
                if b["y_max"] <= 55: continue
                cnt = z_counts.get(name, 0)
                y_draw_min = max(b["y_min"], 55)
                color_val = cnt / max_v if max_v > 0 else 0
                face_color = cmap(color_val) if cnt > 0 else '#f9f9f9'

                ax.add_patch(patches.Rectangle((b["x_min"], y_draw_min), b["x_max"]-b["x_min"], b["y_max"]-y_draw_min, 
                                             facecolor=face_color, alpha=0.7, edgecolor='black', linestyle='--'))
                if cnt > 0:
                    ax.text(b["x_min"] + (b["x_max"]-b["x_min"])/2, y_draw_min + (b["y_max"]-y_draw_min)/2, 
                            f"{name}\n{cnt}", ha='center', va='center', fontsize=8, fontweight='bold')
            st.pyplot(fig)

    with tabs[3]: zone_plot_enhanced(df_skud, False)
    with tabs[4]: zone_plot_enhanced(df_skud[df_skud['EVENT_TYPEID'] == 16], True)
