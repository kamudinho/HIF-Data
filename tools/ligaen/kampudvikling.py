#tools/ligaen/kampudvikling.py
import base64
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# Importér det delte SQL-udtræk
from data.sql.kampe import load_match_level_data
from data.utils.team_mapping import (
    COMPETITION_NAME as DEFAULT_COMP,
    TOURNAMENTCALENDAR_NAME as DEFAULT_SEASON,
    COMPETITIONS,
    SEASON_LEAGUE_MAPPER,
    SEASONS,
    TEAMS,
)

# --- 1. HJÆLPEFUNKTIONER TIL UI ---

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

def draw_match_trend_chart(df_matches, metric, label, team_name, valgt_saeson):
    if df_matches is None or df_matches.empty:
        st.warning("Ingen kampdata tilgængelig for dette hold i den valgte sæson.")
        return

    fig = go.Figure()
    df_matches[metric] = pd.to_numeric(df_matches[metric], errors="coerce").fillna(0)
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
        val1_str = f"{int(total_val)}" if total_val == int(total_val) else f"{total_val:.2f}"
        val2_str = mean_str
    else:
        formatted_label = "xG" if label == "xG" else label.lower()
        formatted_label2 = "xG" if label == "xG" else label.capitalize()
        total_str = f"{int(total_val)}" if total_val == int(total_val) else f"{total_val:.2f}"
        label_line1 = f"Antal {formatted_label} i {valgt_saeson}:"
        label_line2 = f"{formatted_label2} pr. 90 i {valgt_saeson}:"
        val1_str = total_str
        val2_str = mean_str

    fig.add_annotation(
        text=f"{label_line1}<br>{label_line2}",
        xref="paper", yref="paper", x=0.67, y=1.08,
        xanchor="left", yanchor="top", showarrow=False, align="left",
        font=dict(size=11, color="black"),
    )
    fig.add_annotation(
        text=f"<b>{val1_str}</b><br><b>{val2_str}</b>",
        xref="paper", yref="paper", x=0.94, y=1.08,
        xanchor="left", yanchor="top", showarrow=False, align="left",
        font=dict(size=11, color="black"),
    )

    liga_avg_col = f"LIGA_AVG_{metric}"
    if liga_avg_col in df_matches.columns and not df_matches[liga_avg_col].dropna().empty:
        ligasnit = df_matches[liga_avg_col].dropna().iloc[0]
    else:
        ligasnit = y_vals.mean()

    opp_names = []
    opp_logos = []
    hover_texts = []

    current_team_info = TEAMS.get(team_name, {})
    current_team_uuid = current_team_info.get("opta_uuid", "")

    for _, row in df_matches.iterrows():
        home_uuid = row.get("CONTESTANTHOME_OPTAUUID")
        away_uuid = row.get("CONTESTANTAWAY_OPTAUUID")
        row_team_uuid = row.get("TEAM_OPTAUUID")

        if current_team_uuid:
            if current_team_uuid == home_uuid:
                opp_uuid = away_uuid
            else:
                opp_uuid = home_uuid
        else:
            opp_uuid = away_uuid if row_team_uuid == home_uuid else home_uuid

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

        is_shot_metric = label in [
            "Skud total", "Skud på mål", "Skud forbi", "Blokerede skud",
        ]

        if is_shot_metric:
            tot_shots = safe_int(row.get("TOTALSCORINGATT", 0))
            on_target = safe_int(row.get("ONTARGETSCORINGATT", 0))
            off_target = safe_int(row.get("SHOTOFFTARGET", 0))
            blocked = safe_int(row.get("BLOCKEDSCORINGATT", 0))

            tot_str = f"<b>Skud total: {tot_shots}</b>" if label == "Skud total" else f"Skud total: {tot_shots}"
            on_str = f"<b>Skud på mål: {on_target}</b>" if label == "Skud på mål" else f"Skud på mål: {on_target}"
            off_str = f"<b>Skud forbi: {off_target}</b>" if label == "Skud forbi" else f"Skud forbi: {off_target}"
            blk_str = f"<b>Skud blokeret: {blocked}</b>" if label == "Blokerede skud" else f"Skud blokeret: {blocked}"

            hover_texts.append(
                f"<b>Kamp {int(row['MATCH_NUM'])} vs. {o_name}</b><br>"
                f"Dato: {dato}<br>"
                f"Resultat: {g_for} - {g_imod}<br>"
                f"{tot_str}<br>{on_str}<br>{off_str}<br>{blk_str}"
            )
        else:
            hover_texts.append(
                f"<b>Kamp {int(row['MATCH_NUM'])} vs. {o_name}</b><br>"
                f"Dato: {dato}<br>"
                f"Resultat: {g_for} - {g_imod}<br>"
                f"<b>{label}: {val_metric:.2f}</b>"
            )

    df_matches["OPP_NAME"] = opp_names
    df_matches["OPP_LOGO"] = opp_logos
    df_matches["HOVER_TEXT"] = hover_texts

    is_reversed = "PPDA" in label.upper() or "IMOD" in label.upper()

    # 1. Tegn linjer mellem punkterne
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
                    x=[x0, x1], y=[y0, y1], mode="lines",
                    line=dict(color=seg_color, width=2, dash="dot"),
                    showlegend=False, hoverinfo="skip",
                )
            )

    # 2. Usynlige punkter for hover-funktionalitet
    fig.add_trace(
        go.Scatter(
            x=df_matches["MATCH_NUM"], y=df_matches[metric], mode="markers",
            marker=dict(size=40, opacity=0),
            hovertext=df_matches["HOVER_TEXT"], hoverinfo="text",
            showlegend=False,
        )
    )

    if is_reversed:
        team_pos = "top right" if snit_vaerdi < ligasnit else "bottom right"
        liga_pos = "bottom right" if snit_vaerdi < ligasnit else "top right"
    else:
        team_pos = "top right" if snit_vaerdi >= ligasnit else "bottom right"
        liga_pos = "bottom right" if snit_vaerdi >= ligasnit else "top right"

    padding = y_span * 0.15 if y_span > 0 else 1.0
    y_range = [y_max + padding, y_min - padding] if is_reversed else [y_min - padding, y_max + padding]

    fig.update_layout(
        height=550,
        margin=dict(t=70, b=60, l=60, r=40),
        xaxis=dict(
            title="<b>Kampnummer</b>", tickmode="linear", dtick=1,
            gridcolor="#f0f0f0", linecolor="black",
        ),
        yaxis=dict(
            title=f"<b>{label} pr. kamp</b>", gridcolor="#f0f0f0",
            linecolor="black", autorange="reversed" if is_reversed else True,
            range=y_range,
        ),
        plot_bgcolor="white", showlegend=False,
    )

    # 3. Sararota giddu-galeessaa (add_hline) kan darbu, garuu amma isaan booda add_layout_image ni fe'ama
    fig.add_hline(
        y=snit_vaerdi, line_dash="solid", line_color="black", line_width=1.5,
        annotation_text=f"(Gennemsnit: {team_name})", annotation_position=team_pos,
    )
    fig.add_hline(
        y=ligasnit, line_dash="dash", line_color="gray", line_width=1.5,
        annotation_text=f"(Gennemsnit: {DEFAULT_COMP})", annotation_position=liga_pos,
    )

    # 4. LOGOOWWAN: Erga sararri fi hundi dhumanii booda, isaan kana dabalna akkasumas layer="below" geedsisuudhaan
    # Ykn akka sararri jala ta'uuf, nuti add_layout_image duraan dursineetiin ala amma kanaan 
    # sararoota fi waan hunda dura akka kaayamu (underneath) gochuuf 'layer="below"' fayyadamuu dandeenya, 
    # garuu logoowwan olkaasuuf `layer="above"` fi koodii armaan gadii fayyadamna.
    
    logo_size_x = 0.65
    logo_size_y = y_span * 0.20 if y_span > 0.5 else 0.25

    for _, row in df_matches.iterrows():
        if row.get("OPP_LOGO"):
            b64_logo = get_base64_image(row["OPP_LOGO"])
            fig.add_layout_image(
                dict(
                    source=b64_logo, xref="x", yref="y",
                    x=row["MATCH_NUM"], y=row[metric],
                    sizex=logo_size_x, sizey=logo_size_y,
                    xanchor="center", yanchor="middle", layer="above",
                )
            )

    st.plotly_chart(fig, use_container_width=True)

