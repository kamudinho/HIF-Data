import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from mplsoccer import VerticalPitch
import streamlit as st
import matplotlib.colors as mcolors

# --- STRAMME ZONE DEFINITIONER (Rykket op for at undgå overlap) ---
ZONE_BOUNDARIES = {
    # Selve det lille felt (6-yard box)
    "Zone 1": {"y_min": 94.5, "y_max": 100.0, "x_min": 36.8, "x_max": 63.2},

    # Midten af det store felt
    "Zone 2": {"y_min": 89.0, "y_max": 94.5, "x_min": 36.8, "x_max": 63.2},

    # Kanten af det store felt - Nu rykket til 84.0 for at ramme feltkanten
    "Zone 3": {"y_min": 84.0, "y_max": 89.0, "x_min": 36.8, "x_max": 63.2},

    # Siderne af det lille felt
    "Zone 4A": {"y_min": 94.5, "y_max": 100.0, "x_min": 63.2, "x_max": 81.0},
    "Zone 4B": {"y_min": 94.5, "y_max": 100.0, "x_min": 19.0, "x_max": 36.8},

    # Siderne af det store felt - Nu rykket til 84.0
    "Zone 5A": {"y_min": 84.0, "y_max": 94.5, "x_min": 63.2, "x_max": 81.0},
    "Zone 5B": {"y_min": 84.0, "y_max": 94.5, "x_min": 19.0, "x_max": 36.8},

    # Yderzonerne - Nu rykket til 84.0
    "Zone 6A": {"y_min": 84.0, "y_max": 100.0, "x_min": 81.0, "x_max": 100.0},
    "Zone 6B": {"y_min": 84.0, "y_max": 100.0, "x_min": 0.0, "x_max": 19.0},

    # Zone 7 starter nu præcis ved 84.0 (hvor feltet slutter)
    "Zone 7": {"y_min": 70.0, "y_max": 84.0, "x_min": 30.0, "x_max": 70.0},
    "Zone 7B": {"y_min": 70.0, "y_max": 84.0, "x_min": 0.0, "x_max": 30.0},
    "Zone 7A": {"y_min": 70.0, "y_max": 84.0, "x_min": 70.0, "x_max": 100.0},

    # Resten af banen
    "Zone 8": {"y_min": 0.0, "y_max": 70.0, "x_min": 0.0, "x_max": 100.0}
}


def vis_side(df, kamp=None, hold_map=None):
    # ... (Samme mapping og filter som før) ...

    # VIGTIGT: I Wyscout er LOCATIONX længden og LOCATIONY er bredden.
    # Vi mapper dem så de passer til find_zone(bredde, længde)
    df_skud['ZONE_ID'] = df_skud.apply(
        lambda row: find_zone(row['LOCATIONY'], row['LOCATIONX']), axis=1
    )

    # ... (Beregn zone_stats som før) ...
    draw_pitch_with_stats(zone_stats, total_skud)


def draw_pitch_with_stats(zone_stats, total_skud):
    # pitch_type='wyscout' forventer (længde, bredde)
    pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='grey', pad_bottom=60)
    fig, ax = pitch.draw(figsize=(10, 8))

    # ... (Samme Rectangle tegning som før) ...
    # Rectangle((x_min, y_min), bredde, højde)
    for name, b in ZONE_BOUNDARIES.items():
        # ...
        rect = Rectangle((b["x_min"], b["y_min"]),
                         b["x_max"] - b["x_min"],
                         b["y_max"] - b["y_min"],
                         edgecolor='black', linestyle='--', facecolor=cmap(color_val), alpha=0.5)
        ax.add_patch(rect)
        # ...

def find_zone(x, y):
    for zone, b in ZONE_BOUNDARIES.items():
        if b["x_min"] <= x <= b["x_max"] and b["y_min"] <= y <= b["y_max"]:
            return zone
    return "Udenfor"


def vis_side(df, kamp=None, hold_map=None):
    st.title("🎯 Målzoner & Effektivitet")

    # Rens kolonner
    df.columns = [str(c).strip().upper() for c in df.columns]

    # --- 1. HOLD MAPPING ---
    if hold_map:
        hold_map_str = {str(k): v for k, v in hold_map.items()}
        df['HOLD_NAVN'] = df['TEAM_WYID'].astype(str).map(hold_map_str).fillna(df['TEAM_WYID'].astype(str))
    else:
        df['HOLD_NAVN'] = df['TEAM_WYID'].astype(str)

    # --- 2. FILTRE ---
    col1, col2 = st.columns(2)
    with col1:
        hold_liste = ["Alle"] + sorted(df['HOLD_NAVN'].unique().tolist())
        valgt_hold = st.selectbox("Vælg Hold:", hold_liste)
    with col2:
        valgt_type = st.selectbox("Vis type:", ["Alle Skud", "Mål"])

    # --- 3. FILTRERING ---
    mask = df['PRIMARYTYPE'].str.contains('shot', case=False, na=False)

    if valgt_hold != "Alle":
        mask &= (df['HOLD_NAVN'] == valgt_hold)

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

    # --- 4. TEGN BANE ---
    draw_pitch_with_stats(zone_stats, total_skud)


def draw_pitch_with_stats(zone_stats, total_skud):
    pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='grey', pad_bottom=60)
    fig, ax = pitch.draw(figsize=(10, 8))

    max_count = zone_stats['Antal'].max() if not zone_stats.empty else 1
    cmap = mcolors.LinearSegmentedColormap.from_list('HIF', ['#ffffff', '#df003b'])

    for name, b in ZONE_BOUNDARIES.items():
        count = zone_stats.loc[name, 'Antal'] if name in zone_stats.index else 0
        percent = zone_stats.loc[name, 'Procent'] if name in zone_stats.index else 0

        color_val = count / max_count if max_count > 0 else 0

        # Tegn zonen
        rect = Rectangle((b["x_min"], b["y_min"]), b["x_max"] - b["x_min"],
                         b["y_max"] - b["y_min"], edgecolor='black',
                         linestyle='--', facecolor=cmap(color_val), alpha=0.5)
        ax.add_patch(rect)

        # Tekst: Viser Antal og %
        if count > 0:
            x_text = b["x_min"] + (b["x_max"] - b["x_min"]) / 2
            y_text = b["y_min"] + (b["y_max"] - b["y_min"]) / 2

            # Formatering af tekst: Antal øverst, procent under
            label = f"{int(count)}\n({percent:.1f}%)"
            ax.text(x_text, y_text, label, ha='center', va='center',
                    fontweight='bold', fontsize=10, color='black')

    st.pyplot(fig)
    st.write(f"**Total antal afslutninger i valgte filter:** {int(total_skud)}")