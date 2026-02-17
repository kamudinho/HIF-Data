#tools/modstanderanalyse.py
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
        st.error("Kunne ikke finde kampdata. Tjek om COMPETITION_WYID er med i din SQL.")
        return

    # --- 2. DYNAMISK FILTRERING (TURNERING -> HOLD) ---
    # Vi henter de unikke turneringer direkte fra dataframe (ingen hardkodning)
    if 'COMPETITION_WYID' in df_team_matches.columns:
        aktive_turneringer = sorted(df_team_matches['COMPETITION_WYID'].unique())
    else:
        st.warning("⚠️ COMPETITION_WYID mangler i data. Viser alle hold samlet.")
        aktive_turneringer = [None]

    col_sel1, col_sel2, col_sel3 = st.columns([1.5, 1.5, 1.2])

    with col_sel1:
        # Viser turneringens ID (Navne kræver et join i SQL eller mapping i season_show)
        valgt_comp = st.selectbox(
            "Vælg Turnering (ID):", 
            options=aktive_turneringer,
            format_func=lambda x: f"Turnering ID: {int(x)}" if x is not None else "Alle"
        )

    # Filtrer dataframe baseret på valgt turnering
    if valgt_comp is not None:
        df_comp_filtered = df_team_matches[df_team_matches['COMPETITION_WYID'] == valgt_comp]
    else:
        df_comp_filtered = df_team_matches

    # Find holdene der findes i den valgte turnering
    tilgaengelige_ids = df_comp_filtered['TEAM_WYID'].unique()
    navne_dict = {hold_map.get(str(int(tid)), f"Ukendt ({tid})"): tid for tid in tilgaengelige_ids}
    
    with col_sel2:
        valgt_navn = st.selectbox("Vælg modstander:", options=sorted(navne_dict.keys()))
    
    with col_sel3:
        halvdel = st.radio("Fokusområde:", ["Modstanders halvdel", "Egen halvdel"], horizontal=True)

    valgt_id = navne_dict[valgt_navn]
    df_f = df_comp_filtered[df_comp_filtered['TEAM_WYID'] == valgt_id].copy()

    # --- 3. HOVEDLAYOUT ---
    main_left, main_right = st.columns([2.2, 1])

    with main_left:
        st.subheader(f"Halvdel-analyse: {halvdel}")
        
        pitch = VerticalPitch(
            pitch_type='wyscout', pitch_color='#f8f9fa', 
            line_color='#1a1a1a', linewidth=1, half=True 
        )
        
        c1, c2, c3 = st.columns(3)

        if df_events is not None and not df_events.empty:
            df_events.columns = [c.upper() for c in df_events.columns]
            df_hold_events = df_events[df_events['TEAM_WYID'].astype(str) == str(int(valgt_id))].copy()

            # Vi sikrer os at hændelserne også er fra den rigtige turnering hvis muligt
            if 'COMPETITION_WYID' in df_hold_events.columns and valgt_comp is not None:
                df_hold_events = df_hold_events[df_hold_events['COMPETITION_WYID'] == valgt_comp]

            if halvdel == "Modstanders halvdel":
                df_plot = df_hold_events[df_hold_events['LOCATIONX'] >= 50].copy()
            else:
                df_plot = df_hold_events[df_hold_events['LOCATIONX'] < 50].copy()
                df_plot['LOCATIONX'] = 100 - df_plot['LOCATIONX']
                df_plot['LOCATIONY'] = 100 - df_plot['LOCATIONY']

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
        
        st.write("**Offensiv**")
        col_off1, col_off2 = st.columns(2)
        col_off1.metric("Gns. xG", round(df_f['XG'].mean(), 2) if 'XG' in df_f else 0)
        col_off2.metric("Skud/Kamp", round(df_f['SHOTS'].mean(), 1) if 'SHOTS' in df_f else 0)

        st.write("**Spilstyring**")
        col_ctrl1, col_ctrl2 = st.columns(2)
        pos_val = df_f['POSSESSIONPERCENT'].mean() if 'POSSESSIONPERCENT' in df_f else 0
        col_ctrl1.metric("Possession", f"{round(pos_val, 0)}%")
        col_ctrl2.metric("Gns. Mål", round(df_f['GOALS'].mean(), 1) if 'GOALS' in df_f else 0)

        st.write("**Disciplin**")
        col_def1, col_def2 = st.columns(2)
        y_cards = df_f['YELLOWCARDS'].mean() if 'YELLOWCARDS' in df_f else 0
        r_cards = df_f['REDCARDS'].sum() if 'REDCARDS' in df_f else 0
        col_def1.metric("Gule kort/K", round(y_cards, 1))
        col_def2.metric("Røde kort (Tot)", int(r_cards))

        st.markdown("---")
        
        total_shots = df_f['SHOTS'].sum() if 'SHOTS' in df_f else 0
        total_goals = df_f['GOALS'].sum() if 'GOALS' in df_f else 0
        if total_shots > 0:
            rate = (total_goals / total_shots) * 100
            st.write(f"**Effektivitet (Mål/Skud):** {round(rate, 1)}%")
            st.progress(min(rate/30, 1.0))

    # --- 5. RÅ DATA ---
    with st.expander("Se alle rå kampdata for modstanderen"):
        st.dataframe(df_f.sort_values('DATE', ascending=False), use_container_width=True)
