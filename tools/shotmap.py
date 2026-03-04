import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt

# HIF Identitet
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
    
    # 1. Hent data fra din retur-pakke
    df_skud = dp.get('playerstats', pd.DataFrame())
    df_assists = dp.get('assists', pd.DataFrame()) 
    
    tab1, tab2 = st.tabs(["AFSLUTNINGER", "CHANCESKABELSE"])

    # --- TAB 1: AFSLUTNINGER ---
    with tab1:
        if df_skud.empty:
            st.info("Ingen skuddata fundet.")
        else:
            col_viz, col_ctrl = st.columns([3, 1])
            with col_ctrl:
                spiller_liste = sorted(df_skud['PLAYER_NAME'].unique())
                v_skud = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste, key="sb_skud")
                df_vis = df_skud if v_skud == "Hele Holdet" else df_skud[df_skud['PLAYER_NAME'] == v_skud]
                
                st.markdown(f'<div class="stat-box"><div class="stat-label">Skud</div><div class="stat-value">{len(df_vis)}</div></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="stat-box"><div class="stat-label">Mål</div><div class="stat-value">{len(df_vis[df_vis["EVENT_TYPEID"]==16])}</div></div>', unsafe_allow_html=True)

            with col_viz:
                pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
                fig, ax = pitch.draw(figsize=(8, 10))
                c_map = (df_vis['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
                pitch.scatter(df_vis['EVENT_X'], df_vis['EVENT_Y'], s=150, c=c_map, edgecolors=HIF_RED, ax=ax)
                st.pyplot(fig)

    # --- TAB 2: CHANCESKABELSE ---
    with tab2:
        if df_assists.empty:
            st.info("Ingen assists (mål) fundet for Hvidovre.")
        else:
            col_viz_a, col_ctrl_a = st.columns([3, 1])
            
            with col_ctrl_a:
                spiller_liste_a = sorted([s for s in df_assists['ASSIST_PLAYER'].unique() if pd.notna(s)])
                v_a = st.selectbox("Vælg spiller (Assists)", options=["Hele Holdet"] + spiller_liste_a, key="sb_assist")
                
                df_a_vis = df_assists if v_a == "Hele Holdet" else df_assists[df_assists['ASSIST_PLAYER'] == v_a]
                
                st.markdown(f'<div class="stat-box"><div class="stat-label">Goal Assists</div><div class="stat-value">{len(df_a_vis)}</div></div>', unsafe_allow_html=True)

            with col_viz_a:
                pitch_a = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
                fig_a, ax_a = pitch_a.draw(figsize=(8, 10))
                
                # Tilføj i tab2 under kortet
                if not df_a_vis.empty:
                    st.write("---")
                    st.subheader("📋 Detaljeret oversigt")
                    
                    # Klargør data til visning
                    df_table = df_a_vis[['ASSIST_PLAYER', 'SCORER', 'EVENT_TIMESTAMP']].copy()
                    df_table.columns = ['Assisteret af', 'Målscorer', 'Tidspunkt']
                    
                    # Vis tabel
                    st.dataframe(
                        df_table.sort_values('Tidspunkt', ascending=False),
                        use_container_width=True,
                        hide_index=True
                    )
                
                st.pyplot(fig_a, use_container_width=True)
