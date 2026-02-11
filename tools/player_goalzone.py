import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from mplsoccer import VerticalPitch
from matplotlib.patches import Rectangle
import matplotlib.colors as mcolors

# --- ZONE DEFINITIONER (Skal ligge uden for funktionen) ---
ZONE_BOUNDARIES = {
    "Zone 1": {"y_min": 94.2, "y_max": 100.0, "x_min": 36.8, "x_max": 63.2},
    "Zone 4A": {"y_min": 94.2, "y_max": 100.0, "x_min": 63.2, "x_max": 81.0},
    "Zone 4B": {"y_min": 94.2, "y_max": 100.0, "x_min": 19.0, "x_max": 36.8},
    "Zone 2": {"y_min": 90.0, "y_max": 94.2, "x_min": 36.8, "x_max": 63.2},
    "Zone 3": {"y_min": 80.0, "y_max": 85.5, "x_min": 36.8, "x_max": 63.2},
    "Zone 5A": {"y_min": 84.0, "y_max": 94.2, "x_min": 63.2, "x_max": 81.0},
    "Zone 5B": {"y_min": 84.0, "y_max": 94.2, "x_min": 19.0, "x_max": 36.8},
    "Zone 6A": {"y_min": 84.0, "y_max": 100.0, "x_min": 81.0, "x_max": 100.0},
    "Zone 6B": {"y_min": 84.0, "y_max": 100.0, "x_min": 0.0, "x_max": 19.0},
    "Zone 7": {"y_min": 70.0, "y_max": 84.0, "x_min": 30.0, "x_max": 70.0},
    "Zone 7B": {"y_min": 70.0, "y_max": 84.0, "x_min": 0.0, "x_max": 30.0},
    "Zone 7A": {"y_min": 70.0, "y_max": 84.0, "x_min": 70.0, "x_max": 100.0},
    "Zone 8": {"y_min": 0.0, "y_max": 70.0, "x_min": 0.0, "x_max": 100.0}
}

def find_zone(x, y):
    for zone, b in ZONE_BOUNDARIES.items():
        if b["x_min"] <= x <= b["x_max"] and b["y_min"] <= y <= b["y_max"]:
            return zone
    return "Udenfor"

