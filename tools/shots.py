import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

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
        stats_df = df_kamp[(df_kamp['TEAM_WYID'] == HIF_ID) & (df_kamp['MATCH_WYID'].isin(df_events_filtered['MATCH_WYID'].unique()))].copy()
        titel_tekst = f"HIF vs. {valgt_navn}"
    else:
        df_events_filtered = df_events[df_events['TEAM_WYID'] == HIF_ID]
        stats_df = df_kamp[df_kamp['TEAM_WYID'] == HIF_ID].copy()
        titel_tekst = "HIF vs. Alle"

    # --- 3. STATS BEREGNING (xG Robusthed) ---
    if not stats_df.empty:
        s_shots = int(pd.to_numeric(stats_df['SHOTS'], errors='coerce').fillna(0).sum())
        s_goals = int(pd.to_numeric(stats_df['GOALS'], errors='coerce').fillna(0).sum())
        
        # Vi tvinger xG til at være et fornuftigt tal (max 10 pr. kamp som sikkerhed)
        raw_xg = pd.to_numeric(stats_df['XG'], errors='coerce').fillna(0).sum()
        if raw_xg > 100: raw_xg = raw_xg / 100 
        s_xg = f"{raw_xg:.2f}"
        s_conv = f"{(s_goals / s_shots * 100):.1f}%" if s_shots > 0 else "0.0%"
    else:
        s_shots, s_goals, s_xg, s_conv = 0, 0, "0.00", "0.0%"

    # --- 4. VISUALISERING ---
    fig, ax = plt.subplots(figsize=(10, 5.5), facecolor=BG_WHITE)
    pitch = VerticalPitch(pitch_type='custom', pitch_length=105, pitch_width=68,
                          half=True, pitch_color='white', line_color='#1a1a1a', linewidth=1.2)
    pitch.draw(ax=ax)

    # TITEL (Helt i top)
    ax.text(34, 118, titel_tekst.upper(), fontsize=10, color='#333333', ha='center', fontweight='black')

    # STATS RÆKKE (Mindre skrift, god bredde)
    # y=112 for tallene, y=109 for teksten
    ax.text(12, 112, str(s_shots), color=HIF_RED, fontsize=14, fontweight='bold', ha='center')
    ax.text(12, 109, "SKUD", fontsize=4, color='gray', ha='center', fontweight='bold')
    
    ax.text(27, 112, str(s_goals), color=HIF_RED, fontsize=14, fontweight='bold', ha='center')
    ax.text(27, 109, "MÅL", fontsize=4, color='gray', ha='center', fontweight='bold')
    
    ax.text(42, 112, s_conv, color=HIF_RED, fontsize=14, fontweight='bold', ha='center')
    ax.text(42, 109, "KONV.", fontsize=4, color='gray', ha='center', fontweight='bold')
    
    ax.text(57, 112, s_xg, color=HIF_RED, fontsize=14, fontweight='bold', ha='center')
    ax.text(57, 109, "xG TOTAL", fontsize=4, color='gray', ha='center', fontweight='bold')

    # LEGENDS (Placeret præcis i venstre side over kridtstregen)
    # y=106 rammer lige mellem teksten ovenfor og selve banen
    ax.scatter(3, 106, s=50, color=HIF_RED, edgecolors='white', zorder=5)
    ax.text(5, 106, "Mål", fontsize=7, va='center', fontweight='bold')
    
    ax.scatter(11, 106, s=35, color='#4a5568', alpha=0.4, edgecolors='white', zorder=5)
    ax.text(13, 106, "Afslutning", fontsize=7, va='center', fontweight='bold')

    # TEGN SKUD
    shot_mask = df_events_filtered['PRIMARYTYPE'].astype(str).str.contains('shot', case=False, na=False)
    hif_shots = df_events_filtered[shot_mask].copy()
    if not hif_shots.empty:
        hif_shots['IS_GOAL'] = hif_shots.apply(lambda r: 'goal' in str(r.get('PRIMARYTYPE', '')).lower(), axis=1)
        
        # Misses
        ax.scatter(hif_shots[~hif_shots['IS_GOAL']]['LOCATIONY'] * 0.68, hif_shots[~hif_shots['IS_GOAL']]['LOCATIONX'] * 1.05,
                   s=100, color='#4a5568', alpha=0.3, edgecolors='white', linewidth=0.5, zorder=3)
        # Goals
        ax.scatter(hif_shots[hif_shots['IS_GOAL']]['LOCATIONY'] * 0.68, hif_shots[hif_shots['IS_GOAL']]['LOCATIONX'] * 1.05,
                   s=250, color=HIF_RED, alpha=0.9, edgecolors='white', linewidth=0.8, zorder=4)

    # AFGRÆNSNING (Sikrer at vi ser det hele)
    ax.set_ylim(60, 122) 
    ax.set_xlim(-2, 70)
    ax.axis('off')

    st.pyplot(fig)
