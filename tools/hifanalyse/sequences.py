import streamlit as st
import pandas as pd
from mplsoccer import Pitch

HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'

def vis_side(dp):
    st.markdown(f"<style>.match-header {{ font-size: 1.4rem; font-weight: 800; color: {HIF_RED}; text-align: center; margin-bottom: 20px; text-transform: uppercase; }}</style>", unsafe_allow_html=True)

    df_seq = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame()).copy()
    if df_seq.empty: return

    df_seq = df_seq.sort_values(['SEQUENCEID', 'EVENT_TIMESTAMP']).reset_index(drop=True)
    goal_ids = df_seq[df_seq['EVENT_TYPEID'] == 16]['SEQUENCEID'].unique()
    
    col_viz, col_ctrl = st.columns([2.5, 1])

    with col_ctrl:
        selected_id = st.selectbox("Vælg scoring", options=goal_ids)
        active_seq = df_seq[df_seq['SEQUENCEID'] == selected_id].copy().reset_index(drop=True)
        
        # Find de tre nøgle-punkter
        goal_idx = active_seq[active_seq['EVENT_TYPEID'] == 16].index[-1]
        shot_idx = goal_idx - 1
        assist_idx = goal_idx - 2

        goal_row = active_seq.loc[goal_idx]
        shot_row = active_seq.loc[shot_idx] if shot_idx >= 0 else None
        assist_row = active_seq.loc[assist_idx] if assist_idx >= 0 else None
        
        flip = True if goal_row['EVENT_X'] < 50 else False
        def fx(x): return 100 - x if flip else x
        def fy(y): return 100 - y if flip else y

    with col_viz:
        st.markdown(f'<div class="match-header">{goal_row["PLAYER_NAME"]} vs. Modstander</div>', unsafe_allow_html=True)
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(12, 8))

        # 1. TEGN ASSISTEN (Smed på dit billede)
        if assist_row is not None and shot_row is not None:
            pitch.arrows(fx(assist_row['EVENT_X']), fy(assist_row['EVENT_Y']), 
                         fx(shot_row['EVENT_X']), fy(shot_row['EVENT_Y']), 
                         color=HIF_GOLD, width=4, headwidth=4, ax=ax, zorder=2)
            
            # Navn på assistenten (Smed)
            a_name = assist_row['PLAYER_NAME'].split(' ')[-1]
            ax.text(fx(assist_row['EVENT_X']), fy(assist_row['EVENT_Y']) + 3, a_name, 
                    fontsize=9, color='#666666', ha='center', zorder=3)

        # 2. TEGN SKYTTEN (Clausen - ham der scorer)
        if shot_row is not None:
            # Rød pil fra Clausen mod målet
            pitch.arrows(fx(shot_row['EVENT_X']), fy(shot_row['EVENT_Y']), 
                         100, 50, 
                         color=HIF_RED, width=6, headwidth=5, ax=ax, zorder=4)
            
            # Den store "Hoved-prik" ved Clausens fødder
            pitch.scatter(fx(shot_row['EVENT_X']), fy(shot_row['EVENT_Y']), 
                          s=250, color=HIF_RED, edgecolors='black', linewidth=2, ax=ax, zorder=5)
            
            # Clausens navn - Større og tydeligere
            s_name = goal_row['PLAYER_NAME'].split(' ')[-1]
            ax.text(fx(shot_row['EVENT_X']), fy(shot_row['EVENT_Y']) - 5, s_name, 
                    fontsize=12, fontweight='bold', ha='center', zorder=6)

        # 3. MÅL-MARKØR (Hvor bolden ender)
        pitch.scatter(100, 50, s=100, color=HIF_RED, alpha=0.4, ax=ax, zorder=1)

        st.pyplot(fig, use_container_width=True)
