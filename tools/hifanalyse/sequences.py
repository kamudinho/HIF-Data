import streamlit as st
import pandas as pd
from mplsoccer import Pitch
import matplotlib.pyplot as plt

# Forsøg at hente fra din utils-fil
try:
    from data.utils.mappings import OPTA_EVENT_TYPES, get_event_name
except ImportError:
    # Fallback ordbog hvis filen ikke kan findes
    OPTA_EVENT_TYPES = {"16": "Goal", "1": "Pass", "49": "Ball recovery"}
    def get_event_name(eid): return OPTA_EVENT_TYPES.get(str(eid), f"Aktion {eid}")

# HIF Design-konstanter
HIF_RED = '#cc0000'
ASSIST_BLUE = '#1e90ff'
HIF_GOLD = '#ffd700' 
HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

DK_NAMES = {
    "Pass": "Aflevering", "Ball recovery": "Opsamling", "Goal": "MÅL",
    "Clearance": "Clearing", "Tackle": "Tackling", "Attempt Saved": "Blokeret skud"
}

def vis_side(dp):
    # CSS
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

    # Rens & find mål
    df['RAW_X'] = pd.to_numeric(df['RAW_X'], errors='coerce')
    df['RAW_Y'] = pd.to_numeric(df['RAW_Y'], errors='coerce')
    df['EVENT_TIMESTAMP'] = pd.to_datetime(df['EVENT_TIMESTAMP'])
    goal_events = df[df['EVENT_TYPEID'] == 16].sort_values('EVENT_TIMESTAMP', ascending=False)
    
    if goal_events.empty: return
    goal_events['LABEL'] = goal_events.apply(lambda x: f"{x['EVENT_TIMEMIN']}'. min: {x['PLAYER_NAME']}", axis=1)
    
    col_main, col_side = st.columns([2.5, 1])

    with col_side:
        selected_label = st.selectbox("Vælg scoring", options=goal_events['LABEL'].unique())
        sel_row = goal_events[goal_events['LABEL'] == selected_label].iloc[0]
        
        # Sekvens-logik
        active_seq = df[df['SEQUENCEID'] == sel_row['SEQUENCEID']].copy().sort_values('EVENT_TIMESTAMP')
        
        # Global Index fix
        first_global_idx = active_seq.index[0]
        if first_global_idx > 0:
            pre_action = df.loc[[first_global_idx - 1]]
            if pre_action['MATCH_OPTAUUID'].values[0] == sel_row['MATCH_OPTAUUID']:
                active_seq = pd.concat([pre_action, active_seq]).reset_index(drop=True)
        
        active_seq = active_seq.reset_index(drop=True)
        goal_idx = active_seq[active_seq['EVENT_TYPEID'] == 16].index[-1]
        goal_row = active_seq.loc[goal_idx]

        # Find assist (Prip/HIF-spiller logik)
        assist_idx = -1
        for i in range(goal_idx - 1, -1, -1):
            if active_seq.loc[i, 'EVENT_CONTESTANT_OPTAUUID'] == HIF_UUID:
                if active_seq.loc[i, 'PLAYER_NAME'] != goal_row['PLAYER_NAME']:
                    assist_idx = i
                    break

        # Display navne
        scorer_disp = goal_row['PLAYER_NAME'].split()[-1] if pd.notnull(goal_row['PLAYER_NAME']) else "HIF"
        assist_name = active_seq.loc[assist_idx, 'PLAYER_NAME'].split()[-1] if assist_idx != -1 else "Solo"

        # UI: Stats
        st.markdown(f"""
            <div class="stat-box-side">
                <div class="stat-label-side">Målscorer</div>
                <div class="stat-value-side"><span style="color:{HIF_RED};">●</span> {scorer_disp}</div>
            </div>
            <div class="stat-box-side" style="border-left-color: {ASSIST_BLUE}">
                <div class="stat-label-side">Assist / Sidst på bold</div>
                <div class="stat-value-side"><span style="color:{ASSIST_BLUE};">●</span> {assist_name}</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Tabel
        flow_data = []
        for i in range(len(active_seq)):
            r = active_seq.loc[i]
            p = r['PLAYER_NAME'].split()[-1] if pd.notnull(r['PLAYER_NAME']) else "?"
            eid = str(int(r['EVENT_TYPEID']))
            
            eng_name = get_event_name(eid)
            flow_data.append({
                "Spiller": p,
                "Type": DK_NAMES.get(eng_name, eng_name)
            })
        st.dataframe(pd.DataFrame(flow_data), use_container_width=True, hide_index=True)

    with col_main:
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 7))
        # Banetegning fortsætter her som før...
        st.pyplot(fig)
