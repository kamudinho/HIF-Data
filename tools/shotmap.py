import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch

# HIF Identitet - Rene farver på hvid baggrund
HIF_RED = '#cc0000'
HIF_BLUE = '#0056a3'
HIF_GOLD = '#b8860b' # En dybere guld der står skarpt på hvid
HIF_OPTA_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"

def vis_side(dp, logo_map=None):
    # Data check
    df_raw = dp.get('playerstats', pd.DataFrame()) if isinstance(dp, dict) else dp
    if df_raw.empty:
        st.info("Ingen kampdata fundet.")
        return

    # --- DATA RENS ---
    df_hif = df_raw[df_raw['EVENT_CONTESTANT_OPTAUUID'] == HIF_OPTA_UUID].copy()
    df_hif['TYPE_STR'] = df_hif['EVENT_TYPEID'].astype(str).str.replace('.0', '', regex=False).str.strip()
    df_hif['QUAL_STR'] = df_hif['QUALIFIERS'].astype(str)
    df_hif['PLAYER_NAME'] = df_hif['PLAYER_NAME'].fillna('Ukendt').astype(str)

    # --- COMPACT TOP BAR ---
    # Vi bruger columns til at gøre dropdown mindre
    col_title, col_space, col_select = st.columns([2, 1, 1.5])
    with col_title:
        st.subheader("Afslutninger & Assists")
    with col_select:
        spiller_liste = sorted(df_hif['PLAYER_NAME'].unique().tolist())
        valgt_spiller = st.selectbox("Filter", options=["Hele Holdet"] + spiller_liste, label_visibility="collapsed")

    tab1, tab2 = st.tabs(["Skudkort", "Assists"])

    # --- TAB 1: SKUDKORT ---
    with tab1:
        df_skud = df_hif[df_hif['TYPE_STR'].isin(['13', '14', '15', '16'])].copy()
        if valgt_spiller != "Hele Holdet":
            df_skud = df_skud[df_skud['PLAYER_NAME'] == valgt_spiller]

        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Hvid bane med grå linjer - rent og lyst
            pitch = VerticalPitch(half=True, pitch_type='opta', 
                                  pitch_color='white', line_color='#cccccc',
                                  goal_type='box')
            fig, ax = pitch.draw(figsize=(10, 12))
            
            if not df_skud.empty:
                df_skud['ER_MAAL'] = df_skud['TYPE_STR'] == '16'
                # xG plot
                pitch.scatter(df_skud['EVENT_X'], df_skud['EVENT_Y'],
                             s=(df_skud['XG_VAL'] * 1000) + 60,
                             c=df_skud['ER_MAAL'].map({True: HIF_RED, False: 'white'}),
                             edgecolors=HIF_RED, linewidth=1.5, alpha=0.8, ax=ax)
            st.pyplot(fig)

        with col2:
            total_skud = len(df_skud)
            maal = int(df_skud['ER_MAAL'].sum()) if not df_skud.empty else 0
            st.metric("Skud", total_skud)
            st.metric("Mål", maal)
            st.metric("xG", f"{df_skud['XG_VAL'].sum():.2f}" if not df_skud.empty else "0.00")

    # --- TAB 2: ASSISTS ---
    with tab2:
        df_a = df_hif[df_hif['QUAL_STR'].str.contains('210', na=False)].copy()
        if valgt_spiller != "Hele Holdet":
            df_a = df_a[df_a['PLAYER_NAME'] == valgt_spiller]

        col1, col2 = st.columns([3, 1])
        with col1:
            pitch_a = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig_a, ax_a = pitch_a.draw(figsize=(10, 12))
            
            if not df_a.empty:
                # Diskrete guld-pile
                pitch_a.arrows(df_a['EVENT_X'], df_a['EVENT_Y'],
                               df_a['PASS_END_X'].fillna(98), df_a['PASS_END_Y'].fillna(50),
                               color=HIF_GOLD, width=2, headwidth=3, headlength=3, ax=ax_a)
                pitch_a.scatter(df_a['EVENT_X'], df_a['EVENT_Y'], 
                                s=100, color='white', edgecolors=HIF_GOLD, linewidth=1.5, ax=ax_a)
            st.pyplot(fig_a)

        with col2:
            st.metric("Assists", len(df_a))
