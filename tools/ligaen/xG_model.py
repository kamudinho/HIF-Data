import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_match_momentum_and_shotmap(events_df, match_info_df, match_uuid):
  """Genererer en xG-tidslinje (Race Chart) og et skudkort for en given kamp

  baseret på Opta-data fra Hvidovre-appens tabeller.
  """
  # 1. Filtrer data for den valgte kamp
  match_events = events_df[events_df["MATCH_OPTAUUID"] == match_uuid].copy()
  match_info = match_info_df[match_info_df["MATCH_OPTAUUID"] == match_uuid]

  if match_info.empty:
    return "Kamp ikke fundet."

  home_team = match_info.iloc[0]["CONTESTANTHOME_NAME"]
  away_team = match_info.iloc[0]["CONTESTANTAWAY_NAME"]
  home_uuid = match_info.iloc[0]["CONTESTANTHOME_OPTAUUID"]
  away_uuid = match_info.iloc[0]["CONTESTANTAWAY_OPTAUUID"]

  # 2. Filtrer skud-hændelser (EVENT_TYPEID 13, 14, 15, 16)
  shots_df = match_events[match_events["EVENT_TYPEID"].isin([13, 14, 15, 16])].copy()
  shots_df["XG_VAL"] = pd.to_numeric(shots_df["XG_RAW"], errors="coerce").fillna(
      0.0
  )
  shots_df["EVENT_TIMEMIN"] = pd.to_numeric(
      shots_df["EVENT_TIMEMIN"], errors="coerce"
  ).fillna(0)

  # Sorter efter tid for kumulativ xG
  shots_df = shots_df.sort_values(by=["EVENT_TIMEMIN", "EVENT_TIMESTAMP"])

  # Opdel i hjemme- og udehold
  home_shots = shots_df[shots_df["EVENT_CONTESTANT_OPTAUUID"] == home_uuid].copy()
  away_shots = shots_df[shots_df["EVENT_CONTESTANT_OPTAUUID"] == away_uuid].copy()

  # Beregn kumulativ xG minut for minut
  home_shots["CUM_XG"] = home_shots["XG_VAL"].cumsum()
  away_shots["CUM_XG"] = away_shots["XG_VAL"].cumsum()

  # 3. Opret Plotly figur (2 rows: Top = xG Tidslinje, Bund = Skudkort)
  fig = make_subplots(
      rows=2,
      cols=1,
      subplot_titles=(
          f"xG Tidslinje: {home_team} vs {away_team}",
          "Skudkort / Shot Map",
      ),
      specs=[[{"type": "xy"}], [{"type": "xy"}]],
      vertical_spacing=0.15,
  )

  # --- AFSNIT 1: xG TIDSCHART (Step Chart) ---
  if not home_shots.empty:
    fig.add_trace(
        go.Scatter(
            x=home_shots["EVENT_TIMEMIN"],
            y=home_shots["CUM_XG"],
            mode="lines+markers",
            name=f"{home_team} (xG)",
            line=dict(shape="hv", color="red", width=3),
            text=home_shots["PLAYER_NAME"]
            + " ("
            + home_shots["XG_VAL"].astype(str)
            + " xG)",
        ),
        row=1,
        col=1,
    )

  if not away_shots.empty:
    fig.add_trace(
        go.Scatter(
            x=away_shots["EVENT_TIMEMIN"],
            y=away_shots["CUM_XG"],
            mode="lines+markers",
            name=f"{away_team} (xG)",
            line=dict(shape="hv", color="blue", width=3),
            text=away_shots["PLAYER_NAME"]
            + " ("
            + away_shots["XG_VAL"].astype(str)
            + " xG)",
        ),
        row=1,
        col=1,
    )

  # --- AFSNIT 2: SKUDKORT (Shot Map på bane) ---
  # Opta banekoordinater er typisk 0-100 (X) og 0-100 (Y)
  # Vi plotter skud for hjemmehold og udehold med farvekoder
  color_map = {16: "green", 15: "orange", 14: "gray", 13: "black"}  # 16=Mål osv.

  for side_df, name in [(home_shots, home_team), (away_shots, away_team)]:
    if not side_df.empty:
      fig.add_trace(
          go.Scatter(
              x=side_df["LOCATIONX"],
              y=side_df["LOCATIONY"],
              mode="markers",
              name=f"Skud: {name}",
              marker=dict(
                  size=10,
                  color=side_df["EVENT_TYPEID"].map(color_map),
                  line=dict(width=1, color="white"),
              ),
              text=side_df["PLAYER_NAME"]
              + " - Min: "
              + side_df["EVENT_TIMEMIN"].astype(str),
          ),
          row=2,
          col=1,
      )

  # Layout justeringer
  fig.update_xaxes(title_text="Minut", range=[0, 95], row=1, col=1)
  fig.update_yaxes(title_text="Expected Goals (xG)", row=1, col=1)

  fig.update_xaxes(
      title_text="Bane X (0-100)", range=[0, 100], row=2, col=1
  )
  fig.update_yaxes(
      title_text="Bane Y (0-100)", range=[0, 100], row=2, col=1
  )

  fig.update_layout(
      height=800,
      title_text=f"Kampanalyse: {home_team} - {away_team}",
      template="plotly_white",
  )

  return fig
