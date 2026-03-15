import streamlit as st
import pandas as pd
from mplsoccer import Pitch
import matplotlib.pyplot as plt

# HIF Design-konstanter
HIF_RED = '#cc0000'
ASSIST_BLUE = '#1e90ff'
HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

def vis_side(dp):
    st.markdown(f"""
        <style>
            .stat-box-side {{ background-color: #f8f9fa; padding: 12px; border-radius: 8px; border-left: 5px solid {HIF_RED}; margin-bottom: 8px; }}
            .stat-label-side {{ font-size: 0.7rem; text-transform: uppercase; color: #666; font-weight: 800; }}
            .stat-value-side {{ font-size: 1.2rem; font-weight: 900; color: #1a1a1a; }}
        </style>
    """, unsafe_allow_html=True)

    df = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame())
    if df.empty: return

    # 1. Rens data og timestamps
    df['RAW_X'] = pd.to_numeric(df['RAW_X'], errors='coerce')
    df['RAW_Y'] = pd.to_numeric(df['RAW_Y'], errors='coerce')
    df = df[~((df['RAW_X'] == 0) & (df['RAW_Y'] == 0))].copy()
    df['EVENT_TIMESTAMP'] = pd.to_datetime(df['EVENT_TIMESTAMP'])

    goal_events = df[df['EVENT_TYPEID'] == 16].sort_values('EVENT_TIMESTAMP', ascending=False)
    if goal_events.empty: return
    goal_events['LABEL'] = goal_events.apply(lambda x: f"{x['EVENT_TIMEMIN']}'. min: {x['PLAYER_NAME']}", axis=1)
    
    col_main, col_side = st.columns([2.5, 1])

    with col_side:
        selected_label = st.selectbox("Vælg mål", options=goal_events['LABEL'].unique())
        sel_row = goal_events[goal_events['LABEL'] == selected_label].iloc[0]
        
        temp_seq = df[df['SEQUENCEID'] == sel_row['SEQUENCEID']].sort_values('EVENT_TIMESTAMP').reset_index(drop=True)
        
        # Start ved seneste restart (indkast/hjørne)
        restarts = temp_seq[temp_seq['EVENT_TYPEID'].isin([5, 6])]
        start_idx = restarts.index[-1] if not restarts.empty else 0
        active_seq = temp_seq.iloc[start_idx:].reset_index(drop=True)

        # Roller: Scorer og Sidste HIF-spiller
        goal_idx_val = active_seq[active_seq['EVENT_TYPEID'] == 16].index[-1]
        last_hif_idx = next((i for i in range(goal_idx_val - 1, -1, -1) 
                            if active_seq.loc[i, 'EVENT_CONTESTANT_OPTAUUID'] == HIF_UUID), -1)

        st.markdown(f'<div class="stat-box-side"><div class="stat-label-side">Målscorer</div><div class="stat-value-side">{sel_row["PLAYER_NAME"].split()[-1]}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-box-side" style="border-left-color: {ASSIST_BLUE}"><div class="stat-label-side">Sidst på bolden</div><div class="stat-value-side">{active_seq.loc[last_hif_idx, "PLAYER_NAME"].split()[-1] if last_hif_idx != -1 else "Solo"}</div></div>', unsafe_allow_html=True)

    with col_main:
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 7))
        should_flip = True if sel_row['RAW_X'] < 50 else False

        display_elements = []
        for i, r in active_seq.iterrows():
            is_hif = r['EVENT_CONTESTANT_OPTAUUID'] == HIF_UUID
            
            # --- AGGRESSIV DUPLIKAT-RENSNING (Spatial Clustering) ---
            # Hvis den nye hændelse er tættere end 2 enheder på den forrige station, 
            # så dropper vi den, medmindre det er selve målet.
            if display_elements and r['EVENT_TYPEID'] != 16:
                last = display_elements[-1]
                dist = ((r['RAW_X'] - last['raw_x'])**2 + (r['RAW_Y'] - last['raw_y'])**2)**0.5
                if dist < 2.5: # 2.5 enheders radius fjerner sidelinje-støj effektivt
                    continue

            # Relevans-filter: HIF-spillere eller kritiske modstander-aktioner
            if is_hif or (not is_hif and r['EVENT_TYPEID'] in [12, 13, 14, 15, 43, 44]):
                rx, ry = r['RAW_X'], r['RAW_Y']
                
                # Modstander-alignment (tving dem til angrebsenden)
                if not is_hif and ((not should_flip and rx < 50) or (should_flip and rx > 50)):
                    rx, ry = 100 - rx, 100 - ry
                
                cx, cy = (100 - rx if should_flip else rx), (100 - ry if should_flip else ry)
                display_elements.append({
                    'x': cx, 'y': cy, 'raw_x': r['RAW_X'], 'raw_y': r['RAW_Y'],
                    'is_hif': is_hif, 'name': r['PLAYER_NAME'], 'idx': i
                })

        # Tegn linjer
        for i in range(1, len(display_elements)):
            curr, prev = display_elements[i], display_elements[i-1]
            ax.annotate('', xy=(curr['x'], curr['y']), xytext=(prev['x'], prev['y']),
                        arrowprops=dict(arrowstyle='->', color='#cccccc', lw=1.5, alpha=0.4))

        # Tegn spillere
        for el in display_elements:
            if el['is_hif']:
                # Find original index i active_seq for at matche farve korrekt
                orig_idx = el['idx']
                color = HIF_RED if orig_idx == goal_idx_val else (ASSIST_BLUE if orig_idx == last_hif_idx else '#aaaaaa')
                s, z = 180, 4
                ax.text(el['x'], el['y'] + 3, el['name'].split()[-1], fontsize=8, ha='center', fontweight='bold')
            else:
                color, s, z = 'black', 80, 3
            
            pitch.scatter(el['x'], el['y'], s=s, color=color, edgecolors='white', ax=ax, zorder=z)

        st.pyplot(fig)
