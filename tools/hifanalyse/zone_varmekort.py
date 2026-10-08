# tools/hifanalyse/varmekort.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from mplsoccer import Pitch

SEASONNAME = "2025/2026"
TEAM_WYID = 7490

def vis_side():
    st.title("🗺️ Varmekort & Zoner (Banniveau)")
    st.markdown(f"**Sæson:** {SEASONNAME} | **Hold ID:** {TEAM_WYID}")
    st.markdown("Visualisering af holdets aktioner opdelt i præcise banenzoner ved hjælp af `mplsoccer` bin-statistik.")

    # --- 1. SIMULERER ELLER HENTER DATA ---
    # Her simuleres X og Y koordinater (på en 0-100 skala som mplsoccer 'stats' eller standard bruger)
    np.random.seed(42)
    n_aktioner = 400
    df_aktioner = pd.DataFrame({
        "x": np.random.uniform(0, 100, n_aktioner),
        "y": np.random.uniform(0, 100, n_aktioner)
    })

    col1, col2 = st.columns([3, 1])

    with col1:
        # --- 2. OPSETNING AF BANEN OG BIN-STATISTIK ---
        fig, ax = plt.subplots(figsize=(9, 6), constrained_layout=True)
        
        # Initialiser banen
        pitch = Pitch(line_zorder=2, line_color='black', pitch_type='stats', turf_color='white')
        pitch.draw(ax=ax)

        # Beregn bin-statistik (f.eks. 6 kolonner og 4 rækker)
        bin_statistic = pitch.bin_statistic(
            df_aktioner["x"], 
            df_aktioner["y"], 
            statistic='count', 
            bins=(6, 4)
        )

        # Plot varmekortet baseret på zonerne
        pcm = pitch.heatmap(
            bin_statistic, 
            ax=ax, 
            cmap='coolwarm', 
            edgecolor='grey', 
            alpha=0.85
        )

        # Tilføj farveskala (colorbar)
        cbar = fig.colorbar(pcm, ax=ax, fraction=0.03, pad=0.04)
        cbar.set_label("Aktionsfrekvens pr. zone", fontsize=10)

        ax.set_title("Aktionsintensitet fordelt på banenzoner", fontsize=14, fontweight="bold", pad=15)

        st.pyplot(fig)
        plt.close(fig)

    with col2:
        st.subheader("Om Zonerne")
        st.info(
            "Dette kort opdele banen i et gitter vha. `mplsoccer`. "
            "Hver boks opsamler mængden af hændelser, hvilket giver et præcist "
            "og overskueligt overblik over banefordelingen ligesom i professionel fodboldanalyse."
        )

if __name__ == "__main__":
    vis_side()