# --- 2. HOVEDFUNKTION FOR SIDEN ---

def vis_side():
    valgt_saeson = DEFAULT_SEASON
    tilgængelige_hold = SEASON_LEAGUE_MAPPER.get(valgt_saeson, {}).get(DEFAULT_COMP, list(TEAMS.keys()))

    default_team_name = "Hvidovre" if "Hvidovre" in tilgængelige_hold else tilgængelige_hold[0]
    default_team_info = TEAMS.get(default_team_name, {})
    default_team_wyid = default_team_info.get("team_wyid", 7490)
    default_team_opta_uuid = default_team_info.get("opta_uuid", "8gxd9ry2580pu1b1dd5ny9ymy")

    tournament_opta_map = {
        "NordicBet Liga": "2mb332vncy4450vu14paj8844",
        "Superliga": "29actv1ohj8r10kd9hu0jnb0n",
    }
    current_opta_uuid = tournament_opta_map.get(DEFAULT_COMP, "2mb332vncy4450vu14paj8844")
    comp_wyid = COMPETITIONS.get(DEFAULT_COMP, {}).get("wyid", 328)

    try:
        season_start_year = int(valgt_saeson.split("/")[0])
    except:
        season_start_year = 2026

    col_title, col_t, col_m = st.columns([1.8, 1.2, 1.0])

    col_t_val = tilgængelige_hold.index(default_team_name) if default_team_name in tilgængelige_hold else 0
    with col_t:
        valgt_hold = st.selectbox("Vælg hold:", tilgængelige_hold, index=col_t_val)
        valgt_team_info = TEAMS.get(valgt_hold, {})
        valgt_team_wyid = valgt_team_info.get("team_wyid", default_team_wyid)
        valgt_team_opta_uuid = valgt_team_info.get("opta_uuid", default_team_opta_uuid)

    with col_m:
        metric_map = {
            "Offensiv Index": "OFFENSIV_INDEX",
            "Defensiv Index": "DEFENSIV_INDEX",
            "xG": "EXPECTEDGOALS",
            "Mål": "GOALS",
            "Mål fra indskiftere": "SUBSGOALS",
            "Mål imod": "GOALS_AGAINST",
            "Skud total": "TOTALSCORINGATT",
            "Skud på mål": "ONTARGETSCORINGATT",
            "Skud forbi": "SHOTOFFTARGET",
            "Blokerede skud": "BLOCKEDSCORINGATT",
            "Afleveringer total": "TOTALPASS",
            "Præcise afleveringer": "ACCURATEPASS",
            "Boldbesiddelse (%)": "POSSESSIONPERCENTAGE",
            "PPDA": "PPDA",
            "Hjørnespark (for)": "WONCORNERS",
            "Hjørnespark (mod)": "LOSTCORNERS",
            "Tacklinger": "TOTALTACKLE",
            "Succesfulde tacklinger": "WONTACKLE",
            "Clearinger": "TOTALCLEARANCE",
            "Blokeringer": "OUTFIELDERBLOCK",
            "Frispark vundet": "FKFOULWON",
            "Frispark begået": "FKFOULLOST",
            "Redninger": "SAVES",
            "Clean sheets": "CLEANSHEET",
        }
        sel_metric = st.selectbox("Parameter:", list(metric_map.keys()))

    if sel_metric == "Offensiv Index":
        st.markdown(
            """
            <div style="border: 1px solid black; padding: 10px 15px; border-radius: 5px; background-color: #f9f9f9; margin-bottom: 15px; white-space: nowrap; overflow-x: auto;">
                <b>Offensivt Index:</b> Vurderer holdets samlede chanceskabelse baseret på følgende kategorier: xG, Mål, Skud på mål, Skud total og Berøringer i modstanderens felt.
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif sel_metric == "Defensiv Index":
        st.markdown(
            """
            <div style="border: 1px solid black; padding: 10px 15px; border-radius: 5px; background-color: #f9f9f9; margin-bottom: 15px; white-space: nowrap; overflow-x: auto;">
                <b>Defensivt Index:</b> Vurderer holdets evne til at forsvare baseret på følgende kategorier: Vundne tacklinger, Clearinger, Blokeringer, Clean sheets, Mål imod og Modstanderens berøringer i feltet.
            </div>
            """,
            unsafe_allow_html=True,
        )

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
