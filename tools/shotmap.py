import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch

HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b' 
HIF_OPTA_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"

def vis_side(dp, logo_map=None):
    # 1. Hent data
    if isinstance(dp, dict):
        df_raw = dp.get('playerstats', dp.get('opta', {}).get('player_stats', pd.DataFrame()))
    else:
        df_raw = dp

    if df_raw.empty:
        st.info("Ingen kampdata fundet.")
        return

    # --- 2. DATA RENS ---
    df_hif = df_raw[df_raw['EVENT_CONTESTANT_OPTAUUID'] == HIF_OPTA_UUID].copy()
    
    for col in ['EVENT_X', 'EVENT_Y', 'PASS_START_X', 'PASS_START_Y']:
        df_hif[col] = pd.to_numeric(df_hif[col], errors='coerce').fillna(0)

    # Markeringer
    df_hif['IS_GOAL'] = df_hif['EVENT_OUTCOME'] == 1
    df_hif['IS_ASSIST'] = (df_hif['QUALS_IDS'].astype(str).str.contains('210', na=False)) | (df_hif['MANUAL_ASSIST_MARKER'] == '210')
    df_hif['IS_KEY_PASS'] = (df_hif['QUALS_IDS'].astype(str).str.contains('29', na=False)) & (~df_hif['IS_ASSIST'])

    tab1, tab2 = st.tabs(["AFSLUTNINGER", "ASSISTS"])

    with tab1:
        # --- SKUDKORT (Den del der manglede) ---
        pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(8, 10))
        
        # Her viser vi alle afslutninger (Event ID 13, 14, 15, 16 er allerede filtreret i SQL)
        for _, row in df_hif.iterrows():
            color = HIF_RED if row['IS_GOAL'] else 'white'
            edge = 'black' if not row['IS_GOAL'] else HIF_GOLD
            pitch.scatter(row.EVENT_X, row.EVENT_Y, s=200, color=color, 
                         edgecolors=edge, linewidth=1.5, ax=ax, zorder=3)
        
        st.pyplot(fig, use_container_width=True)

    with tab2:
        col_viz, col_ctrl = st.columns([3, 1])
        
        with col_ctrl:
            spiller_liste = sorted(df_hif['PLAYER_NAME'].dropna().unique().tolist())
            valgt_spiller = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste, key="sb_assist")
            
            df_filtered = df_hif if valgt_spiller == "Hele Holdet" else df_hif[df_hif['PLAYER_NAME'] == valgt_spiller]

            st.metric("Assists", int(df_filtered['IS_ASSIST'].sum()))
            st.metric("Shot Assists", int(df_filtered['IS_KEY_PASS'].sum()))

        with col_viz:
            pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(8, 10))
            
            # Find kun dem med assists eller key passes til pilene
            df_passes = df_filtered[df_filtered['IS_ASSIST'] | df_filtered['IS_KEY_PASS']].copy()
            
            if not df_passes.empty:
                # 1. Tegn pile (kun fra gyldige startpunkter)
                df_arrows = df_passes[df_passes['PASS_START_X'] > 0]
                for _, row in df_arrows.iterrows():
                    p_color = HIF_GOLD if row['IS_ASSIST'] else '#999999'
                    pitch.arrows(row.PASS_START_X, row.PASS_START_Y, row.EVENT_X, row.EVENT_Y,
                                 color=p_color, width=2, headwidth=3, ax=ax, zorder=2)
                
                # 2. Slutpunkter
                colors = df_passes['IS_ASSIST'].map({True: HIF_GOLD, False: '#999999'})
                pitch.scatter(df_passes.EVENT_X, df_passes.EVENT_Y, s=150, color=colors, edgecolors='black', ax=ax, zorder=3)
            
            st.pyplot(fig, use_container_width=True)
