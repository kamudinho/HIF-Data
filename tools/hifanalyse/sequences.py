import streamlit as st
import pandas as pd
from mplsoccer import Pitch

def vis_side(dp):
    # 1. Hent data
    df = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame())
    if df.empty:
        st.warning("Ingen sekvensdata fundet.")
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
    selected_label = st.selectbox("Vælg mål-sekvens", options=goal_events['LABEL'].unique())
    
    # Hent SEQUENCEID
    selected_id = goal_events[goal_events['LABEL'] == selected_label]['SEQUENCEID'].iloc[0]

    # 3. Filtrer og sorter hele sekvensen
    active_seq = df[df['SEQUENCEID'] == selected_id].copy().sort_values('EVENT_TIMESTAMP').reset_index(drop=True)
    
    # Identificer roller ud fra index
    goal_idx = active_seq[active_seq['EVENT_TYPEID'] == 16].index[-1]
    assist_idx = goal_idx - 1  # Den sidste pasning/aktion før målet

    # --- Visualisering ---
    pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc', goal_type='box')
    fig, ax = pitch.draw(figsize=(12, 8))

    # Flip logik (Hvidovre angriber mod højre)
    goal_row = active_seq.loc[goal_idx]
    flip = True if goal_row['RAW_X'] < 50 else False
    def fx(x): return 100 - x if flip else x
    def fy(y): return 100 - y if flip else y

    # 4. TEGN SEKVENSEN
    for i, row in active_seq.iterrows():
        if i > goal_idx: break
        
        cur_x, cur_y = fx(row['RAW_X']), fy(row['RAW_Y'])
        prev_x, prev_y = fx(row['PREV_X_1']), fy(row['PREV_Y_1'])
        p_name = str(row['PLAYER_NAME']).split(' ')[-1] if pd.notnull(row['PLAYER_NAME']) else ""

        # Farvevalg baseret på din instruks
        if i == goal_idx:
            m_color = '#cc0000' # Rød prik for mål
            t_color = '#cc0000'
        elif i == assist_idx:
            m_color = '#1e90ff' # Blå prik for assist
            t_color = '#1e90ff'
        else:
            m_color = '#999999' # Grå for resten
            t_color = '#333333'

        # Tegn stiplet linje (boldens vej) - INGEN RØDE STREGER
        if pd.notnull(row['PREV_X_1']):
            ax.plot([prev_x, cur_x], [prev_y, cur_y], color='#dddddd', 
                    linestyle='--', linewidth=1.5, zorder=1)

        # Tegn prikken
        pitch.scatter(cur_x, cur_y, s=150, color=m_color, edgecolors='black', 
                      linewidth=0.8, ax=ax, zorder=3)
        
        # Navn uden for prikken (lige over)
        ax.text(cur_x, cur_y - 3, p_name, fontsize=10, fontweight='bold', 
                ha='center', va='center', color=t_color, zorder=4)

    # Marker selve målet i nettet
    ax.text(fx(100), fy(50), "⚽", fontsize=20, ha='center', va='center')

    st.pyplot(fig)

    # 5. Tabel oversigt under banen
    st.subheader("Sekvensens forløb")
    st.dataframe(active_seq[['PLAYER_NAME', 'EVENT_TIMESTAMP']].rename(columns={'PLAYER_NAME': 'Spiller', 'EVENT_TIMESTAMP': 'Tid'}))
