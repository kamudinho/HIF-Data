import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch

# HIF Identitet
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b' 
HIF_OPTA_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"

def vis_side(dp, logo_map=None):
    # 1. Hent data - Vi tjekker alle mulige nøgler
    if isinstance(dp, dict):
        df_raw = dp.get('opta_shotevents', dp.get('playerstats', pd.DataFrame()))
    else:
        df_raw = dp

    if df_raw.empty:
        st.info("Ingen kampdata fundet i 'opta_shotevents'.")
        return

    # --- DATA RENS ---
    df_hif = df_raw[df_raw['EVENT_CONTESTANT_OPTAUUID'] == HIF_OPTA_UUID].copy()
    
    # Sørg for at kolonnenavne er UPPERCASE (Snowflake standard)
    df_hif.columns = [c.upper() for c in df_hif.columns]
    
    # Tving koordinater til tal
    for col in ['EVENT_X', 'EVENT_Y', 'PASS_START_X', 'PASS_START_Y']:
        if col in df_hif.columns:
            df_hif[col] = pd.to_numeric(df_hif[col], errors='coerce').fillna(0)

    # Robust identifikation af assists (vi tjekker både QUALS_IDS og MANUAL_ASSIST_MARKER)
    def check_assist(row):
        q_str = str(row.get('QUALS_IDS', ''))
        manual = str(row.get('MANUAL_ASSIST_MARKER', '0'))
        # Returner 2 hvis det er en rigtig assist (mål), 1 hvis det er shot assist, 0 ellers
        if '210' in q_str or manual == '210':
            return 2
        if '29' in q_str:
            return 1
        return 0

    df_hif['ASSIST_TYPE'] = df_hif.apply(check_assist, axis=1)

    tab1, tab2 = st.tabs(["AFSLUTNINGER", "ASSISTS"])

    # --- TAB 1: SKUD (Uændret, men med de rensede kolonner) ---
    with tab1:
        spiller_liste = sorted(df_hif['PLAYER_NAME'].dropna().unique().tolist())
        v_spiller = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste, key="sb_skud")
        
        df_skud = df_hif.copy()
        if v_spiller != "Hele Holdet":
            df_skud = df_skud[df_skud['PLAYER_NAME'] == v_spiller]
            
        pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(7, 9))
        
        # Mål vs Miss
        df_mål = df_skud[df_skud['EVENT_OUTCOME'].astype(str) == '1']
        df_miss = df_skud[df_skud['EVENT_OUTCOME'].astype(str) != '1']
        
        pitch.scatter(df_miss.EVENT_X, df_miss.EVENT_Y, s=150, color='white', edgecolors=HIF_RED, ax=ax)
        pitch.scatter(df_mål.EVENT_X, df_mål.EVENT_Y, s=200, color=HIF_RED, edgecolors='black', ax=ax)
        st.pyplot(fig)

    # --- TAB 2: ASSISTS (Den kritiske del) ---
    with tab2:
        col_viz, col_ctrl = st.columns([3, 1])
        
        # Filtrer kun hændelser der er assists eller shot assists
        df_chance = df_hif[df_hif['ASSIST_TYPE'] > 0].copy()
        
        with col_ctrl:
            v_spiller_a = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste, key="sb_assist")
            if v_spiller_a != "Hele Holdet":
                df_chance = df_chance[df_chance['PLAYER_NAME'] == v_spiller_a]
            
            n_assist = (df_chance['ASSIST_TYPE'] == 2).sum()
            n_key = (df_chance['ASSIST_TYPE'] == 1).sum()
            
            st.metric("Assists (Mål)", n_assist)
            st.metric("Shot Assists", n_key)

        with col_viz:
            pitch_a = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig_a, ax_a = pitch_a.draw(figsize=(7, 9))
            
            if not df_chance.empty:
                # 1. Tegn pile for dem med start-koordinater
                df_arrows = df_chance[df_chance['PASS_START_X'] > 0]
                pitch_a.arrows(df_arrows.PASS_START_X, df_arrows.PASS_START_Y,
                               df_arrows.EVENT_X, df_arrows.EVENT_Y,
                               color='#cccccc', width=2, headwidth=3, ax=ax_a, zorder=1)
                
                # 2. Scatter points
                # Guld for rigtige assists, grå for shot assists
                for _, row in df_chance.iterrows():
                    color = HIF_GOLD if row['ASSIST_TYPE'] == 2 else '#999999'
                    pitch_a.scatter(row.EVENT_X, row.EVENT_Y, s=150, color=color, 
                                   edgecolors='white', ax=ax_a, zorder=2)
            else:
                st.warning("Ingen assist-data fundet for denne spiller.")
            
            st.pyplot(fig_a)
