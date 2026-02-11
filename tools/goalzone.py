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

def find_zone(val_x, val_y):
    for zone, b in ZONE_BOUNDARIES.items():
        if b["x_min"] <= val_x <= b["x_max"] and b["y_min"] <= val_y <= b["y_max"]:
            return zone
    return "Udenfor"

def vis_side(df_events, df_spillere, hold_map):
    HIF_ID = 38331
    HIF_RED = '#d31313' # Opdateret til den samme røde som før
    
    # 1. RENS KOLONNER OG ID'er
    df = df_events.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    s_df = df_spillere.copy()
    s_df.columns = [str(c).strip().upper() for c in s_df.columns]

    df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    s_df['PLAYER_WYID'] = s_df['PLAYER_WYID'].astype(str).str.split('.').str[0]

    # 2. HENT NAVNE
    navne_dict = dict(zip(s_df['PLAYER_WYID'], s_df['NAVN']))
    df['NAVN_MAP'] = df['PLAYER_WYID'].map(navne_dict).fillna("Ukendt")

    # 3. FILTRERING (Låst til HIF)
    df_hif = df[df['TEAM_WYID'].astype(int) == HIF_ID].copy()

    opp_ids = sorted([int(tid) for tid in df_hif['OPPONENTTEAM_WYID'].unique() if pd.notna(tid)])
    dropdown_options = [("Alle Kampe", None)]
    for mid in opp_ids:
        dropdown_options.append((hold_map.get(mid, f"Hold {mid}"), mid))

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        valgt_navn, valgt_id = st.selectbox("Vælg modstander", options=dropdown_options, format_func=lambda x: x[0])
    with c2:
        valgt_type = st.selectbox("Type", ["Alle skud", "Mål kun"])

    mask = df_hif['PRIMARYTYPE'].str.contains('shot', case=False, na=False)
    if valgt_id:
        mask &= (df_hif['OPPONENTTEAM_WYID'].astype(int) == valgt_id)
    if valgt_type == "Mål kun":
        mask &= df_hif['PRIMARYTYPE'].str.contains('goal', case=False, na=False)

    df_plot = df_hif[mask].copy()

    if df_plot.empty:
        st.info("Ingen data fundet.")
        return

    # 4. ZONE-BEREGNING
    df_plot['LOCATIONX'] = pd.to_numeric(df_plot['LOCATIONX'], errors='coerce')
    df_plot['LOCATIONY'] = pd.to_numeric(df_plot['LOCATIONY'], errors='coerce')
    df_plot = df_plot.dropna(subset=['LOCATIONX', 'LOCATIONY'])
    df_plot['ZONE_ID'] = df_plot.apply(lambda row: find_zone(row['LOCATIONY'], row['LOCATIONX']), axis=1)

    total_shots = len(df_plot)
    with c3:
        st.metric("Total", total_shots)

    # Find top-spiller per zone
    top_per_zone = {}
    df_names = df_plot[df_plot['NAVN_MAP'] != "Ukendt"]
    if not df_names.empty:
        counts_grouped = df_names.groupby(['ZONE_ID', 'NAVN_MAP']).size().reset_index(name='N')
        for zone in counts_grouped['ZONE_ID'].unique():
            z_data = counts_grouped[counts_grouped['ZONE_ID'] == zone]
            best = z_data.loc[z_data['N'].idxmax(), 'NAVN_MAP']
            p = best.split()
            top_per_zone[zone] = f"{p[0][0]}. {p[-1]}".upper() if len(p) > 1 else best.upper()

    # --- 5. KOMPAKT PLOT ---
    pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#cfcfcf', line_zorder=2)
    fig, ax = pitch.draw(figsize=(10, 4.5)) # Fladere format
    fig.patch.set_facecolor('none')
    ax.set_facecolor('none')

    # Zoom ind for at fjerne spildplads (Zone 8 starter ved 0, men vi klipper ved 55)
    ax.set_ylim(55, 102)
    plt.subplots_adjust(left=0.01, right=0.99, top=0.95, bottom=0.01)

    zone_stats = df_plot['ZONE_ID'].value_counts()
    max_val = zone_stats.max() if not zone_stats.empty else 1
    cmap = mcolors.LinearSegmentedColormap.from_list('HIF', ['#f9f9f9', HIF_RED])

    for name, b in ZONE_BOUNDARIES.items():
        val = zone_stats.get(name, 0)
        pct = (val / total_shots * 100) if total_shots > 0 else 0
        color_val = val / max_val
        
        rect = Rectangle((b["x_min"], b["y_min"]), b["x_max"]-b["x_min"], b["y_max"]-b["y_min"],
                         facecolor=cmap(color_val), alpha=0.7, edgecolor='#444444', 
                         linestyle='-', linewidth=0.5, zorder=1)
        ax.add_patch(rect)
        
        if val > 0:
            x_t = b["x_min"] + (b["x_max"]-b["x_min"])/2
            y_t = b["y_min"] + (b["y_max"]-b["y_min"])/2
            if name == "Zone 8": y_t = 60
            
            # Tekst-farve baseret på baggrund
            text_color = "white" if color_val > 0.4 else "#333333"
            
            # Antal og Procent
            ax.text(x_t, y_t + 1.0, f"{val} ({pct:.0f}%)", ha='center', va='center', 
                    fontweight='bold', fontsize=7.5, color=text_color, zorder=3)
            
            # Top spiller navn
            if name in top_per_zone:
                ax.text(x_t, y_t - 1.5, top_per_zone[name], ha='center', va='center', 
                        fontsize=5.5, fontweight='black', color=text_color, alpha=0.9, zorder=3)

    # --- RESPONSIV VISNING (70% bredde) ---
    spacer_l, center, spacer_r = st.columns([0.15, 0.7, 0.15])
    with center:
        st.pyplot(fig, use_container_width=True)
        st.caption(f"HIF ZONE-ANALYSE: {valgt_navn}")
