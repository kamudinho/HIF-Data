import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
import numpy as np
from mplsoccer import VerticalPitch

def vis_side(df_events, df_spillere, hold_map):
    HIF_ID = 38331
    HIF_RED = '#d31313'
    
    # --- 1. DATA INDLÆSNING (Direkte og uafhængig) ---
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    SHOT_CSV_PATH = os.path.join(BASE_DIR, 'shotevents.csv')

    if not os.path.exists(SHOT_CSV_PATH):
        st.error(f"Fandt ikke shotevents.csv på stien: {SHOT_CSV_PATH}")
        return

    # Læs rådata
    df_s = pd.read_csv(SHOT_CSV_PATH)
    df_s.columns = [str(c).strip().upper() for c in df_s.columns]

    # Rens PLAYER_WYID og TEAM_WYID
    df_s['PLAYER_WYID'] = df_s['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    
    # Filtrer til HIF (38331)
    if 'TEAM_WYID' in df_s.columns:
        df_s = df_s[pd.to_numeric(df_s['TEAM_WYID'], errors='coerce').fillna(0).astype(int) == HIF_ID].copy()

    # Navne mapping fra df_spillere
    s_df = df_spillere.copy()
    s_df.columns = [str(c).strip().upper() for c in s_df.columns]
    s_df['PLAYER_WYID'] = s_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    
    # Mapper navne (Fanger både 'NAVN' eller First+Last kombi)
    if 'NAVN' in s_df.columns:
        navne_dict = dict(zip(s_df['PLAYER_WYID'], s_df['NAVN']))
    else:
        navne_dict = dict(zip(s_df['PLAYER_WYID'], (s_df.get('FIRSTNAME', '') + ' ' + s_df.get('LASTNAME', '')).str.strip()))

    # Berig df_s
    df_s['SPILLER_NAVN'] = df_s['PLAYER_WYID'].map(navne_dict).fillna("Ukendt Spiller")
    df_s['MODSTANDER'] = df_s['OPPONENTTEAM_WYID'].apply(lambda x: hold_map.get(int(float(x)), f"Hold {x}") if pd.notna(x) else "Ukendt")
    
    # Tving tal-format
    for col in ['LOCATIONX', 'LOCATIONY', 'SHOTXG', 'MINUTE']:
        if col in df_s.columns:
            df_s[col] = pd.to_numeric(df_s[col], errors='coerce').fillna(0)

    # Boolean vasker
    def is_true(val):
        v = str(val).lower().strip()
        return v in ['true', '1', '1.0', 't']

    # --- 2. LAYOUT (Dit originale klasse layout) ---
    layout_venstre, layout_hoejre = st.columns([2, 1])

    with layout_hoejre:
        # Spiller vælger
        spiller_liste = sorted(df_s['SPILLER_NAVN'].unique().tolist())
        valgt_spiller = st.selectbox("Vælg spiller", ["Alle Spillere"] + spiller_liste)
        
        df_plot = (df_s if valgt_spiller == "Alle Spillere" else df_s[df_s['SPILLER_NAVN'] == valgt_spiller]).copy()
        df_plot = df_plot.sort_values(by=['MINUTE']).reset_index(drop=True)
        df_plot['SHOT_NR'] = df_plot.index + 1

        # Metrics
        shots = len(df_plot)
        goals = int(df_plot['SHOTISGOAL'].apply(is_true).sum()) if 'SHOTISGOAL' in df_plot.columns else 0
        xg_total = df_plot['SHOTXG'].sum()

        st.metric("Afslutninger", shots)
        st.metric("Mål", goals)
        st.metric("Total xG", f"{xg_total:.2f}")

        # Skudliste i expander
        with st.expander("Se skudliste", expanded=False):
            res_df = df_plot[['SHOT_NR', 'MINUTE', 'SPILLER_NAVN']].copy()
            res_df['MÅL'] = df_plot['SHOTISGOAL'].apply(lambda x: "⚽" if is_true(x) else "")
            st.dataframe(res_df, hide_index=True, use_container_width=True)

    with layout_venstre:
        # Banen
        pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#444444')
        fig, ax = pitch.draw(figsize=(6, 5))
        
        # Plot skuddene
        for _, row in df_plot.iterrows():
            goal = is_true(row.get('SHOTISGOAL', False))
            
            ax.scatter(row['LOCATIONY'], row['LOCATIONX'], 
                       s=150 if goal else 80, 
                       color='gold' if goal else HIF_RED,
                       edgecolors='white', 
                       linewidth=1.2 if goal else 0.5,
                       zorder=3,
                       alpha=0.9)
        
        st.pyplot(fig, bbox_inches='tight', pad_inches=0.05)
