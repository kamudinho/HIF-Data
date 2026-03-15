import streamlit as st
import pandas as pd
from mplsoccer import Pitch
import matplotlib.pyplot as plt

# Importér fra din mapping-fil
try:
    from data.utils.mappings import OPTA_EVENT_TYPES, get_event_name
except:
    def get_event_name(eid): return f"Aktion {eid}"

HIF_RED = '#cc0000'
ASSIST_BLUE = '#1e90ff'
# Din COMP_MAP værdier fra instruktioner (Hvidovre app)
HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy' 

DK_NAMES = {
    "Pass": "Aflevering", "Ball recovery": "Opsamling", "Goal": "MÅL",
    "Clearance": "Clearing", "Tackle": "Tackling", "Attempt Saved": "Blokeret skud",
    "Foul": "Frispark", "Out": "Bold ud", "Corner": "Hjørnespark", "Throw-in": "Indkast"
}

def vis_side(dp):
    # Hent data fra din specifikke query 'opta_sequence_map'
    df_raw = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame())
    
    if df_raw.empty:
        st.warning("Ingen sekvensdata fundet i databasen.")
        return

    # 1. Datarens og benhård sortering
    df = df_raw.copy()
    df['EVENT_TIMESTAMP'] = pd.to_datetime(df['EVENT_TIMESTAMP'])
    df['RAW_X'] = pd.to_numeric(df['RAW_X'], errors='coerce')
    df['RAW_Y'] = pd.to_numeric(df['RAW_Y'], errors='coerce')
    
    # Sorter efter tid, så flowet i tabellen passer
    df = df.sort_values('EVENT_TIMESTAMP').reset_index(drop=True)

    # 2. Find de unikke mål baseret på din GOAL_REF_ID (SEQUENCEID i SQL)
    # Vi tager kun de rækker, hvor selve målet sker (Type 16)
    goals = df[df['EVENT_TYPEID'] == 16].copy()
    
    if goals.empty:
        st.info("Ingen mål (Type 16) fundet i datasættet.")
        return

    # Lav en label til selectbox
    goals['LABEL'] = goals.apply(lambda x: f"{x['EVENT_TIMEMIN']}'. min: {x['PLAYER_NAME']}", axis=1)
    
    col_main, col_side = st.columns([2.5, 1.2])

    with col_side:
        selected_label = st.selectbox("Vælg scoring", options=goals['LABEL'].unique(), label_visibility="collapsed")
        
        # FIND DET SPECIFIKKE MÅL
        # Vi filtrerer på LABEL og tager den første (hvis der er dubletter)
        target_goal = goals[goals['LABEL'] == selected_label].iloc[0]
        
        # VIGTIGT: Vi isolerer nu sekvensen til kun at være hændelser knyttet til DETTE mål-ID
        # Dette løser fejlen fra din SQL JOIN
        active_seq = df[df['SEQUENCEID'] == target_goal['SEQUENCEID']].copy()
        
        # Identificer HIF's ID fra målscoreren
        hif_team_id = target_goal['EVENT_CONTESTANT_OPTAUUID']
        
        # Filtrer modstandere fra og behold kun kronologisk rækkefølge op til målet
        hif_seq = active_seq[active_seq['EVENT_CONTESTANT_OPTAUUID'] == hif_team_id].copy()
        hif_seq = hif_seq[hif_seq['EVENT_TIMESTAMP'] <= target_goal['EVENT_TIMESTAMP']]

        # Find assist (sidste HIF spiller før målscorer)
        scorer_name = target_goal['PLAYER_NAME'].split()[-1] if pd.notnull(target_goal['PLAYER_NAME']) else "HIF"
        assist_name = "Solo"
        assist_idx = -1
        
        # Vi leder baglæns fra målet i den filtrerede liste
        for i in range(len(hif_seq) - 2, -1, -1):
            row = hif_seq.iloc[i]
            if row['PLAYER_NAME'] != target_goal['PLAYER_NAME']:
                assist_name = row['PLAYER_NAME'].split()[-1]
                assist_idx = hif_seq.index[i]
                break

        # UI: Stats
        st.markdown(f"""
            <div style="background:#f8f9fa; padding:10px; border-left:5px solid {HIF_RED}; border-radius:5px; margin-bottom:10px;">
                <small style="color:#666; font-weight:bold; text-transform:uppercase;">Målscorer</small><br>
                <b style="font-size:1.2rem;">{scorer_name}</b>
            </div>
            <div style="background:#f8f9fa; padding:10px; border-left:5px solid {ASSIST_BLUE}; border-radius:5px; margin-bottom:10px;">
                <small style="color:#666; font-weight:bold; text-transform:uppercase;">Assist / Sidst på bold</small><br>
                <b style="font-size:1.2rem;">{assist_name}</b>
            </div>
        """, unsafe_allow_html=True)

        # TABEL: Nu 100% synkroniseret
        flow_list = []
        for idx, r in hif_seq.iterrows():
            p = r['PLAYER_NAME'].split()[-1] if pd.notnull(r['PLAYER_NAME']) else "?"
            ename = get_event_name(str(int(r['EVENT_TYPEID'])))
            disp_name = DK_NAMES.get(ename, ename)
            if r['EVENT_TYPEID'] == 16: disp_name = "MÅL ⚽"
            
            flow_list.append({"Spiller": p, "Aktion": disp_name})
            
        st.dataframe(pd.DataFrame(flow_list), use_container_width=True, hide_index=True, height=300)

    with col_main:
        # Overskrift med holdnavne fra din SQL
        st.subheader(f"{target_goal['HOME_TEAM']} {int(target_goal['HOME_SCORE'])} - {int(target_goal['AWAY_SCORE'])} {target_goal['AWAY_TEAM']}")
        
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 7))
        
        # Retning: Hvis HIF scorer i venstre side (x < 50), flip banen
        should_flip = True if target_goal['RAW_X'] < 50 else False

        plot_points = []
        for idx, r in hif_seq.iterrows():
            rx, ry = r['RAW_X'], r['RAW_Y']
            cx = (100 - rx if should_flip else rx)
            cy = (100 - ry if should_flip else ry)
            
            plot_points.append({
                'x': cx, 'y': cy,
                'name': r['PLAYER_NAME'].split()[-1] if pd.notnull(r['PLAYER_NAME']) else "",
                'is_goal': (r['EVENT_TYPEID'] == 16),
                'is_assist': (idx == assist_idx)
            })

        # Tegn pile
        for i in range(1, len(plot_points)):
            p1, p2 = plot_points[i-1], plot_points[i]
            ax.annotate('', xy=(p2['x'], p2['y']), xytext=(p1['x'], p1['y']),
                        arrowprops=dict(arrowstyle='->', color='#cccccc', lw=2, alpha=0.5))

        # Tegn spillere
        for pt in plot_points:
            color = HIF_RED if pt['is_goal'] else (ASSIST_BLUE if pt['is_assist'] else '#999999')
            pitch.scatter(pt['x'], pt['y'], s=150, color=color, edgecolors='white', ax=ax, zorder=5)
            ax.text(pt['x'], pt['y'] + 3, pt['name'], fontsize=9, ha='center', fontweight='bold')

        st.pyplot(fig)
