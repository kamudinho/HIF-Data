import streamlit as st
import pandas as pd
import numpy as np
import os
from mplsoccer import VerticalPitch
from matplotlib.patches import Rectangle
import matplotlib.colors as mcolors

def vis_side(df_input, df_spillere):
    HIF_ID = 38331
    HIF_RED = '#d31313'

    # --- 1. DATA-PROCESSERING ---
    df_s = df_input.copy()
    df_s.columns = [str(c).strip().upper() for c in df_s.columns]
    
    # Filtrér på hold (TEAM_WYID)
    df_s = df_s[pd.to_numeric(df_s['TEAM_WYID'], errors='coerce') == HIF_ID].copy()
    
    # Klargør spillerliste og filtrér skud-data til kun at gælde aktive spillere
    s_df = df_spillere.copy()
    s_df.columns = [str(c).strip().upper() for c in s_df.columns]
    
    # Rens PLAYER_WYID (fjern .0)
    s_df['PLAYER_WYID'] = s_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    df_s['PLAYER_WYID'] = df_s['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    
    # Behold kun skud fra spillere i din players-fil
    aktive_ids = set(s_df['PLAYER_WYID'].unique())
    df_s = df_s[df_s['PLAYER_WYID'].isin(aktive_ids)].copy()

    # Konverter koordinater og xG
    for col in ['LOCATIONX', 'LOCATIONY', 'SHOTXG']:
        df_s[col] = pd.to_numeric(df_s[col], errors='coerce')
    df_s = df_s.dropna(subset=['LOCATIONX', 'LOCATIONY'])

    # Map navne fra players.csv
    navne_dict = dict(zip(s_df['PLAYER_WYID'], s_df['NAVN']))
    df_s['SPILLER_NAVN'] = df_s['PLAYER_WYID'].map(navne_dict)
    
    # Zone beregning
    df_s['ZONE_ID'] = df_s.apply(lambda row: find_zone(row['LOCATIONY'], row['LOCATIONX']), axis=1)

    # --- 2. LAYOUT ---
    l_venstre, l_hoejre = st.columns([2, 1])

    with l_hoejre:
        mode = st.radio("Visning:", ["Hold", "Individuel"], horizontal=True)
        
        if mode == "Individuel":
            spiller_liste = sorted(df_s['SPILLER_NAVN'].dropna().unique().tolist())
            valgt = st.selectbox("Vælg spiller", options=spiller_liste)
            df_plot = df_s[df_s['SPILLER_NAVN'] == valgt].copy()
        else:
            df_plot = df_s.copy()

        # Metrics
        total_shots = len(df_plot)
        goals = int(df_plot['SHOTISGOAL'].astype(str).str.lower().isin(['true', '1', 't']).sum())
        xg_sum = df_plot['SHOTXG'].sum()
        
        st.metric("Afslutninger", total_shots)
        st.metric("Mål", goals)
        st.metric("Total xG", f"{xg_sum:.2f}")
        st.metric("xG pr. skud", f"{(xg_sum/total_shots) if total_shots > 0 else 0:.2f}")

    with l_venstre:
        # Tegn banen (Wyscout bruger 0-100 koordinater)
        pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#000000', line_alpha=0.5)
        fig, ax = pitch.draw(figsize=(6, 8))
        ax.set_ylim(40, 102) # Fokus på modstanderens banehalvdel

        

        # Heatmap logik
        zone_counts = df_plot['ZONE_ID'].value_counts()
        max_val = zone_counts.max() if not zone_counts.empty else 1
        cmap = mcolors.LinearSegmentedColormap.from_list('HIF', ['#ffffff', HIF_RED])

        for name, b in ZONE_BOUNDARIES.items():
            if b["y_min"] < 40 and name == "Zone 8": continue
            
            count = zone_counts.get(name, 0)
            alpha = 0.4 if count > 0 else 0.05
            
            rect = Rectangle((b["x_min"], b["y_min"]), b["x_max"] - b["x_min"], b["y_max"] - b["y_min"], 
                             facecolor=cmap(count/max_val), alpha=alpha, zorder=1)
            ax.add_patch(rect)
            
            if count > 0:
                ax.text(b["x_min"] + (b["x_max"]-b["x_min"])/2, b["y_min"] + (b["y_max"]-b["y_min"])/2,
                        str(int(count)), ha='center', va='center', fontsize=10, fontweight='bold')

        st.pyplot(fig)
