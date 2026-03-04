import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch

# HIF Identitet
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b' 
HIF_OPTA_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"

def vis_side(dp, logo_map=None):
    # CSS remains the same...
    st.markdown("""<style>...</style>""", unsafe_allow_html=True)
    
    # 1. Hent data - brug den korrekte nøgle fra din SQL dictionary
    if isinstance(dp, dict):
        df_raw = dp.get('opta_shotevents', pd.DataFrame())
    else:
        df_raw = dp

    if df_raw.empty:
        st.info("Ingen kampdata fundet.")
        return

    # --- DATA RENS ---
    df_hif = df_raw[df_raw['EVENT_CONTESTANT_OPTAUUID'] == HIF_OPTA_UUID].copy()
    
    # Tving koordinater til tal
    for col in ['EVENT_X', 'EVENT_Y', 'PASS_START_X', 'PASS_START_Y']:
        df_hif[col] = pd.to_numeric(df_hif[col], errors='coerce').fillna(0)

    # VIGTIGT: Brug QUALS_IDS fra din SQL query
    df_hif['QUAL_STR'] = df_hif['QUALS_IDS'].astype(str)
    df_hif['PLAYER_NAME'] = df_hif['PLAYER_NAME'].fillna('Ukendt')

    tab1, tab2 = st.tabs(["AFSLUTNINGER", "ASSISTS"])

    # --- TAB 1: SKUDKORT ---
    with tab1:
        col_viz, col_ctrl = st.columns([3, 1])
        with col_ctrl:
            spiller_liste = sorted(df_hif['PLAYER_NAME'].unique().tolist())
            v_spiller_skud = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste, key="sb_skud")
            
            df_skud = df_hif.copy()
            if v_spiller_skud != "Hele Holdet":
                df_skud = df_skud[df_skud['PLAYER_NAME'] == v_spiller_skud]
            
            df_skud['ER_MAAL'] = df_skud['EVENT_OUTCOME'].astype(str) == '1'
            
            # Stat-bokse (din CSS stil)
            st.markdown(f'<div class="stat-box">...</div>', unsafe_allow_html=True)

        with col_viz:
            pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(7.5, 9.5))
            pitch.scatter(df_skud['EVENT_X'], df_skud['EVENT_Y'],
                         s=150, c=df_skud['ER_MAAL'].map({True: HIF_RED, False: 'white'}),
                         edgecolors=HIF_RED, linewidth=1.2, ax=ax)
            st.pyplot(fig, use_container_width=True)

    # --- TAB 2: ASSISTS ---
    with tab2:
        col_viz_a, col_ctrl_a = st.columns([3, 1])
        with col_ctrl_a:
            v_spiller_a = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste, key="sb_assist")
            
            # Brug din MANUAL_ASSIST_MARKER fra SQL'en
            df_chance = df_hif[(df_hif['QUAL_STR'].str.contains('210|29', na=False)) | 
                               (df_hif['MANUAL_ASSIST_MARKER'] == '210')].copy()
            
            if v_spiller_a != "Hele Holdet":
                df_chance = df_chance[df_chance['PLAYER_NAME'] == v_spiller_a]
            
            # Tælling
            n_assist = ((df_chance['QUAL_STR'].str.contains('210')) | (df_chance['MANUAL_ASSIST_MARKER'] == '210')).sum()
            n_key = len(df_chance) - n_assist 

            # Stat-bokse...
        
        with col_viz_a:
            pitch_a = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig_a, ax_a = pitch_a.draw(figsize=(7.5, 9.5))
            
            # Tegn kun pile for dem med start-koordinater
            df_plot = df_chance[df_chance['PASS_START_X'] > 0].copy()
            
            if not df_plot.empty:
                # 1. Pile (Start -> Slut)
                pitch_a.arrows(df_plot['PASS_START_X'], df_plot['PASS_START_Y'],
                               df_plot['EVENT_X'], df_plot['EVENT_Y'],
                               color='#dddddd', width=2, zorder=1, ax=ax_a)
                
                # 2. Prikker (Guld for Assist, Grå for Shot Assist)
                for _, row in df_plot.iterrows():
                    is_real_assist = '210' in row['QUAL_STR'] or row['MANUAL_ASSIST_MARKER'] == '210'
                    color = HIF_GOLD if is_real_assist else '#999999'
                    size = 180 if is_real_assist else 100
                    pitch_a.scatter(row.EVENT_X, row.EVENT_Y, s=size, color=color, 
                                   edgecolors='white', linewidth=1, ax=ax_a, zorder=3)
            else:
                st.info("Ingen assists fundet.")
            
            st.pyplot(fig_a, use_container_width=True)
