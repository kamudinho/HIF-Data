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
    st.markdown(f"**Sæson:** {SEASONNAME} | **Hold ID:** {TEAM_WYID}")
    st.markdown("Visualisering af aktioner fordelt på et fuldt banegitter vha. `pitch.grid`.")

    # Eksempel på hold/kategorier (tilpasset til gitteret på 6x4 = 24 felter)
    teams = [f"Hold {i+1}" for i in range(24)]

    # --- 1. OPSETNING AF BANEN OG GITTERET ---
    pitch = Pitch(line_zorder=2, line_color='black')
    fig, axs = pitch.grid(ncols=6, nrows=4, figheight=14,
                          grid_width=0.88, left=0.025,
                          endnote_height=0.03, endnote_space=0,
                          axis=False,
                          title_space=0.02, title_height=0.06, grid_height=0.8)

    # --- 2. SIMULERER / BEREGNER DATA ---
    np.random.seed(42)
    hist_dict = {}
    for team in teams:
        # Simulerer x- og y-koordinater for holdets aktioner
        x_vals = np.random.uniform(0, 120, 150)
        y_vals = np.random.uniform(0, 80, 150)
        
        # Antal aktioner i hver zone (bins)
        bin_statistic = pitch.bin_statistic(x_vals, y_vals, statistic='count', bins=(6, 5), normalize=False)
        
        # Normaliser pr. kamp (f.eks. divideret med antal kampe, her sat til 10)
        no_games = 10
        bin_statistic["statistic"] = bin_statistic["statistic"] / no_games
        hist_dict[team] = bin_statistic

    # Beregner gennemsnit pr. zone på tværs af alle hold
    avg_hist = np.mean(np.array([v["statistic"] for k, v in hist_dict.items()]), axis=0)

    # Trækker gennemsnittet fra for at vise performance over/under gennemsnit
    for team in teams:
        hist_dict[team]["statistic"] = hist_dict[team]["statistic"] - avg_hist

    # Forbereder farveskala (colormap)
    vmax = max([np.amax(v["statistic"]) for k, v in hist_dict.items()])
    vmin = min([np.amin(v["statistic"]) for k, v in hist_dict.items()])
    divnorm = colors.TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)

    # --- 3. PLOTTING AF HVERT HOLD / AXE ---
    for team, ax in zip(teams, axs['pitch'].flat):
        # Sæt holdnavn over plottet
        ax.text(60, -8, team, ha='center', va='center', fontsize=12, fontweight='bold')
        # Plot varmekortet
        pitch.heatmap(hist_dict[team], ax=ax, cmap='coolwarm', norm=divnorm, edgecolor='grey')

    # Tilføj farveskala (legend/colorbar)
    ax_cbar = fig.add_axes((0.92, 0.093, 0.02, 0.77))
    cbar = plt.colorbar(plt.cm.ScalarMappable(norm=divnorm, cmap='coolwarm'), cax=ax_cbar)
    cbar.ax.tick_params(labelsize=10)
    ax_cbar.yaxis.set_ticks_position('left')

    # Tilføj titel i toppen
    if 'title' in axs:
        axs['title'].text(0.5, 0.5, 'Aktioner pr. kamp - performance over zone average', ha='center', va='center', fontsize=18, fontweight='bold')

    st.pyplot(fig)
    plt.close(fig)

if __name__ == "__main__":
    vis_side()
