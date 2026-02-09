import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

def vis_side(df_events, df_kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#df003b'
    BG_WHITE = '#ffffff'

    # Sørg for store bogstaver i kolonner for at undgå KeyError
    df_events.columns = [c.upper() for c in df_events.columns]

    # --- 1. SPILLER DROPDOWN I SIDEBAR ---
    hif_events = df_events[df_events['TEAM_WYID'] == HIF_ID].copy()
    
    # Find spillernavne (bruger NAVN eller PLAYER_NAME alt efter hvad der er merget)
    p_col = 'PLAYER_NAME' if 'PLAYER_NAME' in hif_events.columns else 'NAVN'
    spiller_navne = sorted(hif_events[p_col].dropna().unique())
    
    with st.sidebar:
        st.markdown("---")
        st.markdown('<p class="sidebar-header">Spillerfokus</p>', unsafe_allow_html=True)
        valgt_spiller = st.selectbox("Vælg spiller", options=["Alle Spillere"] + spiller_navne)

    # --- 2. FILTRERING ---
    if valgt_spiller != "Alle Spillere":
        df_filtered = hif_events[hif_events[p_col] == valgt_spiller]
        titel_tekst = valgt_spiller
    else:
        df_filtered = hif_events
        titel_tekst = "HIF - Alle Spillere"

    # Find skud
    shot_mask = df_filtered['PRIMARYTYPE'].astype(str).str.contains('shot', case=False, na=False)
    spiller_shots = df_filtered[shot_mask].copy()
    
    # Marker mål
    spiller_shots['IS_GOAL'] = spiller_shots.apply(
        lambda r: 'goal' in str(r.get('PRIMARYTYPE', '')).lower(), axis=1
    )

    # --- 3. STATS BEREGNING ---
    s_shots = len(spiller_shots)
    s_goals = spiller_shots['IS_GOAL'].sum()
    
    # Sikker håndtering af xG (KeyError fix)
    if 'XG' in spiller_shots.columns:
        raw_xg = pd.to_numeric(spiller_shots['XG'], errors='coerce').fillna(0).sum()
        if raw_xg > s_shots: raw_xg = raw_xg / 100 
        s_xg = f"{raw_xg:.2f}"
    else:
        s_xg = "0.00"
            
    s_conv = f"{(s_goals / s_shots * 100):.1f}%" if s_shots > 0 else "0.0%"

    # --- 4. VISUALISERING (Tilbage til mplsoccer) ---
    fig, ax = plt.subplots(figsize=(10, 7), facecolor=BG_WHITE)
    pitch = VerticalPitch(pitch_type='custom', pitch_length=105, pitch_width=68,
                          half=True, pitch_color='white', line_color='#1a1a1a', linewidth=1.2)
    pitch.draw(ax=ax)

    # TITEL & STATS (Samme stil som dit hold-skudkort)
    ax.text(34, 114, titel_tekst.upper(), fontsize=10, color='#333333', ha='center', fontweight='black')

    x_pos = [15, 28, 41, 54]
    vals = [str(s_shots), str(s_goals), s_conv, s_xg]
    labs = ["SKUD", "MÅL", "KONV.", "xG"]
    for i in range(4):
        ax.text(x_pos[i], 110, vals[i], color=HIF_RED, fontsize=12, fontweight='bold', ha='center')
        ax.text(x_pos[i], 108.3, labs[i], fontsize=7, color='gray', ha='center', fontweight='bold')

    # TEGN SKUD
    if not spiller_shots.empty:
        # Almindelige skud
        no_goal = spiller_shots[~spiller_shots['IS_GOAL']]
        ax.scatter(no_goal['LOCATIONY'] * 0.68, no_goal['LOCATIONX'] * 1.05,
                   s=100, color='#4a5568', alpha=0.3, edgecolors='white', linewidth=0.5, zorder=3)
        
        # Mål
        goals = spiller_shots[spiller_shots['IS_GOAL']]
        ax.scatter(goals['LOCATIONY'] * 0.68, goals['LOCATIONX'] * 1.05,
                   s=250, color=HIF_RED, alpha=0.9, edgecolors='white', linewidth=1.0, zorder=4)

    ax.set_ylim(60, 116)  
    ax.set_xlim(-2, 70)
    ax.axis('off')

    # Vis kortet
    st.pyplot(fig)

    # --- 5. INTERAKTIV TABEL (Erstatning for Hoverlabels) ---
    if not spiller_shots.empty:
        st.markdown("---")
        st.markdown("### Detaljer for valgte skud")
        
        # Vi laver en pæn tabel med hvem de spillede imod og xG
        vis_df = spiller_shots.copy()
        vis_df['Modstander'] = vis_df['OPPONENTTEAM_WYID'].map(hold_map)
        vis_df['Resultat'] = vis_df['IS_GOAL'].map({True: '⚽ MÅL', False: '❌ Skud'})
        
        # Vis kun relevante kolonner
        st.dataframe(
            vis_df[['Modstander', 'Resultat', 'XG']].sort_index(ascending=False),
            hide_index=True,
            use_container_width=True
        )
