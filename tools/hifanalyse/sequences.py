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
        
        # N = Mål (Event 16), N-1 = Skuddet, N-2 = Assisten
        goal_idx = active_seq[active_seq['EVENT_TYPEID'] == 16].index[-1]
        goal_row = active_seq.loc[goal_idx]
        shot_row = active_seq.iloc[goal_idx - 1] if goal_idx > 0 else None
        
        flip = True if goal_row['EVENT_X'] < 50 else False
        def fx(x): return 100 - x if flip else x
        def fy(y): return 100 - y if flip else y

        # Titlen skal vise skytten (fra goal_row, da Opta logger skytten der)
        scorer = goal_row['PLAYER_NAME']
        opp = goal_row.get('AWAY_TEAM') if "Hvidovre" in str(goal_row.get('HOME_TEAM')) else goal_row.get('HOME_TEAM')
        match_title = f"{scorer} vs. {opp}"

    with col_viz:
        st.markdown(f'<div class="match-header">{match_title}</div>', unsafe_allow_html=True)
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(12, 8))

        # 1. TEGN HELE SEKVENSTREEREN (Opspil og assist)
        for i in range(goal_idx - 1):
            curr = active_seq.iloc[i]
            nxt = active_seq.iloc[i+1]
            
            # Vi bruger guld til assisten (sidste aflevering før skuddet)
            is_assist = (i == goal_idx - 2)
            l_color = HIF_GOLD if is_assist else '#e0e0e0'
            l_width = 3 if is_assist else 1.5
            
            pitch.arrows(fx(curr['EVENT_X']), fy(curr['EVENT_Y']), 
                         fx(nxt['EVENT_X']), fy(nxt['EVENT_Y']), 
                         color=l_color, width=l_width, headwidth=4, ax=ax, zorder=2)
            
            # Tegn navne på alle i opspillet (valgfrit, men giver god kontekst)
            p_label = curr['PLAYER_NAME'].split(' ')[-1] if curr['PLAYER_NAME'] else ""
            ax.text(fx(curr['EVENT_X']), fy(curr['EVENT_Y']) - 2, p_label, fontsize=7, alpha=0.6, ha='center')

        # 2. TEGN SELVE AFSLUTNINGEN (Den røde pil)
        if shot_row is not None:
            x_shot, y_shot = fx(shot_row['EVENT_X']), fy(shot_row['EVENT_Y'])
            
            # Pilen går til målet
            pitch.arrows(x_shot, y_shot, 100, 50, 
                         color=HIF_RED, width=6, headwidth=5, ax=ax, zorder=5)
            
            # --- DETTE ER FIXET: Prikken og Navnet flyttes til x_shot ---
            # Vi markerer skyttens position som det vigtigste punkt
            pitch.scatter(x_shot, y_shot, s=200, color=HIF_RED, edgecolors='black', ax=ax, zorder=6)
            
            # Navnet på skytten placeres nu under skud-prikken
            s_name = scorer.split(' ')[-1] if scorer else "Skytte"
            ax.text(x_shot, y_shot - 4, s_name, fontsize=11, fontweight='bold', ha='center', zorder=7)

        # 3. MARKER HVOR BOLDEN ENDER (Kun en lille prik uden navn)
        pitch.scatter(100, 50, s=80, color=HIF_RED, edgecolors='black', alpha=0.3, ax=ax, zorder=4)

        st.pyplot(fig, use_container_width=True)
