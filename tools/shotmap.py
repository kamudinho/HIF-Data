import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch

# HIF Konstanter
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'
HIF_OPTA_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"

def vis_side(dp):
    # Hent data fra din dataprovider
    df_raw = dp.get('opta_shotevents', pd.DataFrame())
    
    if df_raw.empty:
        st.info("Ingen kampdata fundet for Hvidovre IF i denne sæson.")
        return

    # 1. Rens data: Kun HIF og konverter koordinater til tal
    df_hif = df_raw[df_raw['EVENT_CONTESTANT_OPTAUUID'] == HIF_OPTA_UUID].copy()
    for col in ['EVENT_X', 'EVENT_Y', 'PASS_END_X', 'PASS_END_Y']:
        df_hif[col] = pd.to_numeric(df_hif[col], errors='coerce')

    tab1, tab2 = st.tabs(["AFSLUTNINGER", "ASSISTS"])

    # --- TAB 1: AFSLUTNINGER ---
    with tab1:
        # Skud er type 13, 14, 15, 16
        df_skud = df_hif[df_hif['EVENT_TYPEID'].isin([13, 14, 15, 16])].copy()
        
        pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(8, 10))
        
        if not df_skud.empty:
            # Mål (16) bliver helt røde, andre skud hvide med rød kant
            colors = ['#cc0000' if t == 16 else 'white' for t in df_skud['EVENT_TYPEID']]
            pitch.scatter(df_skud.EVENT_X, df_skud.EVENT_Y, s=150, 
                         c=colors, edgecolors='#cc0000', linewidth=1.5, ax=ax)
        
        st.pyplot(fig)

    # --- TAB 2: ASSISTS ---
    with tab2:
        # Assists/Key passes er type 1 med qualifier 210 eller 29
        df_hif['QUAL_STR'] = df_hif['QUALIFIERS'].astype(str)
        df_chance = df_hif[(df_hif['EVENT_TYPEID'] == 1) & 
                           (df_hif['QUAL_STR'].str.contains('210|29'))].copy()
        
        pitch_a = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig_a, ax_a = pitch_a.draw(figsize=(8, 10))
        
        if not df_chance.empty:
            # Tegn pile fra start til slut
            pitch_a.arrows(df_chance.EVENT_X, df_chance.EVENT_Y, 
                         df_chance.PASS_END_X, df_chance.PASS_END_Y, 
                         color='#dddddd', width=2, ax=ax_a)
            
            # Punktet hvor afleveringen blev slået (Guld)
            pitch_a.scatter(df_chance.EVENT_X, df_chance.EVENT_Y, s=120, 
                           color=HIF_GOLD, edgecolors='white', ax=ax_a)
            
        st.pyplot(fig_a)
