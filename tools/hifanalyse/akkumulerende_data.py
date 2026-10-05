# HIF-Data/tools/hifanalyse/akkumulerende_data.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io

# Importér fra dine eksisterende moduler
from data.sql.skud_data import load_league_data
from data.utils.team_mapping import SEASONS, SEASON_LEAGUE_MAPPER, TEAMS, TEAM_COLORS


def plot_accumulating_timeline(df_match, team_name, category, league_teams):
    """
    Genererer en akkumulerende graf over tid for et givent hold og kategori i Opta-stil.
    """
    fig, ax = plt.subplots(figsize=(10, 5))
    
    # Sorter hændelser efter tidspunkt, hvis det findes
    df_sorted = df_match.sort_values("EVENT_TIMESTAMP").copy() if "EVENT_TIMESTAMP" in df_match.columns else df_match.copy()
    
    # Sikr minut-kolonne
    if "EVENT_MINUTE" in df_sorted.columns:
        df_sorted["MINUT"] = df_sorted["EVENT_MINUTE"]
    else:
        df_sorted["MINUT"] = range(1, len(df_sorted) + 1)

    is_against = "Imod" in category
    is_xg = "xG" in category
    is_goal = "Mål" in category

    # Find ud af hvilke spillere/hændelser der tilhører holdet vs modstanderen
    # Vi mapper via team_mapping hvis muligt, ellers standard kolonne-tjek
    if "EVENT_CONTESTANT_OPTAUUID" in df_sorted.columns and team_name in TEAMS:
        target_uuid = TEAMS[team_name].get("opta_uuid")
        if is_against:
            df_data = df_sorted[df_sorted["EVENT_CONTESTANT_OPTAUUID"] != target_uuid]
        else:
            df_data = df_sorted[df_sorted["EVENT_CONTESTANT_OPTAUUID"] == target_uuid]
    else:
        # Fallback baseret på holdnavn kolonne hvis den findes
        if "KLUB_NAVN" in df_sorted.columns:
            if is_against:
                df_data = df_sorted[df_sorted["KLUB_NAVN"] != team_name]
            else:
                df_data = df_sorted[df_sorted["KLUB_NAVN"] == team_name]
        else:
            df_data = df_sorted

    # Vælg værdi baseret på kategori
    if is_xg:
        df_data["VAL"] = df_data["XG_RAW"] if "XG_RAW" in df_data.columns else 0.05
    elif is_goal:
        # EVENT_TYPEID 16 = Goal
        df_data["VAL"] = (df_data["EVENT_TYPEID"] == 16).astype(int)
    else:
        # Generelle skud / afslutninger (13=Miss, 14=Post, 15=Saved, 16=Goal)
        df_data["VAL"] = 1

    df_data = df_data.sort_values("MINUT")
    df_data["ACC_VAL"] = df_data["VAL"].cumsum()

    # Hent holdfarver hvis muligt
    primary_color = TEAM_COLORS.get(team_name, {}).get("primary", "#e57373" if is_against else "#81c784")

    if not df_data.empty:
        ax.step(df_data["MINUT"], df_data["ACC_VAL"], where="post", linewidth=2.5, label=category, color=primary_color)
        ax.fill_between(df_data["MINUT"], df_data["ACC_VAL"], step="post", alpha=0.2, color=primary_color)

    ax.set_title(f"Akkumuleret {category} - {team_name}", fontsize=14, fontweight="bold", color="white", pad=15)
    ax.set_xlabel("Kampens minutter", fontsize=11, color="white")
    ax.set_ylabel("Akkumuleret værdi", fontsize=11, color="white")
    
    # Mørkt tema / Opta-stil
    fig.patch.set_facecolor("#0e1117")
    ax.set_facecolor("#0e1117")
    ax.tick_params(colors="white")
    ax.xaxis.label.set_color("white")
    ax.yaxis.label.set_color("white")
    for spine in ax.spines.values():
        spine.set_edgecolor("white")

    ax.grid(True, linestyle="--", alpha=0.3)
    
    return fig


def vis_side():
    """
    Hovedfunktion der kaldes af appen. Viser side med dropdowns i højre side og graf.
    """
    st.markdown("### Akkumuleret Udvikling i Kampen")
    st.caption("Følg udviklingen af xG, mål, afslutninger og skud imod minut for minut.")

    # --- SIDEBAR / KONTROLVÆLGER (eller i højre hjørne) ---
    # Sæson- og turneringsvalg for at hente det rigtige UUID fra team_mapping.py
    col_top1, col_top2 = st.columns(2)
    with col_top1:
        valgt_saeson = st.selectbox("Vælg sæson", list(SEASONS.keys()), key="acc_saeson_sel")
    with col_top2:
        valgt_turnering = st.selectbox("Vælg turnering", list(SEASONS[valgt_saeson].keys()), key="acc_turnering_sel")

    # Hent det korrekte Opta UUID fra team_mapping
    liga_uuid = SEASONS[valgt_saeson][valgt_turnering]

    # Hent hold-liste for den valgte sæson og turnering
    tilgængelige_hold = SEASON_LEAGUE_MAPPER.get(valgt_saeson, {}).get(valgt_turnering, ["Hvidovre"])

    # Indlæs skuddata via skud_data.py funktionen
    with st.spinner("Henter skud- og hændelsesdata fra Snowflake..."):
        df_all = load_league_data(liga_uuid)

    if df_all.empty:
        st.warning("Ingen data fundet for denne turnering/sæson.")
        return

    # --- LAYOUT: Graf til venstre, Dropdowns i højre hjørne ---
    col_graf, col_filter = st.columns([3, 1])

    with col_filter:
        st.markdown("##### Indstillinger")
        
        # 1. Dropdown for valg af hold i højre hjørne
        valgte_hold = st.selectbox("Vælg hold", tilgængelige_hold, key="acc_hold_sel")
        
        # 2. Dropdown for valg af kategori i højre hjørne
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
            # Generer figur
            fig = plot_accumulating_timeline(df_all, valgte_hold, valgt_kategori, tilgængelige_hold)
            
            # Gem til bytes for visning og download som billede
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=300, bbox_inches='tight')
            buf.seek(0)
            img_bytes = buf.getvalue()
            plt.close(fig)

            # Vis som billede i Streamlit
            st.image(img_bytes, use_container_width=True)

            # Download-knap til billedet
            st.download_button(
                label="📸 Download akkumuleret graf som billede",
                data=img_bytes,
                file_name=f"akkumuleret_{valgt_kategori.lower().replace(' ', '_')}_{valgte_hold.lower()}.png",
                mime="image/png"
            )
        else:
            st.info("Ingen data tilgængelig for de valgte filtre.")

if __name__ == "__main__":
    vis_side()
