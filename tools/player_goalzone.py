import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from mplsoccer import VerticalPitch
import streamlit as st
import matplotlib.colors as mcolors

# --- KONSTANTER ---
ZONE_BOUNDARIES = {
    "Zone 1": {"y_min": 94.2, "y_max": 100.0, "x_min": 36.8, "x_max": 63.2},
    "Zone 4A": {"y_min": 94.2, "y_max": 100.0, "x_min": 63.2, "x_max": 81.0},
    "Zone 4B": {"y_min": 94.2, "y_max": 100.0, "x_min": 19.0, "x_max": 36.8},
    "Zone 2": {"y_min": 88.5, "y_max": 94.2, "x_min": 36.8, "x_max": 63.2},
    "Zone 3": {"y_min": 84.0, "y_max": 88.5, "x_min": 36.8, "x_max": 63.2},
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

def vis_side(df_events, df_spillere):
    df = df_events.copy()
    sp = df_spillere.copy()
    
    # 1. RENS OG KLARGØR (Sikrer at kolonnenavne matcher dine CSV/Parquet filer)
    df.columns = [str(c).strip().upper() for c in df.columns]
    sp.columns = [str(c).strip().upper() for c in sp.columns]
    
    df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    sp['PLAYER_WYID'] = sp['PLAYER_WYID'].astype(str).str.split('.').str[0]
    navne_dict = dict(zip(sp['PLAYER_WYID'], sp['NAVN']))
    df['PLAYER_NAME_CLEAN'] = df['PLAYER_WYID'].map(navne_dict).fillna("Ukendt")

    # --- TOP FILTRE (Som i player_shots.py) ---
    st.markdown("### Zone-baseret Afslutningsanalyse")
    c1, c2, c3 = st.columns([1, 1, 1])
    
    with c1:
        visning_type = st.radio("Niveau:", ["Hold", "Spiller"], horizontal=True)
    with c2:
        if visning_type == "Spiller":
            spiller_liste = sorted([s for s in df['PLAYER_NAME_CLEAN'].unique() if s != "Ukendt"])
            valgt_target = st.selectbox("Vælg Spiller:", spiller_liste)
        else:
            valgt_target = "Hvidovre IF"
    with c3:
        skud_type = st.selectbox("Data filter:", ["Alle skud", "Mål kun"])

    # --- FILTRERING ---
    mask = df['PRIMARYTYPE'].str.contains('shot', case=False, na=False)
    if visning_type == "Spiller":
        mask &= (df['PLAYER_NAME_CLEAN'] == valgt_target)
    if skud_type == "Mål kun":
        mask &= df['PRIMARYTYPE'].str.contains('goal', case=False, na=False)

    df_skud = df[mask].copy()
    df_skud['LOCATIONX'] = pd.to_numeric(df_skud['LOCATIONX'], errors='coerce')
    df_skud['LOCATIONY'] = pd.to_numeric(df_skud['LOCATIONY'], errors='coerce')
    df_skud = df_skud.dropna(subset=['LOCATIONX', 'LOCATIONY'])
    df_skud['ZONE_ID'] = df_skud.apply(lambda row: find_zone(row['LOCATIONY'], row['LOCATIONX']), axis=1)

    # --- OVERBLIK / KPI BOKSE (Ligesom player_shots.py) ---
    total_skud = len(df_skud)
    total_maal = df_skud['PRIMARYTYPE'].str.contains('goal', case=False, na=False).sum()
    
    # xG Beregning (Hvis SHOTXG er merget ind fra shotevents.csv)
    total_xg = df_skud['SHOTXG'].sum() if 'SHOTXG' in df_skud.columns else 0.0
    xg_per_skud = total_xg / total_skud if total_skud > 0 else 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Skud", total_skud)
    m2.metric("Mål", total_maal)
    m3.metric("Total xG", f"{total_xg:.2f}")
    m4.metric("xG/Skud", f"{xg_per_skud:.2f}")

    st.markdown("---")

    # --- BEREGN TOPSCORER PER ZONE (Hvis Hold-visning) ---
    top_per_zone = {}
    if visning_type == "Hold" and not df_skud.empty:
        for zone in df_skud['ZONE_ID'].unique():
            z_data = df_skud[df_skud['ZONE_ID'] == zone]
            if not z_data.empty:
                top_name = z_data['PLAYER_NAME_CLEAN'].value_counts().idxmax()
                parts = top_name.split()
                top_per_zone[zone] = f"{parts[0][0]}. {parts[-1]}".upper() if len(parts) > 1 else top_name.upper()

    # --- TEGN BANE (Med næsten usynlige linjer) ---
    pitch = VerticalPitch(half=True, pitch_type='wyscout', 
                          line_color='#000000', line_alpha=0.05, # Næsten usynlig
                          linewidth=1, line_zorder=1)
    
    fig, ax = pitch.draw(figsize=(10, 6))
    fig.patch.set_facecolor('none')
    ax.set_facecolor('none')
    ax.set_ylim(55, 102)

    max_count = zone_stats = df_skud['ZONE_ID'].value_counts().max() if not df_skud.empty else 1
    cmap = mcolors.LinearSegmentedColormap.from_list('HIF', ['#ffffff', '#d31313'])

    for name, b in ZONE_BOUNDARIES.items():
        if name == "Zone 8" and b["y_max"] < 55: continue
        
        count = df_skud['ZONE_ID'].value_counts().get(name, 0)
        color_val = count / max_count if max_count > 0 else 0
        
        # Rectangle uden kant (ghost lines)
        rect = Rectangle((b["x_min"], b["y_min"]), b["x_max"] - b["x_min"], b["y_max"] - b["y_min"], 
                         edgecolor='none', facecolor=cmap(color_val), alpha=0.4, zorder=0)
        ax.add_patch(rect)
        
        if count > 0:
            x_t = b["x_min"] + (b["x_max"]-b["x_min"])/2
            y_t = b["y_min"] + (b["y_max"]-b["y_min"])/2
            
            # Antal skud i zonen
            ax.text(x_t, y_t + 1, f"{int(count)}", ha='center', va='center', 
                    fontweight='bold', fontsize=10, color="#222222")
            
            # Bedste spiller (kun ved hold-visning)
            if visning_type == "Hold" and name in top_per_zone:
                ax.text(x_t, y_t - 1.2, top_per_zone[name], ha='center', va='center', 
                        fontsize=6, fontweight='black', color="#cc0000", alpha=0.8)

    st.pyplot(fig, use_container_width=True)
