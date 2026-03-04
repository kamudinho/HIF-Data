import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt

HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b' 

def vis_side(dp):
    st.markdown("""
        <style>
            .stat-box { background-color: #f8f9fa; padding: 10px 15px; border-radius: 8px; border-left: 5px solid #cc0000; margin-bottom: 8px; }
            .stat-label { font-size: 0.8rem; text-transform: uppercase; color: #666; font-weight: bold; }
            .stat-value { font-size: 1.6rem; font-weight: 800; color: #1a1a1a; margin-left: 5px; }
        </style>
    """, unsafe_allow_html=True)
    
    df_hif = dp.get('playerstats', pd.DataFrame())
    
    if df_hif.empty:
        st.write("Ingen data fundet for Hvidovre.")
        return

    tab1, tab2 = st.tabs(["AFSLUTNINGER", "CHANCESKABELSE"])

    # --- TAB 1: AFSLUTNINGER ---
    with tab1:
        col_viz, col_ctrl = st.columns([3, 1])
        df_skud = df_hif[df_hif['EVENT_TYPEID'].isin([13, 14, 15, 16])].copy()
        
        with col_ctrl:
            spiller_liste = sorted([s for s in df_skud['PLAYER_NAME'].unique() if pd.notna(s)])
            v_skud = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste, key="sb_skud")
            df_skud_vis = df_skud if v_skud == "Hele Holdet" else df_skud[df_skud['PLAYER_NAME'] == v_skud]
            
            n_goals = int((df_skud_vis["EVENT_TYPEID"] == 16).sum())
            st.markdown(f'<div class="stat-box"><div class="stat-label">Skud</div><div class="stat-value">{len(df_skud_vis)}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Mål</div><div class="stat-value">{n_goals}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">xG</div><div class="stat-value">{df_skud_vis["XG_VAL"].sum():.2f}</div></div>', unsafe_allow_html=True)

        with col_viz:
            pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc', goal_type='box', line_zorder=2)
            fig, ax = pitch.draw(figsize=(8, 10))
            if not df_skud_vis.empty:
                c_map = (df_skud_vis['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
                pitch.scatter(df_skud_vis['EVENT_X'], df_skud_vis['EVENT_Y'], 
                              s=df_skud_vis['XG_VAL']*900 + 70, 
                              c=c_map, edgecolors=HIF_RED, linewidth=1.5, ax=ax, zorder=3)
            st.pyplot(fig, use_container_width=True)

    # --- TAB 2: CHANCESKABELSE ---
    with tab2:
        col_viz_a, col_ctrl_a = st.columns([3, 1])
        # Filtrer rækker hvor vi har fundet en assistmager i data_load
        df_a = df_hif[df_hif['IS_ASSIST'] == 1].copy()

        with col_ctrl_a:
            # Her bruger vi ASSIST_PLAYER_NAME som vi skabte i data_load
            spiller_liste_a = sorted([s for s in df_a['ASSIST_PLAYER_NAME'].unique() if pd.notna(s) and s != "Ukendt"])
            v_a = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste_a, key="sb_assist")
            
            df_a_vis = df_a if v_a == "Hele Holdet" else df_a[df_a['ASSIST_PLAYER_NAME'] == v_a]
            
            n_assists = int((df_a_vis['EVENT_TYPEID'] == 16).sum())
            st.markdown(f'<div class="stat-box"><div class="stat-label">Goal Assists</div><div class="stat-value">{n_assists}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Shot Assists</div><div class="stat-value">{len(df_a_vis) - n_assists}</div></div>', unsafe_allow_html=True)

        with col_viz_a:
            pitch_a = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc', line_zorder=2)
            fig_a, ax_a = pitch_a.draw(figsize=(8, 10))
            
            if not df_a_vis.empty:
                for _, row in df_a_vis.iterrows():
                    color = HIF_GOLD if row['EVENT_TYPEID'] == 16 else '#aaaaaa'
                    # Vi tegner pilen fra afleveringspunktet til skudpunktet
                    pitch_a.arrows(row['PASS_X'], row['PASS_Y'], row['EVENT_X'], row['EVENT_Y'],
                                   color=color, width=2, headwidth=4, ax=ax_a, zorder=3)
                pitch_a.scatter(df_a_vis['EVENT_X'], df_a_vis['EVENT_Y'], s=60, color='white', edgecolors='#333333', ax=ax_a, zorder=4)
            
            st.pyplot(fig_a, use_container_width=True)
