import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

def vis_side(df_events, df_kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#df003b'
    BG_WHITE = '#ffffff'

    # 1. RENS KOLONNER (Aggressiv rensning for at finde MINUTE)
    df_events.columns = [str(c).strip().upper() for c in df_events.columns]
    
    # 2. SPILLER DROPDOWN I SIDEBAR
    hif_events = df_events[df_events['TEAM_WYID'] == HIF_ID].copy()
    p_col = 'PLAYER_NAME' if 'PLAYER_NAME' in hif_events.columns else 'PLAYER_WYID'
    spiller_navne = sorted(hif_events[p_col].dropna().unique())
    
    with st.sidebar:
        st.markdown("---")
        st.markdown('<p style="font-weight:bold; color:#df003b;">SPILLERANALYSE</p>', unsafe_allow_html=True)
        valgt_spiller = st.selectbox("Vælg spiller", options=["Alle Spillere"] + spiller_navne)

    # 3. FILTRERING
    df_filtered = hif_events if valgt_spiller == "Alle Spillere" else hif_events[hif_events[p_col] == valgt_spiller]
    mask = df_filtered['PRIMARYTYPE'].astype(str).str.contains('shot', case=False, na=False)
    df_s = df_filtered[mask].copy()
    
    if df_s.empty:
        st.warning(f"Ingen skud fundet for {valgt_spiller}")
        return

    df_s['IS_GOAL'] = df_s['PRIMARYTYPE'].astype(str).str.contains('goal', case=False, na=False)

    # 4. TEGN DEN ORDENTLIGE BANE (mplsoccer)
    # 
    fig, ax = plt.subplots(figsize=(10, 8), facecolor=BG_WHITE)
    pitch = VerticalPitch(pitch_type='custom', pitch_length=105, pitch_width=68,
                          half=True, pitch_color='white', line_color='#1a1a1a', linewidth=2)
    pitch.draw(ax=ax)

    # Overskrift og Stats på banen (HIF Stil)
    ax.text(34, 115, valgt_spiller.upper(), fontsize=14, color='#333333', ha='center', fontweight='black')
    
    # Tegn skud (Wyscout 0-100 koordinater til 0-68/105)
    # Ikke-mål (Grå)
    no_goal = df_s[~df_s['IS_GOAL']]
    ax.scatter(no_goal['LOCATIONY'] * 0.68, no_goal['LOCATIONX'] * 1.05,
               s=150, color='#4a5568', alpha=0.4, edgecolors='white', linewidth=0.8, zorder=3)
    
    # Mål (HIF Rød)
    goals = df_s[df_s['IS_GOAL']]
    ax.scatter(goals['LOCATIONY'] * 0.68, goals['LOCATIONX'] * 1.05,
               s=350, color=HIF_RED, alpha=0.9, edgecolors='white', linewidth=1.5, zorder=4)

    ax.set_ylim(60, 118)  
    ax.axis('off')
    st.pyplot(fig)

    # 5. SKUD-INSPEKTØR (Boksen du bad om, men som interaktiv liste)
    st.markdown("### 🔍 Skuddetaljer")
    
    # Vi henter data sikkert uden KeyError
    for _, row in df_s.sort_values('MINUTE', ascending=False).iterrows():
        modstander = hold_map.get(row['OPPONENTTEAM_WYID'], "Ukendt")
        minut = row['MINUTE']
        type_skud = "⚽ MÅL" if row['IS_GOAL'] else "❌ Afslutning"
        
        # Dette fungerer som de bokse du ville have, bare stakket pænt
        with st.expander(f"{type_skud} vs. {modstander} (Min: {minut})"):
            st.write(f"**Tidspunkt:** {minut}. minut")
            st.write(f"**Modstander:** {modstander}")
            st.write(f"**Type:** {row['PRIMARYTYPE']}")
