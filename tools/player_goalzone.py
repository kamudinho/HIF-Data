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
    # 1. DATA RENS
    df = df_events.copy()
    sp = df_spillere.copy()
    
    df.columns = [str(c).strip().upper() for c in df.columns]
    sp.columns = [str(c).strip().upper() for c in sp.columns]

    # Sørg for at PLAYER_WYID er string for præcis match
    df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    sp['PLAYER_WYID'] = sp['PLAYER_WYID'].astype(str).str.split('.').str[0]

    # Find kolonnen med navnet
    navne_col = next((col for col in ['NAVN', 'PLAYER_NAME', 'PLAYER', 'SPILLER'] if col in sp.columns), None)
    
    if not navne_col:
        st.error("Kunne ikke finde kolonnen med spillernavne.")
        return

    navne_dict = dict(zip(sp['PLAYER_WYID'], sp[navne_col]))
    df['PLAYER_NAME_CLEAN'] = df['PLAYER_WYID'].map(navne_dict).fillna("Ukendt")

    # --- UI FILTRE ---
    col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
    with col_f1:
        # Kun spillere der faktisk er i event-data og ikke er "Ukendt"
        spiller_liste = sorted([s for s in df['PLAYER_NAME_CLEAN'].unique() if s != "Ukendt"])
        valgt_spiller = st.selectbox("Vælg Spiller:", spiller_liste)
    with col_f2:
        valgt_type = st.selectbox("Vis type:", ["Alle Skud", "Mål"])
    
    # --- FILTRERING ---
    mask = df['PRIMARYTYPE'].str.contains('shot', case=False, na=False)
    mask &= (df['PLAYER_NAME_CLEAN'] == valgt_spiller)
    
    if valgt_type == "Mål":
        mask &= df['PRIMARYTYPE'].str.contains('goal', case=False, na=False)

    df_skud = df[mask].copy()
    
    if df_skud.empty:
        st.info(f"Ingen data fundet for {valgt_spiller} med de valgte filtre.")
        return

    df_skud['LOCATIONX'] = pd.to_numeric(df_skud['LOCATIONX'], errors='coerce')
    df_skud['LOCATIONY'] = pd.to_numeric(df_skud['LOCATIONY'], errors='coerce')
    df_skud = df_skud.dropna(subset=['LOCATIONX', 'LOCATIONY'])

    # Beregn zoner
    df_skud['ZONE_ID'] = df_skud.apply(lambda row: find_zone(row['LOCATIONY'], row['LOCATIONX']), axis=1)
    zone_stats = df_skud['ZONE_ID'].value_counts()
    total = len(df_skud)

    with col_f3:
        st.metric("Total skud", total)

    # --- TEGN BANE ---
    pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#000000', line_zorder=2.5)
    fig, ax = pitch.draw(figsize=(10, 5)) 
    fig.patch.set_facecolor('none')
    ax.set_facecolor('none')

    ax.set_ylim(55, 102) 
    plt.subplots_adjust(left=0.01, right=0.99, top=0.98, bottom=0.01)

    max_count = zone_stats.max() if not zone_stats.empty else 1
    cmap = mcolors.LinearSegmentedColormap.from_list('HIF', ['#f9f9f9', '#d31313'])

    for name, b in ZONE_BOUNDARIES.items():
        if name == "Zone 8" and b["y_max"] < 55: continue 
        
        count = zone_stats.get(name, 0)
        percent = (count / total * 100) if total > 0 else 0
        color_val = count / max_count
        
        rect = Rectangle((b["x_min"], b["y_min"]), b["x_max"] - b["x_min"], b["y_max"] - b["y_min"], 
                         edgecolor='#000000', linestyle='-', linewidth=0.2, 
                         facecolor=cmap(color_val), alpha=0.7, zorder=1)
        ax.add_patch(rect)
        
        if count > 0:
            x_t = b["x_min"] + (b["x_max"]-b["x_min"])/2
            y_t = b["y_min"] + (b["y_max"]-b["y_min"])/2
            if name == "Zone 8": y_t = 60
            
            text_color = "#000000" if color_val > 0.4 else "#333333"
            ax.text(x_t, y_t, f"{int(count)}\n({percent:.0f}%)", 
                    ha='center', va='center', fontweight='bold', fontsize=9, 
                    color=text_color, zorder=3)

    # Visning
    center_col = st.columns([0.1, 0.8, 0.1])[1]
    with center_col:
        st.pyplot(fig, use_container_width=True)
