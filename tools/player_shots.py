import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from mplsoccer import VerticalPitch

def vis_side(df_events, df_spillere, hold_map):
    HIF_ID = 38331
    HIF_RED = '#d31313'

    # --- 1. DATA-RENSNING (Vigtig pga. multiline format) ---
    df = df_events.copy()
    
    # Fjern rækker der reelt er "rester" af tags fra SecondaryType
    # Vi ved at en rigtig række starter med et PLAYER_WYID (et tal)
    df = df[pd.to_numeric(df['PLAYER_WYID'], errors='coerce').notna()].copy()
    
    df.columns = [str(c).strip().upper() for c in df.columns]
    df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].strip()

    # Mapping af navne
    s_df = df_spillere.copy()
    s_df.columns = [str(c).strip().upper() for c in s_df.columns]
    s_df['PLAYER_WYID'] = s_df['PLAYER_WYID'].astype(str).str.split('.').str[0].strip()
    navne_dict = dict(zip(s_df['PLAYER_WYID'], (s_df['FIRSTNAME'].fillna('') + ' ' + s_df['LASTNAME'].fillna('')).str.strip()))

    # Filtrering
    mask = df['PRIMARYTYPE'].str.contains('shot', case=False, na=False)
    if 'TEAM_WYID' in df.columns:
        mask &= (df['TEAM_WYID'].astype(float).astype(int) == HIF_ID)
    df_s = df[mask].copy()

    # Tving tal-formater
    for col in ['LOCATIONX', 'LOCATIONY', 'SHOTXG', 'MINUTE']:
        if col in df_s.columns:
            df_s[col] = pd.to_numeric(df_s[col], errors='coerce').fillna(0)

    if df_s.empty:
        st.warning("Data kunne ikke læses korrekt. Tjek CSV-formatering.")
        return

    # Modstander og Spiller navne
    df_s['MODSTANDER'] = df_s['OPPONENTTEAM_WYID'].apply(lambda x: hold_map.get(int(float(x)), f"Hold {x}") if pd.notna(x) else "Ukendt")
    df_s['SPILLER_NAVN'] = df_s['PLAYER_WYID'].map(navne_dict).fillna("Ukendt Spiller")
    df_s = df_s.sort_values(by=['MINUTE']).reset_index(drop=True)
    df_s['SHOT_NR'] = df_s.index + 1

    # --- BOOLEAN CHECK (Baseret på din fil: TRUE/FALSE) ---
    def is_true(val):
        v = str(val).upper().strip()
        return v in ['TRUE', '1', '1.0']

    # --- 2. LAYOUT ---
    layout_venstre, layout_hoejre = st.columns([2, 1])

    with layout_hoejre:
        spiller_liste = sorted(df_s['SPILLER_NAVN'].unique().tolist())
        valgt_spiller = st.selectbox("Vælg spiller", ["Alle Spillere"] + spiller_liste)
        
        df_plot = (df_s if valgt_spiller == "Alle Spillere" else df_s[df_s['SPILLER_NAVN'] == valgt_spiller]).copy()

        # Metrics
        shots = len(df_plot)
        goals = int(df_plot['SHOTISGOAL'].apply(is_true).sum()) if 'SHOTISGOAL' in df_plot.columns else 0
        xg_total = df_plot['SHOTXG'].sum()

        st.metric("Afslutninger", shots)
        st.metric("Mål", goals)
        st.metric("Total xG", f"{xg_total:.2f}")

        with st.expander("Se skudliste"):
            res_df = df_plot[['SHOT_NR', 'MINUTE', 'SPILLER_NAVN']].copy()
            res_df['MÅL'] = df_plot['SHOTISGOAL'].apply(lambda x: "⚽" if is_true(x) else "")
            st.dataframe(res_df, hide_index=True)

    with layout_venstre:
        pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#444444')
        fig, ax = pitch.draw(figsize=(6, 5))
        
        for _, row in df_plot.iterrows():
            goal = is_true(row.get('SHOTISGOAL', False))
            ax.scatter(row['LOCATIONY'], row['LOCATIONX'], 
                       s=150 if goal else 80, 
                       color=HIF_RED if not goal else 'gold',
                       edgecolors='white', zorder=3)
        
        st.pyplot(fig)
