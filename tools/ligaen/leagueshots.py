import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from data.utils.team_mapping import TEAMS

# Liga/Benchmark Identitet
LIGA_BLUE = '#1f77b4'
DZ_COLOR = '#ff7f0e' 

def vis_side(dp):
    # --- 1. DATA & FILTRERING (OPTA UUID) ---
    df_raw = dp.get('playerstats', pd.DataFrame()).copy()
    if df_raw.empty:
        st.info("Ingen OPTA skuddata fundet.")
        return

    # Hvidovre UUID fra din konfiguration
    HIF_UUID = "8638J8V8SHSNK67VTH1066V9D" 
    
    # Sørg for at kolonner er uppercase og UUIDs er renset
    df_raw.columns = [c.upper() for c in df_raw.columns]
    if 'CONTESTANT_OPTAUUID' in df_raw.columns:
        df_raw['CONTESTANT_OPTAUUID'] = df_raw['CONTESTANT_OPTAUUID'].astype(str).str.upper().str.strip()
    
    # FILTER: Ekskluder Hvidovre, så vi kun har resten af ligaen
    df_skud = df_raw[df_raw['CONTESTANT_OPTAUUID'] != HIF_UUID].copy()

    # --- 2. CSS STYLING ---
    st.markdown(f"""
        <style>
            .stat-box {{ background-color: #f8f9fa; padding: 10px; border-radius: 8px; border-left: 5px solid {LIGA_BLUE}; margin-bottom: 10px; }}
            .stat-label {{ font-size: 0.8rem; text-transform: uppercase; color: #666; font-weight: bold; }}
            .stat-value {{ font-size: 1.5rem; font-weight: 800; color: #1a1a1a; }}
            .legend-dot {{ height: 12px; width: 12px; border-radius: 50%; display: inline-block; vertical-align: middle; }}
        </style>
    """, unsafe_allow_html=True)

    # --- 3. ZONE LOGIK (OPTA Pitch 100x100 -> Meter) ---
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

    # --- 4. TABS ---
    tabs = st.tabs(["LIGAPROFILER", "AFSLUTNINGER", "DZ-ANALYSE", "SKUDZONER", "MÅLZONER"])

    with tabs[0]:
        stats = []
        for p in df_skud['PLAYER_NAME'].unique():
            d = df_skud[df_skud['PLAYER_NAME'] == p]
            t_name = d['CONTESTANT_NAME'].iloc[0] if 'CONTESTANT_NAME' in d.columns else "Modstander"
            s, m = len(d), len(d[d['EVENT_TYPEID'] == 16])
            if s > 1:
                stats.append({
                    "Spiller": p, "Hold": t_name, "Skud": s, "Mål": m, 
                    "Konv.%": (m/s*100), "xG": d['XG'].sum() if 'XG' in d.columns else 0
                })
        st.dataframe(pd.DataFrame(stats).sort_values("Skud", ascending=False), 
                     use_container_width=True, hide_index=True)

    with tabs[1]:
        c1, c2 = st.columns([2, 1])
        with c2:
            sel_p = st.selectbox("Vælg Modstander", ["HELE LIGAEN"] + sorted(df_skud['PLAYER_NAME'].unique()))
            d_v = df_skud if sel_p == "HELE LIGAEN" else df_skud[df_skud['PLAYER_NAME'] == sel_p]
            
            st.markdown(f'<div class="stat-box"><div class="stat-label">Skud (Liga)</div><div class="stat-value">{len(d_v)}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Mål (Liga)</div><div class="stat-value">{len(d_v[d_v["EVENT_TYPEID"]==16])}</div></div>', unsafe_allow_html=True)
        
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            colors = (d_v['EVENT_TYPEID'] == 16).map({True: LIGA_BLUE, False: 'white'})
            pitch.scatter(d_v['EVENT_X'], d_v['EVENT_Y'], s=70, c=colors, edgecolors=LIGA_BLUE, ax=ax, alpha=0.5)
            st.pyplot(fig)

    # --- 5. ZONE PLOTS (Ekskl. Zone 8 i tabel) ---
    def zone_viz(data, is_m):
        viz, ctrl = st.columns([1.8, 1])
        with ctrl:
            z_counts = data.groupby('ZONE').size().reset_index(name='Antal')
            z_counts = z_counts[z_counts['ZONE'] != 'Zone 8'].sort_values('Antal', ascending=False)
            st.write(f"**Top Zoner ({'Mål' if is_m else 'Skud'})**")
            st.table(z_counts)
        
        with viz:
            pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='grey')
            fig, ax = pitch.draw(figsize=(8, 10))
            ax.set_ylim(55, 105)
            
            for name, b in ZONE_BOUNDARIES.items():
                if b["y_max"] <= 55: continue
                cnt = len(data[data['ZONE'] == name])
                rect = patches.Rectangle((b["x_min"], max(b["y_min"], 55)), 
                                         b["x_max"]-b["x_min"], b["y_max"]-max(b["y_min"], 55),
                                         facecolor=LIGA_BLUE if cnt > 0 else '#f9f9f9',
                                         alpha=min(cnt/10, 0.8) if cnt > 0 else 0.1, 
                                         edgecolor='black', linestyle='--')
                ax.add_patch(rect)
            st.pyplot(fig)

    with tabs[3]: zone_viz(df_skud, False)
    with tabs[4]: zone_viz(df_skud[df_skud['EVENT_TYPEID'] == 16], True)
