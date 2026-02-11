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

# #Linjeoversigt (Usynlig Edition)
# line_alpha=0.1: Gør banens linjer 90% gennemsigtige.
# edgecolor='none' i Rectangle: Fjerner de sorte kasser omkring zonerne.
# linewidth=0 i Pitch: Fjerner de hårde kridtstreger.

def find_zone(x, y):
    for zone, b in ZONE_BOUNDARIES.items():
        if b["x_min"] <= x <= b["x_max"] and b["y_min"] <= y <= b["y_max"]:
            return zone
    return "Udenfor"

def vis_side(df_events, df_spillere):
    # 1. DATA PREPARATION
    df = df_events.copy()
    sp = df_spillere.copy()
    
    # Standardiser kolonner
    df.columns = [str(c).strip().upper() for c in df.columns]
    sp.columns = [str(c).strip().upper() for c in sp.columns]
    
    # Rens IDs og navne
    df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    sp['PLAYER_WYID'] = sp['PLAYER_WYID'].astype(str).str.split('.').str[0]
    navne_dict = dict(zip(sp['PLAYER_WYID'], sp['NAVN']))
    df['PLAYER_NAME_CLEAN'] = df['PLAYER_WYID'].map(navne_dict).fillna("Ukendt")

    # --- UI FILTRE ---
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        visning_valg = st.radio("Visning:", ["Hold", "Enkel spiller"], horizontal=True)
    
    with c2:
        if visning_valg == "Enkel spiller":
            spiller_liste = sorted([s for s in df['PLAYER_NAME_CLEAN'].unique() if s != "Ukendt"])
            valgt_target = st.selectbox("Vælg Spiller:", spiller_liste)
        else:
            valgt_target = "Hvidovre IF" # Hold-visning

    with c3:
        valgt_type = st.selectbox("Type:", ["Alle Skud", "Mål"])

    # --- FILTRERING ---
    # Vi bruger SHOTXG hvis den findes i df (fra din shotevents.csv merge i dash-filen)
    mask = df['PRIMARYTYPE'].str.contains('shot', case=False, na=False)
    
    if visning_valg == "Enkel spiller":
        mask &= (df['PLAYER_NAME_CLEAN'] == valgt_target)
    
    if valgt_type == "Mål":
        mask &= df['PRIMARYTYPE'].str.contains('goal', case=False, na=False)

    df_skud = df[mask].copy()
    df_skud['LOCATIONX'] = pd.to_numeric(df_skud['LOCATIONX'], errors='coerce')
    df_skud['LOCATIONY'] = pd.to_numeric(df_skud['LOCATIONY'], errors='coerce')
    df_skud = df_skud.dropna(subset=['LOCATIONX', 'LOCATIONY'])
    df_skud['ZONE_ID'] = df_skud.apply(lambda row: find_zone(row['LOCATIONY'], row['LOCATIONX']), axis=1)

    # --- BEREGNING AF STATS ---
    zone_stats = df_skud['ZONE_ID'].value_counts()
    
    # Hvis hold-visning: Find topscorer per zone
    top_per_zone = {}
    if visning_valg == "Hold" and not df_skud.empty:
        # Find spilleren med flest skud/mål i hver zone
        for zone in df_skud['ZONE_ID'].unique():
            z_data = df_skud[df_skud['ZONE_ID'] == zone]
            if not z_data.empty:
                top_player = z_data['PLAYER_NAME_CLEAN'].value_counts().idxmax()
                # Forkort navn (f.eks. M. Spelmann)
                p_parts = top_player.split()
                name_short = f"{p_parts[0][0]}. {p_parts[-1]}" if len(p_parts) > 1 else top_player
                top_per_zone[zone] = name_short.upper()

    # --- TEGN BANE ---
    # Usynlige linjer: line_alpha=0.1 gør kridtet næsten væk
    pitch = VerticalPitch(half=True, pitch_type='wyscout', 
                          line_color='#000000', line_alpha=0.1, 
                          linewidth=1, line_zorder=1)
    
    fig, ax = pitch.draw(figsize=(8, 5))
    fig.patch.set_facecolor('none')
    ax.set_facecolor('none')
    ax.set_ylim(50, 102) # Fokus på modstanderens banehalvdel

    max_count = zone_stats.max() if not zone_stats.empty else 1
    cmap = mcolors.LinearSegmentedColormap.from_list('HIF', ['#ffffff', '#d31313'])

    for name, b in ZONE_BOUNDARIES.items():
        if name == "Zone 8" and b["y_max"] < 50: continue
        
        count = zone_stats.get(name, 0)
        color_val = count / max_count
        
        # Rectangle uden kant (edgecolor='none') for det usynlige look
        rect = Rectangle((b["x_min"], b["y_min"]), b["x_max"] - b["x_min"], b["y_max"] - b["y_min"], 
                         edgecolor='none', facecolor=cmap(color_val), alpha=0.5, zorder=0)
        ax.add_patch(rect)
        
        if count > 0:
            x_t = b["x_min"] + (b["x_max"]-b["x_min"])/2
            y_t = b["y_min"] + (b["y_max"]-b["y_min"])/2
            
            # Tekst (Antal + Spiller)
            ax.text(x_t, y_t + 1, f"{int(count)}", ha='center', va='center', 
                    fontweight='bold', fontsize=9, color="#333333")
            
            if visning_valg == "Hold" and name in top_per_zone:
                ax.text(x_t, y_t - 1.5, top_per_zone[name], ha='center', va='center', 
                        fontsize=5, fontweight='black', color="#cc0000")

    st.pyplot(fig, use_container_width=True)
    
    # xG overblik (Bruger data fra din shotevents.csv hvis kolonnen SHOTXG findes)
    if 'SHOTXG' in df_skud.columns:
        total_xg = df_skud['SHOTXG'].sum()
        st.caption(f"Samlet xG for udvalgte skud: {total_xg:.2f}")
