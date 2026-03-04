import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch

HIF_RED = '#cc0000'
HIF_BLUE = '#0056a3'
HIF_GOLD = '#ffd700'
HIF_OPTA_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"

def vis_side(dp, logo_map=None):
    # Håndtering af data-input
    df_raw = dp.get('playerstats', pd.DataFrame()) if isinstance(dp, dict) else dp

    if df_raw.empty:
        st.warning("Ingen data fundet. Tjek om SQL henter Type 1 (pasninger).")
        return

    # --- 1. DATA RENS ---
    df_hif = df_raw[df_raw['EVENT_CONTESTANT_OPTAUUID'] == HIF_OPTA_UUID].copy()
    df_hif['TYPE_STR'] = df_hif['EVENT_TYPEID'].astype(str).str.replace('.0', '', regex=False).str.strip().str.upper()
    df_hif['QUAL_STR'] = df_hif['QUALIFIERS'].astype(str)

    # --- 2. DROPDOWN ---
    spiller_liste = sorted(df_hif['PLAYER_NAME'].dropna().unique().tolist())
    valgt_spiller = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste)

    tab1, tab2 = st.tabs(["🎯 Skudkort", "🅰️ Assists"])

    # --- TAB 1: SKUD ---
    with tab1:
        df_skud = df_hif[df_hif['TYPE_STR'].isin(['13', '14', '15', '16'])].copy()
        if valgt_spiller != "Hele Holdet":
            df_skud = df_skud[df_skud['PLAYER_NAME'] == valgt_spiller]
        
        df_skud['ER_MAAL'] = df_skud['TYPE_STR'] == '16'

        col1, col2 = st.columns([2.5, 1])
        with col1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#444444')
            fig, ax = pitch.draw(figsize=(8, 10))
            if not df_skud.empty:
                pitch.scatter(df_skud['EVENT_X'], df_skud['EVENT_Y'], 
                              s=(df_skud['XG_VAL'] * 1500) + 100, 
                              c=df_skud['ER_MAAL'].map({True: HIF_RED, False: HIF_BLUE}),
                              marker='o', edgecolors='white', ax=ax, alpha=0.7)
            st.pyplot(fig)
        with col2:
            st.metric("Skud", len(df_skud))
            st.metric("Mål", int(df_skud['ER_MAAL'].sum()))

    # --- TAB 2: ASSISTS ---
    with tab2:
        # Nu filtrerer vi korrekt på pasninger (Type 1) med assist-qualifier (210)
        df_assists = df_hif[df_hif['QUAL_STR'].str.contains('210', na=False)].copy()
        if valgt_spiller != "Hele Holdet":
            df_assists = df_assists[df_assists['PLAYER_NAME'] == valgt_spiller]

        col1, col2 = st.columns([2.5, 1])
        with col1:
            pitch_a = VerticalPitch(half=True, pitch_type='opta', line_color='#444444')
            fig_a, ax_a = pitch_a.draw(figsize=(8, 10))
            if not df_assists.empty:
                # Tegn pile fra start til slut
                pitch_a.arrows(df_assists['EVENT_X'], df_assists['EVENT_Y'], 
                               df_assists['PASS_END_X'].fillna(98), df_assists['PASS_END_Y'].fillna(50), 
                               color=HIF_GOLD, width=2, ax=ax_a)
                # Kun cirkel ved startpunktet
                pitch_a.scatter(df_assists['EVENT_X'], df_assists['EVENT_Y'], 
                                color=HIF_GOLD, marker='o', s=150, edgecolors='white', ax=ax_a)
            st.pyplot(fig_a)
        with col2:
            st.metric("Assists", len(df_assists))
