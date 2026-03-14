import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from data.utils.team_mapping import TEAMS

# --- DESIGN ---
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'
DZ_COLOR = '#1f77b4'

def vis_side(dp):
    opta_data = dp.get('opta', {})
    logo_map = dp.get("logo_map", {})
    df_skud = opta_data.get('league_shotevents', pd.DataFrame()).copy()

    if df_skud.empty:
        st.info("Ingen data fundet.")
        return
    
    df_skud.columns = [c.upper() for c in df_skud.columns]
    col_team_uuid = 'EVENT_CONTESTANT_OPTAUUID'
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}

    # --- ZONE DEFINITIONER (Præcis som din kilde) ---
    P_L, P_W = 105.0, 68.0
    X_MID_L, X_MID_R = (P_W - 18.32) / 2, (P_W + 18.32) / 2
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

    # --- CSS ---
    st.markdown(f"<style>.stat-box {{ background: #f8f9fa; padding: 10px; border-radius: 8px; border-left: 5px solid {HIF_RED}; margin-bottom: 10px; }} .hif-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }} .hif-table th {{ background: #eee; padding: 8px; border-bottom: 2px solid #ccc; }} .hif-table td {{ padding: 8px; border-bottom: 1px solid #eee; text-align: center; }}</style>", unsafe_allow_html=True)

    tabs = st.tabs(["SPILLEROVERSIGT", "AFSLUTNINGER", "DZ-ANALYSE", "AFSLUTNINGSZONER", "MÅLZONER"])

    # --- FILTRERING ---
    def get_smart_filter(key):
        teams = sorted([uuid_to_name[u.upper()] for u in df_skud[col_team_uuid].unique() if u.upper() in uuid_to_name])
        t = st.selectbox("Vælg Hold", ["HELE LIGAEN"] + teams, key=f"t_{key}")
        if t == "HELE LIGAEN":
            df_t = df_skud
            p_list = sorted(df_skud['PLAYER_NAME'].unique())
        else:
            u = next(v['opta_uuid'].upper() for k, v in TEAMS.items() if k == t)
            df_t = df_skud[df_skud[col_team_uuid].str.upper() == u]
            p_list = sorted(df_t['PLAYER_NAME'].unique())
        p = st.selectbox("Vælg Spiller", ["HELE HOLDET"] + p_list, key=f"p_{key}")
        return df_t[df_t['PLAYER_NAME'] == p] if p != "HELE HOLDET" else df_t

    # --- TAB 0: OVERSIGT ---
    with tabs[0]:
        stats = []
        for player in df_skud['PLAYER_NAME'].unique():
            d = df_skud[df_skud['PLAYER_NAME'] == player]
            t_uuid = str(d[col_team_uuid].iloc[0]).upper()
            s, m = len(d), len(d[d['EVENT_TYPEID'] == 16])
            stats.append({"UUID": t_uuid, "Spiller": player, "S": s, "M": m, "xG": round(d['EXPECTED_GOALS_VALUE'].sum(), 2) if 'EXPECTED_GOALS_VALUE' in d.columns else 0})
        df_top = pd.DataFrame(stats).sort_values("M", ascending=False).head(20)
        html = '<table class="hif-table"><thead><tr><th>#</th><th></th><th style="text-align:left;">Spiller</th><th>S</th><th>M</th><th>xG</th></tr></thead><tbody>'
        for i, r in df_top.reset_index(drop=True).iterrows():
            wy_id = next((v['team_wyid'] for k, v in TEAMS.items() if v.get('opta_uuid') == r['UUID']), None)
            img = f'<img src="{logo_map.get(wy_id, "")}" width="25">'
            html += f"<tr><td>{i+1}</td><td>{img}</td><td style='text-align:left;'><b>{r['Spiller']}</b></td><td>{r['S']}</td><td style='color:{HIF_RED}; font-weight:bold;'>{r['M']}</td><td>{r['xG']}</td></tr>"
        st.markdown(html + "</tbody></table>", unsafe_allow_html=True)

    # --- ZONE PLOT FUNKTION ---
    def zone_viz(is_m, key):
        c1, c2 = st.columns([2, 1])
        with c2:
            data = get_smart_filter(key)
            plot_data = data[data['EVENT_TYPEID'] == 16] if is_m else data
            z_stats = plot_data.groupby('Zone').size().reset_index(name='Antal')
            st.dataframe(z_stats, hide_index=True)
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='grey')
            fig, ax = pitch.draw(figsize=(8, 10))
            ax.set_ylim(55, 105) # Fokus på top
            cmap = plt.cm.YlOrRd if is_m else plt.cm.Blues
            max_v = z_stats['Antal'].max() if not z_stats.empty else 1
            
            for name, b in ZONE_BOUNDS.items():
                if b["y_max"] <= 55: continue
                cnt = z_stats[z_stats['Zone'] == name]['Antal'].iloc[0] if name in z_stats['Zone'].values else 0
                y_min_draw = max(b["y_min"], 55)
                face = cmap(cnt/max_v) if cnt > 0 else '#f9f9f9'
                ax.add_patch(patches.Rectangle((b["x_min"], y_min_draw), b["x_max"]-b["x_min"], b["y_max"]-y_min_draw, facecolor=face, alpha=0.6, edgecolor='black', ls='--'))
                if cnt > 0:
                    ax.text(b["x_min"]+(b["x_max"]-b["x_min"])/2, y_min_draw+(b["y_max"]-y_min_draw)/2, f"{name}\n{cnt}", ha='center', va='center', fontsize=8, fontweight='bold')
            st.pyplot(fig)

    with tabs[1]:
        c1, c2 = st.columns([2, 1])
        with c2: d_v = get_smart_filter("afsl")
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#ccc')
            fig, ax = pitch.draw()
            pitch.scatter(d_v['EVENT_X'], d_v['EVENT_Y'], s=80, c=(d_v['EVENT_TYPEID']==16).map({True:HIF_RED, False:'white'}), edgecolors=HIF_RED, ax=ax)
            st.pyplot(fig)

    with tabs[2]:
        c1, c2 = st.columns([2, 1])
        with c2: d_v = get_smart_filter("dz")
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#ccc')
            fig, ax = pitch.draw()
            ax.set_ylim(75, 105) # Beskåret ved cirklen
            ax.add_patch(patches.Rectangle((37, 88.5), 26, 11.5, color=DZ_COLOR, alpha=0.15))
            dz_d = d_v[(d_v['EVENT_X'] >= 88.5) & (d_v['EVENT_Y'] >= 37.0) & (d_v['EVENT_Y'] <= 63.0)]
            pitch.scatter(dz_d['EVENT_X'], dz_d['EVENT_Y'], s=100, c=(dz_d['EVENT_TYPEID']==16).map({True:HIF_RED, False:'white'}), edgecolors=HIF_RED, ax=ax)
            st.pyplot(fig)

    with tabs[3]: zone_viz(False, "z_s")
    with tabs[4]: zone_viz(True, "z_m")
