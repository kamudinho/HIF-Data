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
    # CSS og Data-hentning (som tidligere)
    df_raw = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame())
    if df_raw.empty: return

    df = df_raw.copy()
    df['EVENT_TIMESTAMP'] = pd.to_datetime(df['EVENT_TIMESTAMP'])
    df['RAW_X'] = pd.to_numeric(df['RAW_X'], errors='coerce')
    df['RAW_Y'] = pd.to_numeric(df['RAW_Y'], errors='coerce')
    df = df.sort_values(['EVENT_TIMESTAMP', 'EVENT_EVENTID']).reset_index(drop=True)

    goals = df[df['EVENT_TYPEID'] == 16].copy()
    if goals.empty: return
    goals['LABEL'] = goals.apply(lambda x: f"{x['EVENT_TIMEMIN']}'. min: {x['PLAYER_NAME']}", axis=1)
    
    col_main, col_side = st.columns([2.5, 1.2])

    with col_side:
        selected_label = st.selectbox("Vælg mål", options=goals['LABEL'].unique(), label_visibility="collapsed")
        target_goal = goals[goals['LABEL'] == selected_label].iloc[0]
        hif_team_id = target_goal['EVENT_CONTESTANT_OPTAUUID']
        
        # 1. Isoler HIF hændelser for dette mål
        active_seq = df[
            (df['SEQUENCEID'] == target_goal['SEQUENCEID']) & 
            (df['EVENT_CONTESTANT_OPTAUUID'] == hif_team_id) &
            (df['EVENT_TIMESTAMP'] <= target_goal['EVENT_TIMESTAMP'])
        ].copy().reset_index(drop=True)

        # 2. LOGIK: Find assist og fix Specialhændelser (Hjørne/Frispark)
        # Vi leder efter hjørnespark (6) eller frispark (5)
        is_set_piece = any(active_seq['EVENT_TYPEID'].isin([6, 5]))
        
        scorer_name = target_goal['PLAYER_NAME'].split()[-1]
        assist_name, assist_idx = "Solo", -1
        
        for i in range(len(active_seq) - 2, -1, -1):
            row = active_seq.iloc[i]
            if row['PLAYER_NAME'] != target_goal['PLAYER_NAME']:
                assist_name = row['PLAYER_NAME'].split()[-1]
                assist_idx = i
                break

        # UI: Stats
        st.markdown(f'<div class="stat-box-side"><small>Målscorer</small><br><b>{scorer_name}</b></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-box-side" style="border-left-color:{ASSIST_BLUE}"><small>Assist</small><br><b>{assist_name}</b></div>', unsafe_allow_html=True)
        
        # Tabel-visning
        flow_table = []
        for _, r in active_seq.iterrows():
            eid = str(int(r['EVENT_TYPEID']))
            ename = get_event_name(eid)
            dan_name = "Hjørnespark" if eid == "6" else (DK_NAMES.get(ename, ename) if eid != "16" else "MÅL ⚽")
            flow_table.append({"Spiller": r['PLAYER_NAME'].split()[-1], "Aktion": dan_name})
        st.dataframe(pd.DataFrame(flow_table), use_container_width=True, hide_index=True)

    with col_main:
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 7))
        should_flip = True if target_goal['RAW_X'] < 50 else False

        plot_points = []
        for i, r in active_seq.iterrows():
            rx, ry = r['RAW_X'], r['RAW_Y']
            
            # CORNER FIX: Hvis det er et hjørnespark (6), tvinger vi koordinaterne til flaget
            if r['EVENT_TYPEID'] == 6:
                rx = 100.0 if rx > 50 else 0.0
                ry = 100.0 if ry > 50 else 0.0
            
            cx = (100 - rx if should_flip else rx)
            cy = (100 - ry if should_flip else ry)
            
            plot_points.append({'x': cx, 'y': cy, 'name': r['PLAYER_NAME'].split()[-1], 'type': r['EVENT_TYPEID'], 'idx': i})

        # Tegn pile (undgå pile fra Corner-Prip til Støj-Prip)
        for i in range(1, len(plot_points)):
            p1, p2 = plot_points[i-1], plot_points[i]
            # Hvis samme spiller optræder to gange i træk lige efter et hjørne, så spring pilen over
            if p1['name'] == p2['name'] and p1['type'] == 6: continue
            
            ax.annotate('', xy=(p2['x'], p2['y']), xytext=(p1['x'], p1['y']),
                        arrowprops=dict(arrowstyle='->', color='#cccccc', lw=1.5, alpha=0.5))

        # Tegn punkter
        for pt in plot_points:
            is_goal = (pt['type'] == 16)
            is_assist = (pt['idx'] == assist_idx)
            color = HIF_RED if is_goal else (ASSIST_BLUE if is_assist else '#999999')
            
            pitch.scatter(pt['x'], pt['y'], s=150, color=color, edgecolors='white', ax=ax, zorder=5)
            ax.text(pt['x'], pt['y'] + 3, pt['name'], fontsize=9, ha='center', fontweight='bold')

        st.pyplot(fig)
