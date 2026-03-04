import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch

# HIF Konstanter
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'
HIF_BLUE = '#0056a3'
HIF_OPTA_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"

def vis_side(dp):
    df_raw = dp.get('opta_shotevents', pd.DataFrame())
    
    if df_raw.empty:
        st.info("Ingen kampdata fundet.")
        return

    # --- DATA RENS (RETTELSE: Robust konvertering) ---
    df_hif = df_raw[df_raw['EVENT_CONTESTANT_OPTAUUID'] == HIF_OPTA_UUID].copy()
    
    coord_cols = ['EVENT_X', 'EVENT_Y', 'PASS_END_X', 'PASS_END_Y']
    for col in coord_cols:
        df_hif[col] = pd.to_numeric(df_hif[col], errors='coerce').fillna(0)

    df_hif['QUAL_STR'] = df_hif['QUALIFIERS'].astype(str)
    df_hif['TYPE_STR'] = df_hif['EVENT_TYPEID'].astype(str).str.replace('.0', '', regex=False)
    
    tab1, tab2 = st.tabs(["AFSLUTNINGER", "ASSISTS & CHANCER"])

    # --- TAB 1: AFSLUTNINGER ---
    with tab1:
        col_viz, col_ctrl = st.columns([3, 1])
        df_skud = df_hif[df_hif['TYPE_STR'].isin(['13', '14', '15', '16'])].copy()
        
        with col_ctrl:
            spiller_liste = sorted(df_skud['PLAYER_NAME'].dropna().unique().tolist())
            v_skud = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste)
            if v_skud != "Hele Holdet":
                df_skud = df_skud[df_skud['PLAYER_NAME'] == v_skud]
            
            n_maal = int((df_skud['TYPE_STR'] == '16').sum())
            st.metric("Afslutninger", len(df_skud))
            st.metric("Mål", n_maal)

        with col_viz:
            pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='#f8f9fa', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(7, 9))
            if not df_skud.empty:
                # Mål er røde, missere er hvide med rød kant
                c_map = (df_skud['TYPE_STR'] == '16').map({True: HIF_RED, False: 'white'})
                pitch.scatter(df_skud.EVENT_X, df_skud.EVENT_Y, s=200, 
                             c=c_map, edgecolors=HIF_RED, linewidth=1.5, ax=ax)
            st.pyplot(fig)

    # --- TAB 2: ASSISTS (RETTELSE: Præcis filtrering) ---
    with tab2:
        col_viz_a, col_ctrl_a = st.columns([3, 1])
        
        # Vi leder efter passes (1) der er enten assist (210) eller key pass (29)
        df_chance = df_hif[(df_hif['TYPE_STR'] == '1') & 
                           (df_hif['QUAL_STR'].str.contains('210|29', na=False))].copy()
        
        with col_ctrl_a:
            v_a = st.selectbox("Vælg spiller", options=["Hele Holdet"] + sorted(df_hif['PLAYER_NAME'].dropna().unique().tolist()), key="sb_a")
            if v_a != "Hele Holdet":
                df_chance = df_chance[df_chance['PLAYER_NAME'] == v_a]
            
            n_ast = df_chance['QUAL_STR'].str.contains('210').sum()
            n_key = df_chance['QUAL_STR'].str.contains('29').sum()
            st.metric("Assists", n_ast)
            st.metric("Key Passes", n_key)

        with col_viz_a:
            pitch_a = VerticalPitch(half=True, pitch_type='opta', pitch_color='#f8f9fa', line_color='#cccccc')
            fig_a, ax_a = pitch_a.draw(figsize=(7, 9))
            if not df_chance.empty:
                # Tegn afleverings-pile
                pitch_a.arrows(df_chance.EVENT_X, df_chance.EVENT_Y,
                             df_chance.PASS_END_X, df_chance.PASS_END_Y,
                             color='#bbbbbb', width=2, headwidth=4, ax=ax_a)
                
                # Farvelæg startpunkt: Guld for assist, Blå for key pass
                df_chance['color'] = df_chance['QUAL_STR'].apply(
                    lambda x: HIF_GOLD if '210' in x else HIF_BLUE
                )
                pitch_a.scatter(df_chance.EVENT_X, df_chance.EVENT_Y, s=150, 
                               color=df_chance.color, edgecolors='white', ax=ax_a)
            st.pyplot(fig_a)
