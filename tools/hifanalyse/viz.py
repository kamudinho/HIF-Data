"""
Data-visualisering for Hvidovre IF: sammenligner alle hold i den valgte liga på
tværs af nøgletal - med grå prikker til modstandere og rød prik til Hvidovre.
"""

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

from data.utils.team_mapping import (
    TEAMS,
    TEAM_COLORS,
    SEASONS,
    COMPETITION_NAME as DEFAULT_COMP,
    TOURNAMENTCALENDAR_NAME as DEFAULT_SEASON,
)
from data.sql.kampe import load_league_match_level_data

HIF_NAVN = "Hvidovre"
HIF_FARVE = TEAM_COLORS.get(HIF_NAVN, {}).get("primary", "#cc0000")
MODSTANDER_FARVE = "#d3d3d3"

VISNING_MAPPING = {
    "skud_vs_xg": ("SHOTS_FOR", "XG_FOR", "Skud vs. xG"),
    "skud_vs_maal": ("SHOTS_FOR", "GOALS_FOR", "Skud vs. Mål"),
    "skud_mod_vs_xg_mod": ("SHOTS_AGAINST", "XG_AGAINST", "Skud mod vs. xG mod"),
    "skud_mod_vs_maal_mod": ("SHOTS_AGAINST", "GOALS_AGAINST", "Skud mod vs. Mål mod"),
    "skud_vs_pasninger": ("SHOTS_FOR", "PASSES", "Skud vs. Pasninger"),
    "possession_vs_fremad": ("POSSESSION", "FORWARD_PASSES", "Possession vs. Fremadrettede pasninger"),
    "touches_vs_skud": ("TOUCHES_IN_BOX_FOR", "SHOTS_FOR", "Touches in box vs. Skud"),
    "possession_vs_touches": ("POSSESSION", "TOUCHES_IN_BOX_FOR", "Possession vs. Touches in box"),
}

IKKE_PR_KAMP = {"POSSESSION"}

DANSK_LABEL = {
    "SHOTS_FOR": "Skud",
    "SHOTS_AGAINST": "Skud mod",
    "XG_FOR": "xG",
    "XG_AGAINST": "xG mod",
    "GOALS_FOR": "Mål",
    "GOALS_AGAINST": "Mål mod",
    "PASSES": "Pasninger",
    "FORWARD_PASSES": "Fremadrettede pasninger",
    "POSSESSION": "Possession %",
    "TOUCHES_IN_BOX_FOR": "Touches in box",
}


def _aggreger_holdstatistik(df_matches: pd.DataFrame) -> pd.DataFrame:
    def side_split(side: str, opp_side: str, uuid_col: str) -> pd.DataFrame:
        return pd.DataFrame({
            "TEAM_OPTAUUID": df_matches[uuid_col].astype(str).str.strip().str.upper(),
            "SHOTS_FOR": pd.to_numeric(df_matches.get(f"{side}_SHOTS"), errors="coerce"),
            "SHOTS_AGAINST": pd.to_numeric(df_matches.get(f"{opp_side}_SHOTS"), errors="coerce"),
            "XG_FOR": pd.to_numeric(df_matches.get(f"{side}_XG"), errors="coerce"),
            "XG_AGAINST": pd.to_numeric(df_matches.get(f"{opp_side}_XG"), errors="coerce"),
            "GOALS_FOR": pd.to_numeric(df_matches.get(f"TOTAL_{side}_SCORE"), errors="coerce"),
            "GOALS_AGAINST": pd.to_numeric(df_matches.get(f"TOTAL_{opp_side}_SCORE"), errors="coerce"),
            "PASSES": pd.to_numeric(df_matches.get(f"{side}_PASSES"), errors="coerce"),
            "FORWARD_PASSES": pd.to_numeric(df_matches.get(f"{side}_FORWARD_PASSES"), errors="coerce"),
            "POSSESSION": pd.to_numeric(df_matches.get(f"{side}_POSS"), errors="coerce"),
            "TOUCHES_IN_BOX_FOR": pd.to_numeric(df_matches.get(f"{side}_TOUCHES_IN_BOX"), errors="coerce"),
        })

    long_df = pd.concat([
        side_split("HOME", "AWAY", "CONTESTANTHOME_OPTAUUID"),
        side_split("AWAY", "HOME", "CONTESTANTAWAY_OPTAUUID"),
    ], ignore_index=True)

    match_counts = long_df.groupby("TEAM_OPTAUUID").size().rename("MATCHES")
    sum_cols = ["SHOTS_FOR", "SHOTS_AGAINST", "XG_FOR", "XG_AGAINST",
                "GOALS_FOR", "GOALS_AGAINST", "PASSES", "FORWARD_PASSES",
                "TOUCHES_IN_BOX_FOR"]
    sums = long_df.groupby("TEAM_OPTAUUID")[sum_cols].sum()
    means = long_df.groupby("TEAM_OPTAUUID")[["POSSESSION"]].mean()

    return pd.concat([match_counts, sums, means], axis=1).reset_index()


