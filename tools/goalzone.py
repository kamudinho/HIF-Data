import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from mplsoccer import VerticalPitch
import streamlit as st
import matplotlib.colors as mcolors

# ... ZONE_BOUNDARIES og find_zone forbliver de samme ...

def vis_side(df, kamp=None, hold_map=None):
    HIF_ID = 38331
    HIF_RED = '#df003b'
    BG_WHITE = '#ffffff'
    df.columns = [str(c).strip().upper() for c in df.columns]

    # --- 1. DROPDOWNS ---
    c1, c2 = st.columns(2)
    opp_ids = sorted([int(tid) for tid in df['OPPONENTTEAM_WYID'].unique() if int(tid) != HIF_ID])
    dropdown_options = [("Alle Kampe", None)]
    for mid in opp_ids:
        navn = hold_map.get(mid, f"ID: {mid}")
        dropdown_options.append((navn, mid))

    with c1:
        valgt_navn, valgt_id = st.selectbox("Vælg modstander", options=dropdown_options, format_func=lambda x: x[0])
    with c2:
        valgt_type = st.selectbox("Vis type:", ["Alle Skud", "Mål"])

    # --- 2. FILTRERING & BEREGNING ---
    mask = (df['TEAM_WYID'].astype(int) == HIF_ID) & (df['PRIMARYTYPE'].str.contains('shot', case=False, na=False))
    if valgt_id:
        mask &= (df['OPPONENTTEAM_WYID'].astype(int) == valgt_id)
        titel_tekst = f"HIF ZONER vs. {valgt_navn}"
    else:
        titel_tekst = "HIF ZONER: ALLE KAMPE"

    if valgt_type == "Mål":
        mask &= df['PRIMARYTYPE'].str.contains('goal', case=False, na=False)

    df_skud = df[mask].copy()
    df_skud['LOCATIONX'] = pd.to_numeric(df_skud['LOCATIONX'], errors='coerce')
    df_skud['LOCATIONY'] = pd.to_numeric(df_skud['LOCATIONY'], errors='coerce')
    df_skud = df_skud.dropna(subset=['LOCATIONX', 'LOCATIONY'])

    df_skud['ZONE_ID'] = df_skud.apply(lambda row: find_zone(row['LOCATIONY'], row['LOCATIONX']), axis=1)
    zone_stats = df_skud['ZONE_ID'].value_counts().to_frame(name='Antal')
    total = int(zone_stats['Antal'].sum())
    zone_stats['Procent'] = (zone_stats['Antal'] / total * 100) if total > 0 else 0

    # --- 3. VISUALISERING (Minimeret afstand) ---
    fig, ax = plt.subplots(figsize=(8, 8), facecolor=BG_WHITE)
    
    # FIX: Vi bruger pad_top=-15 for at fjerne det automatiske tomrum
    pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#1a1a1a', 
                          linewidth=1.2, pad_top=-15, pad_bottom=0)
    pitch.draw(ax=ax)

    # TITEL & STATS (Rykket en smule ned for at møde banen)
    ax.text(50, 108, titel_tekst.upper(), fontsize=7, color='#333333', ha='center', fontweight='black')
    ax.text(50, 105.5, str(total), color=HIF_RED, fontsize=9, fontweight='bold', ha='center')
    ax.text(50, 104, "TOTAL AFSLUTNINGER", fontsize=5, color='gray', ha='center', fontweight='bold')

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
            # Zone 8 tekst er nu løftet mere ind på banen
            y_t = 65 if name == "Zone 8" else b["y_min"] + (b["y_max"]-b["y_min"])/2
            ax.text(x_t, y_t, f"{int(count)}\n{percent:.1f}%", ha='center', va='center', fontweight='bold', fontsize=6)

    # FIX: ylim er nu meget strammere (0 til 110)
    ax.set_ylim(0, 110) 
    ax.set_xlim(-2, 102)
    ax.axis('off')
    st.pyplot(fig)
