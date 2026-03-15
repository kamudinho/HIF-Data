import streamlit as st
import pandas as pd
from mplsoccer import Pitch
import matplotlib.pyplot as plt

# HIF Design-konstanter
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'
ASSIST_BLUE = '#1e90ff'

def vis_side(dp):
    # --- 1. GLOBAL CSS (Deklareres først for at sikre det virker) ---
    st.markdown(f"""
        <style>
            /* Stat-bokse layout */
            .stat-container {{
                display: flex;
                gap: 10px;
                margin-top: 20px;
            }}
            .stat-box {{
                flex: 1;
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 8px;
                border-left: 5px solid {HIF_RED};
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }}
            .stat-label {{
                font-size: 0.75rem;
                text-transform: uppercase;
                color: #666;
                font-weight: 800;
                margin-bottom: 5px;
            }}
            .stat-value {{
                font-size: 1.4rem;
                font-weight: 900;
                color: #1a1a1a;
            }}
            .match-header {{
                font-size: 1.3rem;
                font-weight: 800;
                color: {HIF_RED};
                text-align: center;
                margin-bottom: 20px;
                text-transform: uppercase;
            }}
        </style>
    """, unsafe_allow_html=True)

    # 2. Hent data
    df = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame())
    if df.empty:
        st.info("Ingen sekvensdata fundet.")
        return

    # Konverter koordinater
    for col in ['RAW_X', 'RAW_Y', 'PREV_X_1', 'PREV_Y_1']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # 3. Find mål til dropdown
    goal_events = df[df['EVENT_TYPEID'] == 16].copy()
    if goal_events.empty:
        st.warning("Ingen mål fundet.")
        return

    goal_events['LABEL'] = goal_events['PLAYER_NAME'] + " | " + goal_events['HOME_TEAM'] + " v " + goal_events['AWAY_TEAM']
    
    # --- 4. LAYOUT TOP: BANE OG DROPDOWN ---
    col_main, col_side = st.columns([2.5, 1])

    with col_side:
        st.subheader("Vælg Scoring")
        selected_label = st.selectbox("", options=goal_events['LABEL'].unique(), label_visibility="collapsed")
        
        selected_id = goal_events[goal_events['LABEL'] == selected_label]['SEQUENCEID'].iloc[0]
        active_seq = df[df['SEQUENCEID'] == selected_id].copy().sort_values('EVENT_TIMESTAMP').reset_index(drop=True)
        
        st.write("**Aktioner i opspillet:**")
        st.dataframe(
            active_seq[['PLAYER_NAME']].rename(columns={'PLAYER_NAME': 'Spiller'}),
            use_container_width=True,
            height=320,
            hide_index=True
        )

    with col_main:
        goal_idx = active_seq[active_seq['EVENT_TYPEID'] == 16].index[-1]
        assist_idx = goal_idx - 1 
        goal_row = active_seq.loc[goal_idx]
        
        st.markdown(f'<div class="match-header">{goal_row["HOME_TEAM"]} {int(goal_row["HOME_SCORE"])} - {int(goal_row["AWAY_SCORE"])} {goal_row["AWAY_TEAM"]}</div>', unsafe_allow_html=True)
        
        # Pitch setup
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc', goal_type='box')
        fig, ax = pitch.draw(figsize=(10, 6))

        flip = True if goal_row['RAW_X'] < 50 else False
        def fx(x): return 100 - x if flip else x
        def fy(y): return 100 - y if flip else y

        # Tegn sekvensen
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

    # --- 5. LAYOUT BUND: DE LÆKRE STAT-BOKSE ---
    st.divider()
    
    # Vi bruger HTML her for at sikre at layoutet (flex) følger CSS-reglerne
    assist_name = active_seq.loc[assist_idx, 'PLAYER_NAME'].split()[-1] if assist_idx >= 0 else "N/A"
    
    html_stats = f"""
    <div class="stat-container">
        <div class="stat-box">
            <div class="stat-label">Målscorer</div>
            <div class="stat-value">{goal_row['PLAYER_NAME'].split()[-1]}</div>
        </div>
        <div class="stat-box" style="border-left-color: {ASSIST_BLUE}">
            <div class="stat-label">Assist</div>
            <div class="stat-value">{assist_name}</div>
        </div>
        <div class="stat-box" style="border-left-color: {HIF_GOLD}">
            <div class="stat-label">Antal Aktioner</div>
            <div class="stat-value">{len(active_seq)}</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">Resultat</div>
            <div class="stat-value">{int(goal_row["HOME_SCORE"])} - {int(goal_row["AWAY_SCORE"])}</div>
        </div>
    </div>
    """
    st.markdown(html_stats, unsafe_allow_html=True)
