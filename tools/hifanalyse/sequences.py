import streamlit as st
import pandas as pd
from mplsoccer import Pitch
import matplotlib.pyplot as plt

# Importér fra din mapping-fil (med fallback hvis import fejler)
try:
    from data.utils.mappings import OPTA_EVENT_TYPES, get_event_name
except:
    def get_event_name(eid): return f"Aktion {eid}"

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
    st.markdown(f"""
        <style>
            .stat-box-side {{ background-color: #f8f9fa; padding: 12px; border-radius: 8px; border-left: 5px solid {HIF_RED}; margin-bottom: 8px; }}
            .stat-label-side {{ font-size: 0.7rem; text-transform: uppercase; color: #666; font-weight: 800; }}
            .stat-value-side {{ font-size: 1.2rem; font-weight: 900; color: #1a1a1a; }}
            .match-header {{ font-size: 1.3rem; font-weight: 800; color: {HIF_RED}; text-align: center; margin-bottom: 20px; text-transform: uppercase; }}
        </style>
    """, unsafe_allow_html=True)

    df = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame())
    if df.empty:
        st.warning("Ingen data fundet")
        return

    # 1. Datarens
    df['RAW_X'] = pd.to_numeric(df['RAW_X'], errors='coerce')
    df['RAW_Y'] = pd.to_numeric(df['RAW_Y'], errors='coerce')
    df = df.dropna(subset=['RAW_X', 'RAW_Y'])
    df['EVENT_TIMESTAMP'] = pd.to_datetime(df['EVENT_TIMESTAMP'])

    # 2. Find mål og vælg scoring
    goal_events = df[df['EVENT_TYPEID'] == 16].sort_values('EVENT_TIMESTAMP', ascending=False)
    if goal_events.empty:
        st.info("Ingen scoringer fundet")
        return
        
    goal_events['LABEL'] = goal_events.apply(lambda x: f"{x['EVENT_TIMEMIN']}'. min: {x['PLAYER_NAME']}", axis=1)
    
    col_main, col_side = st.columns([2.5, 1])

    with col_side:
        selected_label = st.selectbox("Vælg scoring", options=goal_events['LABEL'].unique(), label_visibility="collapsed")
        sel_row = goal_events[goal_events['LABEL'] == selected_label].iloc[0]
        
        # Hent sekvens
        active_seq = df[df['SEQUENCEID'] == sel_row['SEQUENCEID']].copy().sort_values('EVENT_TIMESTAMP')
        
        # Inkludér aktionen før (vigtigt for assists fra opsamlinger)
        first_idx = active_seq.index[0]
        if first_idx > 0:
            pre = df.loc[[first_idx - 1]]
            if pre['MATCH_OPTAUUID'].values[0] == sel_row['MATCH_OPTAUUID']:
                active_seq = pd.concat([pre, active_seq]).reset_index(drop=True)
        
        active_seq = active_seq.reset_index(drop=True)
        goal_idx = active_seq[active_seq['EVENT_TYPEID'] == 16].index[-1]
        goal_row = active_seq.loc[goal_idx]

        # Find assist (sidste HIF-spiller før scorer)
        assist_idx = -1
        for i in range(goal_idx - 1, -1, -1):
            if active_seq.loc[i, 'EVENT_CONTESTANT_OPTAUUID'] == HIF_UUID:
                if active_seq.loc[i, 'PLAYER_NAME'] != goal_row['PLAYER_NAME']:
                    assist_idx = i
                    break

        # UI: Stats
        scorer_name = goal_row['PLAYER_NAME'].split()[-1] if pd.notnull(goal_row['PLAYER_NAME']) else "HIF"
        assist_name = active_seq.loc[assist_idx, 'PLAYER_NAME'].split()[-1] if assist_idx != -1 else "Solo/Retur"

        st.markdown(f"""
            <div class="stat-box-side">
                <div class="stat-label-side">Målscorer</div>
                <div class="stat-value-side"><span style="color:{HIF_RED};">●</span> {scorer_name}</div>
            </div>
            <div class="stat-box-side" style="border-left-color: {ASSIST_BLUE}">
                <div class="stat-label-side">Assist / Næstsidst</div>
                <div class="stat-value-side"><span style="color:{ASSIST_BLUE};">●</span> {assist_name}</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Tabel
        flow_list = []
        for i, r in active_seq.iterrows():
            if r['EVENT_CONTESTANT_OPTAUUID'] == HIF_UUID:
                p = r['PLAYER_NAME'].split()[-1] if pd.notnull(r['PLAYER_NAME']) else "?"
                ename = get_event_name(str(int(r['EVENT_TYPEID'])))
                flow_list.append({"Spiller": p, "Aktion": DK_NAMES.get(ename, ename)})
        
        st.dataframe(pd.DataFrame(flow_list), use_container_width=True, hide_index=True, height=250)

    with col_main:
        st.markdown(f'<div class="match-header">{sel_row.get("HOME_TEAM", "HIF")} v {sel_row.get("AWAY_TEAM", "MOD")}</div>', unsafe_allow_html=True)
        
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc', goal_type='box')
        fig, ax = pitch.draw(figsize=(10, 7))
        
        # Bestem retning: Skal vi flippe banen så HIF altid angriber mod højre?
        # Vi tjekker målets position. Hvis målscorer skyder mod venstre (x < 50), flipper vi alt.
        should_flip = True if goal_row['RAW_X'] < 50 else False

        plot_data = []
        for i, r in active_seq.iterrows():
            # KUN HIF aktioner på banen
            if r['EVENT_CONTESTANT_OPTAUUID'] == HIF_UUID:
                rx, ry = r['RAW_X'], r['RAW_Y']
                
                # Koordinat transform
                cx = (100 - rx if should_flip else rx)
                cy = (100 - ry if should_flip else ry)
                
                plot_data.append({
                    'x': cx, 'y': cy, 
                    'name': r['PLAYER_NAME'].split()[-1] if pd.notnull(r['PLAYER_NAME']) else "",
                    'is_goal': (i == goal_idx),
                    'is_assist': (i == assist_idx)
                })

        # 1. Tegn linjer/pile (Sekvens)
        for i in range(1, len(plot_data)):
            p1, p2 = plot_data[i-1], plot_data[i]
            ax.annotate('', xy=(p2['x'], p2['y']), xytext=(p1['x'], p1['y']),
                        arrowprops=dict(arrowstyle='->', color='#dddddd', lw=2, alpha=0.6))

        # 2. Tegn punkter og navne
        for pt in plot_data:
            color = HIF_RED if pt['is_goal'] else (ASSIST_BLUE if pt['is_assist'] else '#aaaaaa')
            z = 5 if pt['is_goal'] or pt['is_assist'] else 3
            size = 200 if pt['is_goal'] else 120
            
            pitch.scatter(pt['x'], pt['y'], s=size, color=color, edgecolors='white', linewidth=1.5, ax=ax, zorder=z)
            ax.text(pt['x'], pt['y'] + 3, pt['name'], fontsize=9, ha='center', fontweight='bold', color='#333')

        st.pyplot(fig)
