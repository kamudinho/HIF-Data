import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import VerticalPitch
import numpy as np

def vis_side(df_events, cols_slider, hold_map=None):
    HIF_ID = 38331
    BG_WHITE = '#ffffff'

    # 1. Filtrering
    mask = df_events['PRIMARYTYPE'].astype(str).str.contains('shot', case=False, na=False)
    df_p = df_events[mask].copy()

    if df_p.empty:
        st.error("Ingen afslutningsdata fundet.")
        return

    # 2. Layout konfiguration
    hold_ids = sorted(df_p['TEAM_WYID'].unique(), key=lambda x: x != HIF_ID)
    rows = int(np.ceil(len(hold_ids) / cols_slider))

    # --- ULTRA KOMPAKT LAYOUT ---
    # Vi sætter højden lavere (rows * 4) for at presse dem sammen vertikalt
    fig, axes = plt.subplots(
        rows, cols_slider,
        figsize=(15, rows * 4.5), 
        facecolor=BG_WHITE
    )

    # Vi fjerner næsten al luft. hspace=0.1 er nøglen til at få dem tæt.
    fig.subplots_adjust(left=0.01, right=0.99, bottom=0.01, top=0.94, wspace=0.02, hspace=0.10)
    axes_flat = np.atleast_1d(axes).flatten()

    pitch = VerticalPitch(
        pitch_type='custom', pitch_length=100, pitch_width=100,
        line_color='#2b2b2b', line_zorder=2, linewidth=1,
        half=True  # Viser kun angrebs-halvdelen for at spare plads
    )

    # 3. Tegne-loop
    for i, tid in enumerate(hold_ids):
        ax = axes_flat[i]
        hold_df = df_p[df_p['TEAM_WYID'] == tid].copy().dropna(subset=['LOCATIONX', 'LOCATIONY'])
        pitch.draw(ax=ax)

        # Navngivning
        navn = str(hold_map.get(tid, f"ID: {tid}")).upper()
        
        # Vi rykker titlen helt ned til banen med pad=2
        ax.set_title(navn, fontsize=12, fontweight='bold', pad=2, color='#1a1a1a')
        
        # Lille tekst-info inde på banen for at spare vertikal plads
        ax.text(50, 52, f"{len(hold_df)} SKUD", color='gray', 
                fontsize=8, ha='center', fontweight='bold', alpha=0.5)

        if len(hold_df) > 3:
            sns.kdeplot(
                x=hold_df['LOCATIONY'], y=hold_df['LOCATIONX'], ax=ax,
                fill=True, thresh=0.05, levels=35, 
                cmap='YlOrRd', alpha=0.8, zorder=1
            )

    # Skjul overskydende plots
    for j in range(i + 1, len(axes_flat)):
        axes_flat[j].axis('off')

    st.pyplot(fig, use_container_width=True)
