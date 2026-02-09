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

    # --- JUSTERING AF FIGURSTØRRELSE ---
    # Vi sætter højden endnu lavere for at fjerne den hvide luft mellem rækkerne
    fig, axes = plt.subplots(
        rows, cols_slider,
        figsize=(16, rows * 3.5), 
        facecolor=BG_WHITE
    )

    # hspace=0.05 fjerner næsten al luft vertikalt. 
    # top=0.96 sikrer, at den øverste rækkes titler ikke bliver klippet.
    fig.subplots_adjust(left=0.01, right=0.99, bottom=0.01, top=0.96, wspace=0.02, hspace=0.05)
    axes_flat = np.atleast_1d(axes).flatten()

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

        navn = str(hold_map.get(tid, f"ID: {tid}")).upper()
        
        # Vi bruger en mindre font og rykker titlen tættere på med pad=1
        ax.set_title(navn, fontsize=11, fontweight='black', pad=1, y=0.98)
        
        # Placerer skud-antallet højere op på banen for at undgå overlap med linjen
        ax.text(50, 65, f"{len(hold_df)} SKUD", color='gray', 
                fontsize=8, ha='center', fontweight='bold', alpha=0.6)

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
