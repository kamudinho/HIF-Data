import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch
from matplotlib.lines import Line2D

def vis_side(df_events, df_kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#df003b'
    BG_WHITE = '#ffffff'

    # --- 1. BYG DROPDOWN LISTE ---
    opp_ids = sorted([int(tid) for tid in df_events['OPPONENTTEAM_WYID'].unique() if tid != HIF_ID])

    dropdown_options = [("Alle Kampe", None)]
    for mid in opp_ids:
        navn = hold_map.get(mid, f"Ukendt Hold (ID: {mid})")
        dropdown_options.append((navn, mid))

    valgt_navn, valgt_id = st.selectbox(
        "Vælg modstander",
        options=dropdown_options,
        format_func=lambda x: x[0]
    )

    # --- 2. FILTRERING ---
    if valgt_id is not None:
        df_events_filtered = df_events[(df_events['TEAM_WYID'] == HIF_ID) &
                                       (df_events['OPPONENTTEAM_WYID'] == valgt_id)]
        relevante_match_ids = df_events_filtered['MATCH_WYID'].unique()
        stats_df = df_kamp[(df_kamp['TEAM_WYID'] == HIF_ID) &
                           (df_kamp['MATCH_WYID'].isin(relevante_match_ids))].copy()
        titel_tekst = f"HIF mod {valgt_navn}"
    else:
        df_events_filtered = df_events[df_events['TEAM_WYID'] == HIF_ID]
        stats_df = df_kamp[df_kamp['TEAM_WYID'] == HIF_ID].copy()
        titel_tekst = "HIF: Alle Kampe"

    # --- 3. BEREGN STATS ---
    if not stats_df.empty:
        s_shots = int(pd.to_numeric(stats_df['SHOTS'], errors='coerce').fillna(0).sum())
        s_goals = int(pd.to_numeric(stats_df['GOALS'], errors='coerce').fillna(0).sum())
        xg_values = pd.to_numeric(stats_df['XG'], errors='coerce').fillna(0)
        s_xg = f"{xg_values.sum():.2f}"
        s_conv = f"{(s_goals / s_shots * 100):.1f}%" if s_shots > 0 else "0.0%"
    else:
        s_shots, s_goals, s_xg, s_conv = 0, 0, "0.00", "0.0%"

    # --- 4. VISUALISERING ---
    # Figurstørrelse optimeret til dashboard (Bredere og mindre høj)
    fig, ax = plt.subplots(figsize=(12, 7), facecolor=BG_WHITE, constrained_layout=True)
    
    pitch = VerticalPitch(pitch_type='custom', pitch_length=105, pitch_width=68,
                          half=True, pitch_color='white', line_color='#1a1a1a', linewidth=1.5)
    pitch.draw(ax=ax)

    # TITEL (Modstander)
    ax.text(34, 118, titel_tekst.upper(), fontsize=14, color='#333333', ha='center', fontweight='black')

    # STATS BLOCK (Mindre og mere kompakt)
    header_data = [(s_xg, "xG Total"), (s_conv, "Konvertering"), (str(s_goals), "Mål"), (str(s_shots), "Skud")]
    x_pos = [10, 26, 42, 58] 
    for i, (val, label) in enumerate(header_data):
        ax.text(x_pos[i], 112, val, color=HIF_RED, fontsize=18, fontweight='bold', ha='center')
        ax.text(x_pos[i], 109, label, fontsize=9, color='gray', ha='center', fontweight='bold')

    # LEGENDS (Placeret i øverste højre hjørne under stats)
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label='Mål', markerfacecolor=HIF_RED, markersize=8),
        Line2D([0], [0], marker='o', color='w', label='Afslutning', markerfacecolor='#4a5568', markersize=6, alpha=0.4)
    ]
    ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(0.98, 1.08), 
              frameon=False, fontsize=8, ncol=1, labelspacing=0.2)

    # TEGN SKUD
    shot_mask = df_events_filtered['PRIMARYTYPE'].astype(str).str.contains('shot', case=False, na=False)
    hif_shots = df_events_filtered[shot_mask].copy()

    if not hif_shots.empty:
        hif_shots['IS_GOAL'] = hif_shots.apply(lambda r: 'goal' in str(r.get('PRIMARYTYPE', '')).lower(), axis=1)
        goals = hif_shots[hif_shots['IS_GOAL'] == True]
        misses = hif_shots[hif_shots['IS_GOAL'] == False]

        ax.scatter(misses['LOCATIONY'] * 0.68, misses['LOCATIONX'] * 1.05,
                   s=120, color='#4a5568', alpha=0.3, edgecolors='white', linewidth=0.5, zorder=3)
        ax.scatter(goals['LOCATIONY'] * 0.68, goals['LOCATIONX'] * 1.05,
                   s=280, color=HIF_RED, alpha=0.9, edgecolors='white', linewidth=1, zorder=4)

    # AFGRÆNSNING
    ax.set_ylim(60, 122) # Giver plads til tekst i toppen
    ax.axis('off')

    st.pyplot(fig)
