import streamlit as st
import pandas as pd
from mplsoccer import Pitch
import matplotlib.pyplot as plt

# HIF Design-konstanter
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'
ASSIST_BLUE = '#1e90ff'

def vis_side(dp):
    # --- 1. CSS ---
    st.markdown(f"""
        <style>
            .stat-box-side {{
                background-color: #f8f9fa;
                padding: 12px;
                border-radius: 8px;
                border-left: 5px solid {HIF_RED};
                margin-bottom: 8px;
            }}
            .stat-label-side {{ font-size: 0.7rem; text-transform: uppercase; color: #666; font-weight: 800; }}
            .stat-value-side {{ font-size: 1.2rem; font-weight: 900; color: #1a1a1a; }}
            .action-flow {{ 
                font-family: monospace; 
                font-size: 0.85rem; 
                background: #ffffff; 
                padding: 5px; 
                border-bottom: 1px solid #eee;
            }}
            .match-header {{
                font-size: 1.3rem; font-weight: 800; color: {HIF_RED};
                text-align: center; margin-bottom: 20px; text-transform: uppercase;
            }}
        </style>
    """, unsafe_allow_html=True)

    # 2. Hent data
    df = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame())
    if df.empty:
        st.info("Ingen sekvensdata fundet.")
        return

    for col in ['RAW_X', 'RAW_Y', 'PREV_X_1', 'PREV_Y_1']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    goal_events = df[df['EVENT_TYPEID'] == 16].copy()
    if goal_events.empty:
        st.warning("Ingen mål fundet.")
        return

    goal_events['LABEL'] = goal_events['PLAYER_NAME'] + " | " + goal_events['HOME_TEAM'] + " v " + goal_events['AWAY_TEAM']
    
    # --- LAYOUT ---
    col_main, col_side = st.columns([2.5, 1])

    with col_side:
        st.caption("Vælg scoring")
        selected_label = st.selectbox("", options=goal_events['LABEL'].unique(), label_visibility="collapsed")
        
        selected_id = goal_events[goal_events['LABEL'] == selected_label]['SEQUENCEID'].iloc[0]
        active_seq = df[df['SEQUENCEID'] == selected_id].copy().sort_values('EVENT_TIMESTAMP').reset_index(drop=True)
        
        goal_idx = active_seq[active_seq['EVENT_TYPEID'] == 16].index[-1]
        assist_idx = goal_idx - 1 
        goal_row = active_seq.loc[goal_idx]
        assist_name = active_seq.loc[assist_idx, 'PLAYER_NAME'].split()[-1] if assist_idx >= 0 else "N/A"

        # --- STAT-BOKSE (RYKKET OP UNDER DROPDOWN) ---
        st.markdown(f"""
            <div class="stat-box-side"><div class="stat-label-side">Målscorer</div><div class="stat-value-side">{goal_row['PLAYER_NAME'].split()[-1]}</div></div>
            <div class="stat-box-side" style="border-left-color: {ASSIST_BLUE}"><div class="stat-label-side">Assist</div><div class="stat-value-side">{assist_name}</div></div>
            <div class="stat-box-side" style="border-left-color: {HIF_GOLD}"><div class="stat-label-side">Aktioner / Resultat</div><div class="stat-value-side">{len(active_seq)} akt. | {int(goal_row["HOME_SCORE"])}-{int(goal_row["AWAY_SCORE"])}</div></div>
        """, unsafe_allow_html=True)
        
        # --- NY AKTIONER VISNING (SMED -> OKOSUN) ---
        st.write("**Spilsekvens:**")
        flow_list = []
        for i in range(len(active_seq)):
            current_p = active_seq.loc[i, 'PLAYER_NAME'].split()[-1] if pd.notnull(active_seq.loc[i, 'PLAYER_NAME']) else "?"
            if i < len(active_seq) - 1:
                next_p = active_seq.loc[i+1, 'PLAYER_NAME'].split()[-1] if pd.notnull(active_seq.loc[i+1, 'PLAYER_NAME']) else "?"
                flow_list.append(f"{current_p} → {next_p}")
            else:
                flow_list.append(f"{current_p} (AFSLUTNING)")
        
        st.dataframe(pd.DataFrame(flow_list, columns=["Sekvens Flow"]), use_container_width=True, height=250, hide_index=True)

    with col_main:
        st.markdown(f'<div class="match-header">{goal_row["HOME_TEAM"]} {int(goal_row["HOME_SCORE"])} - {int(goal_row["AWAY_SCORE"])} {goal_row["AWAY_TEAM"]}</div>', unsafe_allow_html=True)
        
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc', goal_type='box')
        fig, ax = pitch.draw(figsize=(10, 6.5))

        flip = True if goal_row['RAW_X'] < 50 else False
        def fx(x): return 100 - x if flip else x
        def fy(y): return 100 - y if flip else y

        for i, row in active_seq.iterrows():
            if i > goal_idx: break
            cur_x, cur_y = fx(row['RAW_X']), fy(row['RAW_Y'])
            prev_x, prev_y = fx(row['PREV_X_1']), fy(row['PREV_Y_1'])
            p_name = str(row['PLAYER_NAME']).split(' ')[-1] if pd.notnull(row['PLAYER_NAME']) else ""

            if i == goal_idx:
                m_color, t_color = HIF_RED, HIF_RED
            elif i == assist_idx:
                m_color, t_color = ASSIST_BLUE, ASSIST_BLUE
            else:
                m_color, t_color = '#999999', '#444444'

            if pd.notnull(row['PREV_X_1']):
                ax.plot([prev_x, cur_x], [prev_y, cur_y], color='#eeeeee', linestyle='--', linewidth=1.2, zorder=1)

            pitch.scatter(cur_x, cur_y, s=120, color=m_color, edgecolors='black', linewidth=0.8, ax=ax, zorder=3)
            ax.text(cur_x, cur_y - 4, p_name, fontsize=9, fontweight='bold', ha='center', color=t_color, zorder=4)

        ax.text(fx(100), fy(50), "⚽", fontsize=20, ha='center', va='center')
        st.pyplot(fig)
