# tools/hifanalyse/statistisk_analyse.py
import numpy as np
import pandas as pd
import streamlit as st

from data.sql.skud_data import (
    load_final_third_data,
    load_league_data,
    load_passing_data,
)
from data.utils.team_mapping import (
    SEASON_LEAGUE_MAPPER,
    SEASONS,
    TEAM_COLORS,
    TEAMS,
)
from utils.chart_helper import (
    PALETTE,
    SEQ_CMAP,
    add_trendline,
    new_figure,
    pad_xlim,
    show_figure,
    style_axes,
    style_colorbar,
    style_legend,
)


def vis_side():
  st.markdown("### Statistisk Analyse")
  st.caption(
      "Analyser sammenhængen mellem pasningsvolumen, mål, skud og forventede mål"
      " (xG) pr. kamp."
  )

  # --- 1. FILTRE ---
  col_top1, col_top2 = st.columns(2)
  with col_top1:
    valgt_saeson = st.selectbox(
        "Vælg sæson", list(SEASONS.keys()), key="reg_saeson_sel"
    )
  with col_top2:
    valgt_turnering = st.selectbox(
        "Vælg turnering",
        list(SEASONS[valgt_saeson].keys()),
        key="reg_turnering_sel",
    )

  liga_uuid = SEASONS[valgt_saeson][valgt_turnering]
  tilgængelige_hold = SEASON_LEAGUE_MAPPER.get(valgt_saeson, {}).get(
      valgt_turnering, ["Hvidovre"]
  )

  # --- 2. HOLD-VALG & PASNINGSTYPE INDSTILLINGER ---
  col_graf, col_filter = st.columns([3, 1])

  with col_filter:
    st.markdown("##### Indstillinger")
    valgte_hold = st.selectbox(
        "Vælg hold", tilgængelige_hold, key="reg_hold_sel"
    )

    pasningstype = st.selectbox(
        "Pasningstype",
        [
            "Alle pasninger",
            "Fremadrettede pasninger",
            "Pasninger på sidste tredjedel",
        ],
        key="reg_pasningstype_sel",
    )

    # Undervalg ud fra valgt pasningstype
    valgt_dist = 10.0
    fremadrettet_filter = False

    if pasningstype == "Fremadrettede pasninger":
      valgt_dist_str = st.radio(
          "Min. fremgang:",
          ["10 meter", "20 meter", "30 meter"],
          index=1,  # Standard 20m
          key="reg_dist_sel",
      )
      valgt_dist = float(valgt_dist_str.split()[0])
      fremadrettet_filter = True

    elif pasningstype == "Pasninger på sidste tredjedel":
      f_type = st.radio(
          "Type på 1/3:",
          ["Alle pasninger", "Kun fremadrettede"],
          key="reg_f3_type_sel",
      )
      if f_type == "Kun fremadrettede":
        valgt_dist_str = st.radio(
            "Min. fremgang:",
            ["10 meter", "20 meter", "30 meter"],
            index=0,
            key="reg_f3_dist_sel",
        )
        valgt_dist = float(valgt_dist_str.split()[0])
        fremadrettet_filter = True

  # --- 3. DATA INDLÆSNING ---
  with st.spinner("Henter data fra Snowflake..."):
    df_shots_all = load_league_data(liga_uuid)

    if pasningstype == "Pasninger på sidste tredjedel":
      df_passes_all = load_final_third_data(
          liga_uuid, min_distance=valgt_dist
      )
    else:
      df_passes_all = load_passing_data(liga_uuid, min_distance=valgt_dist)

  if df_shots_all.empty or df_passes_all.empty:
    st.warning("Ingen data fundet for denne turnering/sæson.")
    return

  with col_graf:
    target_uuid = TEAMS.get(valgte_hold, {}).get("opta_uuid")

    if not target_uuid:
      st.error("Kunne ikke finde opta_uuid for holdet.")
      return

    df_hold_shots = df_shots_all[
        df_shots_all["EVENT_CONTESTANT_OPTAUUID"] == target_uuid
    ].copy()
    df_hold_passes = df_passes_all[
        df_passes_all["EVENT_CONTESTANT_OPTAUUID"] == target_uuid
    ].copy()

    if df_hold_shots.empty or df_hold_passes.empty:
      st.info(f"Ingen kampdata fundet for {valgte_hold}.")
      return

    # --- BEHANDLING AF SKUD & MÅL ---
    df_hold_shots["er_maal"] = (
        df_hold_shots["EVENT_TYPEID"] == 16
    ).astype(int)
    df_hold_shots["er_skud"] = (
        df_hold_shots["EVENT_TYPEID"].isin([13, 14, 15, 16]).astype(int)
    )

    df_reg_shots = (
        df_hold_shots.groupby("MATCH_OPTAUUID")
        .agg({"XG_RAW": "sum", "er_maal": "sum", "er_skud": "sum"})
        .rename(columns={"XG_RAW": "xG", "er_maal": "Maal", "er_skud": "Skud"})
        .reset_index()
    )

    # --- BEHANDLING AF PASNINGER ---
    if fremadrettet_filter:
      df_hold_passes = df_hold_passes[
          df_hold_passes["IS_PROGRESSIVE_PASS"] == 1
      ]

    # Navngivning til graf-akser og overskrift
    if pasningstype == "Fremadrettede pasninger":
      pas_kolonne_navn = f"Fremadrettede pasninger ({int(valgt_dist)}+ m)"
    elif pasningstype == "Pasninger på sidste tredjedel":
      if fremadrettet_filter:
        pas_kolonne_navn = (
            f"Fremadrettede pasninger på 1/3 ({int(valgt_dist)}+ m)"
        )
      else:
        pas_kolonne_navn = "Pasninger på sidste 1/3"
    else:
      pas_kolonne_navn = "Pasninger"

    df_reg_passes = (
        df_hold_passes.groupby("MATCH_OPTAUUID")
        .agg({"EVENT_OPTAUUID": "count"})
        .rename(columns={"EVENT_OPTAUUID": "Pasninger"})
        .reset_index()
    )

    # Merge
    df_reg = pd.merge(
        df_reg_shots, df_reg_passes, on="MATCH_OPTAUUID", how="inner"
    ).fillna(0)

    if df_reg.empty:
      st.info(f"Ingen matchende kampdata for {valgte_hold}.")
      return

    # --- 4. VISUALISERING (stil styres af chart_helper) ---
    fig, ax = new_figure(
        title=f"{pas_kolonne_navn} vs. mål – {valgte_hold}",
        subtitle=(
            f"{valgt_turnering} {valgt_saeson} · Størrelse = xG, farve = antal"
            " skud"
        ),
    )

    sizes = df_reg["xG"] * 40 + 25

    np.random.seed(42)
    y_jittered = df_reg["Maal"] + np.random.uniform(
        -0.06, 0.06, size=len(df_reg)
    )

    sc = ax.scatter(
        df_reg["Pasninger"],
        y_jittered,
        c=df_reg["Skud"],
        cmap=SEQ_CMAP,
        s=sizes,
        alpha=0.9,
        edgecolors=PALETTE["bg"],
        linewidths=1.2,
        zorder=3,
    )
    style_colorbar(fig.colorbar(sc, ax=ax, pad=0.02), "Antal skud i kampen")

    x_min_lim, x_max_lim = pad_xlim(ax, df_reg["Pasninger"])
    max_maal = int(df_reg["Maal"].max())
    ax.set_ylim(-0.3, max_maal + 0.6)

    add_trendline(
        ax, df_reg["Pasninger"], df_reg["Maal"], xlim=(x_min_lim, x_max_lim)
    )

    style_axes(
        ax,
        xlabel=f"Antal {pas_kolonne_navn.lower()} pr. kamp",
        ylabel="Antal mål i kampen",
        integer_y=True,
        grid_axis="both",
    )
    style_legend(ax, loc="upper left")

    show_figure(fig)

    # --- 5. METRIKKER & TABEL ---
    st.markdown("---")
    st.markdown(f"#### Nøgletal for {valgte_hold}")

    m1, m2, m3 = st.columns(3)
    m1.metric(
        f"Gns. {pas_kolonne_navn.lower()} / kamp",
        f"{df_reg['Pasninger'].mean():.1f}",
    )
    m2.metric("Gns. xG / kamp", f"{df_reg['xG'].mean():.2f}")
    m3.metric(
        "Total mål / skud",
        f"{int(df_reg['Maal'].sum())} / {int(df_reg['Skud'].sum())}",
    )

    with st.expander("Detaljeret kampdata"):
      st.dataframe(
          df_reg[["Pasninger", "Skud", "Maal", "xG"]].style.format(precision=2)
      )


if __name__ == "__main__":
  vis_side()
