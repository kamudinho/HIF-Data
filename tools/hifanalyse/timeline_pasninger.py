# tools/hifanalyse/timeline_pasninger.py
import streamlit as st

from data.data_load import _get_snowflake_conn
from data.sql.timeline import (
    hent_kamp_tids_pasninger,
    hent_seson_tids_pasninger,
)
from data.sql.teams import hent_hoved_stats
from data.utils.team_mapping import TEAMS
from utils.chart_helper import (
    new_figure, style_axes, style_legend, add_line, show_figure,
    SERIES_COLORS, PALETTE,
)
from utils.statistik_helper import render_statistik_filtre

INTERVALS_ORDER = ["1-15", "16-30", "31-45+", "46-60", "61-75", "76-90+"]


def _get_team_name_from_uuid(uuid: str, fallback: str = "Ukendt") -> str:
  """Oversætter Opta UUID til holdnavn ved hjælp af TEAMS mappingen."""
  for team_name, data in TEAMS.items():
    if data.get("opta_uuid") == uuid:
      return team_name
  return fallback


def _lav_pivot(df):
  """Pivotér til hold som rækker og intervaller som kolonner + totaler."""
  pivot_df = (
      df.pivot(index="TEAM_NAME", columns="TIME_INTERVAL", values="PASS_COUNT")
      .reindex(columns=INTERVALS_ORDER)
      .fillna(0)
  )
  pivot_df["Total"] = pivot_df[INTERVALS_ORDER].sum(axis=1)
  pivot_df["1st half"] = pivot_df[["1-15", "16-30", "31-45+"]].sum(axis=1)
  pivot_df["2nd half"] = pivot_df[["46-60", "61-75", "76-90+"]].sum(axis=1)
  return pivot_df


def vis_side():
  st.markdown("### Timeline: Pasningsanalyse")

  conn = _get_snowflake_conn()

  # --- 1. FILTRE (layout styres af statistik_helper) ---
  valg = render_statistik_filtre(
      key="tids",
      hent_kampe=lambda uuid: hent_hoved_stats(conn, uuid),
  )

  # =========================================================================
  # KAMPOVERSIGT
  # =========================================================================
  if valg.er_kamp:
    if valg.kamp is None:
      return

    selected_row = valg.kamp
    match_optauuid = selected_row["MATCH_OPTAUUID"]

    home_uuid = selected_row["CONTESTANTHOME_OPTAUUID"]
    away_uuid = selected_row["CONTESTANTAWAY_OPTAUUID"]

    home_team = _get_team_name_from_uuid(
        home_uuid, selected_row["CONTESTANTHOME_NAME"]
    )
    away_team = _get_team_name_from_uuid(
        away_uuid, selected_row["CONTESTANTAWAY_NAME"]
    )

    df_kamp_pas = hent_kamp_tids_pasninger(conn, match_optauuid)

    if df_kamp_pas.empty:
      st.info("Ingen pasningsdata tilgængelig for denne kamp.")
      return

    # Map TEAM_ID til det pæne holdnavn ved hjælp af mapping-funktionen
    df_kamp_pas["TEAM_NAME"] = df_kamp_pas.apply(
        lambda row: _get_team_name_from_uuid(
            row["TEAM_ID"],
            home_team
            if row["TEAM_ID"] == home_uuid
            else (
                away_team
                if row["TEAM_ID"] == away_uuid
                else row.get("TEAM_ID", "Ukendt")
            ),
        ),
        axis=1,
    )

    pivot_df = _lav_pivot(df_kamp_pas)

    st.markdown(f"#### Pasningsfordeling: {home_team} vs {away_team}")
    st.dataframe(
        pivot_df[["Total", "1st half", "2nd half"]].style.format("{:.0f}"),
        use_container_width=True,
    )

    # --- PLOT GRAF (stil styres af chart_helper) ---
    fig, ax = new_figure(
        title="Afleveringer pr. 15 minutter",
        subtitle=f"{home_team} vs {away_team}",
        figsize=(9, 5),
    )

    for idx, team in enumerate(pivot_df.index.tolist()):
      y_vals = [pivot_df.loc[team, col] for col in INTERVALS_ORDER]
      add_line(
          ax,
          INTERVALS_ORDER,
          y_vals,
          color=SERIES_COLORS[idx % len(SERIES_COLORS)],
          label=team,
      )

    style_axes(
        ax,
        xlabel="Kampens intervaller",
        ylabel="Antal afleveringer",
        integer_y=True,
        grid_axis="y",
    )
    style_legend(ax, loc="upper left")

    show_figure(fig)

  # =========================================================================
  # HOLDOVERSIGT
  # =========================================================================
  else:
    df_seson = hent_seson_tids_pasninger(conn, valg.calendar_uuid)
    if df_seson.empty:
      st.warning("Ingen data fundet for denne sæson.")
      return

    # Oversæt TEAM_ID til holdnavne
    df_seson["TEAM_NAME"] = df_seson["TEAM_ID"].apply(
        lambda x: _get_team_name_from_uuid(x)
    )
    pivot_df = _lav_pivot(df_seson)

    st.markdown("#### Sæson-gennemsnit pr. hold")
    st.caption("Viser gennemsnitligt antal afleveringer fordelt på kampens intervaller over hele sæsonen.")

    st.dataframe(
        pivot_df[["Total", "1st half", "2nd half"]].sort_values("Total", ascending=True).style.format("{:.0f}"),
        use_container_width=True,
    )

    st.markdown("---")
    st.markdown("#### Tendenslinje for udvalgt hold")

    if valg.hold not in pivot_df.index:
      st.info(f"Ingen pasningsdata fundet for {valg.hold}.")
      return

    fig, ax = new_figure(
        title="Sæson-tendens: gns. afleveringer",
        subtitle=f"{valg.hold} · {valg.turnering} {valg.saeson}",
        figsize=(9, 5),
    )

    y_vals = [pivot_df.loc[valg.hold, col] for col in INTERVALS_ORDER]
    add_line(ax, INTERVALS_ORDER, y_vals, color=PALETTE["secondary"], label=valg.hold)

    style_axes(
        ax,
        xlabel="Kampens intervaller",
        ylabel="Gns. antal afleveringer",
        integer_y=True,
        grid_axis="y",
    )
    style_legend(ax, loc="upper left")

    show_figure(fig)
