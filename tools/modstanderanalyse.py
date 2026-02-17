#tools/modstanderanalyse.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import VerticalPitch
import numpy as np

# Vi importerer din centrale konfiguration
try:
    from data.season_show import COMP_MAP
except ImportError:
    COMP_MAP = {}

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

    # --- 2. CENTRALISERET DOBBELT-DROPDOWN ---
    # Vi henter de unikke turneringer direkte fra de data, Snowflake har leveret
    if 'COMPETITION_WYID' in df_team_matches.columns:
        aktive_comp_ids = sorted(df_team_matches['COMPETITION_WYID'].unique())
    else:
        aktive_comp_ids = []

    col_sel1, col_sel2, col_sel3 = st.columns([1.5, 1.5, 1.2])

    with col_sel1:
        # Her bruger vi COMP_MAP til at vise navne i stedet for tal
        valgt_comp_id = st.selectbox(
            "Vælg Turnering:", 
            options=aktive_comp_ids,
            format_func=lambda x: COMP_MAP.get(int(x), f"Turnering {x}")
        )

    # Filtrer data til den valgte turnering
    df_comp = df_team_matches[df_team_matches['COMPETITION_WYID'] == valgt_comp_id]

    # Find holdene i den specifikke turnering
    tilgaengelige_hold_ids = df_comp['TEAM_WYID'].unique()
    navne_dict = {hold_map.get(str(int(tid)), f"Ukendt ({tid})"): tid for tid in tilgaengelige_hold_ids}
    
    with col_sel2:
        valgt_navn = st.selectbox("Vælg modstander:", options=sorted(navne_dict.keys()))
    
    with col_sel3:
        halvdel = st.radio("Fokusområde:", ["Modstanders halvdel", "Egen halvdel"], horizontal=True)

    valgt_id = navne_dict[valgt_navn]
    df_f = df_comp[df_comp['TEAM_WYID'] == valgt_id].copy()

    # --- 3. HOVEDLAYOUT & HEATMAPS ---
    main_left, main_right = st.columns([2.2, 1])

    with main_left:
        st.subheader(f"Analyse af {valgt_navn}")
        pitch = VerticalPitch(pitch_type='wyscout', pitch_color='#f8f9fa', line_color='#1a1a1a', half=True)
        c1, c2, c3 = st.columns(3)

        if df_events is not None and not df_events.empty:
            # Filtrer hændelser på hold og turnering
            df_hold_ev = df_events[
                (df_events['TEAM_WYID'].astype(str) == str(int(valgt_id))) & 
                (df_events['COMPETITION_WYID'] == valgt_comp_id)
            ].copy()

            if halvdel == "Modstanders halvdel":
                df_plot = df_hold_ev[df_hold_ev['LOCATIONX'] >= 50].copy()
            else:
                df_plot = df_hold_ev[df_hold_ev['LOCATIONX'] < 50].copy()
                df_plot['LOCATIONX'] = 100 - df_plot['LOCATIONX']
                df_plot['LOCATIONY'] = 100 - df_plot['LOCATIONY']

            for col, title, p_type, cmap in [(c1, "Passes", "pass", "Reds"), (c2, "Duels", "duel", "Blues"), (c3, "Intercepts", "interception", "Greens")]:
                with col:
                    st.caption(title)
                    fig, ax = pitch.draw(figsize=(4, 6))
                    mask = df_plot['PRIMARYTYPE'].str.contains(p_type, case=False, na=False)
                    df_filtered = df_plot[mask]
                    if not df_filtered.empty:
                        sns.kdeplot(x=df_filtered['LOCATIONY'], y=df_filtered['LOCATIONX'], ax=ax, fill=True, cmap=cmap, alpha=0.6, clip=((0, 100), (50, 100)), levels=10)
                    else:
                        ax.text(50, 75, "Ingen data", ha='center', va='center', alpha=0.5)
                    st.pyplot(fig)

    # --- 4. HØJRE SIDE: STATISTIK ---
    with main_right:
        st.subheader("Holdets Profil")
        col_off1, col_off2 = st.columns(2)
        col_off1.metric("Gns. xG", round(df_f['XG'].mean(), 2) if 'XG' in df_f else 0)
        col_off2.metric("Skud/Kamp", round(df_f['SHOTS'].mean(), 1) if 'SHOTS' in df_f else 0)

        col_ctrl1, col_ctrl2 = st.columns(2)
        pos = df_f['POSSESSIONPERCENT'].mean() if 'POSSESSIONPERCENT' in df_f else 0
        col_ctrl1.metric("Possession", f"{round(pos, 0)}%")
        col_ctrl2.metric("Gns. Mål", round(df_f['GOALS'].mean(), 1) if 'GOALS' in df_f else 0)

    # --- 5. RÅ DATA ---
    with st.expander("Se kamp-log"):
        st.dataframe(df_f.sort_values('DATE', ascending=False), use_container_width=True)
