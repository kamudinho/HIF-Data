import streamlit as st
import pandas as pd
from mplsoccer import Pitch
import matplotlib.pyplot as plt
import numpy as np

# HIF Design-konstanter
HIF_RED = '#cc0000'
ASSIST_BLUE = '#1e90ff'
HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

def vis_side(dp):
    # CSS og Styling bevares
    st.markdown(f"""
        <style>
            .stat-box-side {{ background-color: #f8f9fa; padding: 12px; border-radius: 8px; border-left: 5px solid {HIF_RED}; margin-bottom: 8px; }}
            .stat-label-side {{ font-size: 0.7rem; text-transform: uppercase; color: #666; font-weight: 800; }}
            .stat-value-side {{ font-size: 1.2rem; font-weight: 900; color: #1a1a1a; }}
        </style>
    """, unsafe_allow_html=True)

    df = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame())
    if df.empty: return

    # Rens data
    df['RAW_X'] = pd.to_numeric(df['RAW_X'], errors='coerce')
    df['RAW_Y'] = pd.to_numeric(df['RAW_Y'], errors='coerce')
    df = df[~((df['RAW_X'] == 0) & (df['RAW_Y'] == 0))].copy()
    df = df.dropna(subset=['RAW_X', 'RAW_Y'])
    df['EVENT_TIMESTAMP'] = pd.to_datetime(df['EVENT_TIMESTAMP'])

    goal_events = df[df['EVENT_TYPEID'] == 16].sort_values('EVENT_TIMESTAMP', ascending=False)
    if goal_events.empty: return
    goal_events['LABEL'] = goal_events.apply(lambda x: f"{x['EVENT_TIMEMIN']}'. min: {x['PLAYER_NAME']}", axis=1)
    
    col_main, col_side = st.columns([2.5, 1])

    with col_side:
        selected_label = st.selectbox("Vælg mål", options=goal_events['LABEL'].unique())
        sel_row = goal_events[goal_events['LABEL'] == selected_label].iloc[0]
        
        temp_seq = df[df['SEQUENCEID'] == sel_row['SEQUENCEID']].sort_values('EVENT_TIMESTAMP').reset_index(drop=True)
        
        # Find startpunkt: Prioritér seneste restart (indkast/hjørne)
        restarts = temp_seq[temp_seq['EVENT_TYPEID'].isin([5, 6])]
        if not restarts.empty:
            start_idx = restarts.index[-1]
            is_restart_start = True
        else:
            start_time = sel_row['EVENT_TIMESTAMP'] - pd.Timedelta(seconds=20)
            valid_time = temp_seq[temp_seq['EVENT_TIMESTAMP'] >= start_time]
            start_idx = valid_time.index[0] if not valid_time.empty else 0
            is_restart_start = False
            
        active_seq = temp_seq.iloc[start_idx:].reset_index(drop=True)

        # Roller (Scorer og sidste HIF-spiller før ham)
        goal_idx_in_active = active_seq[active_seq['EVENT_TYPEID'] == 16].index[-1]
        last_hif_idx = -1
        for i in range(goal_idx_in_active - 1, -1, -1):
            if active_seq.loc[i, 'EVENT_CONTESTANT_OPTAUUID'] == HIF_UUID:
                last_hif_idx = i
                break

        st.markdown(f'<div class="stat-box-side"><div class="stat-label-side">Målscorer</div><div class="stat-value-side">{sel_row["PLAYER_NAME"].split()[-1]}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-box-side" style="border-left-color: {ASSIST_BLUE}"><div class="stat-label-side">Sidst på bolden</div><div class="stat-value-side">{active_seq.loc[last_hif_idx, "PLAYER_NAME"].split()[-1] if last_hif_idx != -1 else "Solo"}</div></div>', unsafe_allow_html=True)

    with col_main:
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 7))
        should_flip = True if sel_row['RAW_X'] < 50 else False

        display_elements = []
        for i, r in active_seq.iterrows():
            is_hif = r['EVENT_CONTESTANT_OPTAUUID'] == HIF_UUID
            
            # --- NY RESTART-LOGIK ---
            # Hvis vi starter med et indkast/hjørne, ignorerer vi modstanderen i den ALLERFØRSTE aktion
            # for at sikre den direkte linje fra kanten.
            if is_restart_start and i == 0:
                is_relevant = True 
            else:
                # Ellers: Kun HIF eller vigtige modstander-aktioner (blokering/duel)
                is_relevant = is_hif or (not is_hif and r['EVENT_TYPEID'] in [12, 13, 14, 15, 44, 43])
            
            if is_relevant:
                rx, ry = r['RAW_X'], r['RAW_Y']
                if not is_hif:
                    if (not should_flip and rx < 50) or (should_flip and rx > 60):
                        rx, ry = 100 - rx, 100 - ry
                
                cx, cy = (100 - rx if should_flip else rx), (100 - ry if should_flip else ry)
                display_elements.append({'x': cx, 'y': cy, 'is_hif': is_hif, 'name': r['PLAYER_NAME'], 'idx': i})

        # Tegn streger først (så de ligger bag prikkerne)
        for i in range(1, len(display_elements)):
            curr, prev = display_elements[i], display_elements[i-1]
            ax.annotate('', xy=(curr['x'], curr['y']), xytext=(prev['x'], prev['y']),
                        arrowprops=dict(arrowstyle='->', color='#cccccc', lw=1.5, alpha=0.4))

        # Tegn prikker
        for el in display_elements:
            # Rød for mål, Blå for sidste HIF, Grå for resten, Sort for modstander
            if el['is_hif']:
                color = HIF_RED if el['idx'] == goal_idx_in_active else (ASSIST_BLUE if el['idx'] == last_hif_idx else '#aaaaaa')
                z = 4
                s = 180
            else:
                color = 'black'
                z = 3
                s = 80
            
            pitch.scatter(el['x'], el['y'], s=s, color=color, edgecolors='white', ax=ax, zorder=z)
            if el['is_hif']:
                ax.text(el['x'], el['y'] + 3, el['name'].split()[-1], fontsize=8, ha='center', fontweight='bold', zorder=5)

        st.pyplot(fig)
