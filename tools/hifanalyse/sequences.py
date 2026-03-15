import streamlit as st
import pandas as pd
from mplsoccer import Pitch
import matplotlib.pyplot as plt

# HIF Design-konstanter
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'
ASSIST_BLUE = '#1e90ff'

def vis_side(dp):
    st.write(df.columns)
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
        st.info("Ingen sekvensdata fundet.")
        return

    # Sørg for dansk oversættelse af de gængse typer
    opta_dk = {
        'Pass': 'Aflevering', 'Throw-in': 'Indkast', 'Corner Awarded': 'Hjørnespark',
        'Goal': 'Mål', 'Interception': 'Erobring', 'Ball Recovery': 'Opsamling',
        'Duel': 'Duel', 'Free Kick Won': 'Frispark vundet', 'Take On': 'Dribling'
    }

    for col in ['RAW_X', 'RAW_Y', 'PREV_X_1', 'PREV_Y_1']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    if 'EVENT_TIMESTAMP' in df.columns:
        df['EVENT_TIMESTAMP'] = pd.to_datetime(df['EVENT_TIMESTAMP'])

    # Find mål og gør LABEL unik
    goal_events = df[df['EVENT_TYPEID'] == 16].copy()
    if goal_events.empty:
        st.warning("Ingen mål fundet.")
        return

    goal_events = goal_events.sort_values('EVENT_TIMESTAMP', ascending=False)
    goal_events['LABEL'] = (
        goal_events['PLAYER_NAME'] + " | " + 
        goal_events['HOME_TEAM'] + " v " + goal_events['AWAY_TEAM'] + 
        " (" + goal_events['EVENT_TIMESTAMP'].dt.strftime('%H:%M') + ")"
    )
    
    col_main, col_side = st.columns([2.5, 1])

    with col_side:
        st.subheader("Vælg Scoring")
        selected_label = st.selectbox("", options=goal_events['LABEL'].unique(), label_visibility="collapsed")
        sel_row = goal_events[goal_events['LABEL'] == selected_label].iloc[0]
        selected_id = sel_row['SEQUENCEID']
        
        # Hent sekvensen + tag én aktion FØR sekvensen (Interception/Duel logik)
        active_seq = df[df['SEQUENCEID'] == selected_id].copy().sort_values('EVENT_TIMESTAMP')
        first_idx = active_seq.index[0]
        
        # Forsøg at gå ét skridt tilbage i det store datasæt for at se hvad der skete før
        if first_idx > 0:
            pre_action = df.loc[[first_idx - 1]]
            # Kun hvis det er samme kamp
            if pre_action['GAME_ID'].values[0] == sel_row['GAME_ID']:
                active_seq = pd.concat([pre_action, active_seq]).reset_index(drop=True)
        
        active_seq = active_seq.reset_index(drop=True)
        goal_idx = active_seq[active_seq['EVENT_TYPEID'] == 16].index[-1]
        assist_idx = goal_idx - 1 
        goal_row = active_seq.loc[goal_idx]

        # Stat-bokse
        assist_name = active_seq.loc[assist_idx, 'PLAYER_NAME'].split()[-1] if assist_idx >= 0 else "N/A"
        st.markdown(f"""
            <div class="stat-box-side"><div class="stat-label-side">Målscorer</div><div class="stat-value-side">{goal_row['PLAYER_NAME'].split()[-1]}</div></div>
            <div class="stat-box-side" style="border-left-color: {ASSIST_BLUE}"><div class="stat-label-side">Assist</div><div class="stat-value-side">{assist_name}</div></div>
            <div class="stat-box-side" style="border-left-color: {HIF_GOLD}"><div class="stat-label-side">Aktioner / Resultat</div><div class="stat-value-side">{len(active_seq)} akt. | {int(goal_row["HOME_SCORE"])}-{int(goal_row["AWAY_SCORE"])}</div></div>
        """, unsafe_allow_html=True)
        
        # Flow tabel
        flow_data = []
        for i in range(len(active_seq)):
            p = active_seq.loc[i, 'PLAYER_NAME'].split()[-1] if pd.notnull(active_seq.loc[i, 'PLAYER_NAME']) else "?"
            t = active_seq.loc[i, 'EVENT_TYPE_NAME']
            t_dk = opta_dk.get(t, t) # Oversæt hvis muligt
            
            if i < len(active_seq) - 1:
                n = active_seq.loc[i+1, 'PLAYER_NAME'].split()[-1] if pd.notnull(active_seq.loc[i+1, 'PLAYER_NAME']) else "?"
                flow_data.append({"Flow": f"{p} → {n}", "Type": t_dk})
            else:
                flow_data.append({"Flow": f"{p}", "Type": "Mål ⚽"})
        
        st.dataframe(pd.DataFrame(flow_data), use_container_width=True, height=250, hide_index=True)

    with col_main:
        st.markdown(f'<div class="match-header">{goal_row["HOME_TEAM"]} {int(goal_row["HOME_SCORE"])} - {int(goal_row["AWAY_SCORE"])} {goal_row["AWAY_TEAM"]}</div>', unsafe_allow_html=True)
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc', goal_type='box')
        fig, ax = pitch.draw(figsize=(10, 6.5))

        flip = True if goal_row['RAW_X'] < 50 else False
        def fx(x): return 100 - x if flip else x
        def fy(y): return 100 - y if flip else y

        # TEGN PRIKKER OG STREGER (Garanteret tilbage)
        for i in range(len(active_seq)):
            if i > goal_idx: break
            row = active_seq.loc[i]
            
            cur_x, cur_y = fx(row['RAW_X']), fy(row['RAW_Y'])
            p_name = str(row['PLAYER_NAME']).split(' ')[-1] if pd.notnull(row['PLAYER_NAME']) else ""

            # Bestem farve
            if i == goal_idx: m_c = HIF_RED
            elif i == assist_idx: m_c = ASSIST_BLUE
            else: m_c = '#999999'

            # Tegn linje til forrige aktion
            if i > 0:
                prev_row = active_seq.loc[i-1]
                px, py = fx(prev_row['RAW_X']), fy(prev_row['RAW_Y'])
                ax.plot([px, cur_x], [py, cur_y], color='#dddddd', linestyle='--', linewidth=1.5, zorder=1)

            pitch.scatter(cur_x, cur_y, s=150, color=m_c, edgecolors='black', linewidth=1, ax=ax, zorder=3)
            ax.text(cur_x, cur_y - 4, p_name, fontsize=10, fontweight='bold', ha='center', color=m_c, zorder=4)

        ax.text(fx(100), fy(50), "⚽", fontsize=20, ha='center', va='center')
        st.pyplot(fig)
