import streamlit as st
import pandas as pd
from mplsoccer import Pitch
import matplotlib.pyplot as plt

# HIF Design-konstanter
HIF_RED = '#cc0000'
ASSIST_BLUE = '#1e90ff'
HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

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
        st.info("Ingen sekvensdata fundet.")
        return

    # Sørg for typer
    df['RAW_X'] = pd.to_numeric(df['RAW_X'], errors='coerce')
    df['RAW_Y'] = pd.to_numeric(df['RAW_Y'], errors='coerce')
    df['EVENT_TIMESTAMP'] = pd.to_datetime(df['EVENT_TIMESTAMP'])

    # Find mål
    goal_events = df[df['EVENT_TYPEID'] == 16].copy()
    if goal_events.empty:
        st.warning("Ingen mål fundet.")
        return

    goal_events = goal_events.sort_values('EVENT_TIMESTAMP', ascending=False)
    goal_events['LABEL'] = goal_events.apply(lambda x: f"{x['EVENT_TIMEMIN']}'. min: {x['PLAYER_NAME']} ({x['HOME_TEAM']} v {x['AWAY_TEAM']})", axis=1)
    
    col_main, col_side = st.columns([2.5, 1])

    with col_side:
        selected_label = st.selectbox("Vælg scoring", options=goal_events['LABEL'].unique(), label_visibility="collapsed")
        sel_row = goal_events[goal_events['LABEL'] == selected_label].iloc[0]
        
        # 1. Hent sekvensen
        active_seq = df[df['SEQUENCEID'] == sel_row['SEQUENCEID']].copy()
        goal_time = sel_row['EVENT_TIMESTAMP']
        start_time = goal_time - pd.Timedelta(seconds=20) # Lidt længere vindue for at fange clearingen
        
        active_seq = active_seq[
            (active_seq['EVENT_TIMESTAMP'] >= start_time) & 
            (active_seq['EVENT_TIMESTAMP'] <= goal_time)
        ].sort_values('EVENT_TIMESTAMP').reset_index(drop=True)

        # 2. Find Assist og Scorer
        try:
            goal_idx = active_seq[active_seq['EVENT_TYPEID'] == 16].index[-1]
            scorer_name = active_seq.loc[goal_idx, 'PLAYER_NAME']
            
            assist_idx = -1
            for i in range(goal_idx - 1, -1, -1):
                p = active_seq.loc[i, 'PLAYER_NAME']
                if p != scorer_name and active_seq.loc[i, 'EVENT_CONTESTANT_OPTAUUID'] == HIF_UUID:
                    assist_idx = i
                    break
            
            st.markdown(f"""
                <div class="stat-box-side">
                    <div class="stat-label-side">Målscorer</div>
                    <div class="stat-value-side">{scorer_name.split()[-1]}</div>
                </div>
                <div class="stat-box-side" style="border-left-color: {ASSIST_BLUE}">
                    <div class="stat-label-side">Oplæg</div>
                    <div class="stat-value-side">{active_seq.loc[assist_idx, 'PLAYER_NAME'].split()[-1] if assist_idx != -1 else "Solo"}</div>
                </div>
            """, unsafe_allow_html=True)
        except:
            st.error("Kunne ikke analysere mål.")

    def vis_side(dp):
    # ... (CSS og data hentning er uændret) ...

    with col_main:
        st.markdown(f'<div class="match-header">{sel_row["HOME_TEAM"]} v {sel_row["AWAY_TEAM"]}</div>', unsafe_allow_html=True)
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 7))

        # Vi bruger rå koordinater, men tjekker om vi skal flippe banen ÉN gang for hele sekvensen
        # så Hvidovre altid angriber mod højre.
        should_flip = True if sel_row['RAW_X'] < 50 else False
        def fix_x(x): return 100 - x if should_flip else x
        def fix_y(y): return 100 - y if should_flip else y

        # --- LOGIK: Tegn kun streger når HIF har bolden ---
        for i in range(len(active_seq)):
            if i > goal_idx: break # Stop ved målet
            
            r = active_seq.loc[i]
            cx, cy = fix_x(r['RAW_X']), fix_y(r['RAW_Y'])
            is_hif = r['EVENT_CONTESTANT_OPTAUUID'] == HIF_UUID

            # 1. Tegn stregen FRA forrige aktion HVIS det giver mening
            if i > 0:
                prev = active_seq.loc[i-1]
                px, py = fix_x(prev['RAW_X']), fix_y(prev['RAW_Y'])
                
                # Vi tegner KUN en streg hvis:
                # Modstanderen clearer (sort prik) -> HIF samler op
                # ELLER HIF spiller til HIF
                ax.annotate('', xy=(cx, cy), xytext=(px, py),
                            arrowprops=dict(arrowstyle='->', color='#cccccc', lw=1.5, alpha=0.5))

            # 2. Tegn selve prikken
            if is_hif:
                if i == goal_idx: m_c = HIF_RED
                elif i == assist_idx: m_c = ASSIST_BLUE
                else: m_c = '#aaaaaa'
                
                # Navne-label
                p_label = r['PLAYER_NAME'].split()[-1] if pd.notnull(r['PLAYER_NAME']) else ""
                ax.text(cx, cy + 3, p_label, fontsize=9, ha='center', va='bottom', fontweight='bold')
            else:
                m_c = 'black' # Modstanderens clearing
            
            pitch.scatter(cx, cy, s=180, color=m_c, edgecolors='white', linewidth=1, ax=ax, zorder=3)

        st.pyplot(fig)
