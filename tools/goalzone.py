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
    HIF_RED = '#df003b'
    
    # 1. RENS KOLONNER OG ID'er
    df = df_events.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    s_df = df_spillere.copy()
    s_df.columns = [str(c).strip().upper() for c in s_df.columns]

    # Sikr ID-format (Fjern .0 og gør til tekst)
    df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0]
    s_df['PLAYER_WYID'] = s_df['PLAYER_WYID'].astype(str).str.split('.').str[0]

    # 2. HENT NAVNE FRA SPILLER-ARKET
    # Vi mapper PLAYER_WYID til NAVN
    navne_dict = dict(zip(s_df['PLAYER_WYID'], s_df['NAVN']))
    df['NAVN_MAP'] = df['PLAYER_WYID'].map(navne_dict).fillna("Ukendt")

    # 3. FILTRERING (Låst til HIF)
    df_hif = df[df['TEAM_WYID'].astype(int) == HIF_ID].copy()

    # Dropdown til modstandere
    opp_ids = sorted([int(tid) for tid in df_hif['OPPONENTTEAM_WYID'].unique() if pd.notna(tid)])
    dropdown_options = [("Alle Kampe", None)]
    for mid in opp_ids:
        dropdown_options.append((hold_map.get(mid, f"Hold {mid}"), mid))

    c1, c2 = st.columns(2)
    with c1:
        valgt_navn, valgt_id = st.selectbox("Vælg modstander", options=dropdown_options, format_func=lambda x: x[0])
    with c2:
        valgt_type = st.selectbox("Type", ["Alle skud", "Mål kun"])

    # Filtrer på skud og modstander
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

    # Find hvem der afslutter mest i hver zone
    top_per_zone = {}
    df_names = df_plot[df_plot['NAVN_MAP'] != "Ukendt"]
    if not df_names.empty:
        counts = df_names.groupby(['ZONE_ID', 'NAVN_MAP']).size().reset_index(name='N')
        for zone in counts['ZONE_ID'].unique():
            z_data = counts[counts['ZONE_ID'] == zone]
            best = z_data.loc[z_data['N'].idxmax(), 'NAVN_MAP']
            # Forkort navn: "D. Stenderup"
            p = best.split()
            top_per_zone[zone] = f"{p[0][0]}. {p[-1]}".upper() if len(p) > 1 else best.upper()

    # 5. PLOT
    fig, ax = plt.subplots(figsize=(8, 10))
    pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#1a1a1a')
    pitch.draw(ax=ax)

    zone_stats = df_plot['ZONE_ID'].value_counts()
    max_val = zone_stats.max() if not zone_stats.empty else 1
    cmap = mcolors.LinearSegmentedColormap.from_list('HIF', ['#ffffff', HIF_RED])

    for name, b in ZONE_BOUNDARIES.items():
        val = zone_stats.get(name, 0)
        color_val = val / max_val
        
        rect = Rectangle((b["x_min"], b["y_min"]), b["x_max"]-b["x_min"], b["y_max"]-b["y_min"],
                         facecolor=cmap(color_val), alpha=0.4, edgecolor='black', linestyle='--', linewidth=0.5)
        ax.add_patch(rect)
        
        if val > 0:
            x_t = b["x_min"] + (b["x_max"]-b["x_min"])/2
            y_t = b["y_min"] + (b["y_max"]-b["y_min"])/2 if name != "Zone 8" else 55
            ax.text(x_t, y_t + 0.8, f"{val}", ha='center', fontweight='bold', fontsize=7)
            if name in top_per_zone:
                ax.text(x_t, y_t - 1.2, top_per_zone[name], ha='center', fontsize=5, fontweight='black')

    st.pyplot(fig)
