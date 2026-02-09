import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from mplsoccer import VerticalPitch
import streamlit as st
import matplotlib.colors as mcolors

# --- ZONE DEFINITIONER (Beholdes som de er) ---
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

def vis_individuel_side(df):
    # Rens kolonner
    df.columns = [str(c).strip().upper() for c in df.columns]

    st.subheader("Individuel Målzone Analyse")

    # --- 1. SPILLER FILTRE ---
    # Vi antager at din dataframe har en kolonne 'PLAYER_NAME' eller lignende
    # Hvis den kun har ID, skal du mappe den først.
    spiller_kolonne = 'PLAYER_NAME' if 'PLAYER_NAME' in df.columns else 'PLAYER_WYID'
    
    col1, col2 = st.columns(2)
    with col1:
        spiller_liste = sorted(df[spiller_kolonne].dropna().unique().tolist())
        valgt_spiller = st.selectbox("Vælg Spiller:", spiller_liste)
    with col2:
        valgt_type = st.selectbox("Vis type:", ["Alle Skud", "Mål"])

    # --- 2. FILTRERING ---
    # Filtrer først på skud-events
    mask = df['PRIMARYTYPE'].str.contains('shot', case=False, na=False)
    
    # Filtrer på den valgte spiller
    mask &= (df[spiller_kolonne] == valgt_spiller)

    if valgt_type == "Mål":
        mask &= df['PRIMARYTYPE'].str.contains('goal', case=False, na=False)

    df_skud = df[mask].copy()

    # Konverter X/Y
    df_skud['LOCATIONX'] = pd.to_numeric(df_skud['LOCATIONX'], errors='coerce')
    df_skud['LOCATIONY'] = pd.to_numeric(df_skud['LOCATIONY'], errors='coerce')
    df_skud = df_skud.dropna(subset=['LOCATIONX', 'LOCATIONY'])

    # Match hver afslutning til en zone
    df_skud['ZONE_ID'] = df_skud.apply(lambda row: find_zone(row['LOCATIONY'], row['LOCATIONX']), axis=1)

    # Beregn statistik
    zone_stats = df_skud['ZONE_ID'].value_counts().to_frame(name='Antal')
    total_skud = zone_stats['Antal'].sum()
    zone_stats['Procent'] = (zone_stats['Antal'] / total_skud * 100) if total_skud > 0 else 0

    # --- 3. TEGN BANE ---
    draw_pitch_with_stats(zone_stats, total_skud)

def draw_pitch_with_stats(zone_stats, total_skud):
    pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='grey', pad_bottom=40)
    fig, ax = pitch.draw(figsize=(10, 8))

    ax.set_ylim(45, 105) 

    max_count = zone_stats['Antal'].max() if not zone_stats.empty else 1
    # HIF Rød farveskala
    cmap = mcolors.LinearSegmentedColormap.from_list('HIF', ['#ffffff', '#df003b'])

    for name, b in ZONE_BOUNDARIES.items():
        count = zone_stats.loc[name, 'Antal'] if name in zone_stats.index else 0
        percent = zone_stats.loc[name, 'Procent'] if name in zone_stats.index else 0

        color_val = count / max_count if max_count > 0 else 0

        rect = Rectangle((b["x_min"], b["y_min"]), b["x_max"] - b["x_min"],
                         b["y_max"] - b["y_min"], edgecolor='black',
                         linestyle='--', facecolor=cmap(color_val), alpha=0.5)
        ax.add_patch(rect)

        if count > 0:
            x_text = b["x_min"] + (b["x_max"] - b["x_min"]) / 2
            
            if name == "Zone 8":
                y_text = 57.5
            else:
                y_text = b["y_min"] + (b["y_max"] - b["y_min"]) / 2

            label = f"{int(count)}\n({percent:.1f}%)"
            ax.text(x_text, y_text, label, ha='center', va='center',
                    fontweight='bold', fontsize=10, color='black')

    st.pyplot(fig)
    st.write(f"**Total antal afslutninger for spiller:** {int(total_skud)}")
