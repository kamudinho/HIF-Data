import streamlit as st
import pandas as pd
from mplsoccer import Pitch
import matplotlib.pyplot as plt

# Importér fra din mapping-fil
try:
    from data.utils.mappings import OPTA_EVENT_TYPES, get_event_name
except:
    def get_event_name(eid): return f"Aktion {eid}"

# HIF Design-konstanter
HIF_RED = '#cc0000'
ASSIST_BLUE = '#1e90ff'
HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

# Udvidet ordbog til oversættelse (Sørg for at disse matcher hvad get_event_name returnerer)
DK_NAMES = {
    "Pass": "Aflevering", "Ball recovery": "Opsamling", "Goal": "MÅL",
    "Clearance": "Clearing", "Tackle": "Tackling", "Attempt Saved": "Blokeret skud",
    "Foul": "Frispark", "Out": "Bold ud", "Corner": "Hjørnespark", "Throw-in": "Indkast",
    "Take On": "Dribling", "Aerial": "Hovedstød", "Interception": "Opsnapning"
}

def vis_side(dp):
    # CSS (Beholdes fra tidligere)
    st.markdown(f"""
        <style>
            .stat-box-side {{ background-color: #f8f9fa; padding: 12px; border-radius: 8px; border-left: 5px solid {HIF_RED}; margin-bottom: 8px; }}
            .stat-label-side {{ font-size: 0.7rem; text-transform: uppercase; color: #666; font-weight: 800; display: flex; align-items: center; gap: 8px; }}
            .stat-value-side {{ font-size: 1.2rem; font-weight: 900; color: #1a1a1a; margin-top: 4px; }}
            .dot {{ height: 12px; width: 12px; border-radius: 50%; display: inline-block; }}
            .play-flow-container {{ background: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #eee; margin-top: 20px; }}
            .flow-step {{ font-weight: 700; color: #333; }}
            .flow-action {{ color: #666; font-size: 0.8rem; font-weight: 400; }}
            .flow-arrow {{ color: {HIF_RED}; margin: 0 5px; font-weight: bold; }}
        </style>
    """, unsafe_allow_html=True)

    df_raw = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame())
    if df_raw.empty: return

    # Rens data
    df = df_raw.copy()
    df['RAW_X'] = pd.to_numeric(df['RAW_X'], errors='coerce')
    df['RAW_Y'] = pd.to_numeric(df['RAW_Y'], errors='coerce')
    df['EVENT_TIMESTAMP'] = pd.to_datetime(df['EVENT_TIMESTAMP'])
    df = df.sort_values(['EVENT_TIMESTAMP', 'SEQUENCEID']).reset_index(drop=True)

    goal_events = df[df['EVENT_TYPEID'] == 16].sort_values('EVENT_TIMESTAMP', ascending=False)
    if goal_events.empty: return
    goal_events['LABEL'] = goal_events.apply(lambda x: f"{x['EVENT_TIMEMIN']}'. min: {x['PLAYER_NAME']}", axis=1)
    
    col_main, col_side = st.columns([2.5, 1])

    with col_side:
        selected_label = st.selectbox("Vælg mål", options=goal_events['LABEL'].unique(), label_visibility="collapsed")
        sel_row = goal_events[goal_events['LABEL'] == selected_label].iloc[0]
        
        # Isoler sekvens
        temp_seq = df[df['SEQUENCEID'] == sel_row['SEQUENCEID']].sort_values('EVENT_TIMESTAMP').reset_index(drop=True)
        restarts = temp_seq[temp_seq['EVENT_TYPEID'].isin([5, 6, 107])]
        start_idx = restarts.index[-1] if not restarts.empty else 0
        hif_seq = temp_seq.iloc[start_idx:].reset_index(drop=True)
        hif_seq = hif_seq[hif_seq['EVENT_CONTESTANT_OPTAUUID'] == HIF_UUID].copy().reset_index(drop=True)

        # Målscorer og Assist
        scorer_name = hif_seq.iloc[-1]['PLAYER_NAME'].split()[-1] if not hif_seq.empty else "HIF"
        assist_name = hif_seq.iloc[-2]['PLAYER_NAME'].split()[-1] if len(hif_seq) > 1 else "Solo"

        st.markdown(f'<div class="stat-box-side"><div class="stat-label-side"><span class="dot" style="background-color:{HIF_RED}"></span>Målscorer</div><div class="stat-value-side">{scorer_name}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-box-side" style="border-left-color: {ASSIST_BLUE}"><div class="stat-label-side"><span class="dot" style="background-color:{ASSIST_BLUE}"></span>Assist</div><div class="stat-value-side">{assist_name}</div></div>', unsafe_allow_html=True)

    with col_main:
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 7))
        should_flip = True if sel_row['RAW_X'] < 50 else False

        prev_pt = None
        for i, r in hif_seq.iterrows():
            rx, ry = r['RAW_X'], r['RAW_Y']
            if r['EVENT_TYPEID'] == 6:
                rx, ry = (100.0 if rx > 50 else 0.0), (100.0 if ry > 50 else 0.0)
            cx, cy = (100 - rx if should_flip else rx), (100 - ry if should_flip else ry)
            
            if prev_pt:
                ax.annotate('', xy=(cx, cy), xytext=(prev_pt[0], prev_pt[1]),
                            arrowprops=dict(arrowstyle='->', color='#cccccc', lw=1.5, alpha=0.4, shrinkA=5, shrinkB=5))
            
            p_short = r['PLAYER_NAME'].split()[-1] if pd.notnull(r['PLAYER_NAME']) else "HIF"
            is_goal = r['EVENT_TYPEID'] == 16
            color = HIF_RED if is_goal else (ASSIST_BLUE if p_short == assist_name else '#aaaaaa')
            pitch.scatter(cx, cy, s=180, color=color, edgecolors='white', ax=ax, zorder=5)
            ax.text(cx, cy + 3, p_short, fontsize=8, ha='center', fontweight='bold')
            prev_pt = (cx, cy)
        st.pyplot(fig)

        # --- SEKVENS-OVERSIGT ---
        steps = []
        for _, r in hif_seq.iterrows():
            p = r['PLAYER_NAME'].split()[-1] if pd.notnull(r['PLAYER_NAME']) else "HIF"
            ename = get_event_name(str(int(r['EVENT_TYPEID'])))
            action = DK_NAMES.get(ename, ename) # Her sker oversættelsen
            if str(r['EVENT_TYPEID']) == "16": action = "MÅL"
            steps.append(f'<span class="flow-step">{p}</span> <span class="flow-action">({action})</span>')
        st.markdown(f'<div class="play-flow-container">{" <span class="flow-arrow">→</span> ".join(steps)}</div>', unsafe_allow_html=True)

    # --- NY TABEL: INVOLVERINGER I MÅLSEKVENSER ---
    st.caption("### Flest aktioner i målsekvenser (Top 5)")
    
    # Vi tæller alle HIF aktioner i alle fundne sekvenser i datasættet
    all_hif_actions = df[df['EVENT_CONTESTANT_OPTAUUID'] == HIF_UUID].copy()
    if not all_hif_actions.empty:
        # Tæl involveringer pr spiller
        involvement_counts = all_hif_actions['PLAYER_NAME'].value_counts().reset_index()
        involvement_counts.columns = ['Spiller', 'Antal Aktioner']
        
        # Gør navnene pæne (kun efternavn)
        involvement_counts['Spiller'] = involvement_counts['Spiller'].apply(lambda x: x.split()[-1] if pd.notnull(x) else "HIF")
        
        # Vis som en pæn tabel
        st.table(involvement_counts.head(5))