def vis_side(df_events, df_spillere, hold_map):
    HIF_ID = 38331
    HIF_RED = '#d31313'

    # --- 1. DATA-PROCESSERING ---
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    SHOT_CSV_PATH = os.path.join(BASE_DIR, 'shotevents.csv')
    if not os.path.exists(SHOT_CSV_PATH):
        st.error("Kunne ikke finde shotevents.csv")
        return

    df_s = pd.read_csv(SHOT_CSV_PATH)
    df_s.columns = [str(c).strip().upper() for c in df_s.columns]
    df_s = df_s[pd.to_numeric(df_s['TEAM_WYID'], errors='coerce') == HIF_ID].copy()
    for col in ['LOCATIONX', 'LOCATIONY', 'SHOTXG']:
        df_s[col] = pd.to_numeric(df_s[col], errors='coerce')
    df_s = df_s.dropna(subset=['LOCATIONX', 'LOCATIONY'])

    s_df = df_spillere.copy()
    s_df.columns = [str(c).strip().upper() for c in s_df.columns]
    navne_dict = dict(zip(s_df['PLAYER_WYID'].astype(str).str.split('.').str[0], s_df['NAVN']))
    df_s['SPILLER_NAVN'] = df_s['PLAYER_WYID'].astype(str).str.split('.').str[0].map(navne_dict).fillna("Ukendt")
    
    # Zone beregning - bruger find_zone direkte uden import-fejl
    df_s['ZONE_ID'] = df_s.apply(lambda row: find_zone(row['LOCATIONY'], row['LOCATIONX']), axis=1)

    # --- 2. LAYOUT ---
    layout_venstre, layout_hoejre = st.columns([2, 1])

    with layout_hoejre:
        mode = st.radio(
            "Visning:", ["Hold", "Individuel"], 
            horizontal=True, 
            label_visibility="collapsed"
        )
        
        if mode == "Individuel":
            spiller_liste = sorted(df_s['SPILLER_NAVN'].unique().tolist())
            valgt_target = st.selectbox("Vælg spiller", options=spiller_liste, label_visibility="collapsed")
            df_plot = df_s[df_s['SPILLER_NAVN'] == valgt_target].copy()
        else:
            df_plot = df_s.copy()
            st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

        # Metrics sektion
        total_shots = len(df_plot)
        goals = int(df_plot['SHOTISGOAL'].apply(lambda x: str(x).lower() in ['true', '1', '1.0', 't']).sum())
        xg_sum = df_plot['SHOTXG'].sum()
        
        def custom_metric(label, value):
            st.markdown(f"""
                <div style="margin-bottom: 8px; border-left: 3px solid {HIF_RED}; padding-left: 12px; line-height: 1.2;">
                    <p style="margin:0; font-size: 12px; color: #777; text-transform: uppercase; letter-spacing: 0.5px;">{label}</p>
                    <p style="margin:0; font-size: 22px; font-weight: 700; color: #222;">{value}</p>
                </div>
            """, unsafe_allow_html=True)

        custom_metric("Afslutninger", total_shots)
        custom_metric("Mål", goals)
        custom_metric("Total xG", f"{xg_sum:.2f}")
        custom_metric("xG pr. skud", f"{(xg_sum/total_shots) if total_shots > 0 else 0:.2f}")

    with layout_venstre:
        pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#000000', line_alpha=0.7, line_zorder=2, pad_top=0)
        fig, ax = pitch.draw(figsize=(6, 7))
        ax.set_ylim(48, 102)

        # Zone beregninger til heatmap
        zone_counts = df_plot['ZONE_ID'].value_counts()
        max_val = zone_counts.max() if not zone_counts.empty else 1
        cmap = mcolors.LinearSegmentedColormap.from_list('HIF_MAP', ['#ffffff', HIF_RED])

        # Find topscorer pr. zone hvis Hold-visning
        top_scorers = {}
        if mode == "Hold":
            for z in df_plot['ZONE_ID'].unique():
                z_data = df_plot[df_plot['ZONE_ID'] == z]
                if not z_data.empty:
                    top_name = z_data['SPILLER_NAVN'].value_counts().idxmax()
                    top_scorers[z] = top_name.split()[-1].upper() # Kun efternavn

        # TEGN ZONER
        for name, b in ZONE_BOUNDARIES.items():
            if b["y_min"] < 55 and name == "Zone 8": continue
            
            count = zone_counts.get(name, 0)
            color_val = count / max_val if max_val > 0 else 0
            
            # Farve-patch
            rect = Rectangle((b["x_min"], b["y_min"]), b["x_max"] - b["x_min"], b["y_max"] - b["y_min"], 
                             edgecolor='none', facecolor=cmap(color_val), alpha=0.4, zorder=0)
            ax.add_patch(rect)
            
            if count > 0:
                x_t = b["x_min"] + (b["x_max"]-b["x_min"])/2
                y_t = b["y_min"] + (b["y_max"]-b["y_min"])/2
                
                # Tal i zone
                ax.text(x_t, y_t + 0.8, str(int(count)), ha='center', va='center', 
                        fontsize=11, fontweight='bold', color="#333333", zorder=3)
                
                # Navn i zone (ved hold-visning)
                if mode == "Hold" and name in top_scorers:
                    ax.text(x_t, y_t - 1.5, top_scorers[name], ha='center', va='center', 
                            fontsize=6, fontweight='black', color=HIF_RED, alpha=0.8, zorder=3)

        st.pyplot(fig, bbox_inches='tight', pad_inches=0)
