# tools/hifanalyse/varmekort.py
import matplotlib.colors as colors
import matplotlib.pyplot as plt
from mplsoccer import Pitch
import numpy as np
import pandas as pd
import streamlit as st

# Ret importen, så den henter _get_snowflake_conn korrekt
from data.data_load import _get_snowflake_conn
# Importér fra jeres mapping og SQL-lag
from data.sql.zone_heatmaps import hent_team_zone_passes
from data.utils.team_mapping import COMPETITIONS, SEASONS


def vis_side():
    st.markdown("### ⚽ Pasningszoner (3x4 Gitter) - Holdoversigt")
    st.markdown(
        "Visualisering af afleveringsfordeling fordelt på et 3x4 banegitter i "
        "forhold til liga-gennemsnittet."
    )

    # --- 1. SESSION / FILTER KONTROL ---
    col1, col2 = st.columns(2)
    with col1:
        selected_season = st.selectbox(
            "Vælg Sæson:", list(SEASONS.keys()), index=0
        )
    with col2:
        selected_comp = st.selectbox(
            "Vælg Turnering:", list(SEASONS[selected_season].keys()), index=0
        )

    # Hent den korrekte Tournament Calendar UUID ud fra mappingen
    calendar_uuid = SEASONS[selected_season][selected_comp]

    st.info(f"Henter data for {selected_comp} ({selected_season})...")

    # --- 2. HENT DATA FRA SNOWFLAKE (Brug samme metode som resten af appen) ---
    conn = _get_snowflake_conn()
    df_zones = hent_team_zone_passes(conn, calendar_uuid)

    if df_zones.empty:
        st.warning(
            "Ingen data fundet for denne turnering/sæson. Tjek om kampe er spillet "
            "og om UUID'en er korrekt."
        )
        return
    
    # Resten af koden kører uændret...
