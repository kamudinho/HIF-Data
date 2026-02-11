import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
import numpy as np
from mplsoccer import VerticalPitch

def vis_side(df_events, df_spillere, hold_map):
    HIF_ID = 38331
    HIF_RED = '#d31313'
    
    # --- 1. DATA INDLÆSNING ---
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    SHOT_CSV_PATH = os.path.join(BASE_DIR, 'shotevents.csv')

    if not os.path.exists(SHOT_CSV_PATH):
        st.error(f"Fandt ikke shotevents.csv")
        return

    df_s = pd.read_csv(SHOT_CSV_PATH)
    df_s.columns = [str(c).strip().upper() for c in df_s.columns]
    
    # Rens og filtrer til HIF
    df_s['PLAYER_WYID'] = df_s['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    df_s = df_s[pd.to_numeric(df_s['TEAM_WYID'], errors='coerce').fillna(0).astype(int) == HIF_ID].copy()

    # Navne mapping
    s_df = df_spillere.copy()
    s_df.columns = [str(c).strip().upper() for c in s_df.columns]
    s_df['PLAYER_WYID'] = s_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    navne_dict = dict(zip(s_df['PLAYER_WYID'], s_df['NAVN']))

    df_s['SPILLER_NAVN'] = df_s['PLAYER_WYID'].map(navne_dict).fillna("Ukendt Spiller")
    df_s['MODSTANDER'] = df_s['OPPONENTTEAM_WYID'].apply(lambda x: hold_map.get(int(float(x)), f"Hold {x}") if pd.notna(x) else "Ukendt")

    def is_true(val):
        v = str(val).lower().strip()
        return v in ['true', '1', '1.0', 't']

    # --- 2. LAYOUT ---
    layout_venstre, layout_hoejre = st.columns([2, 1])

    with layout_hoejre:
        spiller_liste = sorted(df_s['SPILLER_NAVN'].unique().tolist())
        valgt_spiller = st.selectbox("Vælg spiller", ["Alle Spillere"] + spiller_liste)
        
        df_plot = (df_s if valgt_spiller == "Alle Spillere" else df_s[df_s['SPILLER_NAVN'] == valgt_spiller]).copy()
        df_plot = df_plot.sort_values(by=['MINUTE']).reset_index(drop=True)

        # --- BEREGNING AF DE 6 METRICS ---
        shots = len(df_plot)
        goals = int(df_plot['SHOTISGOAL'].apply(is_true).sum()) if 'SHOTISGOAL' in df_plot.columns else 0
        on_target = int(df_plot['SHOTONTARGET'].apply(is_true).sum()) if 'SHOTONTARGET' in df_plot.columns else 0
        xg_total = pd.to_numeric(df_plot['SHOTXG'], errors='coerce').sum()
        
        # Afledte metrics
        xg_per_shot = xg_total / shots if shots > 0 else 0
        goal_ratio = (goals / shots) * 100 if shots > 0 else 0

        # Visning af metrics i to rækker
        m1, m2 = st.columns(2)
        m1.metric("Afslutninger", shots)
        m2.metric("Mål", goals)
        
        m3, m4 = st.columns(2)
        m3.metric("Total xG", f"{xg_total:.2f}")
        m4.metric("xG pr. afslutning", f"{xg_per_shot:.2f}")
        
        m5, m6 = st.columns(2)
        m5.metric("Skud på mål", on_target)
        m6.metric("Mål-ratio", f"{goal_ratio:.1f}%")

        with st.expander("Se skudliste"):
            res_df = df_plot.copy()
            res_df['RESULTAT'] = df_plot['SHOTISGOAL'].apply(lambda x: "⚽ MÅL" if is_true(x) else "Skud")
            st.dataframe(res_df[['MINUTE', 'SPILLER_NAVN', 'MODSTANDER', 'RESULTAT']], hide_index=True)

    with layout_venstre:
        # BANEN - Vi bruger VerticalPitch til at vise angrebsretningen opad
        pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#444444', goal_type='box')
        fig, ax = pitch.draw(figsize=(8, 7))
        
        # Plot skud
        for _, row in df_plot.iterrows():
            goal = is_true(row.get('SHOTISGOAL', False))
            on_tgt = is_true(row.get('SHOTONTARGET', False))
            
            # Størrelse baseret på xG (hvis tilgængelig)
            marker_size = (row.get('SHOTXG', 0.1) * 500) + 100
            
            ax.scatter(row['LOCATIONY'], row['LOCATIONX'], 
                       s=marker_size, 
                       color='gold' if goal else (HIF_RED if on_tgt else 'white'),
                       edgecolors='black', 
                       linewidth=1,
                       alpha=0.8,
                       zorder=3)
        
        # Legend/Forklaring
        st.pyplot(fig)
        st.caption("🟡 Mål | 🔴 På mål | ⚪ Forbi/Blokeret | Størrelse indikerer xG værdi")
