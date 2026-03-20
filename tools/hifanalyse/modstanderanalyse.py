import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch
import requests
from io import BytesIO
from PIL import Image
import json
from data.utils.team_mapping import TEAMS, TEAM_COLORS

def vis_side(analysis_package=None):
    try:
        if not analysis_package:
            st.error("Ingen datapakke modtaget.")
            return

        # --- DATA PREP ---
        df_matches = analysis_package.get("matches", pd.DataFrame()).copy()
        opta_dict = analysis_package.get("opta", {})
        df_events = opta_dict.get("opta_events", pd.DataFrame()).copy()
        df_in = analysis_package.get("shapes_in", pd.DataFrame()).copy()
        df_out = analysis_package.get("shapes_out", pd.DataFrame()).copy()

        # Tjek om vi overhovedet har kolonner før vi omdøber
        for df in [df_matches, df_events, df_in, df_out]:
            if not df.empty:
                df.columns = [c.upper() for c in df.columns]

        # --- DEBUG CHECK (Vises kun hvis der er knas) ---
        if df_matches.empty:
            st.warning("Advarsel: 'matches' DataFrame er tom. Tjek din SQL query.")
        
        # --- HOLD VÆLGER LOGIK ---
        all_teams = []
        if 'CONTESTANTHOME_NAME' in df_matches.columns:
            all_teams = sorted(list(set(df_matches['CONTESTANTHOME_NAME'].dropna().tolist() + 
                                      df_matches['CONTESTANTAWAY_NAME'].dropna().tolist())))
        
        if not all_teams:
            all_teams = ["Ingen hold fundet"]
            
        valgt_hold = st.selectbox("Vælg hold:", all_teams)

        # --- UUID OPSLAG ---
        hold_uuid = ""
        if not df_matches.empty and valgt_hold != "Ingen hold fundet":
            mask = (df_matches['CONTESTANTHOME_NAME'] == valgt_hold) | (df_matches['CONTESTANTAWAY_NAME'] == valgt_hold)
            match_row = df_matches[mask]
            if not match_row.empty:
                row = match_row.iloc[0]
                hold_uuid = str(row['CONTESTANTHOME_OPTAUUID'] if row['CONTESTANTHOME_NAME'] == valgt_hold else row['CONTESTANTAWAY_OPTAUUID']).lower()

        # --- VISNING ---
        st.write(f"Valgt: {valgt_hold} (ID: {hold_uuid})")
        
        tabs = st.tabs(["STATISTIK", "DATA TJEK"])
        with tabs[0]:
            st.info("Her kommer din grafik, når vi har bekræftet data.")
        with tabs[1]:
            st.write("Kolonner i Matches:", df_matches.columns.tolist())
            st.dataframe(df_matches.head(3))

    except Exception as e:
        st.error(f"⚠️ Appen fejlede med følgende besked: {str(e)}")
        st.exception(e) # Dette viser den præcise linje hvor det går galt
