import streamlit as st
import pandas as pd
from mplsoccer import Pitch
import matplotlib.pyplot as plt

# HIF Design-konstanter
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'
ASSIST_BLUE = '#1e90ff'

# --- DINE MAPPINGS ---
OPTA_EVENT_TYPES = {
    "1": "Pass", "2": "Offside Pass", "3": "Take On", "4": "Free kick", "5": "Out",
    "6": "Corner", "7": "Tackle", "8": "Interception", "9": "Turnover", "10": "Save",
    "12": "Clearance", "13": "Miss", "14": "Post", "15": "Attempt Saved",
    "16": "Goal", "44": "Aerial", "49": "Ball recovery", "50": "Dispossessed", 
    "51": "Error", "61": "Ball touch"
}

DK_NAMES = {
    "Pass": "Aflevering", "Goal": "Mål", "Interception": "Erobring", 
    "Ball recovery": "Opsamling", "Corner": "Hjørnespark", "Free kick": "Frispark",
    "Throw In": "Indkast", "Tackle": "Tackle", "Clearance": "Clearance"
}

def vis_side(dp):
    # 1. CSS til styling af sidebar-bokse
    st.markdown(f"""
        <style>
            .stat-box-side {{ background-color: #f8f9fa; padding: 12px; border-radius: 8px; border-left: 5px solid {HIF_RED}; margin-bottom: 8px; }}
            .stat-label-side {{ font-size: 0.7rem; text-transform: uppercase; color: #666; font-weight: 800; }}
            .stat-value-side {{ font-size: 1.2rem; font-weight: 900; color: #1a1a1a; display: flex; align-items: center; }}
            .match-header {{ font-size: 1.3rem; font-weight: 800; color: {HIF_RED}; text-align: center; margin-bottom: 20px; text-transform: uppercase; }}
        </style>
    """, unsafe_allow_html=True)

    # 2. Hent data
    df = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame())
    if df.empty:
        st.info("Ingen sekvensdata fundet.")
        return

    # Præparér data
    for col in ['RAW_X', 'RAW_Y', 'PREV_X_1', 'PREV_Y_1']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    if 'EVENT_TIMESTAMP' in df.columns:
        df['EVENT_TIMESTAMP'] = pd.to_datetime(df['EVENT_TIMESTAMP'])

    # 3. Find mål
    goal_events = df[df['EVENT_TYPEID'] == 16].copy()
    if goal_events.empty:
        st.warning("Ingen mål fundet.")
        return

    goal_events = goal_events.sort_values('EVENT_TIMESTAMP', ascending=False)
    
    # Skab unik label til dropdown
    goal_events['LABEL'] = (
        goal_events['EVENT_TIMEMIN'].astype(str) + "'. min: " +
        goal_events['PLAYER_NAME'].fillna("Ukendt") + " (" + 
        goal_events['HOME_TEAM'].fillna("Hjemme") + " v " + goal_events['AWAY_TEAM'].fillna("Ude") + ")" +
        " #" + goal_events['SEQUENCEID'].astype(str)
    )
    
    col_main, col_side = st.columns([2.5, 1])

    with col_side:
        st.caption("Vælg scoring")
        selected_label = st.selectbox("", options=goal_events['LABEL'].unique(), label_visibility="collapsed")
        sel_row = goal_events[goal_events['LABEL'] == selected_label].iloc[0]
        
        # Hent sekvensen
        active_seq = df[df['SEQUENCEID'] == sel_row['SEQUENCEID']].copy().sort_values('EVENT_TIMESTAMP')
        
        # Tjek for aktion før (fra SQL-Query 9)
        first_global_idx = active_seq.index[0]
        if first_global_idx > 0:
            pre_action = df.loc[[first_global_idx - 1]]
            if pre_action['MATCH_OPTAUUID'].values[0] == sel_row['MATCH_OPTAUUID']:
                active_seq = pd.concat([pre_action, active_seq]).reset_index(drop=True)
        
        active_seq = active_seq.reset_index(drop=True)
        goal_idx = active_seq[active_seq['EVENT_TYPEID'] == 16].index[-1]
        goal_row = active_seq.loc[goal_idx]
        goal_scorer_name = goal_row['PLAYER_NAME']

        # LOGIK: Find assist (spring målscorerens egne aktioner over)
        assist_idx = -1
        for i in range(goal_idx - 1, -1, -1):
            potential_p = active_seq.loc[i, 'PLAYER_NAME']
            if potential_p != goal_scorer_name:
                assist_idx = i
                break

        # Navne til visning
        scorer_disp = goal_row['PLAYER_NAME'].split()[-1] if pd.notnull(goal_row['PLAYER_NAME']) else "HIF"
        assist_name = active_seq.loc[assist_idx, 'PLAYER_NAME'].split()[-1] if assist_idx != -1 else "Solo"

        # STAT-BOKSE MED FARVEDE PRIKKER
        st.markdown(f"""
            <div class="stat-box-side">
                <div class="stat-label-side">Målscorer</div>
                <div class="stat-value-side"><span style="color:{HIF_RED}; margin-right:8px;">●</span>{scorer_disp}</div>
            </div>
            <div class="stat-box-side" style="border-left-color: {ASSIST_BLUE}">
                <div class="stat-label-side">Assist</div>
                <div class="stat-value-side"><span style="color:{ASSIST_BLUE}; margin-right:8px;">●</span>{assist_name}</div>
            </div>
            <div class="stat-box-side" style="border-left-color: {HIF_GOLD}">
                <div class="stat-label-side">Resultat / Tid</div>
                <div class="stat-value-side">{int(goal_row["HOME_SCORE"])}-{int(goal_row["AWAY_SCORE"])} | {goal_row['EVENT_TIMEMIN']}'</div>
            </div>
        """, unsafe_allow_html=True)
        
        # FLOW TABEL
        st.write("**Spilsekvens:**")
        flow_data = []
        for i in range(len(active_seq)):
            row = active_seq.loc[i]
            p = row['PLAYER_NAME'].split()[-1] if pd.notnull(row['PLAYER_NAME']) else "?"
            raw_id = str(int(row['EVENT_TYPEID']))
            quals = str(row['QUALIFIER_LIST']) if pd.notnull(row['QUALIFIER_LIST']) else ""
            
            # Navngivning ud fra ID og Qualifiers
            if "107" in quals: display_name = "Indkast"
            elif raw_id == "6": display_name = "Hjørnespark"
            elif raw_id == "16": display_name = "Mål ⚽"
            else:
                eng_name = OPTA_EVENT_TYPES.get(raw_id, f"Aktion {raw_id}")
                display_name = DK_NAMES.get(eng_name, eng_name)
            
            if i < len(active_seq) - 1:
                n = active_seq.loc[i+1, 'PLAYER_NAME'].split()[-1] if pd.notnull(active_seq.loc[i+1, 'PLAYER_NAME']) else "?"
                flow_data.append({"Flow": f"{p} → {n}", "Type": display_name})
            else:
                flow_data.append({"Flow": f"{p}", "Type": display_name})
        
        st.dataframe(pd.DataFrame(flow_data), use_container_width=True, height=280, hide_index=True)

    with col_main:
        st.markdown(f'<div class="match-header">{goal_row["HOME_TEAM"]} v {goal_row["AWAY_TEAM"]}</div>', unsafe_allow_html=True)
        
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc', goal_type='box')
        fig, ax = pitch.draw(figsize=(10, 6.5))

        # Retning af spil (HIF angriber altid mod højre i visningen)
        flip = True if goal_row['RAW_X'] < 50 else False
        def fx(x): return 100 - x if flip else x
        def fy(y): return 100 - y if flip else y

        for i in range(len(active_seq)):
            if i > goal_idx: break
            r = active_seq.loc[i]
            cx, cy = fx(r['RAW_X']), fy(r['RAW_Y'])
            
            # Prik-farve logik
            m_c = HIF_RED if i == goal_idx else (ASSIST_BLUE if i == assist_idx else '#999999')
            
            if i > 0:
                pr = active_seq.loc[i-1]
                ax.plot([fx(pr['RAW_X']), cx], [fy(pr['RAW_Y']), cy], color='#dddddd', linestyle='--', linewidth=1.5, zorder=1)

            pitch.scatter(cx, cy, s=150, color=m_c, edgecolors='black', linewidth=1, ax=ax, zorder=3)
            p_name = str(r['PLAYER_NAME']).split(' ')[-1] if pd.notnull(r['PLAYER_NAME']) else ""
            ax.text(cx, cy - 4, p_name, fontsize=10, fontweight='bold', ha='center', color=m_c, zorder=4)

        ax.text(fx(100), fy(50), "⚽", fontsize=20, ha='center', va='center')
        st.pyplot(fig)
