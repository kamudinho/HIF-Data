import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch

HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b' 
HIF_OPTA_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"

def vis_side(dp, logo_map=None):
    # Hent data fra pakken (tjekker begge mulige nøgler)
    if isinstance(dp, dict):
        df_raw = dp.get('playerstats', dp.get('opta', {}).get('player_stats', pd.DataFrame()))
    else:
        df_raw = dp

    if df_raw.empty:
        st.info("Ingen kampdata fundet.")
        return

    # --- DATA RENS ---
    df_hif = df_raw[df_raw['EVENT_CONTESTANT_OPTAUUID'] == HIF_OPTA_UUID].copy()
    
    # Konverter koordinater til tal med det samme
    for col in ['EVENT_X', 'EVENT_Y', 'PASS_START_X', 'PASS_START_Y']:
        if col in df_hif.columns:
            df_hif[col] = pd.to_numeric(df_hif[col], errors='coerce').fillna(0)

    # Marker Assists vs Key Passes
    df_hif['IS_ASSIST'] = (df_hif['QUALS_IDS'].astype(str).str.contains('210', na=False)) | (df_hif['MANUAL_ASSIST_MARKER'] == '210')
    df_hif['IS_KEY_PASS'] = (df_hif['QUALS_IDS'].astype(str).str.contains('29', na=False)) & (~df_hif['IS_ASSIST'])

    tab1, tab2 = st.tabs(["AFSLUTNINGER", "ASSISTS"])

    with tab1:
        st.write("### Skudkort")
        # Her kan du indsætte din eksisterende skud-plot kode...

    with tab2:
        col_viz, col_ctrl = st.columns([3, 1])
        
        with col_ctrl:
            spiller_liste = sorted(df_hif['PLAYER_NAME'].dropna().unique().tolist())
            st.selectbox("Vælg spiller", options=["Hvidovre IF"] + spiller_liste, key="sb_assist")
            
            n_assist = int(df_hif['IS_ASSIST'].sum())
            n_key = int(df_hif['IS_KEY_PASS'].sum())

            st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-label"><span class="dot" style="background-color:{HIF_GOLD}"></span> Assists</div>
                    <div class="stat-value">{n_assist}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label"><span class="dot" style="background-color:#999999"></span> Shot Assists</div>
                    <div class="stat-value">{n_key}</div>
                </div>
            """, unsafe_allow_html=True)

        with col_viz:
            pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(8, 10))
            
            df_plot = df_hif[df_hif['IS_ASSIST'] | df_hif['IS_KEY_PASS']].copy()
            
            if not df_plot.empty:
                # 1. Pilene (kun hvor vi har start-koordinater)
                df_arrows = df_plot[df_plot['PASS_START_X'] > 0]
                pitch.arrows(df_arrows.PASS_START_X, df_arrows.PASS_START_Y,
                             df_arrows.EVENT_X, df_arrows.EVENT_Y,
                             color='#dddddd', width=2, headwidth=3, ax=ax, zorder=1)
                
                # 2. Prikker (Guld/Grå)
                colors = df_plot['IS_ASSIST'].map({True: HIF_GOLD, False: '#999999'})
                pitch.scatter(df_plot.EVENT_X, df_plot.EVENT_Y, 
                             s=120, color=colors, edgecolors='white', linewidth=1, ax=ax, zorder=2)
            
            st.pyplot(fig, use_container_width=True)
