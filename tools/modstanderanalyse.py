#tools/modstanderanalyse.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import VerticalPitch

def vis_side(df_team_matches, hold_map, df_events):
    # --- 1. KONFIGURATION AF TURNERINGSNAVNE ---
    # Her kan du give dine IDs pæne navne
    COMP_NAMES = {
        3134: "Superliga",
        329: "NordicBet Liga",
        43319: "Oddset Pokalen",
        331: "2. Division",
        1305: "Champions League",
        1570: "Europa League"
    }

    if df_team_matches is None or df_team_matches.empty:
        st.error("Kunne ikke finde kampdata.")
        return

    # --- 2. DOBBELT-DROPDOWN: TURNERING OG SÅ HOLD ---
    # Find alle unikke turneringer i dit datasæt
    aktive_comp_ids = df_team_matches['SEASON_WYID'].unique() # Eller COMPETITION_WYID hvis kolonnen findes
    
    # Hvis din df_team_matches har COMPETITION_WYID, bruger vi den:
    # (Hvis ikke, kan vi ofte udlede det fra matches)
    if 'COMPETITION_WYID' not in df_team_matches.columns:
        # Midlertidig løsning hvis kolonnen mangler: Vis alle hold samlet
        turneringer = ["Alle valgte turneringer"]
    else:
        comp_ids = df_team_matches['COMPETITION_WYID'].unique()
        turneringer = [COMP_NAMES.get(int(cid), f"Turnering {cid}") for cid in comp_ids]

    col_sel1, col_sel2, col_sel3 = st.columns([1.5, 1.5, 1])
    
    with col_sel1:
        valgt_turnering = st.selectbox("Vælg Turnering:", options=sorted(turneringer))

    # Filtrer hold baseret på turnering
    if valgt_turnering == "Alle valgte turneringer":
        df_comp_filter = df_team_matches
    else:
        # Find ID'et på den valgte turnering
        inv_comp_names = {v: k for k, v in COMP_NAMES.items()}
        target_comp_id = inv_comp_names.get(valgt_turnering)
        df_comp_filter = df_team_matches[df_team_matches['COMPETITION_WYID'] == target_comp_id]

    # Byg hold-listen baseret på den valgte turnering
    tilgaengelige_ids = df_comp_filter['TEAM_WYID'].unique()
    navne_dict = {hold_map.get(str(int(tid)), f"Ukendt ({tid})"): tid for tid in tilgaengelige_ids}
    
    with col_sel2:
        valgt_navn = st.selectbox("Vælg modstander:", options=sorted(navne_dict.keys()))
    
    with col_sel3:
        halvdel = st.radio("Fokus:", ["Modstanders halvdel", "Egen halvdel"], horizontal=True)

    # --- RESTEN AF ANALYSEN ---
    valgt_id = navne_dict[valgt_navn]
    df_f = df_team_matches[df_team_matches['TEAM_WYID'] == valgt_id].copy()

    # (Herfra fortsætter koden med main_left, main_right og Heatmaps som før...)
