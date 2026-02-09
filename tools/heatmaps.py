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

    # 2. Layout konfiguration (Hvidovre altid først)
    hold_ids = sorted(df_p['TEAM_WYID'].unique(), key=lambda x: x != HIF_ID)
    rows = int(np.ceil(len(hold_ids) / cols_slider))

    # --- MATCHING GRID STYLE ---
    # Vi bruger constrained_layout=True og en lav rækkehøjde (3.0) 
    # for at fjerne "gabet" ved de halve baner.
    fig, axes = plt.subplots(
        rows, cols_slider,
        figsize=(15, rows * 3.0), 
        facecolor=BG_WHITE,
        constrained_layout=True
    )
    
    axes_flat = np.atleast_1d(axes).flatten()

    # Pitch setup (half=True bibeholdes)
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

        # Hent holdnavn
        if hold_map and tid in hold_map:
            navn = str(hold_map[tid]).upper()
        else:
            navn = "HVIDOVRE IF" if tid == HIF_ID else f"ID: {tid}"

        # TITEL-STIL FRA BILLEDE 2:
        # Navn øverst, antal skud lige under i parentes.
        ax.set_title(f"{navn}\n({len(hold_df)} afslutninger)",
                     fontsize=12, fontweight='bold', pad=8)

        # Heatmap (KDE) - Samme indstillinger som dit heatmap-ark
        if len(hold_df) > 5:
            sns.kdeplot(
                x=hold_df['LOCATIONY'], y=hold_df['LOCATIONX'], ax=ax,
                fill=True, thresh=0.02, levels=40, 
                cmap='YlOrRd', alpha=0.8, zorder=1
            )

    # Skjul overskydende baner
    for j in range(i + 1, len(axes_flat)):
        axes_flat[j].axis('off')

    st.pyplot(fig, use_container_width=True)
