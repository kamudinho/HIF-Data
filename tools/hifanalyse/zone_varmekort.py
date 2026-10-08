# tools/hifanalyse/varmekort.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from mplsoccer import Pitch

SEASONNAME = "2026/2027"
TEAM_WYID = 7490

def vis_side():
    st.title("Heatmaps (Zoner)")
    st.markdown(f"**Sæson:** {SEASONNAME} | **Hold ID:** {TEAM_WYID}")
    st.markdown("Visualisering af Hvidovre IFs aktioner opdelt i deciderede banenzoner på en fodboldbane.")

    # --- 1. DATA FOR ZONER (Opdelt i et 3x4 gitter over banens længde/bredde) ---
    zone_data = [
        {"zone": "Forsvar Venstre", "x_min": 0, "x_max": 26.25, "y_min": 0, "y_max": 22.6, "aktioner": 120},
        {"zone": "Forsvar Central", "x_min": 0, "x_max": 26.25, "y_min": 22.6, "y_max": 45.4, "aktioner": 210},
        {"zone": "Forsvar Højre", "x_min": 0, "x_max": 26.25, "y_min": 45.4, "y_max": 68, "aktioner": 95},
        
        {"zone": "Midt-Forsvar Venstre", "x_min": 26.25, "x_max": 52.5, "y_min": 0, "y_max": 22.6, "aktioner": 180},
        {"zone": "Midt-Forsvar Central", "x_min": 26.25, "x_max": 52.5, "y_min": 22.6, "y_max": 45.4, "aktioner": 310},
        {"zone": "Midt-Forsvar Højre", "x_min": 26.25, "x_max": 52.5, "y_min": 45.4, "y_max": 68, "aktioner": 165},
        
        {"zone": "Midt-Angreb Venstre", "x_min": 52.5, "x_max": 78.75, "y_min": 0, "y_max": 22.6, "aktioner": 240},
        {"zone": "Midt-Angreb Central", "x_min": 52.5, "x_max": 78.75, "y_min": 22.6, "y_max": 45.4, "aktioner": 390},
        {"zone": "Midt-Angreb Højre", "x_min": 52.5, "x_max": 78.75, "y_min": 45.4, "y_max": 68, "aktioner": 220},
        
        {"zone": "Angreb Venstre", "x_min": 78.75, "x_max": 105, "y_min": 0, "y_max": 22.6, "aktioner": 150},
        {"zone": "Modstanderens Felt", "x_min": 78.75, "x_max": 105, "y_min": 22.6, "y_max": 45.4, "aktioner": 340},
        {"zone": "Angreb Højre", "x_min": 78.75, "x_max": 105, "y_min": 45.4, "y_max": 68, "aktioner": 130},
    ]

    df_zoner = pd.DataFrame(zone_data)

    col1, col2 = st.columns([2, 1])

    with col1:
        # --- 2. TEGN BANEN MED MPLSOCCER ---
        fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
        
        # Opret en 'stats'-bane (vandret) uden forældede argumenter
        pitch = Pitch(pitch_type='custom', pitch_length=105, pitch_width=68, line_color='black')
        pitch.draw(ax=ax)

        # Sæt hvid baggrund på figuren/aksen
        ax.set_facecolor('white')
        fig.patch.set_facecolor('white')

        # Tilføj farvede zoner baseret på antal aktioner
        cmap = plt.cm.Reds
        norm = plt.Normalize(vmin=df_zoner["aktioner"].min(), vmax=df_zoner["aktioner"].max())

        for _, row in df_zoner.iterrows():
            rect_color = cmap(norm(row["aktioner"]))
            width = row["x_max"] - row["x_min"]
            height = row["y_max"] - row["y_min"]
            
            rect = Rectangle((row["x_min"], row["y_min"]), width, height, 
                             linewidth=1, edgecolor='gray', facecolor=rect_color, alpha=0.7)
            ax.add_patch(rect)
            
            # Skriv værdien i midten af feltet
            ax.text(row["x_min"] + width / 2, row["y_min"] + height / 2, 
                    f"{int(row['aktioner'])}", 
                    color="black" if row["aktioner"] < 250 else "white", 
                    weight="bold", fontsize=9, ha="center", va="center")

        ax.set_title("Hvidovre IF - Aktionsintensitet fordelt på banenzoner", fontsize=12, fontweight="bold", pad=15)
        
        # Farveskala bar ved siden af
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.04)
        cbar.set_label("Antal aktioner")

        st.pyplot(fig)
        plt.close(fig)

    with col2:
        st.subheader("Top Zoner")
        top_zoner = df_zoner.sort_values(by="aktioner", ascending=False).head(5)
        st.dataframe(top_zoner[["zone", "aktioner"]].rename(columns={"zone": "Zone", "aktioner": "Aktioner"}), use_container_width=True)

if __name__ == "__main__":
    vis_side()
