import streamlit as st
import pandas as pd
from mplsoccer import Pitch
import matplotlib.pyplot as plt

# Importér fra din mapping-fil
try:
    from data.utils.mappings import OPTA_EVENT_TYPES, get_event_name
except:
    def get_event_name(eid): return f"Aktion {eid}"

# HIF Design-konstanter
HIF_RED = '#cc0000'
ASSIST_BLUE = '#1e90ff'
HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

# Danske navne til oversigten
DK_NAMES = {
    "Pass": "Aflevering", "Ball recovery": "Opsamling", "Goal": "MÅL",
    "Clearance": "Clearing", "Tackle": "Tackling", "Attempt Saved": "Blokeret skud",
    "Foul": "Frispark", "Out": "Bold ud", "Corner": "Hjørnespark", "Throw-in": "Indkast"
}

def vis_side(dp):
    # CSS til de nye stat-bokse med prikker
    st.markdown(f"""
        <style>
            .stat-box-side {{ background-color: #f8f9fa; padding: 12px; border-radius: 8px; border-left: 5px solid {HIF_RED}; margin-bottom: 8px; }}
            .stat-label-side {{ font-size: 0.7rem; text-transform: uppercase; color: #666; font-weight: 800; display: flex; align-items: center; gap: 8px; }}
            .stat-value-side {{ font-size: 1.2rem; font-weight: 900; color: #1a1a1a; margin-top: 4px; }}
            .dot {{ height: 12px; width: 12px; border-radius: 50%; display: inline-block; }}
            .play-flow-container {{ background: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #eee; margin-top: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
            .flow-step {{ font-weight: 700; color: #333; }}
            .flow-action {{ color: #666; font-size: 0.85rem; font-weight: 400; }}
            .flow-arrow {{ color: {HIF_RED}; margin: 0 10px; font-weight: bold; }}
        </style>
    """, unsafe_allow_html=True)

    df_raw = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame())
    if df_raw.empty: return

    # Rens data
    df = df_raw.copy()
    df['RAW_X'] = pd.to_numeric(df['RAW_X'], errors='coerce')
    df['RAW_Y'] = pd.to_numeric(df['RAW_Y'], errors='coerce')
    df['EVENT_TIMESTAMP'] = pd.to_datetime(df['EVENT_TIMESTAMP'])
    df = df.sort_values(['EVENT_TIMESTAMP', 'SEQUENCEID']).reset_index(drop=True)

    goal_events = df[df['EVENT_TYPEID'] == 16].sort_values('EVENT_TIMESTAMP', ascending=False)
    if goal_events.empty: return
    goal_events['LABEL'] = goal_events.apply(lambda x: f"{x['EVENT_TIMEMIN']}'. min: {x['PLAYER_NAME']}", axis=1)
    
    col_main, col_side = st.columns([2.5, 1])

    with col_side:
        selected_label = st.selectbox("Vælg mål", options=goal_events['LABEL'].unique(), label_visibility="collapsed")
        sel_row = goal_events[goal_events['LABEL'] == selected_label].iloc[0]
        
        # Isoler sekvens (HIF kun)
        temp_seq = df[df['SEQUENCEID'] == sel_row['SEQUENCEID']].sort_values('EVENT_TIMESTAMP').reset_index(drop=True)
        restarts = temp_seq[temp_seq['EVENT_TYPEID'].isin([5, 6])]
        start_idx = restarts.index[-1] if not restarts.empty else 0
        active_seq = temp_seq.iloc[start_idx:].reset_index(drop=True)
        hif_seq = active_seq[active_seq['EVENT_CONTESTANT_OPTAUUID'] == HIF_UUID].copy().reset_index(drop=True)

        # Find assist (næstsidste spiller)
        scorer_name = hif_seq.iloc[-1]['PLAYER_NAME'].split()[-1] if not hif_seq.empty else "HIF"
        assist_name = hif_seq.iloc[-2]['PLAYER_NAME'].split()[-1] if len(hif_seq) > 1 else "Solo"

        # STAT-BOKSE MED FARVE-PRIKKER
        st.markdown(f"""
            <div class="stat-box-side">
                <div class="stat-label-side"><span class="dot" style="background-color:{HIF_RED}"></span>Målscorer</div>
                <div class="stat-value-side">{scorer_name}</div>
            </div>
            <div class="stat-box-side" style="border-left-color: {ASSIST_BLUE}">
                <div class="stat-label-side"><span class="dot" style="background-color:{ASSIST_BLUE}"></span>Assist</div>
                <div class="stat-value-side">{assist_name}</div>
            </div>
        """, unsafe_allow_html=True)

    with col_main:
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 7))
        should_flip = True if sel_row['RAW_X'] < 50 else False

        # Tegn banen (med din clustering-logik indbygget)
        prev_pt = None
        for i, r in hif_seq.iterrows():
            cx = (100 - r['RAW_X'] if should_flip else r['RAW_X'])
            cy = (100 - r['RAW_Y'] if should_flip else r['RAW_Y'])
            
            if prev_pt:
                ax.annotate('', xy=(cx, cy), xytext=(prev_pt[0], prev_pt[1]),
                            arrowprops=dict(arrowstyle='->', color='#cccccc', lw=1.5, alpha=0.4, shrinkA=5, shrinkB=5))
            
            is_goal = r['EVENT_TYPEID'] == 16
            p_name = r['PLAYER_NAME'].split()[-1]
            color = HIF_RED if is_goal else (ASSIST_BLUE if p_name == assist_name else '#aaaaaa')
            
            pitch.scatter(cx, cy, s=180, color=color, edgecolors='white', ax=ax, zorder=5)
            ax.text(cx, cy + 3, p_name, fontsize=8, ha='center', fontweight='bold')
            prev_pt = (cx, cy)

        st.pyplot(fig)

        # --- SEKVENS-OVERSIGT (TEKST) ---
        st.write("### Angrebssekvens")
        steps = []
        for i, r in hif_seq.iterrows():
            p = r['PLAYER_NAME'].split()[-1]
            ename = get_event_name(str(int(r['EVENT_TYPEID'])))
            action = DK_NAMES.get(ename, ename)
            if r['EVENT_TYPEID'] == 16: action = "MÅL"
            
            steps.append(f'<span class="flow-step">{p}</span> <span class="flow-action">({action})</span>')
        
        flow_html = f'<div class="play-flow-container">{" <span class="flow-arrow">→</span> "join(steps)}</div>
        st.markdown(flow_html, unsafe_allow_html=True)
