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

def vis_side(df_events, df_spillere):
    # 1. Rens kolonner (Fjerner mellemrum og gør dem STORE)
    df_events.columns = [str(c).strip().upper() for c in df_events.columns]
    df_spillere.columns = [str(c).strip().upper() for c in df_spillere.columns]

    # Debug hjælp: Hvis koden fejler herunder, kan vi se navnene
    try:
        # Vi tjekker om de rigtige kolonner findes
        if 'PLAYER_WYID' not in df_spillere.columns:
            st.error(f"Kunne ikke finde 'PLAYER_WYID'. Kolonner i arket er: {list(df_spillere.columns)}")
            return
            
        # Find kolonnen med navnet (den kan hedde PLAYER_NAME, SPILLER, eller NAVN)
        navne_col = None
        for col in ['PLAYER_NAME', 'PLAYER', 'SPILLER', 'NAVN']:
            if col in df_spillere.columns:
                navne_col = col
                break
        
        if not navne_col:
            st.error(f"Kunne ikke finde en kolonne med spillernavn. Tilgængelige kolonner: {list(df_spillere.columns)}")
            return

        # Lav en ren mapping-liste
        navne_df = df_spillere[['PLAYER_WYID', navne_col]].drop_duplicates()
        navne_df = navne_df.rename(columns={navne_col: 'PLAYER_NAME_CLEAN'})

        # Merge navne på events baseret på PLAYER_WYID
        df_final = df_events.merge(navne_df, on='PLAYER_WYID', how='left')
        
    except Exception as e:
        st.error(f"Data-fejl: {e}")
        return

    # --- UI FILTRE ---
    col1, col2 = st.columns(2)
    with col1:
        # Vi bruger det rensede navn fra merge
        spiller_liste = sorted(df_final['PLAYER_NAME_CLEAN'].dropna().unique().tolist())
        if not spiller_liste:
            st.warning("Ingen spillere fundet i data.")
            return
        valgt_spiller = st.selectbox("Vælg Spiller:", spiller_liste)
    
    with col2:
        valgt_type = st.selectbox("Vis type:", ["Alle Skud", "Mål"])

    # --- FILTRERING ---
    mask = df_final['PRIMARYTYPE'].str.contains('shot', case=False, na=False)
    mask &= (df_final['PLAYER_NAME_CLEAN'] == valgt_spiller)
    
    if valgt_type == "Mål":
        mask &= df_final['PRIMARYTYPE'].str.contains('goal', case=False, na=False)

    df_skud = df_final[mask].copy()
    
    # Lokationsdata
    df_skud['LOCATIONX'] = pd.to_numeric(df_skud['LOCATIONX'], errors='coerce')
    df_skud['LOCATIONY'] = pd.to_numeric(df_skud['LOCATIONY'], errors='coerce')
    df_skud = df_skud.dropna(subset=['LOCATIONX', 'LOCATIONY'])

    # Beregn zoner
    df_skud['ZONE_ID'] = df_skud.apply(lambda row: find_zone(row['LOCATIONY'], row['LOCATIONX']), axis=1)
    zone_stats = df_skud['ZONE_ID'].value_counts().to_frame(name='Antal')
    total = zone_stats['Antal'].sum()
    zone_stats['Procent'] = (zone_stats['Antal'] / total * 100) if total > 0 else 0

    # --- TEGN BANE ---
    pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='grey', pad_bottom=40)
    fig, ax = pitch.draw(figsize=(10, 8))
    ax.set_ylim(45, 105)
    
    max_count = zone_stats['Antal'].max() if not zone_stats.empty else 1
    cmap = mcolors.LinearSegmentedColormap.from_list('HIF', ['#ffffff', '#df003b'])

    for name, b in ZONE_BOUNDARIES.items():
        count = zone_stats.loc[name, 'Antal'] if name in zone_stats.index else 0
        percent = zone_stats.loc[name, 'Procent'] if name in zone_stats.index else 0
        color_val = count / max_count if max_count > 0 else 0
        
        rect = Rectangle((b["x_min"], b["y_min"]), b["x_max"] - b["x_min"], b["y_max"] - b["y_min"], 
                         edgecolor='black', linestyle='--', facecolor=cmap(color_val), alpha=0.5)
        ax.add_patch(rect)
        
        if count > 0:
            x_t = b["x_min"] + (b["x_max"]-b["x_min"])/2
            y_t = 57.5 if name == "Zone 8" else b["y_min"] + (b["y_max"]-b["y_min"])/2
            ax.text(x_t, y_t, f"{int(count)}\n({percent:.1f}%)", ha='center', va='center', fontweight='bold', fontsize=9)

    st.pyplot(fig)
    st.write(f"**Total afslutninger for {valgt_spiller}:** {int(total)}")
