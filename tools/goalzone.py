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

def clean_id(val):
    if pd.isna(val): return ""
    return str(val).split('.')[0].strip()

def vis_side(df_events, df_spillere, hold_map):
    HIF_ID = 38331
    HIF_RED = '#df003b'
    BG_WHITE = '#ffffff'
    
    # 1. FORBERED DATA (Upper case kolonner)
    df = df_events.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    s_df = df_spillere.copy()
    s_df.columns = [str(c).strip().upper() for c in s_df.columns]

    # Rens ID-kolonner for præcis matching
    df['PLAYER_WYID'] = df['PLAYER_WYID'].apply(clean_id)
    s_df['PLAYER_WYID'] = s_df['PLAYER_WYID'].apply(clean_id)

    # 2. MAP NAVNE (HIF Spillere)
    navne_dict = {}
    for _, row in s_df.iterrows():
        pid = row['PLAYER_WYID']
        if pid:
            # Brug 'NAVN' kolonnen fra dit Excel-ark
            name = row.get('NAVN')
            if pd.isna(name) or str(name).strip() == "":
                f = str(row.get('FIRSTNAME', '')).replace('nan', '').strip()
                l = str(row.get('LASTNAME', '')).replace('nan', '').strip()
                name = f"{f} {l}".strip()
            navne_dict[pid] = name

    df['SP_NAVN'] = df['PLAYER_WYID'].map(navne_dict).fillna("Ukendt")

    # 3. FILTRERING (Låst til HIF 38331)
    # Vi sikrer os at vi fanger både tal og tekst versioner af ID'et
    hif_mask = (df['TEAM_WYID'].astype(str).str.split('.').str[0] == str(HIF_ID))
    df_hif = df[hif_mask].copy()

    # Dropdowns til modstander og skudtype
    opp_ids = sorted([int(float(tid)) for tid in df_hif['OPPONENTTEAM_WYID'].unique() if pd.notna(tid)])
    dropdown_options = [("Alle Kampe", None)]
    for mid in opp_ids:
        dropdown_options.append((hold_map.get(mid, f"ID: {mid}"), mid))

    c1, c2 = st.columns(2)
    with c1:
        valgt_navn, valgt_id = st.selectbox("Vælg modstander", options=dropdown_options, format_func=lambda x: x[0])
    with c2:
        valgt_type = st.selectbox("Vis type:", ["Alle Skud", "Mål"])

    # Endelig filter på skud/mål og valgt kamp
    final_mask = df_hif['PRIMARYTYPE'].str.contains('shot', case=False, na=False)
    
    if valgt_id:
        final_mask &= (df_hif['OPPONENTTEAM_WYID'].astype(str).str.split('.').str[0] == str(valgt_id))
    
    if valgt_type == "Mål":
        final_mask &= df_hif['PRIMARYTYPE'].str.contains('goal', case=False, na=False)

    df_skud = df_hif[final_mask].copy()
    
    if df_skud.empty:
        st.warning("Ingen data fundet for HIF med de valgte kriterier.")
        return

    # 4. BEREGN ZONER
    df_skud['LOCATIONX'] = pd.to_numeric(df_skud['LOCATIONX'], errors='coerce')
    df_skud['LOCATIONY'] = pd.to_numeric(df_skud['LOCATIONY'], errors='coerce')
    df_skud = df_skud.dropna(subset=['LOCATIONX', 'LOCATIONY'])
    df_skud['ZONE_ID'] = df_skud.apply(lambda row: find_zone(row['LOCATIONY'], row['LOCATIONX']), axis=1)

    # Find topscorer/top-afslutter pr. zone (kun navngivne spillere)
    top_players = {}
    df_valid = df_skud[df_skud['SP_NAVN'] != "Ukendt"]
    if not df_valid.empty:
        stats = df_valid.groupby(['ZONE_ID', 'SP_NAVN']).size().reset_index(name='COUNT')
        for zone in stats['ZONE_ID'].unique():
            z_df = stats[stats['ZONE_ID'] == zone]
            best = z_df.loc[z_df['COUNT'].idxmax(), 'SP_NAVN']
            parts = str(best).split()
            top_players[zone] = f"{parts[0][0]}. {parts[-1]}".upper() if len(parts) > 1 else str(best).upper()

    # 5. VISUALISERING
    fig, ax = plt.subplots(figsize=(8, 10), facecolor=BG_WHITE)
    pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#1a1a1a', linewidth=1.2, pad_top=-15)
    pitch.draw(ax=ax)

    zone_counts = df_skud['ZONE_ID'].value_counts()
    total_s = len(df_skud)
    max_c = zone_counts.max() if not zone_counts.empty else 1
    cmap = mcolors.LinearSegmentedColormap.from_list('HIF', ['#ffffff', HIF_RED])

    for name, b in ZONE_BOUNDARIES.items():
        count = zone_counts.get(name, 0)
        pct = (count / total_s * 100) if total_s > 0 else 0
        
        # Farvelæg zonen baseret på hyppighed
        rect = Rectangle((b["x_min"], b["y_min"]), b["x_max"] - b["x_min"], b["y_max"] - b["y_min"], 
                          facecolor=cmap(count/max_c), alpha=0.4, edgecolor='black', linestyle='--', linewidth=0.5)
        ax.add_patch(rect)
        
        if count > 0:
            x_t = b["x_min"] + (b["x_max"]-b["x_min"])/2
            # Justering for Zone 8 så teksten ikke overlapper midterlinjen
            y_t = b["y_min"] + (b["y_max"]-b["y_min"])/2 if name != "Zone 8" else 55
            
            ax.text(x_t, y_t + 0.8, f"{count} ({pct:.0f}%)", ha='center', fontweight='bold', fontsize=6)
            if name in top_players:
                ax.text(x_t, y_t - 1.2, top_players[name], ha='center', fontsize=5, fontweight='black', color='#333333')

    # Overskrift og total
    titel = f"HIF AFSLUTNINGER: {valgt_navn.upper() if valgt_id else 'ALLE KAMPE'}"
    ax.text(50, 107, titel, ha='center', fontsize=8, fontweight='black')
    ax.text(50, 104.5, f"TOTAL: {total_s}", ha='center', color=HIF_RED, fontsize=10, fontweight='bold')

    ax.set_ylim(40, 110)
    st.pyplot(fig)
