import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from data.sql.skud_data import load_league_data
from data.utils.team_mapping import SEASONS, SEASON_LEAGUE_MAPPER, TEAMS, TEAM_COLORS

def vis_side():
    st.markdown("### Statistisk Analyse")
    st.caption("Analyser sammenhængen mellem forventede mål (xG) og faktiske mål pr. kamp.")
    
    # --- 1. FILTRE ---
    col_top1, col_top2 = st.columns(2)
    with col_top1:
        valgt_saeson = st.selectbox("Vælg sæson", list(SEASONS.keys()), key="reg_saeson_sel")
    with col_top2:
        valgt_turnering = st.selectbox("Vælg turnering", list(SEASONS[valgt_saeson].keys()), key="reg_turnering_sel")

    liga_uuid = SEASONS[valgt_saeson][valgt_turnering]
    tilgængelige_hold = SEASON_LEAGUE_MAPPER.get(valgt_saeson, {}).get(valgt_turnering, ["Hvidovre"])

    # --- 2. DATA INDLÆSNING ---
    with st.spinner("Henter data fra Snowflake..."):
        df_all = load_league_data(liga_uuid)

    if df_all.empty:
        st.warning("Ingen data fundet for denne turnering/sæson.")
        return

    # --- 3. HOLD-VALG & DATA BEHANDLING ---
    col_graf, col_filter = st.columns([3, 1])

    with col_filter:
        st.markdown("##### Indstillinger")
        valgte_hold = st.selectbox("Vælg hold", tilgængelige_hold, key="reg_hold_sel")

    with col_graf:
        target_uuid = TEAMS.get(valgte_hold, {}).get("opta_uuid")
        
        if "MATCH_OPTAUUID" not in df_all.columns:
            st.warning("Data mangler MATCH_OPTAUUID kolonne.")
            return

        # --- OPTIMERET DATA BEHANDLING ---
        if target_uuid and "EVENT_CONTESTANT_OPTAUUID" in df_all.columns:
            df_hold = df_all[df_all["EVENT_CONTESTANT_OPTAUUID"] == target_uuid].copy()
        elif "KLUB_NAVN" in df_all.columns:
            df_hold = df_all[df_all["KLUB_NAVN"] == valgte_hold].copy()
        else:
            st.error("Kunne ikke identificere holdet i datasættet.")
            return

        if df_hold.empty:
            st.info(f"Ingen kampdata fundet for {valgte_hold}.")
            return

        # Sæt er_maal til kun at være deciderede mål (f.eks. typeid 16, tilpas evt. hvis 13, 14, 15 er brændte chancer/skud)
        if "EVENT_TYPEID" in df_hold.columns:
            # Antager f.eks. at 16 er mål, og 13, 14, 15 er andre skudtyper (eller tilpas efter jeres Opta-setup)
            df_hold["er_maal"] = (df_hold["EVENT_TYPEID"] == 16).astype(int)
            df_hold["er_skud"] = df_hold["EVENT_TYPEID"].isin([13, 14, 15, 16]).astype(int)
        else:
            df_hold["er_maal"] = 0
            df_hold["er_skud"] = 0
        
        # Aggregering per kamp
        df_reg = df_hold.groupby("MATCH_OPTAUUID").agg({
            "XG_RAW": "sum",       # Total xG
            "er_maal": "sum",      # Antal mål
            "er_skud": "sum"       # Antal skud
        }).rename(columns={
            "XG_RAW": "xG", 
            "er_maal": "Maal", 
            "er_skud": "Skud"
        }).reset_index()

        # --- 4. VISUALISERING ---
        fig, ax = plt.subplots(figsize=(8, 5.5))
        primary_color = TEAM_COLORS.get(valgte_hold, {}).get("primary", "#1f77b4")

        # Vi kan evt. plotte kampe opdelt, eller lade scatter vise xG mod faktiske mål pr kamp,
        # hvor vi bruger f.eks. antal skud eller om det er mål til at farve/skalere prikkerne.
        # Her viser vi punkter pr. kamp: xG (total i kampen) vs Mål (total i kampen)
        
        # Hvis du vil vise alle skud som prikker, skal det gøres på skud-niveau i stedet for kamp-niveau.
        # Hvis det er på kamp-niveau, kan vi lade prikkerne repræsentere kampene, hvor størrelsen eller farven afspejler antallet af skud (13, 14, 15):
        
        sc = ax.scatter(
            df_reg["xG"], 
            df_reg["Maal"], 
            c=df_reg["Skud"], # Farv efter antal skud i kampen
            cmap="Blues", 
            s=80, 
            alpha=0.9, 
            edgecolors="black", 
            label="Kampe (farvet efter skud)"
        )
        cbar = plt.colorbar(sc, ax=ax)
        cbar.set_label("Antal skud i kampen")

        # Regressionslinje
        if len(df_reg) > 1:
            m, b = np.polyfit(df_reg["xG"], df_reg["Maal"], 1)
            x_range = np.linspace(df_reg["xG"].min(), df_reg["xG"].max(), 100)
            ax.plot(x_range, m*x_range + b, color="red", linestyle="--", linewidth=2, 
                    label=f"Trend (y={m:.2f}x+{b:.2f})")

        ax.set_title(f"xG vs. Faktiske Mål - {valgte_hold}", fontsize=13, fontweight="bold", pad=15)
        ax.set_xlabel("Forventede Mål (xG) pr. kamp", fontsize=10)
        ax.set_ylabel("Faktiske Mål pr. kamp", fontsize=10)

        # Design
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")
        ax.grid(True, linestyle="--", alpha=0.3)
        for spine in ax.spines.values():
            spine.set_edgecolor("black")
        ax.legend(loc="upper left")

        st.pyplot(fig)
        plt.close(fig)

        # --- 5. METRIKKER ---
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric("Total xG", f"{df_reg['xG'].sum():.2f}")
        with col_m2:
            st.metric("Faktiske Mål", int(df_reg["Maal"].sum()))

if __name__ == "__main__":
    vis_side()
