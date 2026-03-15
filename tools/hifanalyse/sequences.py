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
            .stat-label-side {{ font-size: 0.7rem; text-transform: uppercase; color: #666; font-weight: 800; display: flex; align-items: center; }}
            .stat-value-side {{ font-size: 1.2rem; font-weight: 900; color: #1a1a1a; padding-top: 4px; }}
            .dot {{ height: 10px; width: 10px; border-radius: 50%; display: inline-block; margin-right: 6px; }}
            .play-flow {{ background: #ffffff; padding: 15px; border-radius: 8px; border: 1px solid #eee; margin-top: 10px; font-family: monospace; line-height: 1.6; }}
        </style>
    """, unsafe_allow_html=True)

    df = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame())
    if df.empty: return

    # Rens data
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
        
        # Start ved seneste restart
        restarts = temp_seq[temp_seq['EVENT_TYPEID'].isin([5, 6])]
        start_idx = restarts.index[-1] if not restarts.empty else 0
        active_seq = temp_seq.iloc[start_idx:].reset_index(drop=True)

        # --- PROCESSER DISPLAY ELEMENTS ---
        raw_elements = []
        for i, r in active_seq.iterrows():
            is_hif = r['EVENT_CONTESTANT_OPTAUUID'] == HIF_UUID
            if is_hif or r['EVENT_TYPEID'] in [12, 13, 14, 15, 43, 44]:
                raw_elements.append(r.to_dict())

        display_elements = []
        skip_next = False
        for i in range(len(raw_elements)):
            if skip_next: { skip_next := False }; continue
            curr = raw_elements[i]
            if i < len(raw_elements) - 1:
                nxt = raw_elements[i+1]
                dist = ((curr['RAW_X'] - nxt['RAW_X'])**2 + (curr['RAW_Y'] - nxt['RAW_Y'])**2)**0.5
                if dist < 4.0:
                    active_r = nxt if nxt['EVENT_CONTESTANT_OPTAUUID'] == HIF_UUID else curr
                    skip_next = True
                else: active_r = curr
            else: active_r = curr
            
            rx, ry = active_r['RAW_X'], active_r['RAW_Y']
            is_hif = active_r['EVENT_CONTESTANT_OPTAUUID'] == HIF_UUID
            should_flip = True if sel_row['RAW_X'] < 50 else False
            cx, cy = (100 - rx if should_flip else rx), (100 - ry if should_flip else ry)
            
            display_elements.append({
                'x': cx, 'y': cy, 'is_hif': is_hif, 
                'name': active_r['PLAYER_NAME'], 'type': active_r['EVENT_TYPEID']
            })

        # Find målscorer og assist fra den rensede liste
        hif_only = [el for el in display_elements if el['is_hif']]
        scorer_name = hif_only[-1]['name'].split()[-1] if hif_only else "HIF"
        assist_name = hif_only[-2]['name'].split()[-1] if len(hif_only) > 1 else "Solo"

        # STAT-BOKSE
        st.markdown(f"""
            <div class="stat-box-side">
                <div class="stat-label-side"><span class="dot" style="background-color:{HIF_RED}"></span>MÅLSCORER</div>
                <div class="stat-value-side">{scorer_name}</div>
            </div>
            <div class="stat-box-side" style="border-left-color: {ASSIST_BLUE}">
                <div class="stat-label-side"><span class="dot" style="background-color:{ASSIST_BLUE}"></span>ASSIST</div>
                <div class="stat-value-side">{assist_name}</div>
            </div>
        """, unsafe_allow_html=True)

    with col_main:
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 7))

        # Tegn linjer og spillere (samme logik som sidst)
        for i in range(1, len(display_elements)):
            curr, prev = display_elements[i], display_elements[i-1]
            ax.annotate('', xy=(curr['x'], curr['y']), xytext=(prev['x'], prev['y']),
                        arrowprops=dict(arrowstyle='->', color='#cccccc', lw=1.5, alpha=0.4, shrinkA=5, shrinkB=5))

        for el in display_elements:
            if el['is_hif']:
                color = HIF_RED if el['type'] == 16 else (ASSIST_BLUE if el['name'].split()[-1] == assist_name else '#aaaaaa')
                pitch.scatter(el['x'], el['y'], s=180, color=color, edgecolors='white', ax=ax, zorder=5)
                ax.text(el['x'], el['y'] + 3, el['name'].split()[-1] if el['name'] else "", fontsize=8, ha='center', fontweight='bold')
            else:
                pitch.scatter(el['x'], el['y'], s=80, color='black', edgecolors='white', ax=ax, zorder=3)

        st.pyplot(fig)

        # --- SEKVENS-OVERSIGT (PLAY-BY-PLAY) ---
        st.write("### Angrebssekvens")
        flow_text = ""
        for i, el in enumerate(hif_only):
            name = el['name'].split()[-1] if el['name'] else "HIF"
            if i == len(hif_only) - 1:
                flow_text += f"**{name} (MÅL)**"
            else:
                flow_text += f"{name} → "
        
        st.markdown(f'<div class="play-flow">{flow_text}</div>', unsafe_allow_html=True)
