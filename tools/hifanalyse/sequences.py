import streamlit as st
import pandas as pd
from mplsoccer import Pitch
import matplotlib.pyplot as plt

# HIF Design-konstanter
HIF_RED = '#cc0000'
ASSIST_BLUE = '#1e90ff'
HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

def vis_side(dp):
    # 1. CSS til sidebar stats
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

    # Formatering
    df['RAW_X'] = pd.to_numeric(df['RAW_X'], errors='coerce')
    df['RAW_Y'] = pd.to_numeric(df['RAW_Y'], errors='coerce')
    df['EVENT_TIMESTAMP'] = pd.to_datetime(df['EVENT_TIMESTAMP'])

    # Find mål til dropdown
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
        
        # Filtrer data til det specifikke mål (vha. vores GOAL_REF_ID/SEQUENCEID)
        active_seq = df[df['SEQUENCEID'] == sel_row['SEQUENCEID']].copy()
        
        # Tids-vindue: 15 sekunder før mål
        goal_time = sel_row['EVENT_TIMESTAMP']
        start_time = goal_time - pd.Timedelta(seconds=20)
        
        active_seq = active_seq[
            (active_seq['EVENT_TIMESTAMP'] >= start_time) & 
            (active_seq['EVENT_TIMESTAMP'] <= goal_time)
        ].sort_values('EVENT_TIMESTAMP').reset_index(drop=True)

        # Rens modstander-støj (Aerial duels/tackles) så flowet er rent HIF
        active_seq = active_seq[
            (active_seq['EVENT_CONTESTANT_OPTAUUID'] == HIF_UUID) | 
            (active_seq['EVENT_TYPEID'].isin([1, 16]))
        ].reset_index(drop=True)

        try:
            goal_idx = active_seq[active_seq['EVENT_TYPEID'] == 16].index[-1]
            scorer_name = active_seq.loc[goal_idx, 'PLAYER_NAME']
            
            # Find assist (Sidste HIF-spiller der ikke er målscoreren)
            assist_idx = -1
            for i in range(goal_idx - 1, -1, -1):
                p = active_seq.loc[i, 'PLAYER_NAME']
                if p != scorer_name and active_seq.loc[i, 'EVENT_CONTESTANT_OPTAUUID'] == HIF_UUID:
                    assist_idx = i
                    break
            
            assist_name = active_seq.loc[assist_idx, 'PLAYER_NAME'] if assist_idx != -1 else "Solo"

            # Sidebar display
            st.markdown(f"""
                <div class="stat-box-side">
                    <div class="stat-label-side">Målscorer</div>
                    <div class="stat-value-side">{scorer_name.split()[-1] if pd.notnull(scorer_name) else "HIF"}</div>
                </div>
                <div class="stat-box-side" style="border-left-color: {ASSIST_BLUE}">
                    <div class="stat-label-side">Oplæg</div>
                    <div class="stat-value-side">{assist_name.split()[-1] if assist_idx != -1 else "Solo"}</div>
                </div>
            """, unsafe_allow_html=True)
        except:
            st.error("Fejl ved analyse af målsekvensen.")

    with col_main:
        st.markdown(f'<div class="match-header">{sel_row["HOME_TEAM"]} v {sel_row["AWAY_TEAM"]}</div>', unsafe_allow_html=True)
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 7))

        # Retning: HIF angriber altid mod højre
        flip = True if sel_row['RAW_X'] < 50 else False
        def fx(x): return 100 - x if flip else x
        def fy(y): return 100 - y if flip else y

        for i in range(len(active_seq)):
            if i > goal_idx: break
            r = active_seq.loc[i]
            cx, cy = fx(r['RAW_X']), fy(r['RAW_Y'])
            is_hif = r['EVENT_CONTESTANT_OPTAUUID'] == HIF_UUID

            # Farvekode: Mål=Rød, Assist=Blå, HIF-øvrige=Grå, Modstander=Sort
            if is_hif:
                if i == goal_idx: m_c = HIF_RED
                elif i == assist_idx: m_c = ASSIST_BLUE
                else: m_c = '#aaaaaa'
                p_label = r['PLAYER_NAME'].split()[-1] if pd.notnull(r['PLAYER_NAME']) else ""
            else:
                m_c = 'black'
                p_label = ""

            # Tegn linjer (Flow)
            if i > 0:
                pr = active_seq.loc[i-1]
                ax.annotate('', xy=(cx, cy), xytext=(fx(pr['RAW_X']), fy(pr['RAW_Y'])),
                            arrowprops=dict(arrowstyle='->', color='#cccccc', lw=1, alpha=0.6))

            pitch.scatter(cx, cy, s=180, color=m_c, edgecolors='white', linewidth=1, ax=ax, zorder=3)
            if p_label:
                ax.text(cx, cy + 3, p_label, fontsize=9, ha='center', va='bottom', fontweight='bold')

        st.pyplot(fig)
