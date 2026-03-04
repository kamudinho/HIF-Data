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
    
    # 1. Hent data (Søger bredt efter de rigtige nøgler fra din SQL)
    if isinstance(dp, dict):
        df_hif = dp.get('opta_shotevents', dp.get('playerstats', pd.DataFrame()))
    else:
        df_hif = dp
    
    if df_hif.empty:
        st.info("Ingen kampdata fundet for Hvidovre.")
        return

    # --- DATA FORBEREDELSE ---
    # Sørg for at koordinater er tal og map SQL-navne til plot-navne
    coord_cols = {
        'EVENT_X': 'EVENT_X', 'EVENT_Y': 'EVENT_Y',
        'PASS_START_X': 'PASS_X', 'PASS_START_Y': 'PASS_Y'
    }
    for sql_col, plot_col in coord_cols.items():
        if sql_col in df_hif.columns:
            df_hif[plot_col] = pd.to_numeric(df_hif[sql_col], errors='coerce').fillna(0)

    # Identificer Assists (bruger din MANUAL_ASSIST_MARKER eller QUALS_IDS fra SQL)
    if 'IS_ASSIST' not in df_hif.columns:
        df_hif['IS_ASSIST'] = df_hif.apply(
            lambda x: 1 if ('210' in str(x.get('QUALS_IDS', '')) or x.get('MANUAL_ASSIST_MARKER') == '210' or '29' in str(x.get('QUALS_IDS', ''))) else 0, 
            axis=1
        )

    tab1, tab2 = st.tabs(["AFSLUTNINGER", "CHANCESKABELSE"])

    # --- TAB 1: AFSLUTNINGER ---
    with tab1:
        col_viz, col_ctrl = st.columns([3, 1])
        # Opta Event IDs: 13, 14, 15 (Miss/Post/Saved), 16 (Goal)
        df_skud = df_hif[df_hif['EVENT_TYPEID'].isin([13, 14, 15, 16])].copy()
        
        with col_ctrl:
            spiller_liste = sorted([s for s in df_skud['PLAYER_NAME'].unique() if pd.notna(s)])
            v_skud = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste, key="sb_skud")
            df_skud_vis = df_skud if v_skud == "Hele Holdet" else df_skud[df_skud['PLAYER_NAME'] == v_skud]
            
            n_goals = int((df_skud_vis["EVENT_TYPEID"] == 16).sum())
            xg_total = df_skud_vis["XG_VAL"].sum() if "XG_VAL" in df_skud_vis.columns else 0.0
            
            st.markdown(f'<div class="stat-box"><div class="stat-label">Skud</div><div class="stat-value">{len(df_skud_vis)}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Mål</div><div class="stat-value">{n_goals}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">xG</div><div class="stat-value">{xg_total:.2f}</div></div>', unsafe_allow_html=True)

        with col_viz:
            pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc', goal_type='box')
            fig, ax = pitch.draw(figsize=(8, 10))
            if not df_skud_vis.empty:
                c_map = (df_skud_vis['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
                # Hvis xG mangler, bruger vi en standard størrelse (100)
                sizes = (df_skud_vis['XG_VAL'] * 900 + 70) if "XG_VAL" in df_skud_vis.columns else 100
                
                pitch.scatter(df_skud_vis['EVENT_X'], df_skud_vis['EVENT_Y'], 
                             s=sizes, c=c_map, edgecolors=HIF_RED, linewidth=1.5, ax=ax, zorder=3)
            st.pyplot(fig, use_container_width=True)

    # --- TAB 2: CHANCESKABELSE ---
    with tab2:
        col_viz_a, col_ctrl_a = st.columns([3, 1])
        df_a = df_hif[df_hif['IS_ASSIST'] == 1].copy()

        with col_ctrl_a:
            # Vi bruger PLAYER_NAME som assistmager, da det er ham der er på rækken i shotevents
            spiller_liste_a = sorted([s for s in df_a['PLAYER_NAME'].unique() if pd.notna(s)])
            v_a = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste_a, key="sb_assist")
            
            df_a_vis = df_a if v_a == "Hele Holdet" else df_a[df_a['PLAYER_NAME'] == v_a]
            
            n_assists = int((df_a_vis['EVENT_TYPEID'] == 16).sum())
            st.markdown(f'<div class="stat-box" style="border-left-color:{HIF_GOLD}"><div class="stat-label">Goal Assists</div><div class="stat-value">{n_assists}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box" style="border-left-color:#aaaaaa"><div class="stat-label">Shot Assists</div><div class="stat-value">{len(df_a_vis) - n_assists}</div></div>', unsafe_allow_html=True)

        with col_viz_a:
            pitch_a = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig_a, ax_a = pitch_a.draw(figsize=(8, 10))
            
            if not df_a_vis.empty:
                # Filtrer dem fra der mangler start-koordinater for passet
                df_plot_a = df_a_vis[df_a_vis['PASS_X'] > 0]
                
                for _, row in df_plot_a.iterrows():
                    color = HIF_GOLD if row['EVENT_TYPEID'] == 16 else '#aaaaaa'
                    pitch_a.arrows(row['PASS_X'], row['PASS_Y'], row['EVENT_X'], row['EVENT_Y'],
                                   color=color, width=2, headwidth=4, ax=ax_a, zorder=3)
                
                pitch_a.scatter(df_a_vis['EVENT_X'], df_a_vis['EVENT_Y'], s=80, color='white', edgecolors='#333333', ax=ax_a, zorder=4)
            else:
                st.info("Ingen assist-data fundet for denne spiller.")
            
            st.pyplot(fig_a, use_container_width=True)