def _byg_chart(plot_df: pd.DataFrame, x_key: str, y_key: str, x_col: str, y_col: str, title: str) -> alt.LayerChart:
    x_label = DANSK_LABEL.get(x_key, x_key) + (" pr. kamp" if x_key not in IKKE_PR_KAMP else "")
    y_label = DANSK_LABEL.get(y_key, y_key) + (" pr. kamp" if y_key not in IKKE_PR_KAMP else "")

    x_enc = alt.X(f"{x_col}:Q", title=x_label, scale=alt.Scale(zero=False, padding=20),
                  axis=alt.Axis(grid=False, tickCount=6))
    y_enc = alt.Y(f"{y_col}:Q", title=y_label, scale=alt.Scale(zero=False, padding=30),
                  axis=alt.Axis(grid=False, tickCount=6))
    
    tooltip = [
        alt.Tooltip("TEAM_NAME:N", title="Hold"),
        alt.Tooltip(f"{x_col}:Q", title=x_label, format=".2f"),
        alt.Tooltip(f"{y_col}:Q", title=y_label, format=".2f"),
    ]

    v_snit = alt.Chart(pd.DataFrame({"x": [plot_df[x_col].mean()]})).mark_rule(
        strokeDash=[4, 4], color="#bbbbbb"
    ).encode(x="x:Q")
    h_snit = alt.Chart(pd.DataFrame({"y": [plot_df[y_col].mean()]})).mark_rule(
        strokeDash=[4, 4], color="#bbbbbb"
    ).encode(y="y:Q")

    points_andre = alt.Chart(plot_df[~plot_df["ER_HIF"]]).mark_circle(
        size=300,
        filled=True,
        stroke="white",
        strokeWidth=1.5,
        color=MODSTANDER_FARVE
    ).encode(
        x=x_enc,
        y=y_enc,
        tooltip=tooltip
    )

    points_hif = alt.Chart(plot_df[plot_df["ER_HIF"]]).mark_circle(
        size=420,
        filled=True,
        stroke="white",
        strokeWidth=2,
        color=HIF_FARVE
    ).encode(
        x=x_enc,
        y=y_enc,
        tooltip=tooltip
    )

    # Fjernet stroke="white", så teksten står rent og læsbart uden hvide blokke
    labels_andre = alt.Chart(plot_df[~plot_df["ER_HIF"]]).mark_text(
        fontSize=11, fontWeight="bold",
        dy=-15,
        color="#222222"
    ).encode(
        x=x_enc, y=y_enc, text="TEAM_NAME:N", tooltip=tooltip
    )

    labels_hif = alt.Chart(plot_df[plot_df["ER_HIF"]]).mark_text(
        fontSize=13, fontWeight="bold",
        dy=-17,
        color=HIF_FARVE
    ).encode(
        x=x_enc, y=y_enc, text="TEAM_NAME:N", tooltip=tooltip
    )

    chart = alt.layer(v_snit, h_snit, points_andre, points_hif, labels_andre, labels_hif).properties(title=title, height=560)
    return chart.configure_view(strokeWidth=0).configure_axis(domainColor="#dddddd", tickColor="#dddddd")

def vis_side(dp=None):
    st.caption("Sammenligner alle hold i ligaen for sæsonens spillede kampe.")

    liga_uuid = SEASONS.get(DEFAULT_SEASON, {}).get(DEFAULT_COMP)
    if not liga_uuid:
        st.warning(f"Ingen turnerings-UUID fundet for {DEFAULT_COMP} i sæsonen {DEFAULT_SEASON}.")
        return

    visning_valg = st.selectbox(
        "Vælg visualisering",
        list(VISNING_MAPPING.keys()),
        format_func=lambda k: VISNING_MAPPING[k][2],
        key="hifanalyse_dataviz_valg",
    )

    df_matches = load_league_match_level_data(liga_uuid)
    if df_matches is None or df_matches.empty:
        st.warning("Ingen kampdata fundet for denne turnering/sæson.")
        return

    df_matches = df_matches[
        df_matches["MATCH_STATUS"].str.lower().str.contains("play|full|finish", na=False)
    ].copy()
    if df_matches.empty:
        st.warning("Ingen spillede kampe fundet endnu i denne sæson.")
        return

    holdstats = _aggreger_holdstatistik(df_matches)
    if holdstats.empty:
        st.warning("Kunne ikke udregne holdstatistik.")
        return

    opta_to_name = {str(v.get("opta_uuid")).strip().upper(): k for k, v in TEAMS.items() if v.get("opta_uuid")}

    holdstats["TEAM_NAME"] = holdstats["TEAM_OPTAUUID"].map(opta_to_name).fillna("Ukendt hold")
    holdstats["ER_HIF"] = holdstats["TEAM_NAME"] == HIF_NAVN

    x_key, y_key, title = VISNING_MAPPING[visning_valg]

    plot_df = holdstats.copy()
    for key in (x_key, y_key):
        if f"{key}_VAL" in plot_df.columns:
            continue
        if key in IKKE_PR_KAMP:
            plot_df[f"{key}_VAL"] = plot_df[key]
        else:
            plot_df[f"{key}_VAL"] = plot_df[key] / plot_df["MATCHES"].replace(0, np.nan)

    x_col, y_col = f"{x_key}_VAL", f"{y_key}_VAL"
    plot_df[x_col] = plot_df[x_col].replace([np.inf, -np.inf], np.nan)
    plot_df[y_col] = plot_df[y_col].replace([np.inf, -np.inf], np.nan)
    plot_df = plot_df.dropna(subset=[x_col, y_col])

    if plot_df.empty:
        st.warning(f"Ingen hold har gyldig data for '{title}'.")
        return

    chart = _byg_chart(plot_df, x_key, y_key, x_col, y_col, title)
    st.altair_chart(chart, use_container_width=True)


if __name__ == "__main__":
    vis_side()
