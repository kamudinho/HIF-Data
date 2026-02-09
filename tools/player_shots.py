import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

def vis_side(df_events, df_kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#df003b'
    BG_WHITE = '#ffffff'

    # 1. RENS KOLONNER (Sikrer at vi rammer MINUTE præcis)
    df_events.columns = df_events.columns.str.strip().str.upper()

    # 2. SPILLER DROPDOWN I SIDEBAR
    hif_events = df_events[df_events['TEAM_WYID'] == HIF_ID].copy()
    
    # Vi bruger 'PLAYER_NAME' (som vi mergede i hovedfilen) eller falder tilbage på ID
    p_col = 'PLAYER_NAME' if 'PLAYER_NAME' in hif_events.columns else 'PLAYER_WYID'
    spiller_navne = sorted(hif_events[p_col].dropna().unique())
    
    with st.sidebar:
        st.markdown("---")
        st.markdown('<p class="sidebar-header">Spillerfokus</p>', unsafe_allow_html=True)
        valgt_spiller = st.selectbox("Vælg spiller", options=["Alle Spillere"] + spiller_navne)

    # 3. FILTRERING
    df_filtered = hif_events if valgt_spiller == "Alle Spillere" else hif_events[hif_events[p_col] == valgt_spiller]

    # Find skud via PRIMARYTYPE (f.eks. 'shot' eller 'shot_on_target')
    mask = df_filtered['PRIMARYTYPE'].astype(str).str.contains('shot', case=False, na=False)
    df_s = df_filtered[mask].copy()
    
    if df_s.empty:
        st.warning(f"Ingen skud fundet for {valgt_spiller}")
        return

    # Marker om det er mål
    df_s['IS_GOAL'] = df_s['PRIMARYTYPE'].astype(str).str.contains('goal', case=False, na=False)

    # 4. STATS BEREGNING
    s_shots = len(df_s)
    s_goals = df_s['IS_GOAL'].sum()
    s_conv = f"{(s_goals / s_shots * 100):.1f}%" if s_shots > 0 else "0.0%"

    # 5. VISUALISERING (mplsoccer - VerticalPitch)
    fig, ax = plt.subplots(figsize=(10, 8), facecolor=BG_WHITE)
    pitch = VerticalPitch(pitch_type='custom', pitch_length=105, pitch_width=68,
                          half=True, pitch_color='white', line_color='#1a1a1a', linewidth=1.5)
    pitch.draw(ax=ax)

    # Overskrift og Stats i toppen af banen
    ax.text(34, 114, valgt_spiller.upper(), fontsize=12, color='#333333', ha='center', fontweight='black')
    
    stats_config = [(20, s_shots, "SKUD"), (34, s_goals, "MÅL"), (48, s_conv, "KONV.")]
    for x, val, label in stats_config:
        ax.text(x, 110, str(val), color=HIF_RED, fontsize=14, fontweight='bold', ha='center')
        ax.text(x, 108.3, label, fontsize=7, color='gray', ha='center', fontweight='bold')

    # Scatter points (Wyscout 0-100 koordinater til mplsoccer 0-68/105)
    # Ikke-mål
    no_goal = df_s[~df_s['IS_GOAL']]
    ax.scatter(no_goal['LOCATIONY'] * 0.68, no_goal['LOCATIONX'] * 1.05,
               s=130, color='#4a5568', alpha=0.3, edgecolors='white', linewidth=0.6, zorder=3)
    
    # Mål
    goals = df_s[df_s['IS_GOAL']]
    ax.scatter(goals['LOCATIONY'] * 0.68, goals['LOCATIONX'] * 1.05,
               s=320, color=HIF_RED, alpha=0.9, edgecolors='white', linewidth=1.3, zorder=4)

    ax.set_ylim(60, 116)  
    ax.axis('off')
    st.pyplot(fig)

    # 6. DETALJER (I stedet for hover-boks)
    st.markdown("### 📋 Skuddetaljer")
    
    vis_df = df_s.copy()
    vis_df['MODSTANDER'] = vis_df['OPPONENTTEAM_WYID'].map(hold_map).fillna("Ukendt")
    vis_df['RESULTAT'] = vis_df['IS_GOAL'].map({True: '⚽ MÅL', False: '❌ Skud'})
    
    # Viser "vs. xx" og "Min: xx" som du bad om, i tabelform
    st.dataframe(
        vis_df[['MINUTE', 'MODSTANDER', 'RESULTAT']].sort_values('MINUTE', ascending=False),
        hide_index=True,
        use_container_width=True
    )
