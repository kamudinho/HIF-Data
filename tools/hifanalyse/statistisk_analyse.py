#tools/hifanalyse/statistisk_analyse.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from data.sql.skud_data import load_league_data
from data.utils.team_mapping import SEASONS, SEASON_LEAGUE_MAPPER, TEAMS, TEAM_COLORS

def vis_side():
    st.markdown("### Statistisk Analyse")
    st.caption("Analyser effektivitet (mål og skud) i forhold til antallet af pasninger.")
    
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
        
        if target_uuid and "EVENT_CONTESTANT_OPTAUUID" in df_all.columns:
            df_hold = df_all[df_all["EVENT_CONTESTANT_OPTAUUID"] == target_uuid].copy()
        else:
            st.error("Kunne ikke identificere holdet.")
            return

        if df_hold.empty:
            st.info(f"Ingen data fundet for {valgte_hold}.")
            return

        # --- DEFINER EFFEKTIVITET ---
        # 1 = Pasning, 13-16 = Skud, 16 = Mål
        df_hold["er_pasning"] = (df_hold["EVENT_TYPEID"] == 1).astype(int)
        df_hold["er_skud"] = df_hold["EVENT_TYPEID"].isin([13, 14, 15, 16]).astype(int)
        df_hold["er_maal"] = (df_hold["EVENT_TYPEID"] == 16).astype(int)
        
        # Aggregering per kamp
        df_reg = df_hold.groupby("MATCH_OPTAUUID").agg({
            "XG_RAW": "sum",
            "er_maal": "sum",
            "er_skud": "sum",
            "er_pasning": "sum"
        }).rename(columns={
            "XG_RAW": "xG", 
            "er_maal": "Maal", 
            "er_skud": "Skud",
            "er_pasning": "Pasninger"
        }).reset_index()

        # Beregn effektivitet pr. 100 pasninger
        # Vi bruger .replace(0, np.nan) for at undgå division med nul (giver NaN i stedet for inf)
        df_reg["Maal_pr_100_pas"] = (df_reg["Maal"] / df_reg["Pasninger"].replace(0, np.nan) * 100)
        df_reg["Skud_pr_100_pas"] = (df_reg["er_skud"] / df_reg["Pasninger"].replace(0, np.nan) * 100)

        # --- 4. VISUALISERING ---
        # Vi viser her: Pasninger (x-akse) vs Mål (y-akse) for at se volumen vs effektivitet
        fig, ax = plt.subplots(figsize=(8, 5.5))
        
        sc = ax.scatter(
            df_reg["Pasninger"], 
            df_reg["Maal"], 
            c=df_reg["xG"], # Farv efter xG for at se om de scorer mere/mindre end forventet
            cmap="viridis", 
            s=100, 
            alpha=0.8, 
            edgecolors="black"
        )
        cbar = plt.colorbar(sc, ax=ax)
        cbar.set_label("Total xG i kampen")

        if len(df_reg) > 1:
            m, b = np.polyfit(df_reg["Pasninger"], df_reg["Maal"], 1)
            x_range = np.linspace(df_reg["Pasninger"].min(), df_reg["Pasninger"].max(), 100)
            ax.plot(x_range, m*x_range + b, color="red", linestyle="--", alpha=0.5, label="Trendlinje")

        ax.set_title(f"Kamp-volumen: Pasninger vs. Mål ({valgte_hold})", fontsize=12, fontweight="bold")
        ax.set_xlabel("Antal pasninger pr. kamp", fontsize=10)
        ax.set_ylabel("Antal mål pr. kamp", fontsize=10)
        ax.grid(True, linestyle="--", alpha=0.3)
        ax.legend()

        st.pyplot(fig)
        plt.close(fig)

        # --- 5. METRIKKER (EFFEKTIVITET) ---
        st.markdown("---")
        st.markdown(f"#### Effektivitets-gennemsnit for {valgte_hold}")
        
        m1, m2, m3 = st.columns(3)
        
        avg_maal_pas = df_reg["Maal_pr_100_pas"].mean()
        avg_skud_pas = df_reg["Skud_pr_100_pas"].mean()
        total_xg = df_reg["xG"].sum()
        total_maal = df_reg["Maal"].sum()

        m1.metric("Mål pr. 100 pasninger", f"{avg_maal_pas:.2f}")
        m2.metric("Skud pr. 100 pasninger", f"{avg_skud_pas:.2f}")
        m3.metric("Konvertering (xG/Mål)", f"{total_maal/total_xg:.2f}x")

        # Tabel med rådata
        with st.expander("Se detaljeret kamp-data"):
            st.dataframe(df_reg[["Pasninger", "Skud", "Maal", "xG", "Maal_pr_100_pas"]].style.format(precision=2))

if __name__ == "__main__":
    vis_side()
