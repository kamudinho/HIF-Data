# tools/hifanalyse/varmekort.py
import matplotlib.colors as colors
import matplotlib.pyplot as plt
from mplsoccer import Pitch
import numpy as np
import pandas as pd
import streamlit as st
from data.data_load import _get_snowflake_conn

# Importér fra jeres mapping og SQL-lag
from data.sql.zone_heatmaps import hent_team_zone_passes
from data.utils.team_mapping import COMPETITIONS, SEASONS


def vis_side():
  st.markdown("### ⚽ Pasningszoner (3x4 Gitter) - Holdoversigt")
  st.markdown(
      "Visualisering af afleveringsfordeling fordelt på et 3x4 banegitter i"
      " forhold til liga-gennemsnittet."
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
  # Antager at din app stiller Snowflake-forbindelsen til rådighed via st.session_state eller lignende
  # (Tilpas evt. navnet på din connection-variabel, f.eks. st.session_state.get("conn"))
  conn = st.session_state.get("snowflake_conn") or st.connection("snowflake")

  df_zones = hent_team_zone_passes(conn, calendar_uuid)

  if df_zones.empty:
    st.warning(
        "Ingen data fundet for denne turnering/sæson. Tjek om kampe er spillet"
        " og om UUID'en er korrekt."
    )
    return

  # Hold-liste fra det hentede datasæt
  teams = df_zones["TEAM_NAME"].tolist()

  if not teams:
    st.warning("Ingen hold tilgængelige i resultatsættet.")
    return

  # --- 3. OPSÆTNING AF BANEN OG GITTERET ---
  pitch = Pitch(line_zorder=2, line_color="black")
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
  # Vi transformerer de flade ZONE_X_Y kolonner til et 3x4 array pr. hold
  hist_dict = {}
  for _, row in df_zones.iterrows():
    team_name = row["TEAM_NAME"]

    # Byg 3x4 gitter ud fra SQL kolonnenavnene (Y: 1-3, X: 1-4)
    grid_matrix = np.zeros((3, 4))
    for y in [1, 2, 3]:
      for x in [1, 2, 3, 4]:
        col_name = f"ZONE_{x}_{y}"
        grid_matrix[y - 1, x - 1] = row.get(col_name, 0)

    # Gem i dictionary, så mplsoccer/bin_statistic-strukturen matches
    hist_dict[team_name] = {"statistic": grid_matrix}

  # Begræns axs['pitch'] til det antal hold der rent faktisk er data for
  active_teams = [t for t in teams if t in hist_dict]

  if not active_teams:
    st.warning("Ingen matchende hold fundet til visualisering.")
    return

  # Beregner gennemsnit pr. zone på tværs af alle hold
  all_stats = [v["statistic"] for k, v in hist_dict.items()]
  avg_hist = np.mean(np.array(all_stats), axis=0) if all_stats else np.zeros((3, 4))

  # Trækker gennemsnittet fra for at vise performance over/under gennemsnit
  for team in active_teams:
    hist_dict[team]["statistic"] = hist_dict[team]["statistic"] - avg_hist

  # Forbereder farveskala (colormap)
  vmax = (
      max([np.amax(v["statistic"]) for k, v in hist_dict.items()])
      if hist_dict
      else 1
  )
  vmin = (
      min([np.amin(v["statistic"]) for k, v in hist_dict.items()])
      if hist_dict
      else -1
  )
  if vmax == vmin:
    vmax = vmin + 1  # Undgå delingsfejl ved ens værdier
  divnorm = colors.TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)

  # --- 5. PLOTTING AF HVERT HOLD / AXE ---
  # Bemærk: Hvis der er flere hold end felter i 3x4 gitteret (12 felter), tager vi de første 12
  plot_teams = active_teams[:12]

  for team, ax in zip(plot_teams, axs["pitch"].flat):
    # Sæt holdnavn over plottet
    ax.text(
        60,
        -8,
        team,
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
    )
    # Plot varmekortet baseret på det aggregerede 3x4 gitter
    pitch.heatmap(
        hist_dict[team], ax=ax, cmap="coolwarm", norm=divnorm, edgecolor="grey"
    )

  # Skjul eventuelle ubrugte subplots hvis der er færre end 12 hold
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
