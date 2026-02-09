import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

def vis_side(df_events, df_kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#df003b'
    BG_WHITE = '#ffffff'

    # 1. SIKKERHED: Tving store bogstaver og tjek kolonner
    df_events.columns = [str(c).upper().strip() for c in df_events.columns]
    
    # Tjek om vi overhovedet har de nødvendige kolonner, ellers opret dem som tomme
    if 'MINUTE' not in df_events.columns:
        df_events['MINUTE'] = "N/A"

    # 2. SPILLER DROPDOWN I SIDEBAR
    hif_events = df_events[df_events['TEAM_WYID'] == HIF_ID].copy()
    p_col = 'PLAYER_NAME' if 'PLAYER_NAME' in hif_events.columns else 'NAVN'
    
    if p_col not in hif_events.columns:
        st.error(f"Kunne ikke finde kolonnen '{p_col}' i data.")
        return

    spiller_navne = sorted(hif_events[p_col].dropna().unique())
    
    with st.sidebar:
        st.markdown("---")
        st.markdown('<p class="sidebar-header">Spillerfokus</p>', unsafe_allow_html=True)
        valgt_spiller = st.selectbox("Vælg spiller", options=["Alle Spillere"] + spiller_navne)

    # 3. FILTRERING
    if valgt_spiller != "Alle Spillere":
        df_filtered = hif_events[hif_events[p_col] == valgt_spiller].copy()
    else:
        df_filtered = hif_events.copy()

    # Find skud via PRIMARYTYPE
    mask = df_filtered['PRIMARYTYPE'].astype(str).str.contains('shot', case=False, na=False)
    df_s = df_filtered[mask].copy()
    
    if df_s.empty:
        st.warning(f"Ingen skud registreret for {valgt_spiller}")
        return

    # Marker mål
    df_s['IS_GOAL'] = df_s['PRIMARYTYPE'].astype(str).str.contains('goal', case=False, na=False)

    # 4. STATS BEREGNING
    s_shots = len(df_s)
    s_goals = df_s['IS_GOAL'].sum()
    s_conv = f"{(s_goals / s_shots * 100):.1f}%" if s_shots > 0 else "0.0%"

    # 5. VISUALISERING (Ægte mplsoccer)
    fig, ax = plt.subplots(figsize=(10, 8), facecolor=BG_WHITE)
    pitch = VerticalPitch(pitch_type='custom', pitch_length=105, pitch_width=68,
                          half=True, pitch_color='white', line_color='#1a1a1a', linewidth=1.2)
    pitch.draw(ax=ax)

    # Overskrift og Stats på selve billedet
    ax.text(34, 114, valgt_spiller.upper(), fontsize=12, color='#333333', ha='center', fontweight='black')
    
    # Stats række
    ax.text(20, 110, str(s_shots), color=HIF_RED, fontsize=14, fontweight='bold', ha='center')
    ax.text(20, 108.3, "SKUD", fontsize=7, color='gray', ha='center', fontweight='bold')
    
    ax.text(34, 110, str(s_goals), color=HIF_RED, fontsize=14, fontweight='bold', ha='center')
    ax.text(34, 108.3, "MÅL", fontsize=7, color='gray', ha='center', fontweight='bold')
    
    ax.text(48, 110, s_conv, color=HIF_RED, fontsize=14, fontweight='bold', ha='center')
    ax.text(48, 108.3, "KONV.", fontsize=7, color='gray', ha='center', fontweight='bold')

    # Tegn skud (Wyscout bruger 0-100, mplsoccer custom bruger 0-68/0-105)
    no_goal = df_s[~df_s['IS_GOAL']]
    ax.scatter(no_goal['LOCATIONY'] * 0.68, no_goal['LOCATIONX'] * 1.05,
               s=120, color='#4a5568', alpha=0.3, edgecolors='white', linewidth=0.5, zorder=3)
    
    goals = df_s[df_s['IS_GOAL']]
    ax.scatter(goals['LOCATIONY'] * 0.68, goals['LOCATIONX'] * 1.05,
               s=300, color=HIF_RED, alpha=0.9, edgecolors='white', linewidth=1.2, zorder=4)

    ax.set_ylim(60, 116)  
    ax.set_xlim(-2, 70)
    ax.axis('off')
    st.pyplot(fig)

    # 6. DETALJER (Dine hoverlabels som tabel)
    st.markdown("### 📋 Detaljer for afslutninger")
    
    # Forbered tabel-data
    vis_df = df_s.copy()
    vis_df['MODSTANDER'] = vis_df['OPPONENTTEAM_WYID'].map(hold_map).fillna("Ukendt")
    vis_df['RESULTAT'] = vis_df['IS_GOAL'].map({True: '⚽ MÅL', False: '❌ Skud'})
    
    # Vis tabel - sortér efter minut hvis muligt
    tabel_cols = ['MINUTE', 'MODSTANDER', 'RESULTAT']
    st.dataframe(
        vis_df[tabel_cols].sort_values('MINUTE', ascending=False),
        hide_index=True,
        use_container_width=True
    )
