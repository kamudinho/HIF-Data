#tools/hifanalyse/statistisk_analyse.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from data.sql.skud_data import load_league_data, load_passing_data
from data.utils.team_mapping import SEASONS, SEASON_LEAGUE_MAPPER, TEAMS, TEAM_COLORS

def vis_side():
    st.markdown("### Statistisk Analyse")
    st.caption("Analyser sammenhængen mellem pasningsvolumen, skud, mål og forventede mål (xG) pr. kamp.")
    
    # --- 1. FILTRE ---
    col_top1, col_top2 = st.columns(2)
    with col_top1:
        valgt_saeson = st.selectbox("Vælg sæson", list(SEASONS.keys()), key="reg_saeson_sel")
    with col_top2:
        valgt_turnering = st.selectbox("Vælg turnering", list(SEASONS[valgt_saeson].keys()), key="reg_turnering_sel")

    liga_uuid = SEASONS[valgt_saeson][valgt_turnering]
    tilgængelige_hold = SEASON_LEAGUE_MAPPER.get(valgt_saeson, {}).get(valgt_turnering, ["Hvidovre"])

    # --- 2. DATA INDLÆSNING (Både skud og pasninger) ---
    with st.spinner("Henter data fra Snowflake..."):
        df_shots_all = load_league_data(liga_uuid)
        df_passes_all = load_passing_data(liga_uuid)

    if df_shots_all.empty or df_passes_all.empty:
        st.warning("Ingen data fundet for denne turnering/sæson.")
        return

    # --- 3. HOLD-VALG & PASNINGSTYPE ---
    col_graf, col_filter = st.columns([3, 1])

    with col_filter:
        st.markdown("##### Indstillinger")
        valgte_hold = st.selectbox("Vælg hold", tilgængelige_hold, key="reg_hold_sel")
        
        pasningstype = st.selectbox(
            "Pasningstype", 
            ["Alle pasninger", "Fremadrettede pasninger (10+ m)"], 
            key="reg_pasningstype_sel"
        )

    with col_graf:
        target_uuid = TEAMS.get(valgte_hold, {}).get("opta_uuid")
        
        if not target_uuid:
            st.error("Kunne ikke finde opta_uuid for holdet.")
            return

        # Filtrer hold for skud-data
        if "EVENT_CONTESTANT_OPTAUUID" in df_shots_all.columns:
            df_hold_shots = df_shots_all[df_shots_all["EVENT_CONTESTANT_OPTAUUID"] == target_uuid].copy()
        else:
            st.error("Kunne ikke identificere holdet i skud-data.")
            return

        # Filtrer hold for pasnings-data
        if "EVENT_CONTESTANT_OPTAUUID" in df_passes_all.columns:
            df_hold_passes = df_passes_all[df_passes_all["EVENT_CONTESTANT_OPTAUUID"] == target_uuid].copy()
        else:
            st.error("Kunne ikke identificere holdet i pasnings-data.")
            return

        if df_hold_shots.empty or df_hold_passes.empty:
            st.info(f"Ingen kampdata fundet for {valgte_hold}.")
            return

        # --- BEHANDLING AF SKUD & MÅL ---
        if "EVENT_TYPEID" in df_hold_shots.columns:
            df_hold_shots["er_maal"] = (df_hold_shots["EVENT_TYPEID"] == 16).astype(int)
            df_hold_shots["er_skud"] = df_hold_shots["EVENT_TYPEID"].isin([13, 14, 15, 16]).astype(int)
        else:
            df_hold_shots["er_maal"] = 0
            df_hold_shots["er_skud"] = 0

        df_reg_shots = df_hold_shots.groupby("MATCH_OPTAUUID").agg({
            "XG_RAW": "sum",
            "er_maal": "sum",
            "er_skud": "sum"
        }).rename(columns={
            "XG_RAW": "xG",
            "er_maal": "Maal",
            "er_skud": "Skud"
        }).reset_index()

        # --- BEHANDLING AF PASNINGER ---
        if pasningstype == "Fremadrettede pasninger (10+ m)":
            df_hold_passes = df_hold_passes[df_hold_passes["IS_PROGRESSIVE_PASS"] == 1]
            pas_kolonne_navn = "Fremadrettede pasninger"
        else:
            pas_kolonne_navn = "Pasninger"

        df_reg_passes = df_hold_passes.groupby("MATCH_OPTAUUID").agg({
            "EVENT_OPTAUUID": "count"
        }).rename(columns={
            "EVENT_OPTAUUID": "Pasninger"
        }).reset_index()

        # Merge de to tabeller på kamp-id (MATCH_OPTAUUID)
        df_reg = pd.merge(df_reg_shots, df_reg_passes, on="MATCH_OPTAUUID", how="inner").fillna(0)

        if df_reg.empty:
            st.info(f"Ingen matchende kampdata for {valgte_hold}.")
            return

        # --- 4. VISUALISERING (Pasninger vs xG) ---
        fig, ax = plt.subplots(figsize=(8, 5.5))
        
        sc = ax.scatter(
            df_reg["Pasninger"], 
            df_reg["xG"], 
            c=df_reg["Maal"], 
            cmap="YlOrRd", 
            s=90, 
            alpha=0.9, 
            edgecolors="black"
        )
        cbar = plt.colorbar(sc, ax=ax)
        cbar.set_label("Faktiske mål i kampen")

        if len(df_reg) > 1:
            m, b = np.polyfit(df_reg["Pasninger"], df_reg["xG"], 1)
            x_range = np.linspace(df_reg["Pasninger"].min(), df_reg["Pasninger"].max(), 100)
            ax.plot(x_range, m*x_range + b, color="red", linestyle="--", linewidth=2, label="Trendlinje")

        ax.set_title(f"{pas_kolonne_navn} vs. Forventede Mål (xG) - {valgte_hold}", fontsize=12, fontweight="bold")
        ax.set_xlabel(f"Antal {pas_kolonne_navn.lower()} pr. kamp", fontsize=10)
        ax.set_ylabel("Forventede Mål (xG) pr. kamp", fontsize=10)
        ax.grid(True, linestyle="--", alpha=0.3)
        ax.legend()

        st.pyplot(fig)
        plt.close(fig)

        # --- 5. METRIKKER & TABEL ---
        st.markdown("---")
        st.markdown(f"#### Nøgletal for {valgte_hold}")
        
        m1, m2, m3 = st.columns(3)
        m1.metric(f"Gns. {pas_kolonne_navn.lower()} / kamp", f"{df_reg['Pasninger'].mean():.1f}")
        m2.metric("Gns. xG / kamp", f"{df_reg['xG'].mean():.2f}")
        m3.metric("Total mål / skud", f"{int(df_reg['Maal'].sum())} / {int(df_reg['Skud'].sum())}")

        with st.expander("Detaljeret kampdata"):
            st.dataframe(df_reg[["Pasninger", "Skud", "Maal", "xG"]].style.format(precision=2))

if __name__ == "__main__":
    vis_side()
