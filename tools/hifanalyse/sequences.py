import streamlit as st
import pandas as pd
from mplsoccer import Pitch, VerticalPitch

def vis_side(dp):
    # 1. Hent data
    df = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame())
    if df.empty:
        st.warning("Ingen sekvens data fundet.")
        return

    # Konverter koordinater
    for col in ['RAW_X', 'RAW_Y', 'PREV_X_1', 'PREV_Y_1']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # 2. Find mål til dropdown
    goal_events = df[df['EVENT_TYPEID'] == 16].copy()
    if goal_events.empty:
        st.info("Ingen scoringer fundet.")
        return

    goal_events['LABEL'] = goal_events['PLAYER_NAME'] + " | " + goal_events['HOME_TEAM'] + " v " + goal_events['AWAY_TEAM']
    
    # --- LAYOUT: BANE TIL VENSTRE, DROPDOWN TIL HØJRE ---
    col_main, col_side = st.columns([3, 1])

    with col_side:
        st.markdown("### Vælg Mål")
        selected_label = st.selectbox("", options=goal_events['LABEL'].unique(), label_visibility="collapsed")
        
        selected_id = goal_events[goal_events['LABEL'] == selected_label]['SEQUENCEID'].iloc[0]
        active_seq = df[df['SEQUENCEID'] == selected_id].copy().sort_values('EVENT_TIMESTAMP').reset_index(drop=True)
        
        goal_idx = active_seq[active_seq['EVENT_TYPEID'] == 16].index[-1]
        assist_idx = goal_idx - 1 
        goal_row = active_seq.loc[goal_idx]
        
        st.divider()
        st.subheader("Afslutning")
        # Visualisering af målet (Set forfra)
        goal_pitch = VerticalPitch(pitch_type='opta', half=True, goal_type='box', line_color='black')
        fig_g, ax_g = goal_pitch.draw(figsize=(4, 2.5))
        # Her plottes et punkt i målet (Placeholder for Goal Mouth Y/Z)
        ax_g.scatter(50, 98, s=200, color='#cc0000', edgecolors='black', zorder=5)
        st.pyplot(fig_g)

    with col_main:
        # Pitch setup - mindre størrelse for at passe layoutet
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc', goal_type='box')
        fig, ax = pitch.draw(figsize=(9, 5.5))

        flip = True if goal_row['RAW_X'] < 50 else False
        def fx(x): return 100 - x if flip else x
        def fy(y): return 100 - y if flip else y

        for i, row in active_seq.iterrows():
            if i > goal_idx: break
            cur_x, cur_y = fx(row['RAW_X']), fy(row['RAW_Y'])
            prev_x, prev_y = fx(row['PREV_X_1']), fy(row['PREV_Y_1'])
            p_name = str(row['PLAYER_NAME']).split(' ')[-1] if pd.notnull(row['PLAYER_NAME']) else ""

            # Farver: Mål=Rød, Assist=Blå, Rest=Grå
            if i == goal_idx:
                m_color, t_color = '#cc0000', '#cc0000'
            elif i == assist_idx:
                m_color, t_color = '#1e90ff', '#1e90ff'
            else:
                m_color, t_color = '#999999', '#333333'

            # Forbindelsespunkter (grå stiplet)
            if pd.notnull(row['PREV_X_1']):
                ax.plot([prev_x, cur_x], [prev_y, cur_y], color='#eeeeee', linestyle='--', linewidth=1, zorder=1)

            pitch.scatter(cur_x, cur_y, s=100, color=m_color, edgecolors='black', linewidth=0.6, ax=ax, zorder=3)
            ax.text(cur_x, cur_y - 4, p_name, fontsize=8, fontweight='bold', ha='center', color=t_color, zorder=4)

        # Marker målet
        ax.text(fx(100), fy(50), "⚽", fontsize=16, ha='center', va='center')
        st.pyplot(fig)

    # --- BOKSE UNDER BANEN ---
    st.divider()
    b1, b2, b3, b4 = st.columns(4)
    
    with b1:
        st.metric("Antal aktioner", len(active_seq))
    with b2:
        st.metric("Målscorer", goal_row['PLAYER_NAME'].split(' ')[-1])
    with b3:
        # Assistmageren er personen på assist_idx
        assist_name = active_seq.loc[assist_idx, 'PLAYER_NAME'].split(' ')[-1] if assist_idx >= 0 else "N/A"
        st.metric("Assist", assist_name)
    with b4:
        st.metric("Resultat", f"{int(goal_row['HOME_SCORE'])} - {int(goal_row['AWAY_SCORE'])}")
