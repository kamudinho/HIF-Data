import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import VerticalPitch
import numpy as np

def vis_side(df_events, cols_slider, hold_map=None):
    HIF_ID = 38331
    BG_WHITE = '#ffffff'

    # 1. Filtrering af skud (afslutninger)
    mask = df_events['PRIMARYTYPE'].astype(str).str.contains('shot', case=False, na=False)
    df_p = df_events[mask].copy()

    if df_p.empty:
        st.error("Ingen afslutningsdata fundet.")
        return

    # 2. Layout konfiguration
    hold_ids = sorted(df_p['TEAM_WYID'].unique(), key=lambda x: x != HIF_ID)
    rows = int(np.ceil(len(hold_ids) / cols_slider))

    # --- OPTIMERING AF AFSTAND ---
    # Vi sætter en fast højde pr. række (f.eks. 5 i stedet for 8) for at fjerne tom luft
    fig, axes = plt.subplots(
        rows, cols_slider,
        figsize=(20, rows * 5.5), 
        facecolor=BG_WHITE
    )

    # wspace er bredden mellem figurer, hspace er højden. Begge er sat lavt her.
    fig.subplots_adjust(left=0.02, right=0.98, bottom=0.02, top=0.92, wspace=0.05, hspace=0.15)
    axes_flat = np.atleast_1d(axes).flatten()

    pitch = VerticalPitch(pitch_type='custom', pitch_length=100, pitch_width=100,
                          line_color='#1a1a1a', line_zorder=2, linewidth=1.2)

    # 3. Tegne-loop
    for i, tid in enumerate(hold_ids):
        ax = axes_flat[i]
        hold_df = df_p[df_p['TEAM_WYID'] == tid].copy().dropna(subset=['LOCATIONX', 'LOCATIONY'])
        pitch.draw(ax=ax)

        if hold_map and tid in hold_map:
            navn = str(hold_map[tid]).upper()
        else:
            navn = "HVIDOVRE IF" if tid == HIF_ID else f"HOLD ID: {tid}"

        # Mindre pad og fontstørrelse for at spare plads
        ax.set_title(f"{navn} ({len(hold_df)} afslutninger)",
                     fontsize=14, fontweight='bold', pad=5)

        if len(hold_df) > 5:
            sns.kdeplot(x=hold_df['LOCATIONY'], y=hold_df['LOCATIONX'], ax=ax,
                        fill=True, thresh=0.05, levels=30, cmap='YlOrRd', alpha=0.7, zorder=1)

    # Skjul overskydende hvide felter
    for j in range(i + 1, len(axes_flat)):
        axes_flat[j].axis('off')

    st.pyplot(fig, use_container_width=True)
