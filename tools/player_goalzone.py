import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from mplsoccer import VerticalPitch
from matplotlib.patches import Rectangle
import matplotlib.colors as mcolors

# --- ZONE DEFINITIONER ---
ZONE_BOUNDARIES = {
    "Zone 1": {"y_min": 94.2, "y_max": 100.0, "x_min": 36.8, "x_max": 63.2},
    "Zone 4A": {"y_min": 94.2, "y_max": 100.0, "x_min": 63.2, "x_max": 81.0},
    "Zone 4B": {"y_min": 94.2, "y_max": 100.0, "x_min": 19.0, "x_max": 36.8},
    "Zone 2": {"y_min": 89.8, "y_max": 94.2, "x_min": 36.8, "x_max": 63.2},
    "Zone 3": {"y_min": 84.0, "y_max": 89.8, "x_min": 36.8, "x_max": 63.2},
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
    
def vis_side(df_input, df_spillere, hold_map=None):
    HIF_ID = 38331 
    HIF_RED = '#d31313'
    
    if df_input is None or df_input.empty:
        st.warning("Ingen hændelsesdata fundet (df_input er tom).")
        return

    df_s = df_input.copy()
    df_s.columns = [str(c).upper().strip() for c in df_s.columns]
    
    # MEGET ROBUST FILTRERING
    if 'TEAM_WYID' in df_s.columns:
        # Konverterer alt til tal, fjerner NaN, og tjekker mod HIF_ID
        df_s['TEAM_WYID_NUM'] = pd.to_numeric(df_s['TEAM_WYID'], errors='coerce')
        df_s = df_s[df_s['TEAM_WYID_NUM'] == HIF_ID].copy()

    if df_s.empty:
        st.warning(f"Data findes, men ingen rækker matcher TEAM_WYID {HIF_ID}")
        # st.write("Eksisterende Team IDs i filen:", df_input.iloc[:, -1].unique()) # Debug linje
        return

    # --- 1. DATA-PROCESSERING ---
    df_s = df_input.copy()
    df_s.columns = [str(c).strip().upper() for c in df_s.columns]
    
    # Filtrér på hold
    df_s = df_s[pd.to_numeric(df_s['TEAM_WYID'], errors='coerce') == HIF_ID].copy()
    
    # Rens spillere fra players.csv
    s_df = df_spillere.copy()
    s_df.columns = [str(c).strip().upper() for c in s_df.columns]
    s_df['PLAYER_WYID'] = s_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    
    # Rens skud-data og filtrér til trup
    df_s['PLAYER_WYID'] = df_s['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    aktive_ids = set(s_df['PLAYER_WYID'].unique())
    df_s = df_s[df_s['PLAYER_WYID'].isin(aktive_ids)].copy()

    for col in ['LOCATIONX', 'LOCATIONY', 'SHOTXG']:
        if col in df_s.columns:
            df_s[col] = pd.to_numeric(df_s[col], errors='coerce')
    
    df_s = df_s.dropna(subset=['LOCATIONX', 'LOCATIONY'])
    navne_dict = dict(zip(s_df['PLAYER_WYID'], s_df['NAVN']))
    df_s['SPILLER_NAVN'] = df_s['PLAYER_WYID'].map(navne_dict)
    df_s['ZONE_ID'] = df_s.apply(lambda row: find_zone(row['LOCATIONY'], row['LOCATIONX']), axis=1)

    # --- 2. LAYOUT ---
    l_ven, l_hoe = st.columns([2, 1])

    with l_hoe:
        mode = st.radio("Visning:", ["Hold", "Individuel"], horizontal=True)
        if mode == "Individuel":
            sp_liste = sorted(df_s['SPILLER_NAVN'].dropna().unique().tolist())
            valgt = st.selectbox("Vælg spiller", options=sp_liste)
            df_plot = df_s[df_s['SPILLER_NAVN'] == valgt].copy()
        else:
            df_plot = df_s.copy()

        # Metrics
        total = len(df_plot)
        goals = int(df_plot['SHOTISGOAL'].astype(str).str.lower().isin(['true', '1', 't', '1.0']).sum())
        xg = df_plot['SHOTXG'].sum() if 'SHOTXG' in df_plot.columns else 0
        
        st.metric("Afslutninger", total)
        st.metric("Mål", goals)
        st.metric("Total xG", f"{xg:.2f}")

    with l_ven:
        pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#000000', line_alpha=0.5)
        fig, ax = pitch.draw(figsize=(6, 8))
        ax.set_ylim(40, 102)

        zone_counts = df_plot['ZONE_ID'].value_counts()
        max_v = zone_counts.max() if not zone_counts.empty else 1
        cmap = mcolors.LinearSegmentedColormap.from_list('HIF', ['#ffffff', HIF_RED])

        for name, b in ZONE_BOUNDARIES.items():
            if b["y_min"] < 40 and name == "Zone 8": continue
            count = zone_counts.get(name, 0)
            rect = Rectangle((b["x_min"], b["y_min"]), b["x_max"]-b["x_min"], b["y_max"]-b["y_min"], 
                             facecolor=cmap(count/max_v), alpha=0.4 if count > 0 else 0.1, zorder=1)
            ax.add_patch(rect)
            if count > 0:
                ax.text(b["x_min"] + (b["x_max"]-b["x_min"])/2, b["y_min"] + (b["y_max"]-b["y_min"])/2,
                        str(int(count)), ha='center', va='center', fontsize=12, fontweight='bold', zorder=3)

        st.pyplot(fig)
        plt.close(fig)
