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
    
    if len(goal_ids) == 0: return

    col_viz, col_ctrl = st.columns([2.5, 1])

    with col_ctrl:
        selected_id = st.selectbox("Vælg scoring", options=goal_ids)
        active_seq = df_seq[df_seq['SEQUENCEID'] == selected_id].copy().reset_index(drop=True)
        
        goal_idx = active_seq[active_seq['EVENT_TYPEID'] == 16].index[-1]
        goal_row = active_seq.loc[goal_idx]
        shot_row = active_seq.iloc[goal_idx - 1] if goal_idx > 0 else None
        
        flip = True if goal_row['EVENT_X'] < 50 else False
        def fx(x): return 100 - x if flip else x
        def fy(y): return 100 - y if flip else y

        scorer = goal_row['PLAYER_NAME']
        h_team = goal_row.get('HOME_TEAM', 'Hvidovre')
        a_team = goal_row.get('AWAY_TEAM', 'Modstander')
        opp = a_team if "Hvidovre" in str(h_team) else h_team
        match_title = f"{scorer} vs. {opp}"

    with col_viz:
        st.markdown(f'<div class="match-header">{match_title}</div>', unsafe_allow_html=True)
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(12, 8))

        # 1. TEGN OPSPIL (Grå pile)
        for i in range(goal_idx - 1):
            curr = active_seq.iloc[i]
            nxt = active_seq.iloc[i+1]
            pitch.arrows(fx(curr['EVENT_X']), fy(curr['EVENT_Y']), 
                         fx(nxt['EVENT_X']), fy(nxt['EVENT_Y']), 
                         color='#e0e0e0', width=2, headwidth=4, ax=ax, zorder=2)

        # 2. TEGN SELVE AFSLUTNINGEN
        if shot_row is not None:
            # Koordinater for hvor skuddet starter
            x_shot, y_shot = fx(shot_row['EVENT_X']), fy(shot_row['EVENT_Y'])
            
            # Pilen fra skudposition til målet (100, 50)
            pitch.arrows(x_shot, y_shot, 100, 50, 
                         color=HIF_RED, width=5, headwidth=5, headlength=5, ax=ax, zorder=5)
            
            # --- HER ER FIXET ---
            # Vi placerer nu 'prikken' og 'navnet' ved x_shot/y_shot (hvor han skyder fra)
            # i stedet for inde på målstregen.
            pitch.scatter(x_shot, y_shot, s=180, color=HIF_GOLD, edgecolors='black', ax=ax, zorder=6)
            
            s_name = shot_row['PLAYER_NAME'].split(' ')[-1] if shot_row['PLAYER_NAME'] else "Skytte"
            ax.text(x_shot, y_shot - 4, s_name, fontsize=10, fontweight='bold', ha='center', zorder=7)

        # 3. VALGFRIT: En lille markør ved målet (hvor bolden ender)
        # Men vi fjerner navnet herfra for at undgå rod på målstregen
        pitch.scatter(100, 50, s=100, color=HIF_RED, edgecolors='black', alpha=0.5, ax=ax, zorder=4)

        st.pyplot(fig, use_container_width=True)
