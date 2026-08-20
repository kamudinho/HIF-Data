import base64
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# --- IMPORT DYNAMISKE KONSTANTER OG MAPPINGS ---
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import (
    COMPETITION_NAME as DEFAULT_COMP,
    TOURNAMENTCALENDAR_NAME as DEFAULT_SEASON,
    COMPETITIONS,
    SEASON_LEAGUE_MAPPER,
    SEASONS,
    TEAMS,
)

# --- 1. HJÆLPEFUNKTIONER ---


@st.cache_data(ttl=86400)
def get_base64_image(url):
  try:
    if not url:
      return ""
    response = requests.get(url, timeout=5)
    if response.status_code == 200:
      encoded_str = base64.b64encode(response.content).decode("utf-8")
      return f"data:image/png;base64,{encoded_str}"
  except:
    return url
  return url


def safe_int(val):
  """Sikker konvertering af værdier til int, der håndterer NaN og None."""
  try:
    if pd.isnull(val):
      return 0
    return int(float(val))
  except:
    return 0


@st.cache_data(ttl=3600)
def load_match_level_data(
    tournament_opta_uuid,
    team_opta_uuid,
    team_wyid,
    comp_wyid,
    season_start_year=2026,
):
  conn = _get_snowflake_conn()
  db = "KLUB_HVIDOVREIF.AXIS"

  query = f"""
        WITH MatchBase AS (
            SELECT 
                MATCH_OPTAUUID, 
                TO_CHAR(MATCH_DATE_FULL, 'YYYY-MM-DD') AS MATCH_DATE,
                CONTESTANTHOME_OPTAUUID, 
                CONTESTANTAWAY_OPTAUUID,
                TOTAL_HOME_SCORE, 
                TOTAL_AWAY_SCORE
            FROM {db}.OPTA_MATCHINFO
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{tournament_opta_uuid}'
        ),
        MatchStatsPivot AS (
            SELECT 
                MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
                MAX(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN CAST(STAT_TOTAL AS FLOAT) END) AS TOTALSCORINGATT,
                MAX(CASE WHEN STAT_TYPE = 'ontargetScoringAtt' THEN CAST(STAT_TOTAL AS FLOAT) END) AS ONTARGETSCORINGATT,
                MAX(CASE WHEN STAT_TYPE = 'shotOffTarget' THEN CAST(STAT_TOTAL AS FLOAT) END) AS SHOTOFFTARGET,
                MAX(CASE WHEN STAT_TYPE = 'blockedScoringAtt' THEN CAST(STAT_TOTAL AS FLOAT) END) AS BLOCKEDSCORINGATT,
                MAX(CASE WHEN STAT_TYPE = 'subsGoals' THEN CAST(STAT_TOTAL AS FLOAT) END) AS SUBSGOALS,
                MAX(CASE WHEN STAT_TYPE = 'totalPass' THEN CAST(STAT_TOTAL AS FLOAT) END) AS TOTALPASS,
                MAX(CASE WHEN STAT_TYPE = 'accuratePass' THEN CAST(STAT_TOTAL AS FLOAT) END) AS ACCURATEPASS,
                MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN CAST(STAT_TOTAL AS FLOAT) END) AS POSSESSIONPERCENTAGE,
                MAX(CASE WHEN STAT_TYPE = 'wonCorners' THEN CAST(STAT_TOTAL AS FLOAT) END) AS WONCORNERS,
                MAX(CASE WHEN STAT_TYPE = 'lostCorners' THEN CAST(STAT_TOTAL AS FLOAT) END) AS LOSTCORNERS,
                MAX(CASE WHEN STAT_TYPE = 'totalTackle' THEN CAST(STAT_TOTAL AS FLOAT) END) AS TOTALTACKLE,
                MAX(CASE WHEN STAT_TYPE = 'wonTackle' THEN CAST(STAT_TOTAL AS FLOAT) END) AS WONTACKLE,
                MAX(CASE WHEN STAT_TYPE = 'totalClearance' THEN CAST(STAT_TOTAL AS FLOAT) END) AS TOTALCLEARANCE,
                MAX(CASE WHEN STAT_TYPE = 'outfielderBlock' THEN CAST(STAT_TOTAL AS FLOAT) END) AS OUTFIELDERBLOCK,
                MAX(CASE WHEN STAT_TYPE = 'fkFoulWon' THEN CAST(STAT_TOTAL AS FLOAT) END) AS FKFOULWON,
                MAX(CASE WHEN STAT_TYPE = 'fkFoulLost' THEN CAST(STAT_TOTAL AS FLOAT) END) AS FKFOULLOST,
                MAX(CASE WHEN STAT_TYPE = 'saves' THEN CAST(STAT_TOTAL AS FLOAT) END) AS SAVES,
                MAX(CASE WHEN STAT_TYPE = 'goalsConceded' THEN CAST(STAT_TOTAL AS FLOAT) END) AS GOALSCONCEDED,
                MAX(CASE WHEN STAT_TYPE = 'cleanSheet' THEN CAST(STAT_TOTAL AS FLOAT) END) AS CLEANSHEET
            FROM {db}.OPTA_MATCHSTATS
            WHERE MATCH_OPTAUUID IN (SELECT MATCH_OPTAUUID FROM MatchBase)
            GROUP BY 1, 2
        ),
        ExpectedGoalsPivot AS (
            SELECT 
                MATCH_ID AS MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
                SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS EXPECTEDGOALS
            FROM {db}.OPTA_MATCHEXPECTEDGOALS
            WHERE MATCH_ID IN (SELECT MATCH_OPTAUUID FROM MatchBase)
            GROUP BY 1, 2
        ),
        WyscoutDefense AS (
            SELECT 
                TO_CHAR(tm.DATE, 'YYYY-MM-DD') AS MATCH_DATE,
                md.PPDA
            FROM {db}.WYSCOUT_TEAMMATCHES tm
            LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_DEFENCE md 
                ON tm.MATCH_WYID = md.MATCH_WYID AND tm.TEAM_WYID = md.TEAM_WYID
            WHERE tm.COMPETITION_WYID = {comp_wyid} AND tm.TEAM_WYID = {team_wyid}
        ),
        FullTournamentData AS (
            SELECT 
                mb.MATCH_OPTAUUID,
                mb.MATCH_DATE,
                sp.CONTESTANT_OPTAUUID AS TEAM_OPTAUUID,
                
                CASE WHEN sp.CONTESTANT_OPTAUUID = mb.CONTESTANTHOME_OPTAUUID THEN mb.TOTAL_HOME_SCORE ELSE mb.TOTAL_AWAY_SCORE END AS GOALS,
                CASE WHEN sp.CONTESTANT_OPTAUUID = mb.CONTESTANTHOME_OPTAUUID THEN mb.TOTAL_AWAY_SCORE ELSE mb.TOTAL_HOME_SCORE END AS GOALS_AGAINST,
                
                mb.CONTESTANTHOME_OPTAUUID,
                mb.CONTESTANTAWAY_OPTAUUID,

                sp.TOTALSCORINGATT,
                sp.ONTARGETSCORINGATT,
                sp.SHOTOFFTARGET,
                sp.BLOCKEDSCORINGATT,
                sp.SUBSGOALS,
                sp.TOTALPASS,
                sp.ACCURATEPASS,
                sp.POSSESSIONPERCENTAGE,
                sp.WONCORNERS,
                sp.LOSTCORNERS,
                sp.TOTALTACKLE,
                sp.WONTACKLE,
                sp.TOTALCLEARANCE,
                sp.OUTFIELDERBLOCK,
                sp.FKFOULWON,
                sp.FKFOULLOST,
                sp.SAVES,
                sp.GOALSCONCEDED,
                sp.CLEANSHEET,
                xg.EXPECTEDGOALS,
                wd.PPDA,
                
                -- Dynamiske ligagennemsnit
                AVG(xg.EXPECTEDGOALS) OVER() AS LIGA_AVG_EXPECTEDGOALS,
                AVG(CASE WHEN sp.CONTESTANT_OPTAUUID = mb.CONTESTANTHOME_OPTAUUID THEN mb.TOTAL_HOME_SCORE ELSE mb.TOTAL_AWAY_SCORE END) OVER() AS LIGA_AVG_GOALS,
                AVG(CASE WHEN sp.CONTESTANT_OPTAUUID = mb.CONTESTANTHOME_OPTAUUID THEN mb.TOTAL_AWAY_SCORE ELSE mb.TOTAL_HOME_SCORE END) OVER() AS LIGA_AVG_GOALS_AGAINST,
                AVG(sp.TOTALSCORINGATT) OVER() AS LIGA_AVG_TOTALSCORINGATT,
                AVG(sp.ONTARGETSCORINGATT) OVER() AS LIGA_AVG_ONTARGETSCORINGATT,
                AVG(sp.SHOTOFFTARGET) OVER() AS LIGA_AVG_SHOTOFFTARGET,
                AVG(sp.BLOCKEDSCORINGATT) OVER() AS LIGA_AVG_BLOCKEDSCORINGATT,
                AVG(sp.SUBSGOALS) OVER() AS LIGA_AVG_SUBSGOALS,
                AVG(sp.TOTALPASS) OVER() AS LIGA_AVG_TOTALPASS,
                AVG(sp.ACCURATEPASS) OVER() AS LIGA_AVG_ACCURATEPASS,
                AVG(sp.POSSESSIONPERCENTAGE) OVER() AS LIGA_AVG_POSSESSIONPERCENTAGE,
                AVG(sp.WONCORNERS) OVER() AS LIGA_AVG_WONCORNERS,
                AVG(sp.LOSTCORNERS) OVER() AS LIGA_AVG_LOSTCORNERS,
                AVG(sp.TOTALTACKLE) OVER() AS LIGA_AVG_TOTALTACKLE,
                AVG(sp.WONTACKLE) OVER() AS LIGA_AVG_WONTACKLE,
                AVG(sp.TOTALCLEARANCE) OVER() AS LIGA_AVG_TOTALCLEARANCE,
                AVG(sp.OUTFIELDERBLOCK) OVER() AS LIGA_AVG_OUTFIELDERBLOCK,
                AVG(sp.FKFOULWON) OVER() AS LIGA_AVG_FKFOULWON,
                AVG(sp.FKFOULLOST) OVER() AS LIGA_AVG_FKFOULLOST,
                AVG(sp.SAVES) OVER() AS LIGA_AVG_SAVES,
                AVG(sp.GOALSCONCEDED) OVER() AS LIGA_AVG_GOALSCONCEDED,
                AVG(sp.CLEANSHEET) OVER() AS LIGA_AVG_CLEANSHEET,
                AVG(wd.PPDA) OVER() AS LIGA_AVG_PPDA

            FROM MatchBase mb
            JOIN MatchStatsPivot sp ON mb.MATCH_OPTAUUID = sp.MATCH_OPTAUUID
            LEFT JOIN ExpectedGoalsPivot xg ON sp.MATCH_OPTAUUID = xg.MATCH_OPTAUUID AND sp.CONTESTANT_OPTAUUID = xg.CONTESTANT_OPTAUUID
            LEFT JOIN WyscoutDefense wd ON mb.MATCH_DATE = wd.MATCH_DATE 
        )
        SELECT * 
        FROM FullTournamentData
        WHERE TEAM_OPTAUUID = '{team_opta_uuid}'
        ORDER BY MATCH_DATE ASC
    """
  df = conn.query(query)

  if not df.empty:
    df.columns = [c.upper() for c in df.columns]
    # Udfyld NaN med 0 for at sikre, at hold med 0 i en stat vises korrekt
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols].fillna(0)

    # Beregn sammensatte indekser hvis kolonnen findes
    # Offensiv Index: Kombinerer xG, Mål, Skud på mål og Total skud (vægtet)
    df["OFFENSIV_INDEX"] = (
        df.get("EXPECTEDGOALS", 0) * 2.0
        + df.get("GOALS", 0) * 3.0
        + df.get("ONTARGETSCORINGATT", 0) * 1.0
        + df.get("TOTALSCORINGATT", 0) * 0.2
    )

    # Defensiv Index: Kombinerer Vundne taklinger, Clearinger, Blokeringer og Clean sheet (samt lavere mål imod / PPDA)
    df["DEFENSIV_INDEX"] = (
        df.get("WONTACKLE", 0) * 1.0
        + df.get("TOTALCLEARANCE", 0) * 0.5
        + df.get("OUTFIELDERBLOCK", 0) * 1.0
        + df.get("CLEANSHEET", 0) * 3.0
        - df.get("GOALS_AGAINST", 0) * 2.0
    )

    df["LIGA_AVG_OFFENSIV_INDEX"] = df["OFFENSIV_INDEX"].mean()
    df["LIGA_AVG_DEFENSIV_INDEX"] = df["DEFENSIV_INDEX"].mean()

  return df


