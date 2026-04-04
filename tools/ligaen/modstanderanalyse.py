import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS
from data.utils.mapping import OPTA_EVENT_TYPES
import requests
from PIL import Image
from io import BytesIO

# --- 1. KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o"
HVIDOVRE_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"

# --- 2. HJÆLPEFUNKTIONER ---
@st.cache_data(ttl=3600)
def get_logo_img(opta_uuid):
    url = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), None)
    if not url: return None
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except: return None

def draw_match_info_box(ax, scoring_team_logo, opp_team_logo, date_str, score_str, min_str):
    if scoring_team_logo:
        ax_l1 = ax.inset_axes([0.02, 0.08, 0.05, 0.05], transform=ax.transAxes)
        ax_l1.imshow(scoring_team_logo)
        ax_l1.axis('off')
    ax.text(0.08, 0.105, "vs.", transform=ax.transAxes, fontsize=8, fontweight='bold', va='center')
    if opp_team_logo:
        ax_l2 = ax.inset_axes([0.10, 0.08, 0.05, 0.05], transform=ax.transAxes)
        ax_l2.imshow(opp_team_logo)
        ax_l2.axis('off')
    full_info = f"{date_str} | Stilling: {score_str} ({min_str}. min)"
    ax.text(0.03, 0.07, full_info, transform=ax.transAxes, fontsize=8, color='#444444', va='top', fontweight='medium')

# --- 3. HOVEDFUNKTION ---
def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn: return

    with st.spinner("Analyserer mål-sekvenser (inkl. tacklinger før mål)..."):
        # 3.1 Find alle mål (inkl. selvmål via Qualifier 28)
        sql_goals = f"""
        SELECT 
            e.MATCH_OPTAUUID, e.EVENT_TIMESTAMP as GOAL_TIME, e.EVENT_CONTESTANT_OPTAUUID as SCORING_TEAM,
            e.EVENT_TIMEMIN as GOAL_MIN, m.CONTESTANTHOME_NAME, m.CONTESTANTAWAY_NAME,
            m.CONTESTANTHOME_OPTAUUID, m.CONTESTANTAWAY_OPTAUUID
        FROM {DB}.OPTA_EVENTS e
        JOIN {DB}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
        LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
        WHERE e.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        AND (e.EVENT_TYPEID = 16 OR q.QUALIFIER_QID = 28)
        """
        df_goals = conn.query(sql_goals)

        # 3.2 Hent alle hændelser der skete MAX 12 SEKUNDER før et mål
        # Dette fanger tacklinger der starter målet!
        sql_events = f"""
        WITH Goals AS ({sql_goals})
        SELECT 
            e.*, g.GOAL_TIME, g.SCORING_TEAM as GOAL_TEAM_ID, g.GOAL_MIN,
            g.CONTESTANTHOME_NAME, g.CONTESTANTAWAY_NAME, g.CONTESTANTHOME_OPTAUUID, g.CONTESTANTAWAY_OPTAUUID
        FROM {DB}.OPTA_EVENTS e
        JOIN Goals g ON e.MATCH_OPTAUUID = g.MATCH_OPTAUUID
        WHERE e.EVENT_TIMESTAMP >= DATEADD(second, -12, g.GOAL_TIME)
        AND e.EVENT_TIMESTAMP <= g.GOAL_TIME
        AND e.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        """
        df_all_events = conn.query(sql_events)

    # --- 4. UI ---
    # Mapping af hold
    ids = pd.concat([df_goals['CONTESTANTHOME_OPTAUUID'], df_goals['CONTESTANTAWAY_OPTAUUID']]).unique()
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    team_map = {mapping_lookup.get(str(u).lower().replace('t','')): u for u in ids if mapping_lookup.get(str(u).lower().replace('t',''))}

    col_spacer, col_hold = st.columns([3, 1])
    valgt_hold = col_hold.selectbox("Vælg hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]

    t1, t2, t3 = st.tabs(["EVENTS", "MÅL-SEKVENSER", "SPILLEROVERSIGT"])

    with t2:
        # Filtrer mål for det valgte hold
        this_team_goals = df_all_events[df_all_events['GOAL_TEAM_ID'] == valgt_uuid].copy()
        
        if not this_team_goals.empty:
            goal_list = this_team_goals.drop_duplicates(['MATCH_OPTAUUID', 'GOAL_TIME']).sort_values('GOAL_TIME', ascending=False)
            
            goal_options = {f"{row['MATCH_OPTAUUID']}_{row['GOAL_TIME']}": {
                'label': f"vs. {row['CONTESTANTAWAY_NAME'] if row['CONTESTANTHOME_OPTAUUID']==valgt_uuid else row['CONTESTANTHOME_NAME']} ({row['GOAL_MIN']}. min)",
                'match_id': row['MATCH_OPTAUUID'],
                'goal_ts': row['GOAL_TIME'],
                'opp_uuid': row['CONTESTANTAWAY_OPTAUUID'] if row['CONTESTANTHOME_OPTAUUID']==valgt_uuid else row['CONTESTANTHOME_OPTAUUID'],
                'min': row['GOAL_MIN']
            } for _, row in goal_list.iterrows()}

            sel_key = st.selectbox("Vælg mål", list(goal_options.keys()), format_func=lambda x: goal_options[x]['label'])
            sel_data = goal_options[sel_key]

            # Vis hændelser (Tacklinger, Interceptions, Pasninger)
            this_goal_events = this_team_goals[
                (this_team_goals['MATCH_OPTAUUID'] == sel_data['match_id']) & 
                (this_team_goals['GOAL_TIME'] == sel_data['goal_ts'])
            ].sort_values('EVENT_TIMESTAMP')

            col_pitch, col_list = st.columns([2.5, 1])
            
            with col_pitch:
                pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='grey')
                fig, ax = pitch.draw(figsize=(10, 7))
                
                for i, row in this_goal_events.iterrows():
                    # Farvekode: Mål=Guld, Tackling/Interception=Blå, Pasning=Rød
                    color = 'gold' if row['EVENT_TYPEID'] == 16 else ('#0000FF' if row['EVENT_TYPEID'] in [7, 127] else '#cc0000')
                    size = 200 if row['EVENT_TYPEID'] == 16 else 80
                    
                    ax.scatter(row['EVENT_X'], row['EVENT_Y'], color=color, s=size, edgecolors='black', zorder=10)
                    ax.text(row['EVENT_X'], row['EVENT_Y'] + 2, row['PLAYER_NAME'], fontsize=7, ha='center', bbox=dict(facecolor='white', alpha=0.6, edgecolor='none'))

                st.pyplot(fig)

            with col_list:
                this_goal_events['Aktion'] = this_goal_events['EVENT_TYPEID'].astype(str).map(OPTA_EVENT_TYPES)
                st.write("**Aktioner før mål:**")
                st.dataframe(this_goal_events[['PLAYER_NAME', 'Aktion']].iloc[::-1], hide_index=True)

    with t3:
        # Statistik baseret på de hændelser vi har fundet 12 sekunder før mål
        stats = this_team_goals.groupby('PLAYER_NAME').agg({
            'EVENT_TYPEID': [
                lambda x: (x == 16).sum(), # Mål
                lambda x: (x == 7).sum(),  # Tacklinger
                lambda x: (x == 127).sum(), # Interceptions
                lambda x: (x == 1).sum()    # Opbygningspasninger
            ]
        })
        stats.columns = ['Mål', 'Tacklinger før mål', 'Interceptions før mål', 'Pasninger i mål-sekvens']
        st.dataframe(stats.sort_values('Mål', ascending=False))

if __name__ == "__main__":
    vis_side()
