import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import VerticalPitch
import numpy as np

def vis_side(df_events, cols_slider, hold_map=None):
    HIF_ID = 38331
    BG_WHITE = '#ffffff'

    # 1. Filtrering af skud/afslutninger
    mask = df_events['PRIMARYTYPE'].astype(str).str.contains('shot', case=False, na=False)
    df_p = df_events[mask].copy()

    if df_p.empty:
        st.error("Ingen afslutningsdata fundet.")
        return

    # 2. Layout konfiguration (HIF altid først)
    hold_ids = sorted(df_p['TEAM_WYID'].unique(), key=lambda x: x != HIF_ID)
    rows = int(np.ceil(len(hold_ids) / cols_slider))

    # --- KOMPAKT LAYOUT ---
    # Vi bruger en mindre figsize-faktor for at tvinge dem sammen
    fig, axes = plt.subplots(
        rows, cols_slider,
        figsize=(18, rows * 6), 
        facecolor=BG_WHITE
    )

    # Vi minimerer hspace og wspace for at få dem til at ligge tæt
    fig.subplots_adjust(left=0.02, right=0.98, bottom=0.05, top=0.92, wspace=0.02, hspace=0.15)
    axes_flat = np.atleast_1d(axes).flatten()

    # Pitch setup der matcher heatmaps.py stilen
    pitch = VerticalPitch(
        pitch_type='custom', pitch_length=100, pitch_width=100,
        line_color='#2b2b2b', line_zorder=2, linewidth=1, 
        half=True # Viser kun den angribende halvdel for skud (valgfrit)
    )

    # 3. Tegne-loop
    for i, tid in enumerate(hold_ids):
        ax = axes_flat[i]
        hold_df = df_p[df_p['TEAM_WYID'] == tid].copy().dropna(subset=['LOCATIONX', 'LOCATIONY'])
        pitch.draw(ax=ax)

        # Navngivning
        if hold_map and tid in hold_map:
            navn = str(hold_map[tid]).upper()
        else:
            navn = "HVIDOVRE IF" if tid == HIF_ID else f"HOLD ID: {tid}"

        # Titel tæt på banen
        ax.set_title(f"{navn}", fontsize=16, fontweight='bold', pad=8)
        ax.text(50, 55, f"{len(hold_df)} AFSLUTNINGER", color='gray', 
                fontsize=10, ha='center', fontweight='bold', alpha=0.6)

        # Heatmap (KDE)
        if len(hold_df) > 3:
            sns.kdeplot(
                x=hold_df['LOCATIONY'], y=hold_df['LOCATIONX'], ax=ax,
                fill=True, thresh=0.05, levels=40, 
                cmap='YlOrRd', alpha=0.8, zorder=1
            )

    # Skjul overskydende plots
    for j in range(i + 1, len(axes_flat)):
        axes_flat[j].axis('off')

    st.pyplot(fig, use_container_width=True)
