import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from data.utils.team_mapping import TEAMS

# --- DESIGN KONSTANTER ---
HIF_RED = '#cc0000'
DZ_COLOR = '#1f77b4'

def vis_side(dp):
    # 1. DATA & LOGO SETUP
    opta_data = dp.get('opta', {})
    logo_map = dp.get("logo_map", {})
    df_skud = opta_data.get('league_shotevents', pd.DataFrame()).copy()

    if df_skud.empty:
        st.info("Ingen data fundet.")
        return
    
    # Standardiser kolonner til UPPERCASE
    df_skud.columns = [c.upper() for c in df_skud.columns]
    col_team_uuid = 'EVENT_CONTESTANT_OPTAUUID'
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}

    # --- 2. ZONE DEFINITIONER (Til Heatmaps) ---
    P_L, P_W = 105.0, 68.0
    X_MID_L, X_MID_R = (P_W - 18.32) / 2, (P_W + 18.32) / 2
    X_INN_L, X_INN_R = (P_W - 40.2) / 2, (P_W + 40.2) / 2
    Y_GOAL, Y_6YD, Y_PK, Y_18YD, Y_MID = 105.0, 99.5, 94.0, 88.5, 75.0

    ZONE_BOUNDS = {
        "Zone 1": {"y_min": Y_6YD, "y_max": Y_GOAL, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 2": {"y_min": Y_PK, "y_max": Y_6YD, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 3": {"y_min": Y_18YD, "y_max": Y_PK, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 7B": {"y_min": Y_MID, "y_max": Y_18YD, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 8":  {"y_min": 0, "y_max": Y_MID, "x_min": 0, "x_max": P_W}
    }

    def map_to_zone(r):
        mx, my = r['EVENT_X'] * (P_L / 100), r['EVENT_Y'] * (P_W / 100)
        for z, b in ZONE_BOUNDS.items():
            if b["y_min"] <= mx <= b["y_max"] and b["x_min"] <= my <= b["x_max"]: return z
        return "Øvrige"

    df_skud['Zone'] = df_skud.apply(map_to_zone, axis=1)
    df_skud['IS_DZ'] = (df_skud['EVENT_X'] >= 88.5) & (df_skud['EVENT_Y'] >= 37.0) & (df_skud['EVENT_Y'] <= 63.0)

    # --- 3. CSS (Vigtigt for Tabel & Bars) ---
    st.markdown(f"""
        <style>
            .hif-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
            .hif-table th {{ background: #eee; padding: 10px; border-bottom: 2px solid #ccc; }}
            .hif-table td {{ padding: 8px; border-bottom: 1px solid #eee; text-align: center; vertical-align: middle; }}
            .bar-container {{ background: #eee; width: 100%; height: 8px; border-radius: 4px; margin-top: 4px; }}
            .bar-fill {{ background: {HIF_RED}; height: 100%; border-radius: 4px; }}
        </style>
    """, unsafe_allow_html=True)

    tabs = st.tabs(["SPILLEROVERSIGT", "AFSLUTNINGER", "DZ-ANALYSE", "ZONER (SKUD)", "ZONER (MÅL)"])

    # --- TAB 0: OVERSIGT MED LOGO & BARS ---
    with tabs[0]:
        stats = []
        for p in df_skud['PLAYER_NAME'].unique():
            d = df_skud[df_skud['PLAYER_NAME'] == p]
            t_uuid = str(d[col_team_uuid].iloc[0]).upper()
            dz = d[d['IS_DZ']]
            s, m = len(d), len(d[d['EVENT_TYPEID'] == 16])
            stats.append({
                "UUID": t_uuid, "Spiller": p, "S": s, "M": m, 
                "xG": d['EXPECTED_GOALS_VALUE'].sum() if 'EXPECTED_GOALS_VALUE' in d.columns else 0,
                "DZ_A": (len(dz)/s*100) if s > 0 else 0
            })
        
        df_f = pd.DataFrame(stats).sort_values("M", ascending=False).head(20)
        
        html = '<table class="hif-table"><thead><tr><th>#</th><th></th><th>Spiller</th><th>S</th><th>M</th><th>xG</th><th>DZ-Andel</th></tr></thead><tbody>'
        for i, row in df_f.reset_index(drop=True).iterrows():
            wy_id = next((v['team_wyid'] for k, v in TEAMS.items() if v.get('opta_uuid') == row['UUID']), None)
            # Tjekker både tal og streng i logo_map
            l_url = logo_map.get(wy_id) or logo_map.get(str(wy_id), "")
            img = f'<img src="{l_url}" width="25">' if l_url else ""
            
            bar = f'<div class="bar-container"><div class="bar-fill" style="width:{row["DZ_A"]}%;"></div></div>'
            
            html += f"""<tr>
                <td>{i+1}</td><td>{img}</td><td style="text-align:left;"><b>{row['Spiller']}</b></td>
                <td>{row['S']}</td><td style="color:{HIF_RED}; font-weight:bold;">{row['M']}</td>
                <td>{row['xG']:.2f}</td><td>{bar}<span style="font-size:10px;">{int(row['DZ_A'])}%</span></td>
            </tr>"""
        st.markdown(html + "</tbody></table>", unsafe_allow_html=True)

    # --- HJÆLPEFUNKTION: SMART FILTER ---
    def filter_ui(key):
        teams = sorted([uuid_to_name[u.upper()] for u in df_skud[col_team_uuid].unique() if u.upper() in uuid_to_name])
        col1, col2 = st.columns(2)
        with col1:
            t = st.selectbox("Hold", ["ALLE HOLD"] + teams, key=f"t_{key}")
        
        if t == "ALLE HOLD":
            df_t = df_skud
        else:
            u = next(v['opta_uuid'].upper() for k, v in TEAMS.items() if k == t)
            df_t = df_skud[df_skud[col_team_uuid].str.upper() == u]
        
        with col2:
            p_list = sorted(df_t['PLAYER_NAME'].unique())
            p = st.selectbox("Spiller", ["HELE HOLDET"] + p_list, key=f"p_{key}")
        
        return df_t[df_t['PLAYER_NAME'] == p] if p != "HELE HOLDET" else df_t

    # --- TAB 2: DZ ANALYSE (ZOOMET) ---
    with tabs[2]:
        d_v = filter_ui("dz")
        c1, c2 = st.columns([2, 1])
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#ccc')
            fig, ax = pitch.draw()
            ax.set_ylim(75, 105) # BESKÆRING VED CIRKEL
            ax.add_patch(patches.Rectangle((37, 88.5), 26, 11.5, color=DZ_COLOR, alpha=0.15))
            dz_d = d_v[d_v['IS_DZ']]
            pitch.scatter(dz_d['EVENT_X'], dz_d['EVENT_Y'], s=100, c=(dz_d['EVENT_TYPEID']==16).map({True:HIF_RED, False:'white'}), edgecolors=HIF_RED, ax=ax)
            st.pyplot(fig)
        with c2:
            st.metric("DZ Skud", len(dz_d))
            st.metric("DZ Mål", len(dz_d[dz_d['EVENT_TYPEID']==16]))

    # --- TAB 3 & 4: ZONER ---
    def zone_tab(is_m, key):
        d_v = filter_ui(key)
        plot_data = d_v[d_v['EVENT_TYPEID'] == 16] if is_m else d_v
        
        pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='grey')
        fig, ax = pitch.draw(figsize=(8, 10))
        ax.set_ylim(55, 105)
        
        z_counts = plot_data.groupby('Zone').size()
        max_v = z_counts.max() if not z_counts.empty else 1
        cmap = plt.cm.YlOrRd if is_m else plt.cm.Blues

        for name, b in ZONE_BOUNDS.items():
            if b["y_max"] <= 55: continue
            cnt = z_counts.get(name, 0)
            face = cmap(cnt/max_v) if cnt > 0 else '#f9f9f9'
            ax.add_patch(patches.Rectangle((b["x_min"], max(b["y_min"], 55)), b["x_max"]-b["x_min"], b["y_max"]-max(b["y_min"], 55), facecolor=face, alpha=0.6, edgecolor='black', ls='--'))
            if cnt > 0:
                ax.text(b["x_min"]+(b["x_max"]-b["x_min"])/2, max(b["y_min"], 55)+(b["y_max"]-max(b["y_min"], 55))/2, f"{name}\n{cnt}", ha='center', va='center', fontweight='bold')
        st.pyplot(fig)

    with tabs[3]: zone_tab(False, "z_s")
    with tabs[4]: zone_tab(True, "z_m")
