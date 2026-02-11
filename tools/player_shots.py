import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from mplsoccer import VerticalPitch

def vis_side(df_events, df_spillere, hold_map):
    HIF_ID = 38331
    HIF_RED = '#d31313'

    # --- 1. DATA-PROCESSERING (Uændret) ---
    s_df = df_spillere.copy()
    s_df.columns = [str(c).strip().upper() for c in s_df.columns]
    
    s_df['FULL_NAME'] = s_df.apply(
        lambda x: f"{x.get('FIRSTNAME', '')} {x.get('LASTNAME', '')}".strip() if pd.notna(x.get('FIRSTNAME')) or pd.notna(x.get('LASTNAME')) else x.get('NAVN', "-"),
        axis=1
    )
    
    s_df['PLAYER_WYID'] = s_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    navne_dict = dict(zip(s_df['PLAYER_WYID'], s_df['FULL_NAME']))

    df = df_events.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()

    mask = df['PRIMARYTYPE'].str.contains('shot', case=False, na=False)
    if 'TEAM_WYID' in df.columns:
        mask &= (df['TEAM_WYID'].astype(float).astype(int) == HIF_ID)
    
    df_s = df[mask].copy()
    df_s['LOCATIONX'] = pd.to_numeric(df_s['LOCATIONX'], errors='coerce')
    df_s['LOCATIONY'] = pd.to_numeric(df_s['LOCATIONY'], errors='coerce')
    df_s = df_s.dropna(subset=['LOCATIONX', 'LOCATIONY'])

    if df_s.empty:
        st.info("Ingen afslutninger fundet for HIF.")
        return

    # Sortering: Modstander først, så Minut
    df_s['MODSTANDER'] = df_s['OPPONENTTEAM_WYID'].apply(lambda x: hold_map.get(int(x), f"Hold {x}") if pd.notna(x) else "Ukendt")
    df_s = df_s.sort_values(by=['MODSTANDER', 'MINUTE']).reset_index(drop=True)
    df_s['SHOT_NR'] = df_s.index + 1
    df_s['SPILLER_NAVN'] = df_s['PLAYER_WYID'].map(navne_dict).fillna("Ukendt Spiller")

    # --- 2. LAYOUT: BANE TIL VENSTRE, KONTROLLER TIL HØJRE ---
    # Vi bruger en 2:1 fordeling. Bane fylder 66%, kontroller fylder 33%.
    layout_venstre, layout_hoejre = st.columns([2, 1])

    with layout_hoejre:
        st.markdown("### Filtre & Data")
        spiller_liste = sorted(df_s['SPILLER_NAVN'].unique().tolist())
        valgt_spiller = st.selectbox("Vælg spiller", ["Alle Spillere"] + spiller_liste)
        
        # Popover gøres "bred" via use_container_width og placeres her
        with st.popover("🔎 Se data (Bred visning)", use_container_width=True):
            tabel_df = (df_s if valgt_spiller == "Alle Spillere" else df_s[df_s['SPILLER_NAVN'] == valgt_spiller]).copy()
            tabel_df['RESULTAT'] = tabel_df['PRIMARYTYPE'].apply(lambda x: "⚽ MÅL" if 'goal' in str(x).lower() else "❌ Skud")
            
            vis_tabel = tabel_df[['SHOT_NR', 'MODSTANDER', 'MINUTE', 'SPILLER_NAVN', 'RESULTAT']]
            vis_tabel.columns = ['Nr.', 'Modstander', 'Minut', 'Spiller', 'Resultat']
            
            # Vi tvinger containeren til at være bred så tabellen kan ses
            st.dataframe(vis_tabel, hide_index=True, use_container_width=True)

    with layout_venstre:
        df_plot = df_s if valgt_spiller == "Alle Spillere" else df_s[df_s['SPILLER_NAVN'] == valgt_spiller].copy()

        # --- 3. ANTI-OVERLAP (JITTER) ---
        if not df_plot.empty:
            df_plot['LOC_X_JITTER'] = df_plot['LOCATIONX'] + np.random.uniform(-0.6, 0.6, len(df_plot))
            df_plot['LOC_Y_JITTER'] = df_plot['LOCATIONY'] + np.random.uniform(-0.6, 0.6, len(df_plot))

        # --- 4. TEGN BANE ---
        pitch = VerticalPitch(
            half=True, 
            pitch_type='wyscout', 
            line_color='#444444', 
            line_zorder=2,
            pad_bottom=5,  
            pad_top=2
        )
        
        # Vi holder figuren kompakt i bredden (figsize 6 i stedet for 8)
        fig, ax = pitch.draw(figsize=(6, 5))
        ax.set_ylim(45, 102) 

        for _, row in df_plot.iterrows():
            is_goal = 'goal' in str(row['PRIMARYTYPE']).lower()
            
            ax.scatter(row['LOC_Y_JITTER'], row['LOC_X_JITTER'], 
                       s=300 if is_goal else 180, 
                       color=HIF_RED, 
                       edgecolors='white', 
                       linewidth=2.0 if is_goal else 0.8, 
                       alpha=0.9, 
                       zorder=3)
            
            ax.text(row['LOC_Y_JITTER'], row['LOC_X_JITTER'], str(int(row['SHOT_NR'])), 
                    color='white', ha='center', va='center', fontsize=6, fontweight='bold', zorder=4)

        st.pyplot(fig)
