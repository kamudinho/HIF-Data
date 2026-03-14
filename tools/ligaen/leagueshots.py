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
    # --- 1. DATA INDLÆSNING ---
    opta_data = dp.get('opta', {})
    logo_map = dp.get("logo_map", {}) # Henter logo_map fra data_provider
    df_skud = opta_data.get('league_shotevents', pd.DataFrame()).copy()

    if df_skud.empty:
        st.info("Ingen liga-skuddata fundet.")
        return
    
    df_skud.columns = [c.upper() for c in df_skud.columns]
    col_team_uuid = 'EVENT_CONTESTANT_OPTAUUID'
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}

    # --- 2. CSS STYLING ---
    st.markdown(f"""
        <style>
            .stat-box {{ background-color: #f8f9fa; padding: 10px; border-radius: 8px; border-left: 5px solid {HIF_RED}; margin-bottom: 10px; }}
            .stat-label {{ font-size: 0.8rem; text-transform: uppercase; color: #666; font-weight: bold; }}
            .stat-value {{ font-size: 1.5rem; font-weight: 800; color: #1a1a1a; margin-top: 2px; }}
            .liga-table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
            .liga-table th {{ background-color: #f2f2f2; padding: 10px; text-align: center; border-bottom: 2px solid #ddd; }}
            .liga-table td {{ padding: 10px; border-bottom: 1px solid #eee; text-align: center; vertical-align: middle; }}
            .liga-table td.left {{ text-align: left; }}
        </style>
    """, unsafe_allow_html=True)

    # --- 3. ZONE LOGIK & DZ ---
    P_L, P_W = 105.0, 68.0
    X_MID_L, X_MID_R = (P_W - 18.32) / 2, (P_W + 18.32) / 2
    Y_GOAL, Y_6YD, Y_PK, Y_18YD, Y_MID = 105.0, 99.5, 94.0, 88.5, 75.0

    ZONE_BOUNDARIES = {
        "Zone 1": {"y_min": Y_6YD, "y_max": Y_GOAL, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 2": {"y_min": Y_PK, "y_max": Y_6YD, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 3": {"y_min": Y_18YD, "y_max": Y_PK, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 8":  {"y_min": 0, "y_max": Y_MID, "x_min": 0, "x_max": P_W}
    }
    # (Øvrige zoner 4-7 kan tilføjes her hvis de skal plottes specifikt)

    def map_to_zone(r):
        mx, my = r['EVENT_X'] * (P_L / 100), r['EVENT_Y'] * (P_W / 100)
        for z, b in ZONE_BOUNDARIES.items():
            if b["y_min"] <= mx <= b["y_max"] and b["x_min"] <= my <= b["x_max"]:
                return z
        return "Udenfor"

    df_skud['Zone'] = df_skud.apply(map_to_zone, axis=1)
    df_skud['IS_DZ_GEO'] = (df_skud['EVENT_X'] >= 88.5) & (df_skud['EVENT_Y'] >= 37.0) & (df_skud['EVENT_Y'] <= 63.0)

    tabs = st.tabs(["SPILLEROVERSIGT", "AFSLUTNINGER", "DZ-AFSLUTNINGER", "AFSLUTNINGSZONER", "MÅLZONER"])

    # --- TAB 0: SPILLEROVERSIGT ---
    with tabs[0]:
        stats = []
        for p in df_skud['PLAYER_NAME'].unique():
            d = df_skud[df_skud['PLAYER_NAME'] == p]
            t_uuid = str(d[col_team_uuid].iloc[0]).upper()
            dz = d[d['IS_DZ_GEO']]
            s, m = len(d), len(d[d['EVENT_TYPEID'] == 16])
            stats.append({
                "UUID": t_uuid, "Spiller": p, "Klub": uuid_to_name.get(t_uuid, "Ukendt"),
                "Skud": s, "Mål": m, "Konv%": (m/s*100) if s > 0 else 0,
                "DZ-S": len(dz), "DZ-Andel": (len(dz)/s*100) if s > 0 else 0
            })
        
        df_f = pd.DataFrame(stats).sort_values("Mål", ascending=False).head(20).reset_index(drop=True)
        
        html = '<table class="liga-table"><thead><tr><th>#</th><th></th><th class="left">Spiller</th><th class="left">Klub</th><th>S</th><th>M</th><th>K%</th><th>DZ-S</th><th>DZ-Andel</th></tr></thead><tbody>'
        for i, row in df_f.iterrows():
            wy_id = next((v['team_wyid'] for k, v in TEAMS.items() if v.get('opta_uuid') == row['UUID']), None)
            # Vi tjekker både logo_map og TEAMS ordbogen
            l_url = logo_map.get(wy_id) or next((v['logo'] for k, v in TEAMS.items() if v.get('team_wyid') == wy_id), "")
            img = f'<img src="{l_url}" style="height:22px; width:22px; object-fit:contain;">' if l_url else ""
            
            html += f"""<tr><td>{i+1}</td><td>{img}</td><td class="left"><b>{row['Spiller']}</b></td><td class="left">{row['Klub']}</td><td>{row['Skud']}</td><td style="color:{HIF_RED}; font-weight:800;">{row['Mål']}</td><td>{row['Konv%']:.1f}%</td><td>{row['DZ-S']}</td><td><div style="background:#eee; width:40px; height:8px; display:inline-block;"><div style="background:{HIF_RED}; width:{row['DZ-Andel']}%; height:100%;"></div></div></td></tr>"""
        st.markdown(html + "</tbody></table>", unsafe_allow_html=True)

    # --- HJÆLPEFUNKTION TIL FILTRERING ---
    def sidebar_filters(key):
        uuids = df_skud[col_team_uuid].unique()
        teams = sorted([uuid_to_name[u.upper()] for u in uuids if u.upper() in uuid_to_name])
        sel_t = st.selectbox("Vælg Hold", ["ALLE HOLD"] + teams, key=f"t_{key}")
        
        if sel_t == "ALLE HOLD":
            p_list = sorted(df_skud['PLAYER_NAME'].unique())
            d_f = df_skud
        else:
            u = next(v['opta_uuid'].upper() for k, v in TEAMS.items() if k == sel_t)
            d_f = df_skud[df_skud[col_team_uuid].str.upper() == u]
            p_list = sorted(d_f['PLAYER_NAME'].unique())
            
        sel_p = st.selectbox("Vælg Spiller", ["HELE HOLDET"] + p_list, key=f"p_{key}")
        return d_f[d_f['PLAYER_NAME'] == sel_p] if sel_p != "HELE HOLDET" else d_f

    # --- TAB 1: AFSLUTNINGER ---
    with tabs[1]:
        c1, c2 = st.columns([2, 1])
        with c2:
            d_v = sidebar_filters("afsl")
            s, m = len(d_v), len(d_v[d_v["EVENT_TYPEID"]==16])
            st.markdown(f'<div class="stat-box"><div class="stat-label">Skud</div><div class="stat-value">{s}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Mål</div><div class="stat-value">{m}</div></div>', unsafe_allow_html=True)
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            pitch.scatter(d_v['EVENT_X'], d_v['EVENT_Y'], s=80, c=(d_v['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'}), edgecolors=HIF_RED, ax=ax)
            st.pyplot(fig)

    # --- TAB 2: DZ-AFSLUTNINGER (MED ZOOM) ---
    with tabs[2]:
        c1, c2 = st.columns([2, 1])
        with c2:
            d_v = sidebar_filters("dz")
            dz_d = d_v[d_v['IS_DZ_GEO']]
            st.markdown(f'<div class="stat-box"><div class="stat-label">DZ Skud</div><div class="stat-value">{len(dz_d)}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">DZ Mål</div><div class="stat-value">{len(dz_d[dz_d["EVENT_TYPEID"]==16])}</div></div>', unsafe_allow_html=True)
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            # Beskæring/Zoom for at gøre DZ tydeligere
            ax.set_ylim(70, 105) 
            ax.set_xlim(15, 85)
            ax.add_patch(patches.Rectangle((37, 88.5), 26, 11.5, color=DZ_COLOR, alpha=0.15))
            pitch.scatter(dz_d['EVENT_X'], dz_d['EVENT_Y'], s=100, c=(dz_d['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'}), edgecolors=HIF_RED, ax=ax)
            st.pyplot(fig)

    # --- TAB 3 & 4: ZONER ---
    def zone_tab(is_m, key):
        c1, c2 = st.columns([2, 1])
        with c2:
            d_v = sidebar_filters(key)
            data = d_v[d_v['EVENT_TYPEID'] == 16] if is_m else d_v
            # Simpel zone-tabel
            z_counts = data.groupby('Zone').size().reset_index(name='Antal').sort_values('Antal', ascending=False)
            st.dataframe(z_counts[z_counts['Zone'] != 'Udenfor'], hide_index=True)
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='grey')
            fig, ax = pitch.draw(figsize=(5, 7))
            pitch.scatter(data['EVENT_X'], data['EVENT_Y'], s=60, alpha=0.6, ax=ax)
            st.pyplot(fig)

    with tabs[3]: zone_tab(False, "z_s")
    with tabs[4]: zone_tab(True, "z_m")
