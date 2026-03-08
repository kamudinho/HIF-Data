import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# HIF Identitet
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b' 
DZ_COLOR = '#1f77b4'

def vis_side(dp):
    st.markdown("""
        <style>
            .stat-box { background-color: #f8f9fa; padding: 10px 15px; border-radius: 8px; border-left: 5px solid #cc0000; margin-bottom: 8px; }
            .stat-label { font-size: 0.8rem; text-transform: uppercase; color: #666; font-weight: bold; }
            .stat-value { font-size: 1.6rem; font-weight: 800; color: #1a1a1a; margin-left: 5px; }
        </style>
    """, unsafe_allow_html=True)
    
    # 1. Hent data
    df_skud = dp.get('playerstats', pd.DataFrame()).copy()
    df_assists = dp.get('assists', pd.DataFrame()).copy()
    
    # Præ-processering: Definer Danger Zone geografisk (Opta system: 0-100)
    # Dette sikrer at logikken altid matcher det visuelle rektangel
    if not df_skud.empty:
        df_skud['IS_DZ_GEO'] = (
            (df_skud['EVENT_X'] >= 88.5) & 
            (df_skud['EVENT_Y'] >= 37.0) & 
            (df_skud['EVENT_Y'] <= 63.0)
        )
    else:
        df_skud['IS_DZ_GEO'] = False

    tab1, tab2, tab3 = st.tabs(["AFSLUTNINGER", "ASSISTS", "DANGER ZONE"])

    # --- TAB 1: AFSLUTNINGER ---
    with tab1:
        if df_skud.empty:
            st.info("Ingen skuddata fundet.")
        else:
            col_viz, col_ctrl = st.columns([3, 1])
            with col_ctrl:
                spiller_liste = sorted(df_skud['PLAYER_NAME'].unique())
                v_skud = st.selectbox("Vælg spiller", options=["Hvidovre IF"] + spiller_liste, key="sb_skud")
                df_vis = df_skud if v_skud == "Hvidovre IF" else df_skud[df_skud['PLAYER_NAME'] == v_skud]
                
                st.markdown(f'<div class="stat-box"><div class="stat-label">Skud i alt</div><div class="stat-value">{len(df_vis)}</div></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="stat-box"><div class="stat-label">Mål</div><div class="stat-value">{len(df_vis[df_vis["EVENT_TYPEID"]==16])}</div></div>', unsafe_allow_html=True)

            with col_viz:
                pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
                fig, ax = pitch.draw(figsize=(8, 10))
                
                # Farvekode: Mål er røde, miss er hvide med rød kant
                c_map = (df_vis['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
                pitch.scatter(df_vis['EVENT_X'], df_vis['EVENT_Y'], s=150, c=c_map, edgecolors=HIF_RED, ax=ax)
                st.pyplot(fig)

    # --- TAB 2: ASSISTS ---
    with tab2:
        if df_assists.empty:
            st.warning("⚠️ Ingen assists fundet.")
        else:
            col_viz_a, col_ctrl_a = st.columns([3, 1])
            with col_ctrl_a:
                spiller_liste_a = sorted([s for s in df_assists['ASSIST_PLAYER'].unique() if pd.notna(s)])
                v_a = st.selectbox("Vælg spiller (Assists)", options=["Hvidovre IF"] + spiller_liste_a, key="sb_assist")
                df_a_vis = df_assists if v_a == "Hvidovre IF" else df_assists[df_assists['ASSIST_PLAYER'] == v_a]
                st.markdown(f'<div class="stat-box"><div class="stat-label">Goal Assists</div><div class="stat-value">{len(df_a_vis)}</div></div>', unsafe_allow_html=True)

            with col_viz_a:
                pitch_a = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
                fig_a, ax_a = pitch_a.draw(figsize=(8, 10))
                if not df_a_vis.empty:
                    # Tegn afleverings-pile
                    pitch_a.arrows(df_a_vis['PASS_START_X'], df_a_vis['PASS_START_Y'], 
                                   df_a_vis['SHOT_X'], df_a_vis['SHOT_Y'], 
                                   color='#888888', alpha=0.5, width=2, headwidth=4, ax=ax_a, zorder=1)
                    # Tegn startpunktet for afleveringen
                    pitch_a.scatter(df_a_vis['PASS_START_X'], df_a_vis['PASS_START_Y'], 
                                    s=120, color=HIF_GOLD, edgecolors='black', linewidth=1, ax=ax_a, zorder=2)
                st.pyplot(fig_a)

    # --- TAB 3: DANGER ZONE (GEOGRAFISK FILTRERING) ---
    with tab3:
        if df_skud.empty:
            st.info("Ingen data til DZ analyse.")
        else:
            col_dz_viz, col_dz_ctrl = st.columns([3, 1])
            with col_dz_ctrl:
                spiller_liste_dz = sorted(df_skud['PLAYER_NAME'].unique())
                v_dz = st.selectbox("Vælg spiller (DZ)", options=["Hvidovre IF"] + spiller_liste_dz, key="sb_dz")
                
                df_dz_full = df_skud if v_dz == "Hvidovre IF" else df_skud[df_skud['PLAYER_NAME'] == v_dz]
                
                # Split data baseret på den geografiske beregning
                dz_hits = df_dz_full[df_dz_full['IS_DZ_GEO'] == True].copy()
                non_dz = df_dz_full[df_dz_full['IS_DZ_GEO'] == False].copy()
                
                st.markdown(f'<div class="stat-box" style="border-left-color: {DZ_COLOR}"><div class="stat-label">Danger Zone Skud</div><div class="stat-value">{len(dz_hits)}</div></div>', unsafe_allow_html=True)
                
                if len(df_dz_full) > 0:
                    dz_pct = (len(dz_hits) / len(df_dz_full)) * 100
                    st.markdown(f'<div class="stat-box"><div class="stat-label">DZ Andel</div><div class="stat-value">{dz_pct:.1f}%</div></div>', unsafe_allow_html=True)

            with col_dz_viz:
                pitch_dz = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
                fig_dz, ax_dz = pitch_dz.draw(figsize=(8, 10))
                
                # Tegn Danger Zone rektangel (Matplotlib patches bruger Y, X for VerticalPitch)
                dz_rect = patches.Rectangle((37, 88.5), 26, 11.5, linewidth=2, 
                                            edgecolor=DZ_COLOR, facecolor=DZ_COLOR, 
                                            alpha=0.15, linestyle='--', zorder=1)
                ax_dz.add_patch(dz_rect)
                
                # 1. Tegn skud udenfor (tonet helt ned)
                if not non_dz.empty:
                    pitch_dz.scatter(non_dz['EVENT_X'], non_dz['EVENT_Y'], 
                                     s=60, c='white', edgecolors='#dddddd', 
                                     alpha=0.15, ax=ax_dz, zorder=2)
                
                # 2. Tegn skud indenfor (tydelige og farvekodede)
                if not dz_hits.empty:
                    c_dz = (dz_hits['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
                    pitch_dz.scatter(dz_hits['EVENT_X'], dz_hits['EVENT_Y'], 
                                     s=180, c=c_dz, edgecolors=HIF_RED, 
                                     linewidth=2, ax=ax_dz, zorder=3)
                
                st.pyplot(fig_dz)
