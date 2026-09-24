#tools/hifanalyse/dataviz.py
"""
Data-visualisering for Hvidovre IF: sammenligner alle hold i den valgte liga på
tværs af nøgletal (skud, xG, mål, pasninger, possession) - ét punkt pr. hold,
med gennemsnitslinjer og Hvidovre fremhævet.

Bygget på samme princip som Næsby-akademiets pages/data_viz.py (Dash/Plotly:
punkt-scatter pr. hold med gennemsnitslinjer og fremhævet eget hold), men
portet til Streamlit og til denne kodebases egen datakilde
(data/sql/kampe.py's load_league_match_level_data) i stedet for et separat
Excel-datasæt, og tegnet med Altair for at matche den charting-library resten
af appen allerede bruger (se HIF-head.py's trendgrafer).

Til forskel fra Næsby-siden, som fik data pr. kamp direkte fra sit datasæt,
kommer load_league_match_level_data som én række PR. KAMP med HOME_-/AWAY_-
kolonner. Denne side aggregerer den om til én række PR. HOLD for hele sæsonen
(summer "for" og "mod" ud fra hjemme/ude-siden), fordi alle seks visninger her
er sæson-totaler, ikke enkeltkampe.
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
GRAA = "#999999"

# Nøgle -> (x-kolonne, y-kolonne, titel). Kolonnerne refererer til de
# aggregerede holdkolonner fra _aggreger_holdstatistik nedenfor.
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

# Kolonner der IKKE skal deles med antal kampe (possession er allerede en procent)
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
    """
    Lægger load_league_match_level_data's én-række-pr.-kamp-format (HOME_-/
    AWAY_-kolonner) om til én række pr. hold for hele sæsonen, med separate
    "for"- og "mod"-summer.
    """
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


def _byg_chart(plot_df: pd.DataFrame, x_col: str, y_col: str, title: str) -> alt.LayerChart:
    x_label = f"{DANSK_LABEL.get(x_col, x_col)}" + (" pr. kamp" if x_col not in IKKE_PR_KAMP else "")
    y_label = f"{DANSK_LABEL.get(y_col, y_col)}" + (" pr. kamp" if y_col not in IKKE_PR_KAMP else "")

    points = alt.Chart(plot_df).mark_circle(size=160, opacity=0.9).encode(
        x=alt.X(f"{x_col}:Q", title=x_label, scale=alt.Scale(zero=False)),
        y=alt.Y(f"{y_col}:Q", title=y_label, scale=alt.Scale(zero=False)),
        color=alt.condition(alt.datum.ER_HIF, alt.value(HIF_FARVE), alt.value(GRAA)),
        tooltip=[
            alt.Tooltip("TEAM_NAME:N", title="Hold"),
            alt.Tooltip(f"{x_col}:Q", title=x_label, format=".2f"),
            alt.Tooltip(f"{y_col}:Q", title=y_label, format=".2f"),
        ],
    )
    labels = alt.Chart(plot_df).mark_text(dy=-14, fontSize=10, fontWeight="bold").encode(
        x=f"{x_col}:Q", y=f"{y_col}:Q", text="TEAM_NAME:N",
        color=alt.condition(alt.datum.ER_HIF, alt.value(HIF_FARVE), alt.value("#555555")),
    )
    v_snit = alt.Chart(pd.DataFrame({"x": [plot_df[x_col].mean()]})).mark_rule(
        strokeDash=[4, 4], color="black", opacity=0.5
    ).encode(x="x:Q")
    h_snit = alt.Chart(pd.DataFrame({"y": [plot_df[y_col].mean()]})).mark_rule(
        strokeDash=[4, 4], color="black", opacity=0.5
    ).encode(y="y:Q")

    return (v_snit + h_snit + points + labels).properties(title=title, height=560)


def vis_side(dp=None):
    st.caption("Sammenligner alle hold i ligaen for sæsonens spillede kampe - hvert punkt er ét hold.")

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

    chart = _byg_chart(plot_df, x_col, y_col, title)
    st.altair_chart(chart, use_container_width=True)


if __name__ == "__main__":
    vis_side()
