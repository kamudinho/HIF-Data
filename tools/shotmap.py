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

    # --- 2. DATA RENS & MARKERING ---
    df_hif = df_raw[df_raw['EVENT_CONTESTANT_OPTAUUID'] == HIF_OPTA_UUID].copy()
    
    # Sørg for at koordinater er tal
    for col in ['EVENT_X', 'EVENT_Y', 'PASS_START_X', 'PASS_START_Y']:
        if col in df_hif.columns:
            df_hif[col] = pd.to_numeric(df_hif[col], errors='coerce').fillna(0)

    # Logik for Assists (210) og Key Passes (29)
    df_hif['IS_ASSIST'] = (df_hif['QUALS_IDS'].astype(str).str.contains('210', na=False)) | (df_hif['MANUAL_ASSIST_MARKER'] == '210')
    df_hif['IS_KEY_PASS'] = (df_hif['QUALS_IDS'].astype(str).str.contains('29', na=False)) & (~df_hif['IS_ASSIST'])

    tab1, tab2 = st.tabs(["AFSLUTNINGER", "ASSISTS"])

    with tab1:
        st.write("### Skudkort (Under udvikling)")

    with tab2:
        col_viz, col_ctrl = st.columns([3, 1])
        
        with col_ctrl:
            spiller_liste = sorted(df_hif['PLAYER_NAME'].dropna().unique().tolist())
            valgt_spiller = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste, key="sb_assist")
            
            # Filtrering baseret på valg
            if valgt_spiller == "Hele Holdet":
                df_filtered = df_hif.copy()
            else:
                df_filtered = df_hif[df_hif['PLAYER_NAME'] == valgt_spiller].copy()

            # Optælling til bokse
            n_assist = int(df_filtered['IS_ASSIST'].sum())
            n_key = int(df_filtered['IS_KEY_PASS'].sum())

            st.markdown(f"""
                <div style="background-color:#f0f2f6; padding:15px; border-radius:10px; border-left: 5px solid {HIF_GOLD};">
                    <small>ASSISTS</small><br><strong style="font-size:20px;">{n_assist}</strong>
                </div><br>
                <div style="background-color:#f0f2f6; padding:15px; border-radius:10px; border-left: 5px solid #999999;">
                    <small>SHOT ASSISTS (KEY PASSES)</small><br><strong style="font-size:20px;">{n_key}</strong>
                </div>
            """, unsafe_allow_html=True)

        with col_viz:
            # Opsætning af banen
            pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(8, 10))
            
            # Kun rækker med enten assist eller key pass
            df_plot = df_filtered[df_filtered['IS_ASSIST'] | df_filtered['IS_KEY_PASS']].copy()
            
            if not df_plot.empty:
                # Filtrer dem fra som mangler start-koordinater (f.eks. hvis data er ukomplet)
                df_plot = df_plot[df_plot['PASS_START_X'] > 0]

                # 1. Tegn pilene (Fra start til skud-punkt)
                # Vi deler dem op for at give assists guld og key passes grå
                for _, row in df_plot.iterrows():
                    color = HIF_GOLD if row['IS_ASSIST'] else '#999999'
                    alpha = 1.0 if row['IS_ASSIST'] else 0.6
                    
                    pitch.arrows(row.PASS_START_X, row.PASS_START_Y,
                                 row.EVENT_X, row.EVENT_Y,
                                 color=color, alpha=alpha, width=2, 
                                 headwidth=3, headlength=3, ax=ax, zorder=2)
                
                # 2. Prikker hvor afleveringen SLUTTER (der hvor skuddet tages)
                colors = df_plot['IS_ASSIST'].map({True: HIF_GOLD, False: '#999999'})
                pitch.scatter(df_plot.EVENT_X, df_plot.EVENT_Y, 
                             s=150, color=colors, edgecolors='black', linewidth=0.8, ax=ax, zorder=3)
            else:
                st.warning("Ingen assists fundet for denne spiller.")
            
            st.pyplot(fig, use_container_width=True)
