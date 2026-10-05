# HIF-Data/tools/hifanalyse/akkumulerende_data.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import io
import requests
from PIL import Image

# Importér fra dine eksisterende moduler
from data.sql.skud_data import load_league_data
from data.utils.team_mapping import SEASONS, SEASON_LEAGUE_MAPPER, TEAMS, TEAM_COLORS


def get_logo(url):
    """
    Henter og konverterer et logo fra URL vha. din foretrukne metode.
    """
    if not url:
        return None
    try:
        response = requests.get(url, timeout=5)
        img = Image.open(io.BytesIO(response.content)).convert("RGBA")
        img.thumbnail((30, 30))
        return img
    except Exception:
        return None


def get_opponent_logo(match_df, team_name):
    """
    Finder modstanderens logo-URL via Opta UUID eller klubnavn og henter billedet.
    """
    modstander_navn = None
    target_uuid = TEAMS.get(team_name, {}).get("opta_uuid")
    
    if "EVENT_CONTESTANT_OPTAUUID" in match_df.columns:
        opp_uuids = match_df["EVENT_CONTESTANT_OPTAUUID"].unique()
        for u in opp_uuids:
            if u and u != target_uuid:
                for t_name, t_info in TEAMS.items():
                    if t_info.get("opta_uuid") == u:
                        modstander_navn = t_name
                        break
            if modstander_navn:
                break

    if not modstander_navn and "KLUB_NAVN" in match_df.columns:
        klubber_i_kamp = match_df["KLUB_NAVN"].unique().tolist()
        modstandere = [k for k in klubber_i_kamp if str(k).strip().lower() != str(team_name).strip().lower()]
        if modstandere:
            modstander_navn = modstandere[0]

    logo_url = None
    if modstander_navn:
        if modstander_navn in TEAMS and "logo" in TEAMS[modstander_navn]:
            logo_url = TEAMS[modstander_navn]["logo"]
        else:
            for team_key, team_info in TEAMS.items():
                if str(team_key).strip().lower() == str(modstander_navn).strip().lower():
                    if "logo" in team_info:
                        logo_url = team_info["logo"]
                        break

    return get_logo(logo_url)


def plot_accumulating_matches_timeline(df_all, team_name, category):
    """
    Genererer en akkumulerende graf med hvid baggrund, hvor linjen og fyldet når helt ud til kanterne.
    """
    is_against = "Imod" in category
    is_xg = "xG" in category
    is_goal = "Mål" in category

    target_uuid = TEAMS.get(team_name, {}).get("opta_uuid")

    if "MATCH_OPTAUUID" not in df_all.columns:
        fig, ax = plt.subplots(figsize=(11, 5.5))
        ax.text(0.5, 0.5, "Data mangler MATCH_OPTAUUID kolonne.", color="black", ha="center", va="center", transform=ax.transAxes)
        return fig

    match_data_list = []
    
    for match_id, df_match in df_all.groupby("MATCH_OPTAUUID"):
        if df_match.empty or len(df_match) < 2:
            continue

        involveret_uuid = False
        if target_uuid and "EVENT_CONTESTANT_OPTAUUID" in df_match.columns:
            if target_uuid in df_match["EVENT_CONTESTANT_OPTAUUID"].values:
                involveret_uuid = True
                
        involveret_navn = False
        if "KLUB_NAVN" in df_match.columns:
            if team_name in df_match["KLUB_NAVN"].values:
                involveret_navn = True

        if not (involveret_uuid or involveret_navn):
            continue

        logo_img = get_opponent_logo(df_match, team_name)

        if target_uuid and "EVENT_CONTESTANT_OPTAUUID" in df_match.columns:
            if is_against:
                df_subset = df_match[df_match["EVENT_CONTESTANT_OPTAUUID"] != target_uuid]
            else:
                df_subset = df_match[df_match["EVENT_CONTESTANT_OPTAUUID"] == target_uuid]
        elif "KLUB_NAVN" in df_match.columns:
            if is_against:
                df_subset = df_match[df_match["KLUB_NAVN"] != team_name]
            else:
                df_subset = df_match[df_match["KLUB_NAVN"] == team_name]
        else:
            df_subset = df_match

        if is_xg:
            val = df_subset["XG_RAW"].sum() if "XG_RAW" in df_subset.columns else 0.0
        elif is_goal:
            val = int((df_subset["EVENT_TYPEID"] == 16).sum())
        else:
            val = len(df_subset)

        timestamp = df_match["EVENT_TIMESTAMP"].min() if "EVENT_TIMESTAMP" in df_match.columns else 0

        match_data_list.append({
            "MATCH_OPTAUUID": match_id,
            "TIMESTAMP": timestamp,
            "MATCH_VAL": val,
            "LOGO_IMG": logo_img
        })

    if not match_data_list:
        fig, ax = plt.subplots(figsize=(11, 5.5))
        ax.text(0.5, 0.5, f"Ingen spillede kampe fundet for {team_name}", color="black", ha="center", va="center", transform=ax.transAxes)
        return fig

    df_matches = pd.DataFrame(match_data_list)
    df_matches = df_matches.sort_values("TIMESTAMP").drop_duplicates(subset=["MATCH_OPTAUUID"]).reset_index(drop=True)
    
    df_matches["KAMP_NR"] = range(1, len(df_matches) + 1)
    df_matches["ACC_VAL"] = df_matches["MATCH_VAL"].cumsum()

    num_matches = len(df_matches)

    # Dynamisk bredde baseret på antal kampe
    fig_width = max(11, num_matches * 0.4)
    fig, ax = plt.subplots(figsize=(fig_width, 5.5))

    primary_color = TEAM_COLORS.get(team_name, {}).get("primary", "#e57373" if is_against else "#1f77b4")

    ax.step(df_matches["KAMP_NR"], df_matches["ACC_VAL"], where="mid", linewidth=2.5, label=category, color=primary_color)
    ax.plot(df_matches["KAMP_NR"], df_matches["ACC_VAL"], marker="o", markersize=5, color=primary_color)
    ax.fill_between(df_matches["KAMP_NR"], df_matches["ACC_VAL"], step="mid", alpha=0.15, color=primary_color)

    ax.set_title(f"Akkumuleret {category} per kamp - {team_name}", fontsize=14, fontweight="bold", color="black", pad=25)
    ax.set_ylabel(f"Akkumuleret {category}", fontsize=11, color="black")
    
    ax.set_xticks(df_matches["KAMP_NR"])
    ax.set_xticklabels([])

    # Sæt x-aksen til at starte præcist ved 1 og slutte ved sidste kamp, så det når helt ud til kanterne
    ax.set_xlim(1, num_matches)

    # Dynamisk logo-zoom
    logo_zoom = max(0.55, min(0.6, 5.5 / num_matches))

    for idx, row in df_matches.iterrows():
        x_pos = row["KAMP_NR"]
        logo = row["LOGO_IMG"]
        
        if logo is not None:
            imagebox = OffsetImage(logo, zoom=logo_zoom)
            ab = AnnotationBbox(imagebox, (x_pos, 0), xybox=(0, -28),
                                xycoords=('data', 'axes fraction'),
                                boxcoords="offset points", frameon=False, pad=0)
            ax.add_artist(ab)
        else:
            ax.text(x_pos, -0.05, f"K{x_pos}", transform=ax.get_xaxis_transform(),
                    ha='center', va='top', color='black', fontsize=9)

    # Hvid baggrund og standard lyselementer
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.tick_params(colors="black")
    ax.xaxis.label.set_color("black")
    ax.yaxis.label.set_color("black")
    for spine in ax.spines.values():
        spine.set_edgecolor("black")

    ax.grid(True, linestyle="--", alpha=0.3)
    ax.set_ylim(bottom=min(0, df_matches["ACC_VAL"].min() - 0.5))
    
    return fig


