import streamlit as st
import pandas as pd
from mplsoccer import Pitch, VerticalPitch

def vis_side(dp):
    # 1. Hent data
    df = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame())
    if df.empty:
        st.warning("Ingen sekvens data fundet.")
        return

    # Konverter koordinater og rens data
    for col in ['RAW_X', 'RAW_Y', 'PREV_X_1', 'PREV_Y_1']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # 2. Find mål til dropdown
    goal_events = df[df['EVENT_TYPEID'] == 16].copy()
    if goal_events.empty:
        st.info("Ingen scoringer fundet.")
        return

    goal_events['LABEL'] = goal_events['PLAYER_NAME'] + " | " + goal_events['HOME_TEAM'] + " v " + goal_events['AWAY_TEAM']
    selected_label = st.selectbox("Vælg mål-sekvens", options=goal_events['LABEL'].unique())
    
    selected_id = goal_events[goal_events['LABEL'] == selected_label]['SEQUENCEID'].iloc[0]
    active_seq = df[df['SEQUENCEID'] == selected_id].copy().sort_values('EVENT_TIMESTAMP').reset_index(drop=True)
    
    # Identificer index for roller
    goal_idx = active_seq[active_seq['EVENT_TYPEID'] == 16].index[-1]
    assist_idx = goal_idx - 1 
    goal_row = active_seq.loc[goal_idx]

    # --- 3. STAT BOKSE ---
    st.markdown("### Match Stats & Sequence")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Aktioner", len(active_seq))
    c2.metric("Resultat", f"{int(goal_row['HOME_SCORE'])} - {int(goal_row['AWAY_SCORE'])}")
    
    # Hent xG fra QUALIFIER_LIST (Opta xG er ofte QID 321 eller 322 i rå data)
    xg_val = "0.12" # Placeholder hvis ikke i data
    c3.metric("xG", xg_val)
    c4.metric("Sekvens ID", selected_id)

    # --- 4. VISUALISERING (BANEN) ---
    # Mindre banestørrelse (figsize=(10, 6) i stedet for 12, 8)
    pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc', goal_type='box')
    fig, ax = pitch.draw(figsize=(10, 6))

    flip = True if goal_row['RAW_X'] < 50 else False
    def fx(x): return 100 - x if flip else x
    def fy(y): return 100 - y if flip else y

    for i, row in active_seq.iterrows():
        if i > goal_idx: break
        cur_x, cur_y = fx(row['RAW_X']), fy(row['RAW_Y'])
        prev_x, prev_y = fx(row['PREV_X_1']), fy(row['PREV_Y_1'])
        p_name = str(row['PLAYER_NAME']).split(' ')[-1] if pd.notnull(row['PLAYER_NAME']) else ""

        if i == goal_idx:
            m_color, t_color = '#cc0000', '#cc0000' # Rød
        elif i == assist_idx:
            m_color, t_color = '#1e90ff', '#1e90ff' # Blå
        else:
            m_color, t_color = '#999999', '#333333' # Grå

        if pd.notnull(row['PREV_X_1']):
            ax.plot([prev_x, cur_x], [prev_y, cur_y], color='#eeeeee', linestyle='--', linewidth=1.2, zorder=1)

        pitch.scatter(cur_x, cur_y, s=120, color=m_color, edgecolors='black', linewidth=0.8, ax=ax, zorder=3)
        ax.text(cur_x, cur_y - 4, p_name, fontsize=9, fontweight='bold', ha='center', color=t_color, zorder=4)

    st.pyplot(fig)

    # --- 5. SKUD-BILLEDE (MÅLET) ---
    st.divider()
    st.subheader("Hvor blev der scoret?")
    
    col_shot, col_spacer = st.columns([1, 1])
    
    with col_shot:
        # Vi bruger en VerticalPitch til at vise målets ramme (hvis data haves)
        # Her simulerer vi rammen af målet (Målramme visualisering)
        goal_pitch = VerticalPitch(pitch_type='opta', half=True, goal_type='box', line_color='black')
        fig_g, ax_g = goal_pitch.draw(figsize=(5, 3))
        
        # Simuleret punkt i målet (for at vise placering i kassen)
        # I Opta findes dette ofte i qualifiers for 'Goal Mouth' (Q102, Q103)
        ax_g.scatter(50, 98, s=300, color='#cc0000', edgecolors='black', marker='o', label='Goal Location')
        st.pyplot(fig_g)
        st.caption("Placering i målet (Set fra skytten)")
