import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import VerticalPitch
import numpy as np

def vis_side(df_team_matches, hold_map, df_events):
    # --- 1. CSS STYLING ---
    st.markdown("""
        <style>
        .stMetric { 
            background-color: #ffffff; padding: 10px; border-radius: 8px; 
            border-bottom: 3px solid #df003b; box-shadow: 0 2px 4px rgba(0,0,0,0.05); 
        }
        [data-testid="stMetricValue"] { font-size: 20px !important; }
        </style>
    """, unsafe_allow_html=True)

    if df_team_matches is None or df_team_matches.empty:
        st.error("Kunne ikke finde kampdata.")
        return

    # --- 2. VALG AF MODSTANDER (FILTRERET PÅ TURNERINGER) ---
    # Vi tager kun de unikke IDs fra de kampe, der allerede er filtreret i data_load.py
    tilgaengelige_ids = df_team_matches['TEAM_WYID'].unique()
    
    # Byg ordbog: Navn -> ID (Kun for de relevante hold)
    navne_dict = {}
    for tid in tilgaengelige_ids:
        tid_str = str(int(tid))
        navn = hold_map.get(tid_str, f"Ukendt ({tid_str})")
        navne_dict[navn] = tid

    col_sel1, col_sel2 = st.columns([2, 1])
    with col_sel1:
        valgt_navn = st.selectbox(
            "Vælg modstander:", 
            options=sorted(navne_dict.keys()),
            help="Listen er begrænset til de turneringer, du har valgt i din konfiguration."
        )
    with col_sel2:
        halvdel = st.radio("Fokusområde:", ["Modstanders halvdel", "Egen halvdel"], horizontal=True)

    valgt_id = navne_dict[valgt_navn]
    df_f = df_team_matches[df_team_matches['TEAM_WYID'] == valgt_id].copy()

    # --- 3. HOVEDLAYOUT ---
    main_left, main_right = st.columns([2.2, 1])

    with main_left:
        st.subheader(f"Halvdel-analyse: {halvdel}")
        
        # Pitch setup (Wyscout dimensioner)
        pitch = VerticalPitch(
            pitch_type='wyscout', pitch_color='#f8f9fa', 
            line_color='#1a1a1a', linewidth=1, 
            half=True 
        )
        
        c1, c2, c3 = st.columns(3)

        if df_events is not None and not df_events.empty:
            df_events.columns = [c.upper() for c in df_events.columns]
            df_hold = df_events[df_events['TEAM_WYID'].astype(str) == str(int(valgt_id))].copy()

            # Filtrering baseret på zone (Wyscout X: 0-100)
            if halvdel == "Modstanders halvdel":
                df_plot = df_hold[df_hold['LOCATIONX'] >= 50].copy()
            else:
                # Ved egen halvdel flipper vi aksen for at vise forsvarszonen i bunden
                df_plot = df_hold[df_hold['LOCATIONX'] < 50].copy()
                df_plot['LOCATIONX'] = 100 - df_plot['LOCATIONX']
                df_plot['LOCATIONY'] = 100 - df_plot['LOCATIONY']

            # Heatmap konfigurationer
            plot_configs = [
                (c1, "Afleveringer", "pass", "Reds"),
                (c2, "Dueller", "duel", "Blues"),
                (c3, "Interceptions", "interception", "Greens")
            ]

            for col, title, p_type, cmap in plot_configs:
                with col:
                    st.caption(title)
                    fig, ax = pitch.draw(figsize=(4, 6))
                    mask = df_plot['PRIMARYTYPE'].str.contains(p_type, case=False, na=False)
                    df_filtered = df_plot[mask]
                    
                    if not df_filtered.empty:
                        sns.kdeplot(
                            x=df_filtered['LOCATIONY'], y=df_filtered['LOCATIONX'], 
                            ax=ax, fill=True, cmap=cmap, alpha=0.6, 
                            clip=((0, 100), (50, 100)), levels=10
                        )
                    else:
                        ax.text(50, 75, "Ingen data", ha='center', va='center', alpha=0.5)
                    st.pyplot(fig)

    # --- 4. HØJRE SIDE: STATISTIK ---
    with main_right:
        st.subheader("Holdets Profil")
        
        # Offensiv Metrics
        st.write("**Offensiv**")
        col_off1, col_off2 = st.columns(2)
        col_off1.metric("Gns. xG", round(df_f['XG'].mean(), 2) if 'XG' in df_f else 0)
        col_off2.metric("Skud/Kamp", round(df_f['SHOTS'].mean(), 1) if 'SHOTS' in df_f else 0)

        # Spilstyring Metrics
        st.write("**Spilstyring**")
        col_ctrl1, col_ctrl2 = st.columns(2)
        pos_val = df_f['POSSESSIONPERCENT'].mean() if 'POSSESSIONPERCENT' in df_f else 0
        col_ctrl1.metric("Possession", f"{round(pos_val, 0)}%")
        col_ctrl2.metric("Gns. Mål", round(df_f['GOALS'].mean(), 1) if 'GOALS' in df_f else 0)

        # Defensiv & Disciplin
        st.write("**Defensiv & Disciplin**")
        col_def1, col_def2 = st.columns(2)
        y_cards = df_f['YELLOWCARDS'].mean() if 'YELLOWCARDS' in df_f else 0
        r_cards = df_f['REDCARDS'].sum() if 'REDCARDS' in df_f else 0
        col_def1.metric("Gule kort/K", round(y_cards, 1))
        col_def2.metric("Røde kort (Tot)", int(r_cards))

        st.markdown("---")
        
        # Effektivitets-beregning
        total_shots = df_f['SHOTS'].sum() if 'SHOTS' in df_f else 0
        total_goals = df_f['GOALS'].sum() if 'GOALS' in df_f else 0
        if total_shots > 0:
            rate = (total_goals / total_shots) * 100
            st.write(f"**Effektivitet (Mål/Skud):** {round(rate, 1)}%")
            st.progress(min(rate/30, 1.0))

        st.info(f"Viser data for **{halvdel.lower()}**.")

    # --- 5. RÅ DATA ---
    with st.expander("Se alle rå kampdata for modstanderen"):
        if not df_f.empty:
            st.dataframe(df_f.sort_values('DATE', ascending=False), use_container_width=True)
