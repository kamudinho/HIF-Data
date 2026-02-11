import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from mplsoccer import VerticalPitch

def vis_side(df_events, df_spillere, hold_map):
    HIF_ID = 38331
    HIF_RED = '#d31313'
    DARK_GREY = '#413B4D'

    # --- 1. DATA-PROCESSERING ---
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

    # Tilføj modstander-navn og sorter (Hold -> Minut)
    df_s['MODSTANDER'] = df_s['OPPONENTTEAM_WYID'].apply(lambda x: hold_map.get(int(x), f"Hold {x}") if pd.notna(x) else "Ukendt")
    df_s = df_s.sort_values(by=['MODSTANDER', 'MINUTE']).reset_index(drop=True)
    df_s['SHOT_NR'] = df_s.index + 1
    df_s['SPILLER_NAVN'] = df_s['PLAYER_WYID'].map(navne_dict).fillna("Ukendt Spiller")

    # --- 2. UI FILTRE ---
    spiller_liste = sorted(df_s['SPILLER_NAVN'].unique().tolist())
    valgt_spiller = st.selectbox("Vælg spiller", ["Alle Spillere"] + spiller_liste)
    
    df_plot = df_s if valgt_spiller == "Alle Spillere" else df_s[df_s['SPILLER_NAVN'] == valgt_spiller].copy()

    # --- 3. ANTI-OVERLAP (JITTER) ---
    if not df_plot.empty:
        df_plot['LOC_X_JITTER'] = df_plot['LOCATIONX'] + np.random.uniform(-0.6, 0.6, len(df_plot))
        df_plot['LOC_Y_JITTER'] = df_plot['LOCATIONY'] + np.random.uniform(-0.6, 0.6, len(df_plot))

# --- 4. TEGN BANE (Kompakt halvbane) ---
    pitch = VerticalPitch(
        half=True, 
        pitch_type='wyscout', 
        line_color='#444444', 
        line_zorder=2,
        pad_bottom=5,  
        pad_top=2
    )
    
    # Vi sætter højden ned til 5.5 for at gøre den mere skærmvenlig
    fig, ax = pitch.draw(figsize=(8, 5.5))
    
    # Vi beholder 45 for at få buen med, men lader lærredet være mindre
    ax.set_ylim(45, 102) 

    for _, row in df_plot.iterrows():
        is_goal = 'goal' in str(row['PRIMARYTYPE']).lower()
        color = HIF_RED if is_goal else DARK_GREY
        
        ax.scatter(row['LOC_Y_JITTER'], row['LOC_X_JITTER'], 
                   s=350 if is_goal else 220, # En anelse mindre prikker til mindre bane
                   color=color, edgecolors='white', linewidth=1.2, alpha=0.9, zorder=3)
        
        ax.text(row['LOC_Y_JITTER'], row['LOC_X_JITTER'], str(int(row['SHOT_NR'])), 
                color='white', ha='center', va='center', fontsize=6, fontweight='bold', zorder=4)

    # --- 5. VISNING (Skalering via kolonner) ---
    # Ved at bruge [0.2, 0.6, 0.2] tvinger vi banen ned i størrelse,
    # så den ikke optager for meget vertikal plads.
    l, c, r = st.columns([0.2, 0.6, 0.2]) 
    with c:
        st.pyplot(fig)
        
        with st.popover(f"🔎 Se detaljer for {valgt_spiller}"):
            tabel_df = df_plot.copy()
            tabel_df['RESULTAT'] = tabel_df['PRIMARYTYPE'].apply(lambda x: "⚽ MÅL" if 'goal' in str(x).lower() else "❌ Skud")
            
            vis_tabel = tabel_df[['SHOT_NR', 'MODSTANDER', 'MINUTE', 'SPILLER_NAVN', 'RESULTAT']]
            vis_tabel.columns = ['Nr.', 'Modstander', 'Minut', 'Spiller', 'Resultat']
            
            st.dataframe(vis_tabel, hide_index=True, use_container_width=True)
