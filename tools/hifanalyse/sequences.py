import streamlit as st
import pandas as pd
from mplsoccer import Pitch
import matplotlib.pyplot as plt

# Sikker import af din mapping-fil
try:
    from data.utils.mappings import OPTA_EVENT_TYPES, get_event_name
except:
    def get_event_name(eid): return f"Aktion {eid}"

# HIF Design-konstanter
HIF_RED = '#cc0000'
ASSIST_BLUE = '#1e90ff'

# Danske navne (Fallback hvis din mapping.py er engelsk)
DK_NAMES = {
    "Pass": "Aflevering", "Ball recovery": "Opsamling", "Goal": "MÅL",
    "Clearance": "Clearing", "Tackle": "Tackling", "Attempt Saved": "Blokeret skud",
    "Foul": "Frispark", "Out": "Bold ud", "Corner": "Hjørnespark", "Throw-in": "Indkast"
}

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
        st.warning("Ingen Opta-data fundet.")
        return

    # Forbered data
    df['RAW_X'] = pd.to_numeric(df['RAW_X'], errors='coerce')
    df['RAW_Y'] = pd.to_numeric(df['RAW_Y'], errors='coerce')
    df['EVENT_TIMESTAMP'] = pd.to_datetime(df['EVENT_TIMESTAMP'])
    df = df.dropna(subset=['RAW_X', 'RAW_Y']).sort_values('EVENT_TIMESTAMP')

    # Find mål
    goal_events = df[df['EVENT_TYPEID'] == 16].sort_values('EVENT_TIMESTAMP', ascending=False)
    if goal_events.empty:
        st.info("Ingen scoringer fundet.")
        return
        
    goal_events['LABEL'] = goal_events.apply(lambda x: f"{x['EVENT_TIMEMIN']}'. min: {x['PLAYER_NAME']}", axis=1)
    
    col_main, col_side = st.columns([2.3, 1.2])

    with col_side:
        selected_label = st.selectbox("Vælg mål", options=goal_events['LABEL'].unique(), label_visibility="collapsed")
        sel_row = goal_events[goal_events['LABEL'] == selected_label].iloc[0]
        
        # Identificer HIF (Holdet der scorede)
        hif_team_id = sel_row['EVENT_CONTESTANT_OPTAUUID']
        
        # Hent og Sorter hele sekvensen kronologisk
        active_seq = df[df['SEQUENCEID'] == sel_row['SEQUENCEID']].copy().sort_values('EVENT_TIMESTAMP')
        
        # Sørg for at tabellen kun viser HIF-aktioner frem til målet
        # Vi filtrerer modstandere fra med det samme
        hif_only_seq = active_seq[active_seq['EVENT_CONTESTANT_OPTAUUID'] == hif_team_id].copy().reset_index(drop=True)
        
        # Find målscorer og assist (sidste HIF-spiller før målet)
        # Vi leder efter '16' i hif_only_seq
        try:
            goal_idx_final = hif_only_seq[hif_only_seq['EVENT_TYPEID'] == 16].index[-1]
            goal_row = hif_only_seq.loc[goal_idx_final]
            
            assist_row_idx = -1
            for i in range(goal_idx_final - 1, -1, -1):
                if hif_only_seq.loc[i, 'PLAYER_NAME'] != goal_row['PLAYER_NAME']:
                    assist_row_idx = i
                    break
            
            scorer_disp = goal_row['PLAYER_NAME'].split()[-1]
            assist_disp = hif_only_seq.loc[assist_row_idx, 'PLAYER_NAME'].split()[-1] if assist_row_idx != -1 else "Solo"
        except:
            scorer_disp, assist_disp = "HIF", "Solo"

        # UI: Stats
        st.markdown(f"""
            <div class="stat-box-side">
                <div class="stat-label-side">Målscorer</div>
                <div class="stat-value-side"><span style="color:{HIF_RED};">●</span> {scorer_disp}</div>
            </div>
            <div class="stat-box-side" style="border-left-color: {ASSIST_BLUE}">
                <div class="stat-label-side">Assist / Sidst på bold</div>
                <div class="stat-value-side"><span style="color:{ASSIST_BLUE};">●</span> {assist_disp}</div>
            </div>
        """, unsafe_allow_html=True)
        
        # TABEL: Sorteret og oversat
        flow_data = []
        for i, r in hif_only_seq.iterrows():
            p_name = r['PLAYER_NAME'].split()[-1] if pd.notnull(r['PLAYER_NAME']) else "?"
            eid = str(int(r['EVENT_TYPEID']))
            
            # Navngivning fra mapping
            eng_name = get_event_name(eid)
            dan_name = DK_NAMES.get(eng_name, eng_name)
            
            if eid == "16": dan_name = "MÅL ⚽"
            
            flow_data.append({"Spiller": p_name, "Aktion": dan_name})
        
        st.dataframe(pd.DataFrame(flow_data), use_container_width=True, hide_index=True, height=350)

    with col_main:
        st.markdown(f'<div class="match-header">{sel_row.get("HOME_TEAM", "HVIDOVRE")} V {sel_row.get("AWAY_TEAM", "MODSTANDER")}</div>', unsafe_allow_html=True)
        
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 7))
        
        # Flip-logik (HIF angriber altid mod højre)
        should_flip = True if sel_row['RAW_X'] < 50 else False

        plot_points = []
        for i, r in hif_only_seq.iterrows():
            rx, ry = r['RAW_X'], r['RAW_Y']
            cx = (100 - rx if should_flip else rx)
            cy = (100 - ry if should_flip else ry)
            
            plot_points.append({
                'x': cx, 'y': cy,
                'name': r['PLAYER_NAME'].split()[-1] if pd.notnull(r['PLAYER_NAME']) else "",
                'is_goal': (r['EVENT_TYPEID'] == 16),
                'is_assist': (i == assist_row_idx)
            })

        # Tegn pile
        for i in range(1, len(plot_points)):
            p1, p2 = plot_points[i-1], plot_points[i]
            ax.annotate('', xy=(p2['x'], p2['y']), xytext=(p1['x'], p1['y']),
                        arrowprops=dict(arrowstyle='->', color='#cccccc', lw=2, alpha=0.6))

        # Tegn spillere
        for pt in plot_points:
            color = HIF_RED if pt['is_goal'] else (ASSIST_BLUE if pt['is_assist'] else '#999999')
            size = 250 if pt['is_goal'] else 150
            pitch.scatter(pt['x'], pt['y'], s=size, color=color, edgecolors='white', linewidth=2, ax=ax, zorder=5)
            ax.text(pt['x'], pt['y'] + 3, pt['name'], fontsize=10, ha='center', fontweight='bold')

        st.pyplot(fig)
