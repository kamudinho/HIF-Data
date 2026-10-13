# tools/hifanalyse/timeline_pasninger.py
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from data.data_load import _get_snowflake_conn
from data.sql.timeline import (
    hent_kamp_tids_pasninger,
    hent_seson_tids_pasninger,
)
from data.sql.teams import hent_hoved_stats
from data.utils.team_mapping import SEASONS, TEAMS
from utils.chart_helper import (
    new_figure, style_axes, style_legend, add_line, show_figure,
    SERIES_COLORS, PALETTE,
)


def _get_team_name_from_uuid(uuid: str, fallback: str = "Ukendt") -> str:
  """Oversætter Opta UUID til holdnavn ved hjælp af TEAMS mappingen."""
  for team_name, data in TEAMS.items():
    if data.get("opta_uuid") == uuid:
      return team_name
  return fallback


def vis_side():
  st.markdown("### Timeline: Pasningsanalyse")

  # --- 1. FILTER KONTROL ---
  col1, col2 = st.columns(2)
  with col1:
    selected_season = st.selectbox(
        "Vælg Sæson:", list(SEASONS.keys()), index=0, key="tids_saeson"
    )
  with col2:
    selected_comp = st.selectbox(
        "Vælg Turnering:",
        list(SEASONS[selected_season].keys()),
        index=0,
        key="tids_comp",
    )

  calendar_uuid = SEASONS[selected_season][selected_comp]
  conn = _get_snowflake_conn()

  visnings_valg = st.radio(
      "Vælg analyseniveau:",
      ["Enkeltkamp (H2H sammenligning)", "Sæsonoverblik pr. hold"],
      horizontal=True,
  )

  intervals_order = ["1-15", "16-30", "31-45+", "46-60", "61-75", "76-90+"]

  if visnings_valg == "Enkeltkamp (H2H sammenligning)":
    df_kampe = hent_hoved_stats(conn, calendar_uuid)
    if df_kampe.empty:
      st.warning("Ingen spillede kampe fundet for denne turnering.")
      return

    df_kampe["MATCH_LABEL"] = (
        df_kampe["MATCH_DATE_FULL"].astype(str)
        + ": "
        + df_kampe["CONTESTANTHOME_NAME"]
        + " vs "
        + df_kampe["CONTESTANTAWAY_NAME"]
    )
    valgt_kamp_label = st.selectbox(
        "Vælg kamp:", df_kampe["MATCH_LABEL"].tolist()
    )

    selected_row = df_kampe[df_kampe["MATCH_LABEL"] == valgt_kamp_label].iloc[0]
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

    # --- PLOT GRAF (stil styres af chart_helper) ---
    fig, ax = new_figure(
        title="Afleveringer pr. 15 minutter",
        subtitle=f"{home_team} vs {away_team}",
        figsize=(9, 5),
    )

    for idx, team in enumerate(pivot_df.index.tolist()):
      y_vals = [pivot_df.loc[team, col] for col in intervals_order]
      add_line(
          ax,
          intervals_order,
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

  else:
    # --- SÆSONOVERBLIK PR. HOLD ---
    df_seson = hent_seson_tids_pasninger(conn, calendar_uuid)
    if df_seson.empty:
      st.warning("Ingen data fundet for denne sæson.")
      return

    # 1. Oversæt TEAM_ID til holdnavne
    df_seson["TEAM_NAME"] = df_seson["TEAM_ID"].apply(
        lambda x: _get_team_name_from_uuid(x)
    )

    # 2. Pivotér data så vi har intervaller som kolonner og hold som rækker
    pivot_df = (
        df_seson.pivot(
            index="TEAM_NAME", columns="TIME_INTERVAL", values="PASS_COUNT"
        )
        .reindex(columns=intervals_order)
        .fillna(0)
    )

    # 3. Beregn totaler (ligesom i enkeltkamp)
    pivot_df["Total"] = pivot_df[intervals_order].sum(axis=1)
    pivot_df["1st half"] = pivot_df[["1-15", "16-30", "31-45+"]].sum(axis=1)
    pivot_df["2nd half"] = pivot_df[["46-60", "61-75", "76-90+"]].sum(axis=1)

    st.markdown("#### Sæson-gennemsnit pr. hold")
    st.caption("Viser gennemsnitligt antal afleveringer fordelt på kampens intervaller over hele sæsonen.")

    # Vis tabellen med alle hold
    st.dataframe(
        pivot_df[["Total", "1st half", "2nd half"]].sort_values("Total", ascending=True).style.format("{:.0f}"),
        use_container_width=True,
    )

    # 4. VISUALISERING (Vælg ét hold for at se trenden)
    st.markdown("---")
    st.markdown("#### Tendenslinje for udvalgt hold")

    hold_liste = pivot_df.index.tolist()
    valgt_hold_seson = st.selectbox("Vælg hold til detaljeret visning:", hold_liste)

    if valgt_hold_seson:
        fig, ax = new_figure(
            title="Sæson-tendens: gns. afleveringer",
            subtitle=f"{valgt_hold_seson} · {selected_comp} {selected_season}",
            figsize=(9, 5),
        )

        y_vals = [pivot_df.loc[valgt_hold_seson, col] for col in intervals_order]
        add_line(ax, intervals_order, y_vals, color=PALETTE["secondary"], label=valgt_hold_seson)

        style_axes(
            ax,
            xlabel="Kampens intervaller",
            ylabel="Gns. antal afleveringer",
            integer_y=True,
            grid_axis="y",
        )
        style_legend(ax, loc="upper left")

        show_figure(fig)


    st.markdown(f"#### Pasningsfordeling: {home_team} vs {away_team}")

    pivot_df = (
        df_kamp_pas.pivot(
            index="TEAM_NAME", columns="TIME_INTERVAL", values="PASS_COUNT"
        )
        .reindex(columns=intervals_order)
        .fillna(0)
    )

    pivot_df["Total"] = pivot_df[intervals_order].sum(axis=1)
    pivot_df["1st half"] = pivot_df[["1-15", "16-30", "31-45+"]].sum(axis=1)
    pivot_df["2nd half"] = pivot_df[["46-60", "61-75", "76-90+"]].sum(axis=1)

    st.dataframe(
        pivot_df[["Total", "1st half", "2nd half"]].style.format("{:.0f}"),
        use_container_width=True,
    )

    
