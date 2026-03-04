import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch

# HIF Identitet
HIF_RED = '#cc0000'
HIF_BLUE = '#0056a3'
HIF_GOLD = '#b8860b' 
HIF_OPTA_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"

def vis_side(dp, logo_map=None):
    # CSS - Samme stil som før
    st.markdown("""
        <style>
            .stat-box {
                background-color: #f8f9fa;
                padding: 10px 15px;
                border-radius: 8px;
                border-left: 5px solid #cc0000;
                margin-bottom: 8px;
            }
            .stat-label {
                font-size: 0.8rem;
                text-transform: uppercase;
                color: #666;
                font-weight: bold;
                display: flex;
                align-items: center;
            }
            .stat-value {
                font-size: 1.6rem;
                font-weight: 800;
                color: #1a1a1a;
                margin-left: 22px;
                line-height: 1.1;
            }
            .dot { height: 10px; width: 10px; border-radius: 50%; display: inline-block; margin-right: 8px; }
        </style>
    """, unsafe_allow_html=True)
    
    # Hent data fra din nye struktur
    # Vi prioriterer 'player_stats' fra 'opta' pakken
    df_hif = dp.get('opta', {}).get('player_stats', pd.DataFrame())
    
    if df_hif.empty:
        st.info("Ingen kampdata fundet (Hvidovre IF).")
        return

    # Sørg for at vi kun kigger på Hvidovre
    df_hif = df_hif[df_hif['EVENT_CONTESTANT_OPTAUUID'] == HIF_OPTA_UUID].copy()
    df_hif['PLAYER_NAME'] = df_hif['PLAYER_NAME'].fillna('Ukendt')

    tab1, tab2 = st.tabs(["AFSLUTNINGER", "CHANCESKABELSE"])

    # --- TAB 1: AFSLUTNINGER (Shots & Goals) ---
    with tab1:
        col_viz, col_ctrl = st.columns([3, 1])
        
        # Filtrer shots (Type 13, 14, 15, 16)
        df_skud_alle = df_hif[df_hif['EVENT_TYPEID'].isin([13, 14, 15, 16])].copy()
        
        with col_ctrl:
            spiller_liste = sorted(df_skud_alle['PLAYER_NAME'].unique().tolist())
            v_skud = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste, key="sb_skud")
            
            df_skud_vis = df_skud_alle.copy()
            if v_skud != "Hele Holdet":
                df_skud_vis = df_skud_vis[df_skud_vis['PLAYER_NAME'] == v_skud]
            
            n_maal = int((df_skud_vis['EVENT_TYPEID'] == 16).sum())
            n_skud = len(df_skud_vis)
            total_xg = df_skud_vis['XG_VAL'].sum() if 'XG_VAL' in df_skud_vis.columns else 0

            st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-label"><span class="dot" style="background-color:white; border:2px solid {HIF_RED}"></span> Skud</div>
                    <div class="stat-value">{n_skud}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label"><span class="dot" style="background-color:{HIF_RED}"></span> Mål</div>
                    <div class="stat-value">{n_maal}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Expected Goals (xG)</div>
                    <div class="stat-value">{total_xg:.2f}</div>
                </div>
            """, unsafe_allow_html=True)

        with col_viz:
            pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(7, 9))
            
            if not df_skud_vis.empty:
                # Mål er fyldte, misses er hvide med rød kant
                c_map = (df_skud_vis['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
                # Størrelse baseret på xG hvis muligt
                size = df_skud_vis['XG_VAL'] * 1000 + 50 if 'XG_VAL' in df_skud_vis.columns else 100
                
                pitch.scatter(df_skud_vis['EVENT_X'], df_skud_vis['EVENT_Y'], 
                              s=size, c=c_map, edgecolors=HIF_RED, 
                              linewidth=1.2, ax=ax, zorder=3)
            st.pyplot(fig, use_container_width=True)

    # --- TAB 2: CHANCESKABELSE (Assists & Key Passes) ---
    with tab2:
        col_viz_a, col_ctrl_a = st.columns([3, 1])
        
        # Nu kigger vi efter alle events, der har en assist-markør ELLER en pass_start position på et skud
        df_assists_alle = df_hif[
            (df_hif['IS_ASSIST'] == 1) | 
            (pd.notna(df_hif['PASS_START_X']) & (df_hif['PASS_START_X'] > 0))
        ].copy()

        with col_ctrl_a:
            spiller_liste_a = sorted(df_assists_alle['PLAYER_NAME'].unique().tolist())
            v_a = st.selectbox("Vælg spiller", options=["Hvidovre IF"] + spiller_liste_a, key="sb_assist")
            
            df_a_vis = df_assists_alle.copy()
            if v_a != "Hvidovre IF":
                df_a_vis = df_a_vis[df_a_vis['PLAYER_NAME'] == v_a]
            
            n_assists = int((df_a_vis['IS_ASSIST'] == 1) & (df_a_vis['EVENT_OUTCOME'] == 1)).sum()
            n_key_passes = len(df_a_vis) - n_assists

            st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-label"><span class="dot" style="background-color:{HIF_GOLD}"></span> Assists</div>
                    <div class="stat-value">{n_assists}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label"><span class="dot" style="background-color:#999999"></span> Shot Assists</div>
                    <div class="stat-value">{n_key_passes}</div>
                </div>
            """, unsafe_allow_html=True)

        with col_viz_a:
            pitch_a = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig_a, ax_a = pitch_a.draw(figsize=(7, 9))
            
            if not df_a_vis.empty:
                # Vi tegner linjen fra der hvor afleveringen startede (PASS_START) til skuddet (EVENT_X)
                # Bemærk: I din nye struktur ligger pass-data PÅ selve skud-eventet
                pitch_a.arrows(df_a_vis['PASS_START_X'].astype(float), 
                               df_a_vis['PASS_START_Y'].astype(float),
                               df_a_vis['EVENT_X'].astype(float), 
                               df_a_vis['EVENT_Y'].astype(float),
                               color='#dddddd', width=2, headwidth=3, ax=ax_a, zorder=1)
                
                # Prikken markerer skudpositionen
                dot_colors = df_a_vis['IS_ASSIST'].map({1: HIF_GOLD, 0: '#999999'})
                pitch_a.scatter(df_a_vis['EVENT_X'], df_a_vis['EVENT_Y'], 
                                s=100, color=dot_colors, edgecolors='white', 
                                linewidth=1.2, ax=ax_a, zorder=2)
            st.pyplot(fig_a, use_container_width=True)
