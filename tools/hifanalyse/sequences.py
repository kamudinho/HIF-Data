import streamlit as st
import pandas as pd
from mplsoccer import Pitch
import matplotlib.pyplot as plt

# Importér fra din mapping-fil
from data.utils.mappings import OPTA_EVENT_TYPES, get_event_name

# HIF Design-konstanter
HIF_RED = '#cc0000'
ASSIST_BLUE = '#1e90ff'
HIF_GOLD = '#ffd700' 
HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

# Danske navne (hvis de ikke allerede er i mappings.py)
DK_NAMES = {
    "Pass": "Aflevering", "Take On": "Dribling", "Tackle": "Tackling",
    "Ball recovery": "Opsamling", "Goal": "MÅL", "Attempt Saved": "Blokeret skud",
    "Save": "Redning", "Interception": "Opspringning", "Clearance": "Clearing"
}

def vis_side(dp):
    # 1. CSS til Stats-bokse
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
        st.warning("Ingen Opta-data fundet.")
        return

    # Datarens
    df['RAW_X'] = pd.to_numeric(df['RAW_X'], errors='coerce')
    df['RAW_Y'] = pd.to_numeric(df['RAW_Y'], errors='coerce')
    df = df[~((df['RAW_X'] == 0) & (df['RAW_Y'] == 0))].copy()
    df['EVENT_TIMESTAMP'] = pd.to_datetime(df['EVENT_TIMESTAMP'])

    # Find mål
    goal_events = df[df['EVENT_TYPEID'] == 16].sort_values('EVENT_TIMESTAMP', ascending=False)
    if goal_events.empty:
        st.info("Ingen mål fundet i denne kørsel.")
        return
        
    goal_events['LABEL'] = goal_events.apply(lambda x: f"{x['EVENT_TIMEMIN']}'. min: {x['PLAYER_NAME']}", axis=1)
    
    col_main, col_side = st.columns([2.5, 1])

    with col_side:
        st.caption("Vælg scoring")
        selected_label = st.selectbox("", options=goal_events['LABEL'].unique(), label_visibility="collapsed")
        sel_row = goal_events[goal_events['LABEL'] == selected_label].iloc[0]
        
        # Hent sekvensen
        active_seq = df[df['SEQUENCEID'] == sel_row['SEQUENCEID']].copy().sort_values('EVENT_TIMESTAMP')
        
        # Tjek for aktion før (Query 9 logik)
        first_global_idx = active_seq.index[0]
        if first_global_idx > 0:
            pre_action = df.loc[[first_global_idx - 1]]
            if pre_action['MATCH_OPTAUUID'].values[0] == sel_row['MATCH_OPTAUUID']:
                active_seq = pd.concat([pre_action, active_seq]).reset_index(drop=True)
        
        active_seq = active_seq.reset_index(drop=True)
        goal_idx = active_seq[active_seq['EVENT_TYPEID'] == 16].index[-1]
        goal_row = active_seq.loc[goal_idx]
        goal_scorer_name = goal_row['PLAYER_NAME']

        # LOGIK: Find assist (Prip-fix: vi leder efter sidste HIF-spiller før målscoreren)
        assist_idx = -1
        for i in range(goal_idx - 1, -1, -1):
            if active_seq.loc[i, 'EVENT_CONTESTANT_OPTAUUID'] == HIF_UUID:
                if active_seq.loc[i, 'PLAYER_NAME'] != goal_scorer_name:
                    assist_idx = i
                    break

        # Navne til visning
        scorer_disp = goal_row['PLAYER_NAME'].split()[-1] if pd.notnull(goal_row['PLAYER_NAME']) else "HIF"
        assist_name = active_seq.loc[assist_idx, 'PLAYER_NAME'].split()[-1] if assist_idx != -1 else "Solo"

        # STAT-BOKSE
        st.markdown(f"""
            <div class="stat-box-side">
                <div class="stat-label-side">Målscorer</div>
                <div class="stat-value-side"><span style="color:{HIF_RED}; margin-right:8px;">●</span>{scorer_disp}</div>
            </div>
            <div class="stat-box-side" style="border-left-color: {ASSIST_BLUE}">
                <div class="stat-label-side">Assist / Sidst på bold</div>
                <div class="stat-value-side"><span style="color:{ASSIST_BLUE}; margin-right:8px;">●</span>{assist_name}</div>
            </div>
            <div class="stat-box-side" style="border-left-color: {HIF_GOLD}">
                <div class="stat-label-side">Resultat / Tid</div>
                <div class="stat-value-side">{int(goal_row["HOME_SCORE"])}-{int(goal_row["AWAY_SCORE"])} | {goal_row['EVENT_TIMEMIN']}'</div>
            </div>
        """, unsafe_allow_html=True)
        
        # FLOW TABEL
        st.caption("**Spilsekvens:**")
        flow_data = []
        for i in range(len(active_seq)):
            row = active_seq.loc[i]
            p = row['PLAYER_NAME'].split()[-1] if pd.notnull(row['PLAYER_NAME']) else "?"
            raw_id = str(int(row['EVENT_TYPEID']))
            quals = str(row['QUALIFIER_LIST']) if pd.notnull(row['QUALIFIER_LIST']) else ""
            
            # Navngivning
            if "107" in quals or raw_id == "5": display_name = "Indkast"
            elif raw_id == "6": display_name = "Hjørnespark"
            elif raw_id == "16": display_name = "Mål ⚽"
            else:
                eng_name = get_event_name(raw_id)
                display_name = DK_NAMES.get(eng_name, eng_name)
            
            if i < len(active_seq) - 1:
                next_p = active_seq.loc[i+1, 'PLAYER_NAME'].split()[-1] if pd.notnull(active_seq.loc[i+1, 'PLAYER_NAME']) else "?"
                flow_data.append({"Flow": f"{p} → {next_p}", "Type": display_name})
            else:
                flow_data.append({"Flow": f"{p}", "Type": display_name})
        
        st.dataframe(pd.DataFrame(flow_data), use_container_width=True, height=280, hide_index=True)

    with col_main:
        st.markdown(f'<div class="match-header">{sel_row.get("HOME_TEAM", "HIF")} v {sel_row.get("AWAY_TEAM", "MOD")}</div>', unsafe_allow_html=True)
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 7))
        
        # Bestem spilleretning (Vi vil altid angribe mod højre i visningen)
        should_flip = True if sel_row['RAW_X'] < 50 else False

        display_elements = []
        for i, r in active_seq.iterrows():
            is_hif = r['EVENT_CONTESTANT_OPTAUUID'] == HIF_UUID
            is_relevant = is_hif or r['EVENT_TYPEID'] in [12, 13, 14, 15, 43, 44]
            
            if is_relevant:
                # Sidelinje-oprydning: hvis stationen er for tæt på den forrige, spring over (undtagen mål)
                if display_elements and r['EVENT_TYPEID'] != 16:
                    last = display_elements[-1]
                    dist = ((r['RAW_X'] - last['orig_x'])**2 + (r['RAW_Y'] - last['orig_y'])**2)**0.5
                    if dist < 4.0: continue

                rx, ry = r['RAW_X'], r['RAW_Y']
                # Flip koordinater hvis nødvendigt
                if not is_hif and ((not should_flip and rx < 50) or (should_flip and rx > 50)):
                    rx, ry = 100 - rx, 100 - ry
                
                cx, cy = (100 - rx if should_flip else rx), (100 - ry if should_flip else ry)
                
                display_elements.append({
                    'x': cx, 'y': cy, 'orig_x': r['RAW_X'], 'orig_y': r['RAW_Y'],
                    'is_hif': is_hif, 'name': r['PLAYER_NAME'], 
                    'is_goal': (i == goal_idx),
                    'is_assist': (i == assist_idx)
                })

        # Tegn pile mellem aktioner
        for i in range(1, len(display_elements)):
            curr, prev = display_elements[i], display_elements[i-1]
            ax.annotate('', xy=(curr['x'], curr['y']), xytext=(prev['x'], prev['y']),
                        arrowprops=dict(arrowstyle='->', color='#cccccc', lw=1.5, alpha=0.4))

        # Tegn spillere/begivenheder
        for el in display_elements:
            if el['is_hif']:
                color = HIF_RED if el['is_goal'] else (ASSIST_BLUE if el['is_assist'] else '#aaaaaa')
                name_text = el['name'].split()[-1] if pd.notnull(el['name']) else ""
                ax.text(el['x'], el['y'] + 3, name_text, fontsize=8, ha='center', fontweight='bold')
                s, z = 180, 4
            else:
                color, s, z = 'black', 80, 3 # Modstander-aktioner (clearinger/tacklinger)
                
            pitch.scatter(el['x'], el['y'], s=s, color=color, edgecolors='white', ax=ax, zorder=z)

        st.pyplot(fig)
