import streamlit as st
import pandas as pd
from mplsoccer import Pitch
import matplotlib.pyplot as plt

# Sikker import fra din mappings-fil
try:
    from data.utils.mappings import OPTA_EVENT_TYPES, get_event_name
except:
    def get_event_name(eid): return f"Aktion {eid}"

# HIF Design
HIF_RED = '#cc0000'
ASSIST_BLUE = '#1e90ff'

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

    df_raw = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame())
    if df_raw.empty:
        st.warning("Ingen Opta-data tilgængelig.")
        return

    # 1. Præ-processering: Sørg for tal og tid er korrekte før sortering
    df = df_raw.copy()
    df['RAW_X'] = pd.to_numeric(df['RAW_X'], errors='coerce')
    df['RAW_Y'] = pd.to_numeric(df['RAW_Y'], errors='coerce')
    df['EVENT_TIMESTAMP'] = pd.to_datetime(df['EVENT_TIMESTAMP'])
    # Sorter benhårdt på tid og derefter rækkefølge-ID
    df = df.sort_values(['EVENT_TIMESTAMP', 'EVENT_EVENTID']).reset_index(drop=True)

    # 2. Identificer alle mål (Event 16)
    goals = df[df['EVENT_TYPEID'] == 16].copy()
    if goals.empty:
        st.info("Ingen mål i denne kørsel.")
        return
    
    goals['LABEL'] = goals.apply(lambda x: f"{x['EVENT_TIMEMIN']}'. min: {x['PLAYER_NAME']}", axis=1)
    
    col_main, col_side = st.columns([2.5, 1])

    with col_side:
        selected_label = st.selectbox("Vælg mål", options=goals['LABEL'].unique(), label_visibility="collapsed")
        # Find præcis den række der matcher det valgte mål
        goal_row = goals[goals['LABEL'] == selected_label].iloc[0]
        hif_team_id = goal_row['EVENT_CONTESTANT_OPTAUUID']
        
        # 3. Hent den fulde sekvens for dette mål
        active_seq = df[df['SEQUENCEID'] == goal_row['SEQUENCEID']].copy()
        
        # 4. Filtrer til KUN HIF og fjern alt EFTER målet (hvis der skulle være støj)
        # Vi finder målets placering i den sorterede sekvens
        goal_timestamp = goal_row['EVENT_TIMESTAMP']
        hif_seq = active_seq[
            (active_seq['EVENT_CONTESTANT_OPTAUUID'] == hif_team_id) & 
            (active_seq['EVENT_TIMESTAMP'] <= goal_timestamp)
        ].copy().reset_index(drop=True)

        # 5. Definer målscorer og assist (sidste to spillere i den filtrerede liste)
        scorer_name = "HIF"
        assist_name = "Solo"
        assist_idx = -1
        
        if not hif_seq.empty:
            # Den sidste række i hif_seq ER målet
            final_goal_row = hif_seq.iloc[-1]
            scorer_name = final_goal_row['PLAYER_NAME'].split()[-1] if pd.notnull(final_goal_row['PLAYER_NAME']) else "HIF"
            
            # Find den sidste spiller der IKKE er målscoreren
            for i in range(len(hif_seq) - 2, -1, -1):
                if hif_seq.loc[i, 'PLAYER_NAME'] != final_goal_row['PLAYER_NAME']:
                    assist_name = hif_seq.loc[i, 'PLAYER_NAME'].split()[-1]
                    assist_idx = i
                    break

        # UI: Stats Bokse
        st.markdown(f"""
            <div class="stat-box-side">
                <div class="stat-label-side">Målscorer</div>
                <div class="stat-value-side"><span style="color:{HIF_RED};">●</span> {scorer_name}</div>
            </div>
            <div class="stat-box-side" style="border-left-color: {ASSIST_BLUE}">
                <div class="stat-label-side">Assist / Sidst på bold</div>
                <div class="stat-value-side"><span style="color:{ASSIST_BLUE};">●</span> {assist_name}</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Tabel: Viser kun HIF kronologisk
        flow_table = []
        for _, r in hif_seq.iterrows():
            p = r['PLAYER_NAME'].split()[-1] if pd.notnull(r['PLAYER_NAME']) else "?"
            ename = get_event_name(str(int(r['EVENT_TYPEID'])))
            flow_table.append({
                "Spiller": p,
                "Aktion": DK_NAMES.get(ename, ename) if r['EVENT_TYPEID'] != 16 else "MÅL ⚽"
            })
        st.dataframe(pd.DataFrame(flow_table), use_container_width=True, hide_index=True, height=300)

    with col_main:
        st.markdown(f'<div class="match-header">{goal_row.get("HOME_TEAM", "HVIDOVRE")} V {goal_row.get("AWAY_TEAM", "MODSTANDER")}</div>', unsafe_allow_html=True)
        
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 7))
        
        # HIF angriber altid mod højre
        should_flip = True if goal_row['RAW_X'] < 50 else False

        plot_data = []
        for i, r in hif_seq.iterrows():
            rx, ry = r['RAW_X'], r['RAW_Y']
            cx = (100 - rx if should_flip else rx)
            cy = (100 - ry if should_flip else ry)
            
            plot_data.append({
                'x': cx, 'y': cy,
                'name': r['PLAYER_NAME'].split()[-1] if pd.notnull(r['PLAYER_NAME']) else "",
                'is_goal': (r['EVENT_TYPEID'] == 16),
                'is_assist': (i == assist_idx)
            })

        # Pile og Punkter
        for i in range(1, len(plot_data)):
            p1, p2 = plot_data[i-1], plot_data[i]
            ax.annotate('', xy=(p2['x'], p2['y']), xytext=(p1['x'], p1['y']),
                        arrowprops=dict(arrowstyle='->', color='#cccccc', lw=2, alpha=0.6))

        for pt in plot_data:
            color = HIF_RED if pt['is_goal'] else (ASSIST_BLUE if pt['is_assist'] else '#999999')
            z = 10 if pt['is_goal'] else 5
            pitch.scatter(pt['x'], pt['y'], s=200 if pt['is_goal'] else 120, color=color, edgecolors='white', ax=ax, zorder=z)
            ax.text(pt['x'], pt['y'] + 3, pt['name'], fontsize=10, ha='center', fontweight='bold')

        st.pyplot(fig)
