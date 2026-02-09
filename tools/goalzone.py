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

def vis_side(df_events, spillere_df, hold_map=None):
    HIF_ID = 38331
    HIF_RED = '#df003b'
    BG_WHITE = '#ffffff'
    
    # 1. TVING store bogstaver på alle kolonner med det samme
    df = df_events.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    s_df = spillere_df.copy()
    s_df.columns = [str(c).strip().upper() for c in s_df.columns]

    # Vi ved nu fra din fejlbesked, at PLAYER_WYID findes i df_events
    id_col = 'PLAYER_WYID'
    
    # Tjek om den også findes i spillere_df (ellers brug WYID)
    s_id_col = 'PLAYER_WYID' if 'PLAYER_WYID' in s_df.columns else 'WYID'

    # 2. Rens ID'er
    s_df[s_id_col] = s_df[s_id_col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    df[id_col] = df[id_col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    
    # 3. Lav navne_dict fra Spillere-arket
    navne_dict = {}
    for _, row in s_df.iterrows():
        f = str(row.get('FIRSTNAME', '')).replace('nan', '').strip()
        l = str(row.get('LASTNAME', '')).replace('nan', '').strip()
        navne_dict[row[s_id_col]] = f"{f} {l}".strip()
    
    # Map navnene over på skud-data
    df['NAVN'] = df[id_col].map(navne_dict).fillna("Ukendt Spiller")

    # 4. DROPDOWNS (Brug de kolonner vi ved findes)
    c1, c2 = st.columns(2)
    opp_col = 'OPPONENTTEAM_WYID'
    opp_ids = sorted([int(tid) for tid in df[opp_col].unique() if int(tid) != HIF_ID])
    
    dropdown_options = [("Alle Kampe", None)]
    for mid in opp_ids:
        navn = hold_map.get(mid, f"ID: {mid}")
        dropdown_options.append((navn, mid))

    with c1:
        valgt_navn, valgt_id = st.selectbox("Vælg modstander", options=dropdown_options, format_func=lambda x: x[0])
    with c2:
        valgt_type = st.selectbox("Vis type:", ["Alle Skud", "Mål"])

    # 5. FILTRERING
    mask = (df['TEAM_WYID'].astype(int) == HIF_ID) & (df['PRIMARYTYPE'].str.contains('shot', case=False, na=False))
    
    if valgt_id:
        mask &= (df[opp_col].astype(int) == valgt_id)
        titel_tekst = f"HIF ZONER VS. {valgt_navn}"
    else:
        titel_tekst = "HIF ZONER: ALLE KAMPE"

    if valgt_type == "Mål":
        mask &= df['PRIMARYTYPE'].str.contains('goal', case=False, na=False)

    df_skud = df[mask].copy()
    df_skud['LOCATIONX'] = pd.to_numeric(df_skud['LOCATIONX'], errors='coerce')
    df_skud['LOCATIONY'] = pd.to_numeric(df_skud['LOCATIONY'], errors='coerce')
    df_skud = df_skud.dropna(subset=['LOCATIONX', 'LOCATIONY'])

    # Beregn zoner
    df_skud['ZONE_ID'] = df_skud.apply(lambda row: find_zone(row['LOCATIONY'], row['LOCATIONX']), axis=1)
    
    # 6. TOP SPILLER LOGIK
    top_players = {}
    if not df_skud.empty:
        player_stats = df_skud.groupby(['ZONE_ID', 'NAVN']).size().reset_index(name='COUNT')
        for zone in player_stats['ZONE_ID'].unique():
            zone_df = player_stats[player_stats['ZONE_ID'] == zone]
            best_p = zone_df.loc[zone_df['COUNT'].idxmax(), 'NAVN']
            dele = str(best_p).split()
            short = f"{dele[0][0]}. {dele[-1]}" if len(dele) > 1 else best_p
            top_players[zone] = short.upper()

    zone_stats = df_skud['ZONE_ID'].value_counts().to_frame(name='Antal')
    total = int(zone_stats['Antal'].sum())
    zone_stats['Procent'] = (zone_stats['Antal'] / total * 100) if total > 0 else 0

    # 7. PITCH PLOT
    fig, ax = plt.subplots(figsize=(8, 10), facecolor=BG_WHITE)
    pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#1a1a1a', 
                          linewidth=1.2, pad_top=-15, pad_bottom=0)
    pitch.draw(ax=ax)

    ax.text(50, 107.5, titel_tekst.upper(), fontsize=7, color='#333333', ha='center', fontweight='black')
    ax.text(50, 105.2, str(total), color=HIF_RED, fontsize=9, fontweight='bold', ha='center')
    ax.text(50, 103.8, "TOTAL AFSLUTNINGER", fontsize=5, color='gray', ha='center', fontweight='bold')

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
            y_t = 55 if name == "Zone 8" else b["y_min"] + (b["y_max"]-b["y_min"])/2
            ax.text(x_t, y_t + 0.6, f"{int(count)} ({percent:.0f}%)", ha='center', va='bottom', fontweight='bold', fontsize=5.5)
            if name in top_players:
                ax.text(x_t, y_t - 1.2, top_players[name], ha='center', va='top', fontsize=4.8, color='#1a1a1a', fontweight='black')

    ax.set_ylim(40, 110) 
    ax.set_xlim(-2, 102)
    ax.axis('off')
    st.pyplot(fig)
