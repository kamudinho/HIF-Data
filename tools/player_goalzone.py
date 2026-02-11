import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from mplsoccer import VerticalPitch
from matplotlib.patches import Rectangle
import matplotlib.colors as mcolors

def vis_side(df_events, df_spillere, hold_map):
    HIF_ID = 38331
    HIF_RED = '#d31313'

    # --- 1. DATA-PROCESSERING (Beholdes som før) ---
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    SHOT_CSV_PATH = os.path.join(BASE_DIR, 'shotevents.csv')
    if not os.path.exists(SHOT_CSV_PATH):
        st.error("Kunne ikke finde shotevents.csv")
        return

    df_s = pd.read_csv(SHOT_CSV_PATH)
    df_s.columns = [str(c).strip().upper() for c in df_s.columns]
    df_s = df_s[pd.to_numeric(df_s['TEAM_WYID'], errors='coerce') == HIF_ID].copy()
    for col in ['LOCATIONX', 'LOCATIONY', 'SHOTXG']:
        df_s[col] = pd.to_numeric(df_s[col], errors='coerce')
    df_s = df_s.dropna(subset=['LOCATIONX', 'LOCATIONY'])

    s_df = df_spillere.copy()
    s_df.columns = [str(c).strip().upper() for c in s_df.columns]
    navne_dict = dict(zip(s_df['PLAYER_WYID'].astype(str).str.split('.').str[0], s_df['NAVN']))
    df_s['SPILLER_NAVN'] = df_s['PLAYER_WYID'].astype(str).str.split('.').str[0].map(navne_dict).fillna("Ukendt")
    
    # Zone beregning
    from tools.player_goalzone import find_zone # Eller indsæt find_zone her
    df_s['ZONE_ID'] = df_s.apply(lambda row: find_zone(row['LOCATIONY'], row['LOCATIONX']), axis=1)

    # --- 2. LAYOUT ---
    layout_venstre, layout_hoejre = st.columns([2, 1])

    with layout_hoejre:
        # Ingen st.write eller andet her - vi går direkte til radio
        mode = st.radio(
            "Visning:", ["Hold", "Individuel"], 
            horizontal=True, 
            label_visibility="collapsed"
        )
        
        # Hvis individuel, vis selectbox. Hvis ikke, lav en lille spacer.
        if mode == "Individuel":
            spiller_liste = sorted(df_s['SPILLER_NAVN'].unique().tolist())
            valgt_target = st.selectbox("Vælg spiller", options=spiller_liste, label_visibility="collapsed")
            df_plot = df_s[df_s['SPILLER_NAVN'] == valgt_target].copy()
        else:
            df_plot = df_s.copy()
            st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

        # Metrics sektion
        total_shots = len(df_plot)
        goals = int(df_plot['SHOTISGOAL'].apply(lambda x: str(x).lower() in ['true', '1', '1.0', 't']).sum())
        xg_sum = df_plot['SHOTXG'].sum()
        
        def custom_metric(label, value):
            st.markdown(f"""
                <div style="margin-bottom: 8px; border-left: 3px solid {HIF_RED}; padding-left: 12px; line-height: 1.2;">
                    <p style="margin:0; font-size: 12px; color: #777; text-transform: uppercase; letter-spacing: 0.5px;">{label}</p>
                    <p style="margin:0; font-size: 22px; font-weight: 700; color: #222;">{value}</p>
                </div>
            """, unsafe_allow_html=True)

        custom_metric("Afslutninger", total_shots)
        custom_metric("Mål", goals)
        custom_metric("Total xG", f"{xg_sum:.2f}")
        custom_metric("xG pr. skud", f"{(xg_sum/total_shots) if total_shots > 0 else 0:.2f}")

    with layout_venstre:
        # Pitch setup - pad_top=0 for at rykke banen op
        pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#000000', line_alpha=0.1, line_zorder=2, pad_top=0)
        fig, ax = pitch.draw(figsize=(6, 7))
        ax.set_ylim(55, 102)

        # Resten af zone-tegningen (beholdes fra tidligere)
        # ... (Zone tegning her) ...
        st.pyplot(fig, bbox_inches='tight', pad_inches=0)
