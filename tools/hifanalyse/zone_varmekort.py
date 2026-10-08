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
    # Bruger pitch_type='opta', da SQL-aggregeringen bruger 0-100 for X og Y
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
    
    # Definér bin-kanter for 3x4 gitteret på 0-100 skala
    x_edges = np.array([0, 25, 50, 75, 100])
    y_edges = np.array([0, 33.33, 66.66, 100])

    for _, row in df_zones.iterrows():
        team_name = row["TEAM_NAME"]

        grid_matrix = np.zeros((3, 4))
        for y in [1, 2, 3]:
            for x in [1, 2, 3, 4]:
                col_name = f"ZONE_{x}_{y}"
                grid_matrix[y - 1, x - 1] = row.get(col_name, 0)

        # Inkluder x_edge og y_edge, som pitch.heatmap() kræver
        hist_dict[team_name] = {
            "statistic": grid_matrix,
            "x_edge": x_edges,
            "y_edge": y_edges
        }

    active_teams = [t for t in teams if t in hist_dict]
    if not active_teams:
        st.warning("Ingen matchende hold fundet til visualisering.")
        return

    # Beregner gennemsnit pr. zone på tværs af alle hold
    all_stats = [v["statistic"] for k, v in hist_dict.items()]
    avg_hist = np.mean(np.array(all_stats), axis=0) if all_stats else np.zeros((3, 4))

    # Trækker gennemsnittet fra for at vise afvigelse over/under snit
    for team in active_teams:
        hist_dict[team]["statistic"] = hist_dict[team]["statistic"] - avg_hist

    # Forbereder farveskala (colormap)
    vmax = max([np.amax(v["statistic"]) for v in hist_dict.values()]) if hist_dict else 1
    vmin = min([np.amin(v["statistic"]) for v in hist_dict.values()]) if hist_dict else -1
    if vmax == vmin:
        vmax = vmin + 1

    divnorm = colors.TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)

    # --- 5. PLOTTING AF HVERT HOLD / AXE ---
    plot_teams = active_teams[:12]

    for team, ax in zip(plot_teams, axs["pitch"].flat):
        ax.text(
            50,  # Midten af banen på Opta-skalaen (0-100)
            -8,
            team,
            ha="center",
            va="center",
            fontsize=11,
            fontweight="bold",
        )
        pitch.heatmap(
            hist_dict[team], ax=ax, cmap="coolwarm", norm=divnorm, edgecolor="grey"
        )

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
