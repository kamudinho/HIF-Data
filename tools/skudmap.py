import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import VerticalPitch
import numpy as np

def vis_side(df_events, cols_slider, hold_map=None):
    HIF_ID = 38331
    BG_WHITE = '#ffffff'

    # 1. Filtrering af skud
    mask = df_events['PRIMARYTYPE'].astype(str).str.contains('shot', case=False, na=False)
    df_p = df_events[mask].copy()

    if df_p.empty:
        st.error("Ingen afslutningsdata fundet.")
        return

    # 2. Layout konfiguration
    hold_ids = sorted(df_p['TEAM_WYID'].unique(), key=lambda x: x != HIF_ID)
    rows = int(np.ceil(len(hold_ids) / cols_slider))

    # --- ULTRA KOMPAKT GRID ---
    # Vi sætter højden meget lavt (3.0 per række), da vi kun bruger en halv bane.
    # Dette fjerner det hvide tomrum mellem rækkerne.
    fig, axes = plt.subplots(
        rows, cols_slider,
        figsize=(16, rows * 3.0), 
        facecolor=BG_WHITE,
        constrained_layout=True  # Fjerner automatisk overflødig luft
    )
    
    axes_flat = np.atleast_1d(axes).flatten()

    # Pitch setup: half=True giver det fokus du ønsker
    pitch = VerticalPitch(
        pitch_type='custom', pitch_length=100, pitch_width=100,
        line_color='#2b2b2b', line_zorder=2, linewidth=1,
        half=True
    )

    # 3. Tegne-loop
    for i, tid in enumerate(hold_ids):
        ax = axes_flat[i]
        hold_df = df_p[df_p['TEAM_WYID'] == tid].copy().dropna(subset=['LOCATIONX', 'LOCATIONY'])
        pitch.draw(ax=ax)

        # Hent holdnavn og antal
        navn = str(hold_map.get(tid, f"ID: {tid}")).upper()
        antal = len(hold_df)
        
        # TITEL-STRUKTUR FRA BILLEDE 2:
        # Vi placerer antallet lige under holdnavnet i selve titlen
        ax.set_title(f"{navn}\n({antal} SKUD)", 
                     fontsize=10, 
                     fontweight='bold', 
                     pad=2) # Meget lille pad for at holde det tæt på banen

        # Heatmap (KDE)
        if antal > 3:
            sns.kdeplot(
                x=hold_df['LOCATIONY'], y=hold_df['LOCATIONX'], ax=ax,
                fill=True, thresh=0.05, levels=40, 
                cmap='YlOrRd', alpha=0.8, zorder=1
            )

    # Skjul tomme felter hvis antal hold ikke går op i kolonner
    for j in range(i + 1, len(axes_flat)):
        axes_flat[j].axis('off')

    st.pyplot(fig, use_container_width=True)
