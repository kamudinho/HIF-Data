import streamlit as st
import pandas as pd
from mplsoccer import Pitch
import matplotlib.pyplot as plt

# Importér fra din mapping-fil
try:
    from data.utils.mappings import OPTA_EVENT_TYPES, get_event_name
except:
    def get_event_name(eid): return f"Aktion {eid}"

HIF_RED = '#cc0000'
ASSIST_BLUE = '#1e90ff'
# Din COMP_MAP værdier fra instruktioner (Hvidovre app)
HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy' 

DK_NAMES = {
    "Pass": "Aflevering", "Ball recovery": "Opsamling", "Goal": "MÅL",
    "Clearance": "Clearing", "Tackle": "Tackling", "Attempt Saved": "Blokeret skud",
    "Foul": "Frispark", "Out": "Bold ud", "Corner": "Hjørnespark", "Throw-in": "Indkast"
}

def vis_side(dp):
    # CSS og indledende datatjek (som i de forrige versioner)
    df_raw = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame())
    if df_raw.empty: return

    df = df_raw.copy()
    df['EVENT_TIMESTAMP'] = pd.to_datetime(df['EVENT_TIMESTAMP'])
    df['RAW_X'] = pd.to_numeric(df['RAW_X'], errors='coerce')
    df['RAW_Y'] = pd.to_numeric(df['RAW_Y'], errors='coerce')
    df = df.sort_values(['EVENT_TIMESTAMP', 'SEQUENCEID']).reset_index(drop=True)

    goals = df[df['EVENT_TYPEID'] == 16].copy()
    if goals.empty: return
    goals['LABEL'] = goals.apply(lambda x: f"{x['EVENT_TIMEMIN']}'. min: {x['PLAYER_NAME']}", axis=1)
    
    col_main, col_side = st.columns([2.5, 1.2])

    with col_side:
        selected_label = st.selectbox("Vælg mål", options=goals['LABEL'].unique(), label_visibility="collapsed")
        target_goal = goals[goals['LABEL'] == selected_label].iloc[0]
        hif_team_id = target_goal['EVENT_CONTESTANT_OPTAUUID']
        
        # 1. ISOLER SEKVENSHÆNDELSER
        active_seq = df[
            (df['SEQUENCEID'] == target_goal['SEQUENCEID']) & 
            (df['EVENT_CONTESTANT_OPTAUUID'] == hif_team_id) &
            (df['EVENT_TIMESTAMP'] <= target_goal['EVENT_TIMESTAMP'])
        ].copy().reset_index(drop=True)

        # 2. LOGISK VASK (Fjern "støj-punkter" langt fra målet)
        # Vi beholder kun hændelser der er relevante for flowet mod mål
        clean_seq_indices = []
        for i in range(len(active_seq)):
            curr = active_seq.iloc[i]
            # Målet skal altid med
            if curr['EVENT_TYPEID'] == 16:
                clean_seq_indices.append(i)
                continue
            
            # Tjek afstand til målet (hvis punktet er i egen forsvarszone mens målet scores, er det ofte støj)
            dist_to_goal = ((curr['RAW_X'] - target_goal['RAW_X'])**2 + (curr['RAW_Y'] - target_goal['RAW_Y'])**2)**0.5
            if dist_to_goal < 60: # Justér denne værdi hvis du mister for meget af opspillet
                clean_seq_indices.append(i)
        
        active_seq = active_seq.iloc[clean_seq_indices].copy().reset_index(drop=True)

        # Find assist og målscorer (som før)
        scorer_name = target_goal['PLAYER_NAME'].split()[-1]
        assist_name, assist_idx = "Solo", -1
        for i in range(len(active_seq) - 2, -1, -1):
            if active_seq.loc[i, 'PLAYER_NAME'] != target_goal['PLAYER_NAME']:
                assist_name = active_seq.loc[i, 'PLAYER_NAME'].split()[-1]
                assist_idx = i
                break

        # UI: Stats & Tabel (Vises nu med de rensede data)
        st.markdown(f'<div class="stat-box-side"><small>Målscorer</small><br><b>{scorer_name}</b></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-box-side" style="border-left-color:{ASSIST_BLUE}"><small>Assist</small><br><b>{assist_name}</b></div>', unsafe_allow_html=True)
        
        flow_table = []
        for _, r in active_seq.iterrows():
            ename = get_event_name(str(int(r['EVENT_TYPEID'])))
            flow_table.append({"Spiller": r['PLAYER_NAME'].split()[-1], "Aktion": DK_NAMES.get(ename, ename) if r['EVENT_TYPEID'] != 16 else "MÅL ⚽"})
        st.dataframe(pd.DataFrame(flow_table), use_container_width=True, hide_index=True)

    with col_main:
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 7))
        should_flip = True if target_goal['RAW_X'] < 50 else False

        # Tegn kun de rensede punkter
        prev_pt = None
        for i, r in active_seq.iterrows():
            cx = (100 - r['RAW_X'] if should_flip else r['RAW_X'])
            cy = (100 - r['RAW_Y'] if should_flip else r['RAW_Y'])
            
            # Tegn pil fra forrige punkt
            if prev_pt:
                ax.annotate('', xy=(cx, cy), xytext=(prev_pt[0], prev_pt[1]),
                            arrowprops=dict(arrowstyle='->', color='#cccccc', lw=1.5, alpha=0.5))
            
            color = HIF_RED if r['EVENT_TYPEID'] == 16 else (ASSIST_BLUE if i == assist_idx else '#999999')
            pitch.scatter(cx, cy, s=150, color=color, edgecolors='white', ax=ax, zorder=5)
            ax.text(cx, cy + 3, r['PLAYER_NAME'].split()[-1], fontsize=9, ha='center', fontweight='bold')
            prev_pt = (cx, cy)

        st.pyplot(fig)
