import streamlit as st
import pandas as pd
from data.utils.data.sql.teams import (
    def_load_season_team_average,
    hent_hurtig_stilling,
    hent_hold_formkurve
)

def vis_side():
    season_name = "2026/2027"
    # Sørg for at dette UUID peger på 2026/2027-kalenderen for NordicBet Liga i din database
    calendar_uuid = '2mb332vncy4450vu14paj8844' 

    st.markdown(f"### Holdets Nøgletal - Sæson {season_name}")
    
    # Hent data fra Snowflake
    df_season_stats = def_load_season_team_average(calendar_uuid)
    df_stilling = hent_hurtig_stilling(calendar_uuid)

    # Find Hvidovres Opta UUID ud fra stillingstabellen
    hvidovre_optauuid = None
    if df_stilling is not None and not df_stilling.empty:
        hv_row_st = df_stilling[df_stilling['HOLD'].str.contains("Hvidovre", case=False, na=False)]
        if not hv_row_st.empty:
            hvidovre_optauuid = hv_row_st.iloc[0].get('TEAM_ID')

    # Udtræk Hvidovres specifikke række fra sæsondata
    hvidovre_row = pd.Series()
    if hvidovre_optauuid and df_season_stats is not None and not df_season_stats.empty:
        match_row = df_season_stats[df_season_stats['TEAM_OPTAUUID'] == hvidovre_optauuid]
        if not match_row.empty:
            hvidovre_row = match_row.iloc[0]

    # Udtræk værdier til KPI-kort
    kampe_spillet = int(hvidovre_row.get('SPILLER_KAMPE', 0)) if not hvidovre_row.empty else 0
    maal_for = int(hvidovre_row.get('TOTAL_GOALS', 0)) if not hvidovre_row.empty else 0
    maal_imod = int(hvidovre_row.get('TOTAL_GOALS_AGAINST', 0)) if not hvidovre_row.empty else 0
    xg_pr_kamp = float(hvidovre_row.get('AVG_EXPECTEDGOALS', 0.0)) if not hvidovre_row.empty else 0.0
    boldbesiddelse = float(hvidovre_row.get('AVG_POSSESSION', 0.0)) if not hvidovre_row.empty else 0.0

    # Hent point fra stillingstabellen
    point = 0
    if df_stilling is not None and not df_stilling.empty:
        hv_stilling = df_stilling[df_stilling['HOLD'].str.contains("Hvidovre", case=False, na=False)]
        if not hv_stilling.empty:
            point = int(hv_stilling.iloc[0].get('P', 0))

    # --- 1. SEKTION: HOVEDOVERBLIK & NØGLEMETAL (KPI KORT) ---
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(label="Kampe Spillet", value=str(kampe_spillet))
    with col2:
        st.metric(label="Point", value=str(point))
    with col3:
        st.metric(label="Målscore", value=f"{maal_for} - {maal_imod}")
    with col4:
        st.metric(label="Forventede Mål (xG)", value=f"{xg_pr_kamp:.2f}", delta="pr. kamp")
    with col5:
        st.metric(label="Boldbesiddelse", value=f"{boldbesiddelse:.1f}%")

    st.divider()

    # --- 2. SEKTION: SENESTE RESULTATER OG TAKTISKE NØGLETAL ---
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### Seneste kampe")
        if hvidovre_optauuid:
            df_form = hent_hold_formkurve(calendar_uuid, hvidovre_optauuid, limit=5)
            if df_form is not None and not df_form.empty:
                recent_matches = pd.DataFrame({
                    "Kamp": df_form['CONTESTANTHOME_NAME'] + " - " + df_form['CONTESTANTAWAY_NAME'],
                    "Resultat": df_form['TOTAL_HOME_SCORE'].astype(str) + " - " + df_form['TOTAL_AWAY_SCORE'].astype(str),
                    "Form": df_form['RESULTAT']
                })
                st.dataframe(recent_matches, use_container_width=True, hide_index=True)
            else:
                st.info("Ingen formkurve-data fundet endnu.")
        else:
            st.info("Hvidovre ID ikke fundet i turneringen.")

    with col_right:
        st.markdown("#### Taktiske Nøgletal (Gennemsnit)")
        if not hvidovre_row.empty:
            tactical_stats = pd.DataFrame({
                "Parameter": ["Afslutninger pr. kamp", "Skud på mål pr. kamp", "Berøringer i felt pr. kamp", "Afleveringer pr. kamp", "Gule kort pr. kamp"],
                "Værdi": [
                    f"{float(hvidovre_row.get('AVG_TOTALSCORINGATT', 0)):.1f}",
                    f"{float(hvidovre_row.get('AVG_ONTARGETSCORINGATT', 0)):.1f}",
                    f"{float(hvidovre_row.get('AVG_TOUCHESINOPPBOX', 0)):.1f}",
                    f"{float(hvidovre_row.get('AVG_TOTALPASS', 0)):.1f}",
                    f"{float(hvidovre_row.get('AVG_TOTALYELLOW_CARDS', 0)):.1f}"
                ]
            })
            st.dataframe(tactical_stats, use_container_width=True, hide_index=True)
        else:
            st.info("Ingen taktisk data tilgængelig.")

    st.divider()

    # --- 3. SEKTION: TURNERINGSSTILLING ---
    st.markdown("### Stilling i Ligaen")
    if df_stilling is not None and not df_stilling.empty:
        st.dataframe(df_stilling[['POSITION', 'HOLD', 'K', 'V', 'U', 'T', 'MF', 'P']], use_container_width=True, hide_index=True)
    else:
        st.info("Kunne ikke indhente stillingstabellen.")
