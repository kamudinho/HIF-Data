import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import VerticalPitch
import numpy as np

@st.cache_data(show_spinner="Heatmaps præsenteres...")
def generate_cached_heatmaps(df_p, cols_slider, hold_ids_tuple, hold_map):
    BG_WHITE = '#ffffff'
    rows = int(np.ceil(len(hold_ids_tuple) / cols_slider))
    
    fig, axes = plt.subplots(
        rows, cols_slider,
        figsize=(15, rows * 4), 
        facecolor=BG_WHITE
    )

    fig.subplots_adjust(left=0.05, right=0.95, bottom=0.02, top=0.92, wspace=0.05, hspace=0.25)
    axes_flat = np.atleast_1d(axes).flatten()

    # Bruger VerticalPitch for konsistens
    pitch = VerticalPitch(
        pitch_type='custom', pitch_length=100, pitch_width=100,
        line_color='#1a1a1a', line_zorder=2, linewidth=0.5
    )

    for i, tid in enumerate(hold_ids_tuple):
        ax = axes_flat[i]
        hold_df_full = df_p[df_p['TEAM_WYID'] == tid].copy().dropna(subset=['LOCATIONX', 'LOCATIONY'])
        total_passes = len(hold_df_full)
        
        # Speed boost
        hold_df_draw = hold_df_full.sample(n=min(total_passes, 2000), random_state=42)

        pitch.draw(ax=ax)
        navn = str(hold_map.get(tid, f"HOLD ID: {tid}")).upper()
        ax.set_title(f"{navn}\n({total_passes:,} PASSES)".replace(',', '.'), 
                     fontsize=10, fontweight='bold', pad=8)

        if total_passes > 10:
            sns.kdeplot(
                x=hold_df_draw['LOCATIONY'], y=hold_df_draw['LOCATIONX'], ax=ax,
                fill=True, thresh=0.05, levels=20, 
                cmap='YlOrRd', alpha=0.8, zorder=1,
                clip=((0, 100), (0, 100)), # HOLDER DET INDEN FOR LINJERNE
                linewidths=0
            )

    for j in range(i + 1, len(axes_flat)):
        axes_flat[j].axis('off')

    return fig
