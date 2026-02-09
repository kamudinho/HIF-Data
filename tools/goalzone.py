import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from mplsoccer import VerticalPitch
import streamlit as st
import matplotlib.colors as mcolors

# --- ZONE DEFINITIONER (Behold dine nuværende) ---
ZONE_BOUNDARIES = {
    "Zone 1": {"y_min": 94.2, "y_max": 100.0, "x_min": 36.8, "x_max": 63.2},
    # ... indsæt alle dine zoner her ligesom før ...
    "Zone 8": {"y_min": 0.0, "y_max": 70.0, "x_min": 0.0, "x_max": 100.0}
}

def find_zone(x, y):
    for zone, b in ZONE_BOUNDARIES.items():
        if b["x_min"] <= x <= b["x_max"] and b["y_min"] <= y <= b["y_max"]:
            return zone
    return "Udenfor"

# --- HOLD VISNING (Den der fejlede) ---
def vis_side(df, kamp=None, hold_map=None):
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    # Mapping af hold
    if hold_map:
        df['HOLD_NAVN'] = df['TEAM_WYID'].astype(str).map({str(k): v for k, v in hold_map.items()})
    
    col1, col2 = st.columns(2)
    with col1:
        valgt_hold = st.selectbox("Vælg Hold:", ["Alle"] + sorted(df['HOLD_NAVN'].dropna().unique().tolist()))
    with col2:
        valgt_type = st.selectbox("Vis type:", ["Alle Skud", "Mål"], key="team_type")

    mask = df['PRIMARYTYPE'].str.contains('shot', case=False, na=False)
    if valgt_hold != "Alle": mask &= (df['HOLD_NAVN'] == valgt_hold)
    if valgt_type == "Mål": mask &= df['PRIMARYTYPE'].str.contains('goal', case=False, na=False)

    process_and_draw(df[mask].copy())

# --- INDIVIDUEL VISNING (Kobling til "Spillere"-ark) ---
def vis_individuel_side(df_events, df_spillere):
    # Rens kolonner
    df_events.columns = [str(c).strip().upper() for c in df_events.columns]
    df_spillere.columns = [str(c).strip().upper() for c in df_spillere.columns]

    # SAMMENKOBLING (Merge PLAYER_WYID med Spillere-arket for at få navne)
    # Vi antager df_spillere har kolonnerne: 'PLAYER_WYID' og 'PLAYER_NAME' (eller 'SPILLER')
    if 'PLAYER_NAME' not in df_events.columns:
        df_events = df_events.merge(df_spillere[['PLAYER_WYID', 'PLAYER_NAME']], on='PLAYER_WYID', how='left')

    col1, col2 = st.columns(2)
    with col1:
        spiller_liste = sorted(df_events['PLAYER_NAME'].dropna().unique().tolist())
        valgt_spiller = st.selectbox("Vælg Spiller:", spiller_liste)
    with col2:
        valgt_type = st.selectbox("Vis type:", ["Alle Skud", "Mål"], key="player_type")

    mask = df_events['PRIMARYTYPE'].str.contains('shot', case=False, na=False)
    mask &= (df_events['PLAYER_NAME'] == valgt_spiller)
    if valgt_type == "Mål": mask &= df_events['PRIMARYTYPE'].str.contains('goal', case=False, na=False)

    process_and_draw(df_events[mask].copy())

# --- FÆLLES LOGIK TIL AT TEGNE ---
def process_and_draw(df_skud):
    df_skud['LOCATIONX'] = pd.to_numeric(df_skud['LOCATIONX'], errors='coerce')
    df_skud['LOCATIONY'] = pd.to_numeric(df_skud['LOCATIONY'], errors='coerce')
    df_skud = df_skud.dropna(subset=['LOCATIONX', 'LOCATIONY'])
    
    df_skud['ZONE_ID'] = df_skud.apply(lambda row: find_zone(row['LOCATIONY'], row['LOCATIONX']), axis=1)
    
    zone_stats = df_skud['ZONE_ID'].value_counts().to_frame(name='Antal')
    total = zone_stats['Antal'].sum()
    zone_stats['Procent'] = (zone_stats['Antal'] / total * 100) if total > 0 else 0
    
    # Indsæt din draw_pitch_with_stats logik her...
    # (Den funktion du allerede har sendt tidligere)