def draw_match_trend_chart(df_matches, metric, label, team_name, valgt_saeson):
  if df_matches is None or df_matches.empty:
    st.warning("Ingen kampdata tilgængelig for dette hold i den valgte sæson.")
    return

  fig = go.Figure()
  df_matches[metric] = pd.to_numeric(df_matches[metric], errors="coerce").fillna(
      0
  )
  df_matches["MATCH_NUM"] = range(1, len(df_matches) + 1)

  y_vals = df_matches[metric]
  has_data = not y_vals.empty

  if has_data:
    y_min = y_vals.min()
    y_max = y_vals.max()
    y_span = y_max - y_min if y_max != y_min else 1.0
    snit_vaerdi = y_vals.mean()
    total_val = y_vals.sum()
  else:
    y_min, y_max = 0.0, 1.0
    y_span = 1.0
    snit_vaerdi = 0.0
    total_val = 0.0

  mean_str = f"{snit_vaerdi:.2f}"

  if label == "PPDA":
    label_line1 = f"PPDA i {valgt_saeson}:"
    label_line2 = f"PPDA pr. 90 i {valgt_saeson}:"
    val1_str = mean_str
    val2_str = mean_str
  elif "Index" in label:
    label_line1 = f"Samlet {label} i {valgt_saeson}:"
    label_line2 = f"Gennemsnit pr. kamp:"
    val1_str = (
        f"{int(total_val)}" if total_val == int(total_val) else f"{total_val:.2f}"
    )
    val2_str = mean_str
  else:
    formatted_label = "xG" if label == "xG" else label.lower()
    formatted_label2 = "xG" if label == "xG" else label.capitalize()
    total_str = (
        f"{int(total_val)}" if total_val == int(total_val) else f"{total_val:.2f}"
    )
    label_line1 = f"Antal {formatted_label} i {valgt_saeson}:"
    label_line2 = f"{formatted_label2} pr. 90 i {valgt_saeson}:"
    val1_str = total_str
    val2_str = mean_str

  fig.add_annotation(
      text=f"{label_line1}<br>{label_line2}",
      xref="paper",
      yref="paper",
      x=0.67,
      y=1.08,
      xanchor="left",
      yanchor="top",
      showarrow=False,
      align="left",
      font=dict(size=11, color="black"),
  )
  fig.add_annotation(
      text=f"<b>{val1_str}</b><br><b>{val2_str}</b>",
      xref="paper",
      yref="paper",
      x=0.94,
      y=1.08,
      xanchor="left",
      yanchor="top",
      showarrow=False,
      align="left",
      font=dict(size=11, color="black"),
  )

  liga_avg_col = f"LIGA_AVG_{metric}"
  if (
      liga_avg_col in df_matches.columns
      and not df_matches[liga_avg_col].dropna().empty
  ):
    ligasnit = df_matches[liga_avg_col].dropna().iloc[0]
  else:
    ligasnit = y_vals.mean()

  opp_names = []
  opp_logos = []
  hover_texts = []

  for _, row in df_matches.iterrows():
    home_uuid = row.get("CONTESTANTHOME_OPTAUUID")
    away_uuid = row.get("CONTESTANTAWAY_OPTAUUID")
    current_team_uuid = row.get("TEAM_OPTAUUID")
    opp_uuid = away_uuid if current_team_uuid == home_uuid else home_uuid

    o_name, o_logo = "Modstander", ""
    for name, info in TEAMS.items():
      if info.get("opta_uuid") == opp_uuid:
        o_name, o_logo = name, info.get("logo", "")
        break

    opp_names.append(o_name)
    opp_logos.append(o_logo)

    g_for = safe_int(row.get("GOALS"))
    g_imod = safe_int(row.get("GOALS_AGAINST"))
    dato = str(row.get("MATCH_DATE", ""))[:10]
    val_metric = row.get(metric, 0)

    hover_texts.append(
        f"<b>Kamp {int(row['MATCH_NUM'])} vs. {o_name}</b><br>"
        f"Dato: {dato}<br>"
        f"Resultat: {g_for} - {g_imod}<br>"
        f"{label}: {val_metric:.2f}"
    )

  df_matches["OPP_NAME"] = opp_names
  df_matches["OPP_LOGO"] = opp_logos
  df_matches["HOVER_TEXT"] = hover_texts

  is_reversed = "PPDA" in label.upper() or "IMOD" in label.upper()

  if len(df_matches) > 1:
    for i in range(len(df_matches) - 1):
      y0 = df_matches[metric].iloc[i]
      y1 = df_matches[metric].iloc[i + 1]
      x0 = df_matches["MATCH_NUM"].iloc[i]
      x1 = df_matches["MATCH_NUM"].iloc[i + 1]

      if is_reversed:
        is_up = y1 < y0
      else:
        is_up = y1 > y0

      seg_color = "#2ECC71" if is_up else "#E74C3C" if y1 != y0 else "#95A5A6"

      fig.add_trace(
          go.Scatter(
              x=[x0, x1],
              y=[y0, y1],
              mode="lines",
              line=dict(color=seg_color, width=2, dash="dot"),
              showlegend=False,
              hoverinfo="skip",
          )
      )

  fig.add_trace(
      go.Scatter(
          x=df_matches["MATCH_NUM"],
          y=df_matches[metric],
          mode="markers",
          marker=dict(size=40, opacity=0),
          hovertext=df_matches["HOVER_TEXT"],
          hoverinfo="text",
          showlegend=False,
      )
  )

  logo_size_x = 0.65
  logo_size_y = y_span * 0.20 if y_span > 0.5 else 0.25

  # Sikrer at logoer tilføjes SIDST, så de ligger øverst over alt andet
  for _, row in df_matches.iterrows():
    if row.get("OPP_LOGO"):
      b64_logo = get_base64_image(row["OPP_LOGO"])
      fig.add_layout_image(
          dict(
              source=b64_logo,
              xref="x",
              yref="y",
              x=row["MATCH_NUM"],
              y=row[metric],
              sizex=logo_size_x,
              sizey=logo_size_y,
              xanchor="center",
              yanchor="middle",
              layer="above",  # Ændret fra 'top' til 'above', som er gyldigt i Plotly
          )
      )

  if is_reversed:
    team_pos = "top right" if snit_vaerdi < ligasnit else "bottom right"
    liga_pos = "bottom right" if snit_vaerdi < ligasnit else "top right"
  else:
    team_pos = "top right" if snit_vaerdi >= ligasnit else "bottom right"
    liga_pos = "bottom right" if snit_vaerdi >= ligasnit else "top right"

  fig.add_hline(
      y=snit_vaerdi,
      line_dash="solid",
      line_color="black",
      line_width=1.5,
      annotation_text=f"(Gennemsnit: {team_name})",
      annotation_position=team_pos,
  )
  fig.add_hline(
      y=ligasnit,
      line_dash="dash",
      line_color="gray",
      line_width=1.5,
      annotation_text=f"(Gennemsnit: {DEFAULT_COMP})",
      annotation_position=liga_pos,
  )

  padding = y_span * 0.15 if y_span > 0 else 1.0
  y_range = (
      [y_max + padding, y_min - padding]
      if is_reversed
      else [y_min - padding, y_max + padding]
  )

  fig.update_layout(
      height=550,
      margin=dict(t=70, b=60, l=60, r=40),
      xaxis=dict(
          title="<b>Kampnummer</b>",
          tickmode="linear",
          dtick=1,
          gridcolor="#f0f0f0",
          linecolor="black",
      ),
      yaxis=dict(
          title=f"<b>{label} pr. kamp</b>",
          gridcolor="#f0f0f0",
          linecolor="black",
          autorange="reversed" if is_reversed else True,
          range=y_range,
      ),
      plot_bgcolor="white",
      showlegend=False,
  )
  st.plotly_chart(fig, use_container_width=True)

