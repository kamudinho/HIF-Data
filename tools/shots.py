import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch
from matplotlib.lines import Line2D

def vis_side(df_events, df_kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#df003b'
    BG_WHITE = '#ffffff'

    # --- 1. DROPDOWN ---
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

    # --- 3. BEREGN STATS ---
    if not stats_df.empty:
        s_shots = int(pd.to_numeric(stats_df['SHOTS'], errors='coerce').fillna(0).sum())
        s_goals = int(pd.to_numeric(stats_df['GOALS'], errors='coerce').fillna(0).sum())
        
        # xG FIX: Sikrer korrekt decimalformat
        raw_xg = pd.to_numeric(stats_df['XG'], errors='coerce').fillna(0).sum()
        if raw_xg > 100: raw_xg = raw_xg / 100 
        s_xg = f"{raw_xg:.2f}"
        
        s_conv = f"{(s_goals / s_shots * 100):.1f}%" if s_shots > 0 else "0.0%"
    else:
        s_shots, s_goals, s_xg, s_conv = 0, 0, "0.00", "0.0%"

    # --- 4. VISUALISERING ---
    # Beholder en god bredde (12) men reducerer højden (7) for at undgå scroll
    fig, ax = plt.subplots(figsize=(12, 7), facecolor=BG_WHITE)
    pitch = VerticalPitch(pitch_type='custom', pitch_length=105, pitch_width=68,
                          half=True, pitch_color='white', line_color='#1a1a1a', linewidth=1.2)
    pitch.draw(ax=ax)

    # TITEL (Kompakt størrelse)
    ax.text(34, 118, titel_tekst.upper(), fontsize=15, color='#1a1a1a', ha='center', fontweight='black')

    # STATS BLOCK (Mindre tekst, men bevarer bredden fra x_pos)
    # Tallene er nu 20 (før 28), Labels er 9 (før 12)
    header_data = [(str(s_shots), "Skud"), (str(s_goals), "Mål"), (s_conv, "Konvertering"), (s_xg, "xG Total")]
    x_pos = [12, 27, 42, 57] 
    for i, (val, label) in enumerate(header_data):
        ax.text(x_pos[i], 111, val, color=HIF_RED, fontsize=20, fontweight='bold', ha='center')
        ax.text(x_pos[i], 108, label, fontsize=9, color='gray', ha='center', fontweight='bold')

    # LEGENDS (Placeret præcis i venstre side mellem stats og banelinje)
    ax.scatter(3, 103.5, s=70, color=HIF_RED, edgecolors='white', zorder=5)
    ax.text(5, 103.5, "Mål", fontsize=10, va='center', fontweight='bold')
    
    ax.scatter(11, 103.5, s=50, color='#4a5568', alpha=0.4, edgecolors='white', zorder=5)
    ax.text(13, 103.5, "Afslutning", fontsize=10, va='center', fontweight='bold')

    # TEGN SKUD
    shot_mask = df_events_filtered['PRIMARYTYPE'].astype(str).str.contains('shot', case=False, na=False)
    hif_shots = df_events_filtered[shot_mask].copy()
    if not hif_shots.empty:
        hif_shots['IS_GOAL'] = hif_shots.apply(lambda r: 'goal' in str(r.get('PRIMARYTYPE', '')).lower(), axis=1)
        
        # Misses (Kompakt størrelse)
        ax.scatter(hif_shots[~hif_shots['IS_GOAL']]['LOCATIONY'] * 0.68, hif_shots[~hif_shots['IS_GOAL']]['LOCATIONX'] * 1.05,
                   s=110, color='#4a5568', alpha=0.3, edgecolors='white', linewidth=0.5, zorder=3)
        # Goals (Tydelige men ikke gigantiske)
        ax.scatter(hif_shots[hif_shots['IS_GOAL']]['LOCATIONY'] * 0.68, hif_shots[hif_shots['IS_GOAL']]['LOCATIONX'] * 1.05,
                   s=260, color=HIF_RED, alpha=0.9, edgecolors='white', linewidth=0.8, zorder=4)

    # Grænser for at styre luft i toppen
    ax.set_ylim(60, 122) 
    ax.set_xlim(-2, 70)
    ax.axis('off')

    st.pyplot(fig, use_container_width=True)
