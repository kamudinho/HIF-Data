import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch
from matplotlib.lines import Line2D

def vis_side(df_events, df_kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#df003b'
    BG_WHITE = '#ffffff'

    # --- 1. BYG DROPDOWN ---
    opp_ids = sorted([int(tid) for tid in df_events['OPPONENTTEAM_WYID'].unique() if tid != HIF_ID])
    dropdown_options = [("Alle Kampe", None)]
    for mid in opp_ids:
        navn = hold_map.get(mid, f"Ukendt Hold (ID: {mid})")
        dropdown_options.append((navn, mid))

    valgt_navn, valgt_id = st.selectbox("Vælg modstander", options=dropdown_options, format_func=lambda x: x[0])

    # --- 2. FILTRERING ---
    if valgt_id is not None:
        df_events_filtered = df_events[(df_events['TEAM_WYID'] == HIF_ID) & (df_events['OPPONENTTEAM_WYID'] == valgt_id)]
        relevante_match_ids = df_events_filtered['MATCH_WYID'].unique()
        stats_df = df_kamp[(df_kamp['TEAM_WYID'] == HIF_ID) & (df_kamp['MATCH_WYID'].isin(relevante_match_ids))].copy()
        titel_tekst = f"HIF mod {valgt_navn}"
    else:
        df_events_filtered = df_events[df_events['TEAM_WYID'] == HIF_ID]
        stats_df = df_kamp[df_kamp['TEAM_WYID'] == HIF_ID].copy()
        titel_tekst = "HIF: Alle Kampe"

    # --- 3. BEREGN STATS (MED xG FIX) ---
    if not stats_df.empty:
        s_shots = int(pd.to_numeric(stats_df['SHOTS'], errors='coerce').fillna(0).sum())
        s_goals = int(pd.to_numeric(stats_df['GOALS'], errors='coerce').fillna(0).sum())
        # Vi tjekker om xG er pr. kamp eller total. Her summerer vi dem. 
        # Hvis 1438 virker vildt, kan det være fordi kolonnen indeholder mærkelige værdier.
        raw_xg = pd.to_numeric(stats_df['XG'], errors='coerce').fillna(0).sum()
        s_xg = f"{raw_xg:.2f}"
        s_conv = f"{(s_goals / s_shots * 100):.1f}%" if s_shots > 0 else "0.0%"
    else:
        s_shots, s_goals, s_xg, s_conv = 0, 0, "0.00", "0.0%"

    # --- 4. VISUALISERING ---
    # Vi bruger constrained_layout=False for at have fuld manuel kontrol over placering
    fig, ax = plt.subplots(figsize=(12, 8), facecolor=BG_WHITE)
    pitch = VerticalPitch(pitch_type='custom', pitch_length=105, pitch_width=68,
                          half=True, pitch_color='white', line_color='#1a1a1a', linewidth=1.5)
    pitch.draw(ax=ax)

    # A. TITEL (Helt øverst - y=122)
    ax.text(34, 122, titel_tekst.upper(), fontsize=18, color='#1a1a1a', ha='center', fontweight='black')

    # B. STATS BLOCK (y=114)
    # Vi rykker dem lidt ind mod midten så de ikke rammer kanten
    header_data = [(str(s_shots), "Skud"), (str(s_goals), "Mål"), (s_conv, "Konvertering"), (s_xg, "xG Total")]
    x_pos = [12, 27, 42, 57] 
    for i, (val, label) in enumerate(header_data):
        ax.text(x_pos[i], 114, val, color=HIF_RED, fontsize=22, fontweight='bold', ha='center')
        ax.text(x_pos[i], 110, label, fontsize=11, color='gray', ha='center', fontweight='bold')

    # C. LEGENDS (y=107 - Lige over banen i venstre side)
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label='Mål', markerfacecolor=HIF_RED, markersize=10),
        Line2D([0], [0], marker='o', color='w', label='Afslutning', markerfacecolor='#4a5568', markersize=8, alpha=0.4)
    ]
    ax.legend(handles=legend_elements, loc='lower left', bbox_to_anchor=(0.02, 0.88), 
              transform=ax.transAxes, frameon=False, fontsize=10, ncol=2, columnspacing=1.5)

    # D. TEGN SKUD
    shot_mask = df_events_filtered['PRIMARYTYPE'].astype(str).str.contains('shot', case=False, na=False)
    hif_shots = df_events_filtered[shot_mask].copy()
    
    if not hif_shots.empty:
        # x og y skal ofte vendes/skaleres afhængig af datakilde (Wyscout bruger 0-100)
        # Her bruger vi dine koordinater fra tidligere
        hif_shots['IS_GOAL'] = hif_shots.apply(lambda r: 'goal' in str(r.get('PRIMARYTYPE', '')).lower(), axis=1)
        
        # Misses
        ax.scatter(hif_shots[~hif_shots['IS_GOAL']]['LOCATIONY'] * 0.68, 
                   hif_shots[~hif_shots['IS_GOAL']]['LOCATIONX'] * 1.05,
                   s=150, color='#4a5568', alpha=0.3, edgecolors='white', linewidth=0.5, zorder=3)
        # Goals
        ax.scatter(hif_shots[hif_shots['IS_GOAL']]['LOCATIONY'] * 0.68, 
                   hif_shots[hif_shots['IS_GOAL']]['LOCATIONX'] * 1.05,
                   s=350, color=HIF_RED, alpha=0.9, edgecolors='white', linewidth=1, zorder=4)

    # Juster y-aksen så vi kan se alt tekst
    ax.set_ylim(60, 125) 
    ax.axis('off')

    st.pyplot(fig, use_container_width=True)