def vis_side():
    st.markdown("### Akkumuleret Udvikling med Modstanderlogoer")
    st.caption("Følg holdets udvikling runde for runde med modstandernes logoer på x-aksen.")

    col_top1, col_top2 = st.columns(2)
    with col_top1:
        valgt_saeson = st.selectbox("Vælg sæson", list(SEASONS.keys()), key="acc_saeson_sel")
    with col_top2:
        valgt_turnering = st.selectbox("Vælg turnering", list(SEASONS[valgt_saeson].keys()), key="acc_turnering_sel")

    liga_uuid = SEASONS[valgt_saeson][valgt_turnering]
    tilgængelige_hold = SEASON_LEAGUE_MAPPER.get(valgt_saeson, {}).get(valgt_turnering, ["Hvidovre"])

    with st.spinner("Henter skud- og hændelsesdata fra Snowflake..."):
        df_all = load_league_data(liga_uuid)

    if df_all.empty:
        st.warning("Ingen data fundet for denne turnering/sæson.")
        return

    col_graf, col_filter = st.columns([3, 1])

    with col_filter:
        st.markdown("##### Indstillinger")
        valgte_hold = st.selectbox("Vælg hold", tilgængelige_hold, key="acc_hold_sel")
        kategorier = [
            "xG (For)", 
            "Mål (For)", 
            "Afslutninger (For)", 
            "xG (Imod)", 
            "Skud (Imod)"
        ]
        valgt_kategori = st.selectbox("Vælg kategori", kategorier, key="acc_kat_sel")

    with col_graf:
        if not df_all.empty:
            fig = plot_accumulating_matches_timeline(df_all, valgte_hold, valgt_kategori)
            
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=300, bbox_inches='tight')
            buf.seek(0)
            img_bytes = buf.getvalue()
            plt.close(fig)

            st.image(img_bytes, use_container_width=True)

            st.download_button(
                label="📸 Download graf med logoer som billede",
                data=img_bytes,
                file_name=f"akkumuleret_logoer_{valgt_kategori.lower().replace(' ', '_')}_{valgte_hold.lower()}.png",
                mime="image/png"
            )
        else:
            st.info("Ingen data tilgængelig for de valgte filtre.")

if __name__ == "__main__":
    vis_side()
