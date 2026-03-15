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
    # 1. CSS og Styling
    st.markdown(f"""
        <style>
            .stat-box-side {{ background-color: #f8f9fa; padding: 12px; border-radius: 8px; border-left: 5px solid {HIF_RED}; margin-bottom: 8px; }}
            .stat-label-side {{ font-size: 0.7rem; text-transform: uppercase; color: #666; font-weight: 800; }}
            .stat-value-side {{ font-size: 1.2rem; font-weight: 900; color: #1a1a1a; }}
            .match-header {{ font-size: 1.3rem; font-weight: 800; color: {HIF_RED}; text-align: center; margin-bottom: 20px; text-transform: uppercase; }}
        </style>
    """, unsafe_allow_html=True)

    df = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame())
    if df.empty: return

    # Rens data: Fjern 0,0 og None
    df['RAW_X'] = pd.to_numeric(df['RAW_X'], errors='coerce')
    df['RAW_Y'] = pd.to_numeric(df['RAW_Y'], errors='coerce')
    df = df[~((df['RAW_X'] == 0) & (df['RAW_Y'] == 0))].copy()
    df = df.dropna(subset=['RAW_X', 'RAW_Y'])
    df['EVENT_TIMESTAMP'] = pd.to_datetime(df['EVENT_TIMESTAMP'])

    goal_events = df[df['EVENT_TYPEID'] == 16].copy()
    if goal_events.empty: return
    goal_events = goal_events.sort_values('EVENT_TIMESTAMP', ascending=False)
    goal_events['LABEL'] = goal_events.apply(lambda x: f"{x['EVENT_TIMEMIN']}'. min: {x['PLAYER_NAME']}", axis=1)
    
    col_main, col_side = st.columns([2.5, 1])

    with col_side:
        selected_label = st.selectbox("Vælg mål", options=goal_events['LABEL'].unique())
        sel_row = goal_events[goal_events['LABEL'] == selected_label].iloc[0]
        
        # Sekvens-logik
        temp_seq = df[df['SEQUENCEID'] == sel_row['SEQUENCEID']].copy()
        temp_seq = temp_seq.sort_values('EVENT_TIMESTAMP').reset_index(drop=True)
        
        # Start ved indkast/hjørne
        restart_idx = temp_seq[temp_seq['EVENT_TYPEID'].isin([5, 6, 107])].index
        start_idx = restart_idx[-1] if not restart_idx.empty else 0
        active_seq = temp_seq.iloc[start_idx:].reset_index(drop=True)

        # Stat-boks data
        try:
            goal_idx = active_seq[active_seq['EVENT_TYPEID'] == 16].index[-1]
            scorer_name = active_seq.loc[goal_idx, 'PLAYER_NAME']
            assist_idx = -1
            for i in range(goal_idx - 1, -1, -1):
                if active_seq.loc[i, 'EVENT_CONTESTANT_OPTAUUID'] == HIF_UUID:
                    assist_idx = i
                    break
            
            st.markdown(f'<div class="stat-box-side"><div class="stat-label-side">Målscorer</div><div class="stat-value-side">{scorer_name.split()[-1]}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box-side" style="border-left-color: {ASSIST_BLUE}"><div class="stat-label-side">Oplæg</div><div class="stat-value-side">{active_seq.loc[assist_idx, "PLAYER_NAME"].split()[-1] if assist_idx != -1 else "Solo"}</div></div>', unsafe_allow_html=True)
        except: pass

    with col_main:
        st.markdown(f'<div class="match-header">{sel_row.get("HOME_TEAM", "HIF")} v {sel_row.get("AWAY_TEAM", "MOD")}</div>', unsafe_allow_html=True)
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 7))

        # Flip-anker: Vi bestemmer retningen ud fra målet
        should_flip_base = True if sel_row['RAW_X'] < 50 else False

        processed = []
        for i, r in active_seq.iterrows():
            is_hif = r['EVENT_CONTESTANT_OPTAUUID'] == HIF_UUID
            
            # --- NY KOORDINAT LOGIK ---
            # Hvis det er modstanderen (som Buur), og hans X er i den modsatte ende af jeres angreb,
            # så skal han spejles ind i jeres zone, fordi de forsvarer samme mål.
            rx, ry = r['RAW_X'], r['RAW_Y']
            
            if not is_hif:
                # Hvis modstanderens X er meget lav (<20) mens jeres mål er i den anden ende (>80),
                # så er det en "defensiv" koordinat fra Opta der skal vendes.
                if (not should_flip_base and rx < 50) or (should_flip_base and rx > 50):
                    rx = 100 - rx
                    ry = 100 - ry

            cx = 100 - rx if should_flip_base else rx
            cy = 100 - ry if should_flip_base else ry
            
            processed.append({'x': cx, 'y': cy, 'hif': is_hif})

            # Tegn prikker
            if is_hif:
                m_c = HIF_RED if i == goal_idx else (ASSIST_BLUE if i == assist_idx else '#aaaaaa')
                p_label = r['PLAYER_NAME'].split()[-1] if pd.notnull(r['PLAYER_NAME']) else ""
                ax.text(cx, cy + 3, p_label, fontsize=9, ha='center', fontweight='bold')
                z = 3
            else:
                m_c = 'black'
                z = 2
            pitch.scatter(cx, cy, s=180 if is_hif else 100, color=m_c, edgecolors='white', ax=ax, zorder=z)

        # Tegn stregerne
        for i in range(1, len(processed)):
            curr, prev = processed[i], processed[i-1]
            if curr['hif']: 
                ax.annotate('', xy=(curr['x'], curr['y']), xytext=(prev['x'], prev['y']),
                            arrowprops=dict(arrowstyle='->', color='#cccccc', lw=1.5, alpha=0.5))

        st.pyplot(fig)
