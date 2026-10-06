import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Importér fra dine eksisterende moduler
from data.sql.skud_data import load_league_data
from data.utils.team_mapping import SEASONS, SEASON_LEAGUE_MAPPER, TEAMS, TEAM_COLORS


def vis_side():
    st.markdown("### 📊 Regression & Statistisk Analyse")
    st.caption("Analyser sammenhængen mellem forventede mål (xG) og faktiske mål pr. kamp for det valgte hold.")

    # Top-filtre til sæson og turnering (præcis som i akkumulerende data)
    col_top1, col_top2 = st.columns(2)
    with col_top1:
        valgt_saeson = st.selectbox("Vælg sæson", list(SEASONS.keys()), key="reg_saeson_sel")
    with col_top2:
        valgt_turnering = st.selectbox("Vælg turnering", list(SEASONS[valgt_saeson].keys()), key="reg_turnering_sel")

    liga_uuid = SEASONS[valgt_saeson][valgt_turnering]
    tilgængelige_hold = SEASON_LEAGUE_MAPPER.get(valgt_saeson, {}).get(valgt_turnering, ["Hvidovre"])

    with st.spinner("Henter data fra Snowflake..."):
        df_all = load_league_data(liga_uuid)

    if df_all.empty:
        st.warning("Ingen data fundet for denne turnering/sæson.")
        return

    col_graf, col_filter = st.columns([3, 1])

    with col_filter:
        st.markdown("##### Indstillinger")
        valgte_hold = st.selectbox("Vælg hold", tilgængelige_hold, key="reg_hold_sel")

    with col_graf:
        target_uuid = TEAMS.get(valgte_hold, {}).get("opta_uuid")
        
        if "MATCH_OPTAUUID" not in df_all.columns:
            st.warning("Data mangler MATCH_OPTAUUID kolonne.")
            return

        # Aggreger data per kamp for det valgte hold
        match_stats = []
        for match_id, df_match in df_all.groupby("MATCH_OPTAUUID"):
            # Filtrer til det valgte hold
            if target_uuid and "EVENT_CONTESTANT_OPTAUUID" in df_match.columns:
                df_subset = df_match[df_match["EVENT_CONTESTANT_OPTAUUID"] == target_uuid]
            elif "KLUB_NAVN" in df_match.columns:
                df_subset = df_match[df_match["KLUB_NAVN"] == valgte_hold]
            else:
                continue

            if df_subset.empty:
                continue

            xg_sum = df_subset["XG_RAW"].sum() if "XG_RAW" in df_subset.columns else 0.0
            maal_sum = int((df_subset["EVENT_TYPEID"] == 16).sum()) if "EVENT_TYPEID" in df_subset.columns else 0

            match_stats.append({
                "MATCH_OPTAUUID": match_id,
                "xG": xg_sum,
                "Maal": maal_sum
            })

        df_reg = pd.DataFrame(match_stats)

        if df_reg.empty:
            st.info(f"Ingen kampdata fundet for {valgte_hold}.")
        else:
            # Opsæt matplotlib figur med hvid baggrund
            fig, ax = plt.subplots(figsize=(8, 5.5))
            primary_color = TEAM_COLORS.get(valgte_hold, {}).get("primary", "#1f77b4")

            ax.scatter(df_reg["xG"], df_reg["Maal"], color=primary_color, s=70, alpha=0.8, edgeports="black", label="Kampe")

            # Tilføj regressionslinje (Polyfit grad 1)
            if len(df_reg) > 1:
                m, b = np.polyfit(df_reg["xG"], df_reg["Maal"], 1)
                ax.plot(df_reg["xG"], m*df_reg["xG"] + b, color="red", linestyle="--", linewidth=2, label=f"Trend (y={m:.2f}x+{b:.2f})")

            ax.set_title(f"xG vs. Faktiske Mål - {valgte_hold}", fontsize=13, fontweight="bold", pad=15)
            ax.set_xlabel("Forventede Mål (xG)", fontsize=10)
            ax.set_ylabel("Faktiske Mål", fontsize=10)

            # Design elementer
            fig.patch.set_facecolor("white")
            ax.set_facecolor("white")
            ax.grid(True, linestyle="--", alpha=0.3)
            for spine in ax.spines.values():
                spine.set_edgecolor("black")
            ax.legend(loc="upper left")

            st.pyplot(fig)
            plt.close(fig)

            # Vis nøgletal
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.metric("Total xG", f"{df_reg['xG'].sum():.2f}")
            with col_m2:
                st.metric("Faktiske Mål", int(df_reg["Maal"].sum()))

if __name__ == "__main__":
    vis_side()