# --- 3. HOVEDFUNKTION ---


def vis_side():
  valgt_saeson = "2026/2027"
  tilgængelige_hold = SEASON_LEAGUE_MAPPER.get(valgt_saeson, {}).get(
      DEFAULT_COMP, list(TEAMS.keys())
  )

  default_team_name = (
      "Hvidovre" if "Hvidovre" in tilgængelige_hold else tilgængelige_hold[0]
  )
  default_team_info = TEAMS.get(default_team_name, {})
  default_team_wyid = default_team_info.get("team_wyid", 7490)
  default_team_opta_uuid = default_team_info.get(
      "opta_uuid", "8gxd9ry2580pu1b1dd5ny9ymy"
  )

  tournament_opta_map = {
      "NordicBet Liga": "2mb332vncy4450vu14paj8844",
      "Superliga": "29actv1ohj8r10kd9hu0jnb0n",
  }
  current_opta_uuid = tournament_opta_map.get(
      DEFAULT_COMP, "2mb332vncy4450vu14paj8844"
  )
  comp_wyid = COMPETITIONS.get(DEFAULT_COMP, {}).get("wyid", 328)

  try:
    season_start_year = int(valgt_saeson.split("/")[0])
  except:
    season_start_year = 2026

  col_title, col_t, col_m = st.columns([1.8, 1.2, 1.0])

  col_t_val = (
      tilgængelige_hold.index(default_team_name)
      if default_team_name in tilgængelige_hold
      else 0
  )
  with col_t:
    valgt_hold = st.selectbox("Vælg hold:", tilgængelige_hold, index=col_t_val)
    valgt_team_info = TEAMS.get(valgt_hold, {})
    valgt_team_wyid = valgt_team_info.get("team_wyid", default_team_wyid)
    valgt_team_opta_uuid = valgt_team_info.get(
        "opta_uuid", default_team_opta_uuid
    )

  with col_m:
    metric_map = {
        # Nye sammensatte indekser
        "Offensiv Index": "OFFENSIV_INDEX",
        "Defensiv Index": "DEFENSIV_INDEX",
        # Offensiv / Generelt
        "xG": "EXPECTEDGOALS",
        "Mål": "GOALS",
        "Mål imod": "GOALS_AGAINST",
        "Skud total": "TOTALSCORINGATT",
        "Skud på mål": "ONTARGETSCORINGATT",
        "Skud forbi": "SHOTOFFTARGET",
        "Blokerede skud": "BLOCKEDSCORINGATT",
        "Mål fra indskiftere": "SUBSGOALS",
        # Afleveringer & Besiddelse
        "Afleveringer total": "TOTALPASS",
        "Præcise afleveringer": "ACCURATEPASS",
        "Boldbesiddelse (%)": "POSSESSIONPERCENTAGE",
        # Defensive / Duel / Andet
        "PPDA": "PPDA",
        "Hjørnespark (for)": "WONCORNERS",
        "Hjørnespark (mod)": "LOSTCORNERS",
        "Taklinger total": "TOTALTACKLE",
        "Vundne taklinger": "WONTACKLE",
        "Clearinger": "TOTALCLEARANCE",
        "Blokeringer (outfield)": "OUTFIELDERBLOCK",
        "Frispark vundet": "FKFOULWON",
        "Frispark tabt": "FKFOULLOST",
        "Redninger": "SAVES",
        "Mål imod (stat)": "GOALSCONCEDED",
        "Clean sheets": "CLEANSHEET",
    }
    sel_metric = st.selectbox("Parameter:", list(metric_map.keys()))

  with col_title:
    st.subheader(f"{valgt_hold} – Kampoversigt")
    st.caption(f"Udvikling i {DEFAULT_COMP} ({valgt_saeson})")

  df_matches = load_match_level_data(
      tournament_opta_uuid=current_opta_uuid,
      team_opta_uuid=valgt_team_opta_uuid,
      team_wyid=valgt_team_wyid,
      comp_wyid=comp_wyid,
      season_start_year=season_start_year,
  )
  draw_match_trend_chart(
      df_matches, metric_map[sel_metric], sel_metric, valgt_hold, valgt_saeson
  )


if __name__ == "__main__":
  vis_side()
