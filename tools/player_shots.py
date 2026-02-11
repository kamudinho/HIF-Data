import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from mplsoccer import VerticalPitch

def vis_side(df_events, df_spillere, hold_map):
    HIF_ID = 38331
    HIF_RED = '#d31313'

    # --- 1. DATA-PROCESSERING ---
    df = df_events.copy()
    
    # Sørg for at alle kolonnenavne er store (matcher HIF-dash merge)
    df.columns = [str(c).strip().upper() for c in df.columns]

    # FIX: Fjern brudstykker/tomme rækker og rens PLAYER_WYID korrekt
    if 'PLAYER_WYID' in df.columns:
        df = df[pd.to_numeric(df['PLAYER_WYID'], errors='coerce').notna()].copy()
        # Her er fixet: Tilføjet .str før .strip() for at undgå AttributeError
        df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()

    # Mapping af navne fra spillere-filen
    s_df = df_spillere.copy()
    s_df.columns = [str(c).strip().upper() for c in s_df.columns]
    if 'PLAYER_WYID' in s_df.columns:
        s_df['PLAYER_WYID'] = s_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    
    # Lav navne-dict (bruger NAVN hvis den findes, ellers First+Last)
    if 'NAVN' in s_df.columns:
        navne_dict = dict(zip(s_df['PLAYER_WYID'], s_df['NAVN']))
    else:
        s_df['FULL_NAME'] = (s_df.get('FIRSTNAME', '').fillna('') + ' ' + s_df.get('LASTNAME', '').fillna('')).str.strip()
        navne_dict = dict(zip(s_df['PLAYER_WYID'], s_df['FULL_NAME']))

    # Filtrering: Kun skud fra HIF
    mask = df['PRIMARYTYPE'].str.contains('shot', case=False, na=False)
    if 'TEAM_WYID' in df.columns:
        # Vi sikrer os at TEAM_WYID tjekkes som heltal
        mask &= (pd.to_numeric(df['TEAM_WYID'], errors='coerce').fillna(0).astype(int) == HIF_ID)
    
    df_s = df[mask].copy()

    # Tving tal-formater til koordinater og xG
    for col in ['LOCATIONX', 'LOCATIONY', 'SHOTXG', 'MINUTE']:
        if col in df_s.columns:
            df_s[col] = pd.to_numeric(df_s[col], errors='coerce').fillna(0)

    if df_s.empty:
        st.warning("Ingen afslutninger fundet. Tjek om TEAM_WYID (38331) findes i din data.")
        return

    # Berig data med modstander og pæne navne
    df_s['MODSTANDER'] = df_s['OPPONENTTEAM_WYID'].apply(lambda x: hold_map.get(int(float(x)), f"Hold {x}") if pd.notna(x) else "Ukendt")
    df_s['SPILLER_NAVN'] = df_s['PLAYER_WYID'].map(navne_dict).fillna("Ukendt Spiller")
    df_s = df_s.sort_values(by=['MINUTE']).reset_index(drop=True)
    df_s['SHOT_NR'] = df_s.index + 1

    # Hjælpefunktion til at læse TRUE/FALSE korrekt fra din fil
    def is_true(val):
        v = str(val).upper().strip()
        return v in ['TRUE', '1', '1.0']

    # --- 2. LAYOUT ---
    layout_venstre, layout_hoejre = st.columns([2, 1])

    with layout_hoejre:
        spiller_liste = sorted(df_s['SPILLER_NAVN'].unique().tolist())
        valgt_spiller = st.selectbox("Vælg spiller", ["Alle Spillere"] + spiller_liste)
        
        df_plot = (df_s if valgt_spiller == "Alle Spillere" else df_s[df_s['SPILLER_NAVN'] == valgt_spiller]).copy()

        # Metrics beregninger
        shots = len(df_plot)
        # Tæller mål baseret på is_true logikken
        goals = int(df_plot['SHOTISGOAL'].apply(is_true).sum()) if 'SHOTISGOAL' in df_plot.columns else 0
        xg_total = df_plot['SHOTXG'].sum() if 'SHOTXG' in df_plot.columns else 0.0

        st.metric("Afslutninger", shots)
        st.metric("Mål", goals)
        st.metric("Total xG", f"{xg_total:.2f}")

        with st.expander("Se skudliste", expanded=False):
            res_df = df_plot[['SHOT_NR', 'MINUTE', 'SPILLER_NAVN']].copy()
            res_df['MÅL'] = df_plot['SHOTISGOAL'].apply(lambda x: "⚽" if is_true(x) else "")
            st.dataframe(res_df, hide_index=True, use_container_width=True)

    with layout_venstre:
        # Tegn banen (VerticalPitch er bedst til afslutninger)
        pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#444444', line_zorder=2)
        fig, ax = pitch.draw(figsize=(6, 5))
        
        # Sæt fokus på den øverste halvdel
        ax.set_ylim(45, 102) 
        
        for _, row in df_plot.iterrows():
            goal = is_true(row.get('SHOTISGOAL', False))
            
            # Scatter plot af skuddet
            ax.scatter(row['LOCATIONY'], row['LOCATIONX'], 
                       s=180 if goal else 90, 
                       color='gold' if goal else HIF_RED,
                       edgecolors='white', 
                       linewidth=1.2 if goal else 0.6,
                       alpha=0.85,
                       zorder=3)
        
        st.pyplot(fig, bbox_inches='tight', pad_inches=0.05)
