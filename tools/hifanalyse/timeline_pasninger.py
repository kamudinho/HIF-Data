# tools/hifanalyse/tids_pasninger.py
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from data.data_load import _get_snowflake_conn
from data.sql.timeline import (
    hent_kamp_tids_pasninger,
    hent_seson_tids_pasninger,
)
from data.sql.teams import hent_hoved_stats  # For at få liste over spillede kampe
from data.utils.team_mapping import SEASONS


def vis_side():
  st.markdown("### ⏱️ Tidsbaseret Pasningsanalyse (15-minutters intervaller)")
  st.markdown(
      "Analyser afleveringsfordeling fordelt over kampens 15-minutters"
      " perioder – enten for en enkelt kamp eller som gennemsnit over hele"
      " sæsonen."
  )

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

  # Vælg visningstype: Enkeltskamp vs. Sæsonoverblik
  visnings_valg = st.radio(
      "Vælg analyseniveau:",
      ["Enkeltkamp (H2H sammenligning)", "Sæsonoverblik pr. hold"],
      horizontal=True,
  )

  intervals_order = ["1-15", "16-30", "31-45+", "46-60", "61-75", "76-90+"]

  if visnings_valg == "Enkeltkamp (H2H sammenligning)":
    # Hent kampliste for denne turnering
    df_kampe = hent_hoved_stats(conn, calendar_uuid)
    if df_kampe.empty:
      st.warning("Ingen spillede kampe fundet for denne turnering.")
      return

    # Lav en læsevenlig kamp-label
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
    home_team = selected_row["CONTESTANTHOME_NAME"]
    away_team = selected_row["CONTESTANTAWAY_NAME"]

    # Hent pasningsdata for kampen
    df_kamp_pas = hent_kamp_tids_pasninger(conn, match_optauuid)

    if df_kamp_pas.empty:
      st.info("Ingen pasningsdata tilgængelig for denne kamp.")
      return

    st.markdown(f"#### 📊 Pasningsfordeling: {home_team} vs {away_team}")

    # Pivotér data, så intervaller bliver kolonner og hold bliver rækker
    pivot_df = (
        df_kamp_pas.pivot(
            index="TEAM_NAME", columns="TIME_INTERVAL", values="PASS_COUNT"
        )
        .reindex(columns=intervals_order)
        .fillna(0)
    )

    # Udregn Total, 1. halvleg og 2. halvleg til tabellen (ligesom i skærmbilledet)
    pivot_df["Total"] = pivot_df[
        ["1-15", "16-30", "31-45+", "46-60", "61-75", "76-90+"]
    ].sum(axis=1)
    pivot_df["1st half"] = pivot_df["1-15"] + pivot_df["16-30"] + pivot_df["31-45+"]
    pivot_df["2nd half"] = (
        pivot_df["46-60"] + pivot_df["61-75"] + pivot_df["76-90+"]
    )

    # Vis tabel-oversigt (ligner eksemplet)
    st.dataframe(
        pivot_df[["Total", "1st half", "2nd half"]].style.format("{:.0f}"),
        use_container_width=True,
    )

    # --- PLOT GRAF ---
    fig, ax = plt.subplots(figsize=(9, 5))

    teams = pivot_df.index.tolist()
    colors = ["black", "red"]  # Standardfarver til Hvidovre vs modstander

    for idx, team in enumerate(teams):
      y_vals = [pivot_df.loc[team, col] for col in intervals_order]
      color = colors[idx % len(colors)]
      ax.plot(
          intervals_order,
          y_vals,
          marker="o",
          linewidth=3,
          color=color,
          label=team,
      )

      # Skriv værdien ved hvert punkt
      for x_pos, y_val in enumerate(y_vals):
        ax.text(
            x_pos,
            y_val + max(y_vals) * 0.03,
            f"{int(y_val)}",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            color=color,
        )

    ax.set_title(
        f"Afleveringer pr. 15 min - {home_team} vs {away_team}",
        fontsize=12,
        fontweight="bold",
    )
    ax.set_xlabel("Kampens intervaller", fontsize=10)
    ax.set_ylabel("Antal afleveringer", fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(loc="upper left")

    st.pyplot(fig)
    plt.close(fig)

  else:
    # --- SÆSONOVERBLIK PR. HOLD ---
    df_seson = hent_seson_tids_pasninger(conn, calendar_uuid)
    if df_seson.empty:
      st.warning("Ingen data fundet for denne sæson.")
      return

    alle_hold = df_seson["TEAM_NAME"].unique().tolist()
    valgt_hold = st.selectbox(
        "Vælg hold for sæsonanalyse:",
        alle_hold,
        index=(
            alle_hold.index("Hvidovre") if "Hvidovre" in alle_hold else 0
        ),
    )

    df_hold = df_seson[df_seson["TEAM_NAME"] == valgt_hold]

    fig, ax = plt.subplots(figsize=(9, 5))
    pass_counts = []
    for interval in intervals_order:
      val = df_hold.loc[df_hold["TIME_INTERVAL"] == interval, "PASS_COUNT"]
      pass_counts.append(val.values[0] if not val.empty else 0)

    ax.plot(
        intervals_order,
        pass_counts,
        marker="o",
        linewidth=3,
        color="black",
        label=valgt_hold,
    )
    for x_pos, y_val in enumerate(pass_counts):
      ax.text(
          x_pos,
          y_val + max(pass_counts) * 0.03,
          f"{int(y_val)}",
          ha="center",
          va="bottom",
          fontsize=10,
          fontweight="bold",
      )

    ax.set_title(
        f"Samlet pasningsmønster pr. interval (Sæson): {valgt_hold}",
        fontsize=12,
        fontweight="bold",
    )
    ax.set_xlabel("Kampens intervaller", fontsize=10)
    ax.set_ylabel("Total antal afleveringer", fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.4)

    st.pyplot(fig)
    plt.close(fig)


if __name__ == "__main__":
  vis_side()
