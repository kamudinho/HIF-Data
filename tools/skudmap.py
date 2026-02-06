import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import VerticalPitch
import numpy as np


# Tilføj hold_map som parameter her!
def vis_side(df_events, cols_slider, hold_map=None):
    HIF_ID = 38331
    HIF_RED = '#df003b'
    BG_WHITE = '#ffffff'

    # 1. Filtrering af afleveringer
    mask = df_events['PRIMARYTYPE'].astype(str).str.contains('shot', case=False, na=False)
    df_p = df_events[mask].copy()

    if df_p.empty:
        st.error("Ingen afleveringsdata fundet.")
        return

    # 2. Layout konfiguration
    # Vi sorterer så Hvidovre (38331) altid kommer først
    hold_ids = sorted(df_p['TEAM_WYID'].unique(), key=lambda x: x != HIF_ID)

    # Beregn rækker baseret på antal hold og slideren
    rows = int(np.ceil(len(hold_ids) / cols_slider))

    fig, axes = plt.subplots(
        rows, cols_slider,
        figsize=(25, rows * 8),  # Øget højde en smule for bedre læsbarhed
        facecolor=BG_WHITE
    )

    fig.subplots_adjust(left=0.05, right=0.95, bottom=0.05, top=0.90, wspace=0.1, hspace=0.3)
    axes_flat = np.atleast_1d(axes).flatten()

    pitch = VerticalPitch(pitch_type='custom', pitch_length=100, pitch_width=100,
                          line_color='#1a1a1a', line_zorder=2, linewidth=1.5)

    # 3. Tegne-loop
    for i, tid in enumerate(hold_ids):
        ax = axes_flat[i]
        hold_df = df_p[df_p['TEAM_WYID'] == tid].copy().dropna(subset=['LOCATIONX', 'LOCATIONY'])
        pitch.draw(ax=ax)

        # DYNAMISK NAVNGIVNING FRA EXCEL
        # Vi tjekker i hold_map (ordbogen fra dit Hold-ark)
        if hold_map and tid in hold_map:
            navn = str(hold_map[tid]).upper()
        else:
            # Fallback hvis ID ikke findes i Excel endnu
            navn = f"HVIDOVRE IF" if tid == HIF_ID else f"UKENDT HOLD (ID: {tid})"

        ax.set_title(f"{navn}\n({len(hold_df)} afleveringer)",
                     fontsize=18, fontweight='bold', pad=10)

        # Tegn selve heatmappet
        if len(hold_df) > 5:
            sns.kdeplot(x=hold_df['LOCATIONY'], y=hold_df['LOCATIONX'], ax=ax,
                        fill=True, thresh=0.02, levels=40, cmap='YlOrRd', alpha=0.8, zorder=1)

    # Skjul overskydende hvide felter
    for j in range(i + 1, len(axes_flat)):
        axes_flat[j].axis('off')

    st.pyplot(fig, use_container_width=True)