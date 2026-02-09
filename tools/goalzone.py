import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from mplsoccer import VerticalPitch
import streamlit as st
import matplotlib.colors as mcolors

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

def vis_side(df, kamp=None, hold_map=None):
    HIF_ID = 38331
    HIF_RED = '#df003b'
    BG_WHITE = '#ffffff'
    df.columns = [str(c).strip().upper() for c in df.columns]

   # --- 1. MODSTANDER DROPDOWN (PÅ ÉN LINJE) ---
    col1, col2 = st.columns(2)
    
    opp_ids = sorted([int(tid) for tid in df['OPPONENTTEAM_WYID'].unique() if int(tid) != HIF_ID])
    dropdown_options = [("Alle Kampe", None)]
    for mid in opp_ids:
        navn = hold_map.get(mid, f"ID: {mid}")
        dropdown_options.append((navn, mid))

    with col1:
        valgt_navn, valgt_id = st.selectbox("Vælg modstander", options=dropdown_options, format_func=lambda x: x[0])
    
    with col2:
        valgt_type = st.selectbox("Vis type:", ["Alle Skud", "Mål"])
        
    # --- 2. FILTRERING ---
    mask = (df['TEAM_WYID'].astype(int) == HIF_ID) & (df['PRIMARYTYPE'].str.contains('shot', case=False, na=False))
    if valgt_id:
        mask &= (df['OPPONENTTEAM_WYID'].astype(int) == valgt_id)
        titel_tekst = f"HIF Zoner vs. {valgt_navn}"
    else:
        titel_tekst = "HIF Zoner: Alle Kampe"

    if valgt_type == "Mål":
        mask &= df['PRIMARYTYPE'].str.contains('goal', case=False, na=False)

    df_skud = df[mask].copy()
    df_skud['LOCATIONX'] = pd.to_numeric(df_skud['LOCATIONX'], errors='coerce')
    df_skud['LOCATIONY'] = pd.to_numeric(df_skud['LOCATIONY'], errors='coerce')
    df_skud = df_skud.dropna(subset=['LOCATIONX', 'LOCATIONY'])

    # Beregn stats
    df_skud['ZONE_ID'] = df_skud.apply(lambda row: find_zone(row['LOCATIONY'], row['LOCATIONX']), axis=1)
    zone_stats = df_skud['ZONE_ID'].value_counts().to_frame(name='Antal')
    total = int(zone_stats['Antal'].sum())
    zone_stats['Procent'] = (zone_stats['Antal'] / total * 100) if total > 0 else 0

    # --- 3. VISUALISERING ---
    fig, ax = plt.subplots(figsize=(10, 5), facecolor=BG_WHITE)
    pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#1a1a1a', linewidth=1.2)
    pitch.draw(ax=ax)

    # Titel (fontsize=7 som aftalt)
    ax.text(50, 114, titel_tekst.upper(), fontsize=7, color='#333333', ha='center', fontweight='black')

    # Stats Block (Kompakt look)
    ax.text(50, 110, str(total), color=HIF_RED, fontsize=8, fontweight='bold', ha='center')
    ax.text(50, 108.5, "TOTAL AFSLUTNINGER", fontsize=5, color='gray', ha='center', fontweight='bold')

    # Tegn Zoner
    max_count = zone_stats['Antal'].max() if not zone_stats.empty else 1
    cmap = mcolors.LinearSegmentedColormap.from_list('HIF', ['#ffffff', HIF_RED])

    for name, b in ZONE_BOUNDARIES.items():
        count = zone_stats.loc[name, 'Antal'] if name in zone_stats.index else 0
        percent = zone_stats.loc[name, 'Procent'] if name in zone_stats.index else 0
        color_val = count / max_count if max_count > 0 else 0
        
        rect = Rectangle((b["x_min"], b["y_min"]), b["x_max"] - b["x_min"], b["y_max"] - b["y_min"], 
                         edgecolor='black', linestyle='--', facecolor=cmap(color_val), alpha=0.4, linewidth=0.5)
        ax.add_patch(rect)
        
        if count > 0:
            x_t = b["x_min"] + (b["x_max"]-b["x_min"])/2
            y_t = b["y_min"] + (b["y_max"]-b["y_min"])/2
            ax.text(x_t, y_t, f"{int(count)}\n{percent:.1f}%", ha='center', va='center', fontweight='bold', fontsize=5)

    ax.set_ylim(45, 116)
    ax.axis('off')
    st.pyplot(fig)
