# tools/hifanalyse/varmekort.py
import matplotlib.colors as colors
import matplotlib.pyplot as plt
from mplsoccer import Pitch
import numpy as np
import pandas as pd
import streamlit as st

# Importér fra jeres mapping og SQL-lag
from data.sql.zone_heatmaps import hent_team_zone_passes
from data.utils.team_mapping import COMPETITIONS, SEASONS


def vis_side():
    st.markdown("### ⚽ Pasningszoner (3x4 Gitter) - Holdoversigt")
    st.markdown(
        "Visualisering af afleveringsfordeling fordelt på et 3x4 banegitter i "
        "forhold til liga-gennemsnittet."
    )

    # --- 1. SESSION / FILTER KONTROL ---
    col1, col2 = st.columns(2)
    with col1:
        selected_season = st.selectbox(
            "Vælg Sæson:", list(SEASONS.keys()), index=0
        )
    with col2:
        selected_comp = st.selectbox(
            "Vælg Turnering:", list(SEASONS[selected_season].keys()), index=0
        )

    # Hent den korrekte Tournament Calendar UUID ud fra mappingen
    calendar_uuid = SEASONS[selected_season][selected_comp]

    st.info(f"Henter data for {selected_comp} ({selected_season})...")

    # --- 2. HENT DATA FRA SNOWFLAKE ---
    conn = st.session_state.get("snowflake_conn") or st.connection("snowflake")
    df_zones = hent_team_zone_passes(conn, calendar_uuid)

    if df_zones.empty:
        st.warning(
            "Ingen data fundet for denne turnering/sæson. Tjek om kampe er spillet "
            "og om UUID'en er korrekt."
        )
        return

    teams = df_zones["TEAM_NAME"].tolist()
    if not teams:
        st.warning("Ingen hold tilgængelige i resultatsættet.")
        return

    # --- 3. OPSÆTNING AF BANEN OG GITTERET (Opta 0-100 skala) ---
    pitch = Pitch(pitch_type="opta", line_zorder=2, line_color="black")
    fig, axs = pitch.grid(
        ncols=4,
        nrows=3,
        figheight=12,
        grid_width=0.88,
        left=0.025,
        endnote_height=0.03,
        endnote_space=0,
        axis=False,
        title_space=0.02,
        title_height=0.06,
        grid_height=0.8,
    )

    # --- 4. BYG ZONESTATISTIK FRA SQL DATA ---
    hist_dict = {}

    for _, row in df_zones.iterrows():
        team_name = row["TEAM_NAME"]

        # 3 rækker (Y: 0-33.3, 33.3-66.6, 66.6-100) og 4 kolonner (X: 0-25, 25-50, 50-75, 75-100)
        grid_matrix = np.zeros((3, 4))
        for y_idx, y_val in enumerate([1, 2, 3]):
            for x_idx, x_val in enumerate([1, 2, 3, 4]):
                col_name = f"ZONE_{x_val}_{y_val}"
                grid_matrix[y_idx, x_idx] = row.get(col_name, 0)

        hist_dict[team_name] = grid_matrix

    active_teams = [t for t in teams if t in hist_dict]
    if not active_teams:
        st.warning("Ingen matchende hold fundet til visualisering.")
        return

    # Beregner gennemsnit pr. zone på tværs af alle hold
    all_stats = list(hist_dict.values())
    avg_hist = np.mean(np.array(all_stats), axis=0) if all_stats else np.zeros((3, 4))

    # Trækker gennemsnittet fra for at vise afvigelse over/under snit
    for team in active_teams:
        hist_dict[team] = hist_dict[team] - avg_hist

    # Forbereder farveskala (colormap)
    vmax = max([np.amax(v) for v in hist_dict.values()]) if hist_dict else 1
    vmin = min([np.amin(v) for v in hist_dict.values()]) if hist_dict else -1
    if vmax == vmin:
        vmax = vmin + 1

    divnorm = colors.TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)
    cmap = plt.get_cmap("coolwarm")

    # X- og Y-grænser for de 12 zoner i Opta (X: 0, 25, 50, 75, 100 | Y: 0, 33.33, 66.66, 100)
    x_bins = [0, 25, 50, 75, 100]
    y_bins = [0, 33.33, 66.66, 100]

    # --- 5. PLOTTING AF HVERT HOLD / AXE ---
    plot_teams = active_teams[:12]

    for team, ax in zip(plot_teams, axs["pitch"].flat):
        ax.text(
            50,
            -8,
            team,
            ha="center",
            va="center",
            fontsize=11,
            fontweight="bold",
        )
        
        # Tegn 3x4 gitteret som rektangler med værdier
        matrix = hist_dict[team]
        for i in range(3):      # Y-akse rækker (0 til 2)
            for j in range(4):  # X-akse kolonner (0 til 3)
                val = matrix[i, j]
                # Normaliser værdien til colormap (0 til 1)
                norm_val = divnorm(val)
                color = cmap(norm_val)
                
                xmin, xmax = x_bins[j], x_bins[j+1]
                ymin, ymax = y_bins[i], y_bins[i+1]
                
                ax.fill_between(
                    [xmin, xmax], 
                    [ymin, ymin], 
                    [ymax, ymax], 
                    color=color, 
                    edgecolor="grey", 
                    linewidth=0.5
                )
                
                # Valgfrit: Skriv selve afvigelsen ind i zonen hvis det ønskes, ellers klarer farven det
                ax.text(
                    (xmin + xmax) / 2,
                    (ymin + ymax) / 2,
                    f"{val:.0f}" if abs(val) >= 1 else "",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="black" if abs(val) < (vmax * 0.6) else "white",
                    fontweight="bold"
                )

        # Tilføj banelinjer ovenpå
        pitch.draw(ax=ax)

    # Skjul ubrugte subplots hvis der er færre end 12 hold
    for ax in axs["pitch"].flat[len(plot_teams) :]:
        ax.set_visible(False)

    # Tilføj farveskala (legend/colorbar)
    ax_cbar = fig.add_axes((0.92, 0.093, 0.02, 0.77))
    cbar = plt.colorbar(
        plt.cm.ScalarMappable(norm=divnorm, cmap="coolwarm"), cax=ax_cbar
    )
    cbar.ax.tick_params(labelsize=10)
    ax_cbar.yaxis.set_ticks_position("left")

    # Tilføj titel i toppen
    if "title" in axs:
        axs["title"].text(
            0.5,
            0.5,
            f"Pasningszoner pr. hold - Afvigelse fra liga-snit ({selected_comp})"
            f" - {selected_season}",
            ha="center",
            va="center",
            fontsize=14,
            fontweight="bold",
        )

    st.pyplot(fig)
    plt.close(fig)

    with st.expander("Se rå data for zonerne"):
        st.dataframe(df_zones)


if __name__ == "__main__":
    vis_side()
