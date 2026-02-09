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

    # --- MATCHING FIGSIZE ---
    # Vi bruger præcis samme bredde (15), men da banen er halv, 
    # skal række-multiplikatoren være lavere (2.5) for at undgå at strække skriften.
    fig, axes = plt.subplots(
        rows, cols_slider,
        figsize=(15, rows * 2.5), 
        facecolor=BG_WHITE
    )

    # Vi bruger subplots_adjust i stedet for constrained_layout for at få 100% kontrol
    fig.subplots_adjust(left=0.05, right=0.95, bottom=0.05, top=0.90, wspace=0.1, hspace=0.4)
    axes_flat = np.atleast_1d(axes).flatten()

    pitch = VerticalPitch(
        pitch_type='custom', pitch_length=100, pitch_width=100,
        line_color='#1a1a1a', line_zorder=2, linewidth=0.5,
        half=True
    )

    # 3. Tegne-loop
    for i, tid in enumerate(hold_ids):
        ax = axes_flat[i]
        hold_df = df_p[df_p['TEAM_WYID'] == tid].copy().dropna(subset=['LOCATIONX', 'LOCATIONY'])
        pitch.draw(ax=ax)

        if hold_map and tid in hold_map:
            navn = str(hold_map[tid]).upper()
        else:
            navn = "HVIDOVRE IF" if tid == HIF_ID else f"ID: {tid}"

        # Her bruger vi præcis samme fontsize=12 og pad=10 som i din heatmap-kode
        ax.set_title(f"{navn}\n({len(hold_df)} afslutninger)",
                     fontsize=12, fontweight='bold', pad=10)

        if len(hold_df) > 5:
            sns.kdeplot(
                x=hold_df['LOCATIONY'], y=hold_df['LOCATIONX'], ax=ax,
                fill=True, thresh=0.02, levels=40, 
                cmap='YlOrRd', alpha=0.8, zorder=1
            )

    for j in range(i + 1, len(axes_flat)):
        axes_flat[j].axis('off')

    st.pyplot(fig, use_container_width=True)
