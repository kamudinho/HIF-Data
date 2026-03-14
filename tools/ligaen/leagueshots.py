import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from data.utils.team_mapping import TEAMS

# Farver
HIF_RED = '#d71920'
LIGA_BLUE = '#1f77b4'

def vis_side(dp):
    # --- 1. DATA INDLÆSNING & LOGO SETUP ---
    opta_data = dp.get('opta', {})
    logo_map = dp.get("logo_map", {})
    df_skud = opta_data.get('league_shotevents', pd.DataFrame()).copy()

    if df_skud.empty:
        st.warning("Ingen liga-skuddata fundet.")
        return
    
    df_skud.columns = [c.upper() for c in df_skud.columns]
    col_team = 'EVENT_CONTESTANT_OPTAUUID'

    # Hjælpefunktion: Returnerer kun den RÅ URL (Ingen HTML!)
    def get_logo_url_raw(opta_uuid):
        # 1. Tjek Wyscout ID mapping via logo_map
        wy_id = next((info.get('team_wyid') for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), None)
        if wy_id and wy_id in logo_map:
            return logo_map[wy_id]
        # 2. Backup fra TEAMS dict
        return next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), None)

    # --- 2. ZONE LOGIK & CSS ---
    st.markdown(f"""
        <style>
            .stat-box {{ background-color: #f8f9fa; padding: 10px; border-radius: 8px; border-left: 5px solid {LIGA_BLUE}; margin-bottom: 10px; }}
            .stat-label {{ font-size: 0.8rem; text-transform: uppercase; color: #666; font-weight: bold; }}
            .stat-value {{ font-size: 1.5rem; font-weight: 800; color: #1a1a1a; }}
        </style>
    """, unsafe_allow_html=True)

    df_skud['IS_DZ'] = (df_skud['EVENT_X'] >= 88.5) & (df_skud['EVENT_Y'] >= 37.0) & (df_skud['EVENT_Y'] <= 63.0)

    # --- 3. DATABEREGNING ---
    stats_list = []
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    
    for p in df_skud['PLAYER_NAME'].unique():
        d = df_skud[df_skud['PLAYER_NAME'] == p]
        t_uuid = str(d[col_team].iloc[0]).upper()
        t_name = uuid_to_name.get(t_uuid, "Modstander")
        
        s = len(d)
        m = len(d[d['EVENT_TYPEID'] == 16])
        dz_d = d[d['IS_DZ'] == True]
        dz_s = len(dz_d)
        dz_m = len(dz_d[dz_d['EVENT_TYPEID'] == 16])
        
        if s > 0:
            stats_list.append({
                "Logo": get_logo_url_raw(t_uuid), # Sender rå URL string
                "Spiller": p, 
                "Klub": t_name, 
                "Skud": int(s),
                "Mål": int(m),
                "K%": float(round((m/s*100), 1)),
                "DZ-S": int(dz_s),
                "DZ-M": int(dz_m),
                "DZ-K%": float(round((dz_m/dz_s*100), 1)) if dz_s > 0 else 0.0,
                "DZ-Andel": float(round((dz_s/s*100), 1))
            })
    
    df_final = pd.DataFrame(stats_list).sort_values("Skud", ascending=False)

    # --- 4. TABS ---
    tabs = st.tabs(["LIGAPROFILER", "AFSLUTNINGER", "DZ-ANALYSE", "SKUDZONER", "MÅLZONER"])

    with tabs[0]:
        st.dataframe(
            df_final, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Logo": st.column_config.ImageColumn("", width="small"),
                "Spiller": st.column_config.TextColumn("Spiller", width="medium"),
                "Klub": st.column_config.TextColumn("Klub", width="small"),
                "Skud": st.column_config.NumberColumn("S", format="%d"),
                "Mål": st.column_config.NumberColumn("M", format="%d"),
                "K%": st.column_config.NumberColumn("K%", format="%.1f%%"),
                "DZ-S": st.column_config.NumberColumn("DZ-S", format="%d"),
                "DZ-M": st.column_config.NumberColumn("DZ-M", format="%d"),
                "DZ-K%": st.column_config.NumberColumn("DZ-K%", format="%.1f%%"),
                "DZ-Andel": st.column_config.ProgressColumn(
                    "DZ-Andel", 
                    format="%.0f%%", 
                    min_value=0, 
                    max_value=100,
                    color=HIF_RED
                )
            }
        )

    with tabs[1]:
        c1, c2 = st.columns([2, 1])
        with c2:
            sel_p = st.selectbox("Vælg Spiller", ["HELE LIGAEN"] + sorted(df_skud['PLAYER_NAME'].unique()))
            d_v = df_skud if sel_p == "HELE LIGAEN" else df_skud[df_skud['PLAYER_NAME'] == sel_p]
            st.markdown(f'<div class="stat-box"><div class="stat-label">Skud</div><div class="stat-value">{len(d_v)}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Mål</div><div class="stat-value">{len(d_v[d_v["EVENT_TYPEID"]==16])}</div></div>', unsafe_allow_html=True)
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            colors = (d_v['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
            pitch.scatter(d_v['EVENT_X'], d_v['EVENT_Y'], s=80, c=colors, edgecolors=HIF_RED, ax=ax, alpha=0.7)
            st.pyplot(fig)

    # Zone definitioner til heatmap
    P_L, P_W = 105.0, 68.0
    X_MID_L, X_MID_R = (P_W - 18.32) / 2, (P_W + 18.32) / 2
    X_INN_L, X_INN_R = (P_W - 40.2) / 2, (P_W + 40.2) / 2
    Y_GOAL, Y_6YD, Y_PK, Y_18YD, Y_MID = 105.0, 99.5, 94.0, 88.5, 75.0

    ZONE_BOUNDS = {
        "Zone 1": {"y_min": Y_6YD, "y_max": Y_GOAL, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 2": {"y_min": Y_PK, "y_max": Y_6YD, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 3": {"y_min": Y_18YD, "y_max": Y_PK, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 8": {"y_min": 0, "y_max": Y_MID, "x_min": 0, "x_max": P_W}
    }

    def zone_viz(data, is_m):
        viz, ctrl = st.columns([1.8, 1])
        with ctrl:
            z_counts = data.groupby('ZONE').size().reset_index(name='Antal')
            st.table(z_counts[z_counts['ZONE'] != 'Zone 8'].sort_values('Antal', ascending=False))
        with viz:
            pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='grey')
            fig, ax = pitch.draw(figsize=(8, 10))
            ax.set_ylim(55, 105)
            for name, b in ZONE_BOUNDS.items():
                if b["y_max"] <= 55: continue
                cnt = len(data[data['ZONE'] == name])
                rect = patches.Rectangle((b["x_min"], max(b["y_min"], 55)), 
                                         b["x_max"]-b["x_min"], b["y_max"]-max(b["y_min"], 55),
                                         facecolor=LIGA_BLUE, alpha=min(cnt/15, 0.8) if cnt > 0 else 0.05, 
                                         edgecolor='black', linestyle='--')
                ax.add_patch(rect)
            st.pyplot(fig)

    if 'ZONE' not in df_skud.columns:
        def map_z(r):
            mx, my = r['EVENT_X'] * (105/100), r['EVENT_Y'] * (68/100)
            for z, b in ZONE_BOUNDS.items():
                if b["y_min"] <= mx <= b["y_max"] and b["x_min"] <= my <= b["x_max"]: return z
            return "Zone 8"
        df_skud['ZONE'] = df_skud.apply(map_z, axis=1)

    with tabs[3]: zone_viz(df_skud, False)
    with tabs[4]: zone_viz(df_skud[df_skud['EVENT_TYPEID'] == 16], True)
