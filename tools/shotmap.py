import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt

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
    df_quals = dp.get('qualifiers', pd.DataFrame())
    
    # Præ-processering af Danger Zone
    if not df_skud.empty and not df_quals.empty:
        danger_ids = [16, 17, '16', '17']
        dz_events = df_quals[df_quals['QUALIFIER_QID'].isin(danger_ids)]['EVENT_OPTAUUID'].unique()
        df_skud['IS_DZ'] = df_skud['EVENT_OPTAUUID'].isin(dz_events)
    else:
        df_skud['IS_DZ'] = False

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
                st.markdown(f'<div class="stat-box"><div class="stat-label">Skud</div><div class="stat-value">{len(df_vis)}</div></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="stat-box"><div class="stat-label">Mål</div><div class="stat-value">{len(df_vis[df_vis["EVENT_TYPEID"]==16])}</div></div>', unsafe_allow_html=True)

            with col_viz:
                pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
                fig, ax = pitch.draw(figsize=(8, 10))
                c_map = (df_vis['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
                pitch.scatter(df_vis['EVENT_X'], df_vis['EVENT_Y'], s=150, c=c_map, edgecolors=HIF_RED, ax=ax)
                st.pyplot(fig)

    # --- TAB 2: ASSISTS (FIXET) ---
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
                    pitch_a.arrows(df_a_vis['PASS_START_X'], df_a_vis['PASS_START_Y'], 
                                   df_a_vis['SHOT_X'], df_a_vis['SHOT_Y'], 
                                   color='#888888', alpha=0.5, width=2, headwidth=4, ax=ax_a, zorder=1)
                    pitch_a.scatter(df_a_vis['PASS_START_X'], df_a_vis['PASS_START_Y'], 
                                    s=120, color=HIF_GOLD, edgecolors='black', linewidth=1, ax=ax_a, zorder=2)
                st.pyplot(fig_a)

    # --- TAB 3: DANGER ZONE (FIXET MED RECT) ---
    with tab3:
        if df_skud.empty:
            st.info("Ingen data til DZ analyse.")
        else:
            col_dz_viz, col_dz_ctrl = st.columns([3, 1])
            with col_dz_ctrl:
                spiller_liste_dz = sorted(df_skud['PLAYER_NAME'].unique())
                v_dz = st.selectbox("Vælg spiller (DZ)", options=["Hvidovre IF"] + spiller_liste_dz, key="sb_dz")
                df_dz_vis = df_skud if v_dz == "Hvidovre IF" else df_skud[df_skud['PLAYER_NAME'] == v_dz]
                
                dz_hits = df_dz_vis[df_dz_vis['IS_DZ']]
                st.markdown(f'<div class="stat-box" style="border-left-color: {DZ_COLOR}"><div class="stat-label">Danger Zone Skud</div><div class="stat-value">{len(dz_hits)}</div></div>', unsafe_allow_html=True)

            with col_dz_viz:
                pitch_dz = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
                fig_dz, ax_dz = pitch_dz.draw(figsize=(8, 10))
                
                # Brug .rect i stedet for .box
                # Opta koordinater: x_min=88.5, y_min=37, bredde=11.5, højde=26
                pitch_dz.rect(88.5, 37, 11.5, 26, ax=ax_dz, color=DZ_COLOR, alpha=0.15, linestyle='--', linewidth=2, zorder=1)
                
                non_dz = df_dz_vis[~df_dz_vis['IS_DZ']]
                pitch_dz.scatter(non_dz['EVENT_X'], non_dz['EVENT_Y'], s=80, c='white', edgecolors='#cccccc', alpha=0.3, ax=ax_dz)
                pitch_dz.scatter(dz_hits['EVENT_X'], dz_hits['EVENT_Y'], s=180, c=HIF_RED, edgecolors='black', ax=ax_dz)
                
                st.pyplot(fig_dz)
