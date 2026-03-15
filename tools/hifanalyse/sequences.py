import streamlit as st
import pandas as pd
from mplsoccer import Pitch
import matplotlib.pyplot as plt

# HIF Design-konstanter og ID
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'
ASSIST_BLUE = '#1e90ff'
HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy' # Hvidovre Opta ID

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
    "Throw In": "Indkast", "Tackle": "Tackle", "Clearance": "Clearance",
    "Out": "Bold ude"
}

def vis_side(dp):
    # 1. CSS (Beholdes som den er)
    st.markdown(f"""
        <style>
            .stat-box-side {{ background-color: #f8f9fa; padding: 12px; border-radius: 8px; border-left: 5px solid {HIF_RED}; margin-bottom: 8px; }}
            .stat-label-side {{ font-size: 0.7rem; text-transform: uppercase; color: #666; font-weight: 800; }}
            .stat-value-side {{ font-size: 1.2rem; font-weight: 900; color: #1a1a1a; display: flex; align-items: center; }}
            .match-header {{ font-size: 1.3rem; font-weight: 800; color: {HIF_RED}; text-align: center; margin-bottom: 20px; text-transform: uppercase; }}
        </style>
    """, unsafe_allow_html=True)

    # 2. Data Check
    df = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame())
    if df.empty:
        st.info("Ingen sekvensdata fundet.")
        return

    # Konverter typer
    for col in ['RAW_X', 'RAW_Y']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    if 'EVENT_TIMESTAMP' in df.columns:
        df['EVENT_TIMESTAMP'] = pd.to_datetime(df['EVENT_TIMESTAMP'])

    # Find mål
    goal_events = df[df['EVENT_TYPEID'] == 16].copy()
    if goal_events.empty:
        st.warning("Ingen mål fundet.")
        return

    goal_events = goal_events.sort_values('EVENT_TIMESTAMP', ascending=False)
    goal_events['LABEL'] = (
        goal_events['EVENT_TIMEMIN'].astype(str) + "'. min: " +
        goal_events['PLAYER_NAME'].fillna("Ukendt") + " #" + goal_events['SEQUENCEID'].astype(str)
    )
    
    col_main, col_side = st.columns([2.5, 1])

    with col_side:
        selected_label = st.selectbox("Vælg scoring", options=goal_events['LABEL'].unique())
        sel_row = goal_events[goal_events['LABEL'] == selected_label].iloc[0]
        
        # Hent og filtrer sekvens
        active_seq = df[df['SEQUENCEID'] == sel_row['SEQUENCEID']].copy().sort_values('EVENT_TIMESTAMP')
        
        # FILTRERING: Fjern modstander-dueller (som Racic), der ikke resulterer i boldtab for HIF
        # Vi beholder kun HIF aktioner ELLER modstander aktioner der er reelle (f.eks. type 1, 16)
        active_seq = active_seq[
            (active_seq['EVENT_CONTESTANT_OPTAUUID'] == HIF_UUID) | 
            (~active_seq['EVENT_TYPEID'].isin([44, 50]))
        ].reset_index(drop=True)

        goal_idx = active_seq[active_seq['EVENT_TYPEID'] == 16].index[-1]
        
        # Find Assist (Smed i dit tilfælde)
        assist_idx = goal_idx - 1 if goal_idx > 0 else -1
        
        scorer_name = active_seq.loc[goal_idx, 'PLAYER_NAME']
        assist_name = active_seq.loc[assist_idx, 'PLAYER_NAME'] if assist_idx != -1 else "Solo"

        # Sidebar Stats
        st.markdown(f"""
            <div class="stat-box-side">
                <div class="stat-label-side">Målscorer</div>
                <div class="stat-value-side">{scorer_name.split()[-1] if pd.notnull(scorer_name) else "HIF"}</div>
            </div>
            <div class="stat-box-side" style="border-left-color: {ASSIST_BLUE}">
                <div class="stat-label-side">Oplæg</div>
                <div class="stat-value-side">{assist_name.split()[-1] if pd.notnull(assist_name) else "Solo"}</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Flow tabel uden ikoner
        flow_data = []
        for i in range(len(active_seq)):
            r = active_seq.loc[i]
            is_hif = r['EVENT_CONTESTANT_OPTAUUID'] == HIF_UUID
            p_name = r['PLAYER_NAME'].split()[-1] if (pd.notnull(r['PLAYER_NAME']) and is_hif) else "Modstander"
            etype = OPTA_EVENT_TYPES.get(str(int(r['EVENT_TYPEID'])), "Aktion")
            flow_data.append({"Spiller": p_name, "Handling": DK_NAMES.get(etype, etype)})
        
        st.dataframe(pd.DataFrame(flow_data), use_container_width=True, height=250, hide_index=True)

    with col_main:
        st.markdown(f'<div class="match-header">{sel_row["HOME_TEAM"]} v {sel_row["AWAY_TEAM"]}</div>', unsafe_allow_html=True)
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 7))

        # Retning (HIF angriber altid mod højre i visningen)
        flip = True if sel_row['RAW_X'] < 50 else False
        def fx(x): return 100 - x if flip else x
        def fy(y): return 100 - y if flip else y

        for i in range(len(active_seq)):
            if i > goal_idx: break
            r = active_seq.loc[i]
            cx, cy = fx(r['RAW_X']), fy(r['RAW_Y'])
            is_hif = r['EVENT_CONTESTANT_OPTAUUID'] == HIF_UUID

            # Farver: Mål=Rød, Assist=Blå, HIF-andre=Grå, Modstander=Sort
            if is_hif:
                if i == goal_idx: m_c = HIF_RED
                elif i == assist_idx: m_c = ASSIST_BLUE
                else: m_c = '#777777'
                p_label = r['PLAYER_NAME'].split()[-1] if pd.notnull(r['PLAYER_NAME']) else ""
            else:
                m_c = 'black'
                p_label = ""

            # Tegn linje fra forrige aktion
            if i > 0:
                pr = active_seq.loc[i-1]
                ax.annotate('', xy=(cx, cy), xytext=(fx(pr['RAW_X']), fy(pr['RAW_Y'])),
                            arrowprops=dict(arrowstyle='->', color='#bbbbbb', lw=1.5, alpha=0.8))

            # Tegn spiller-punkt
            pitch.scatter(cx, cy, s=180, color=m_c, edgecolors='white', linewidth=1.5, ax=ax, zorder=3)
            
            # Navn (Kun HIF)
            if p_label:
                ax.text(cx, cy + 3, p_label, fontsize=9, fontweight='bold', ha='center', va='bottom')

        st.pyplot(fig)
