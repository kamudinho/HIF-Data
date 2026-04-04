import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.utils.mapping import OPTA_QUALIFIERS, OPTA_EVENT_TYPES
import requests
from PIL import Image
from io import BytesIO

# --- 1. KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o"

# --- 2. HJÆLPEFUNKTIONER ---

@st.cache_data(ttl=3600)
def get_logo_img(opta_uuid):
    url = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), None)
    if not url: return None
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except: return None

def build_team_map(df_matches):
    if df_matches.empty: return {}
    ids = pd.concat([df_matches['CONTESTANTHOME_OPTAUUID'], df_matches['CONTESTANTAWAY_OPTAUUID']]).unique()
    team_map = {}
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    for u_raw in ids:
        if pd.isna(u_raw): continue
        u_clean = str(u_raw).lower().strip().replace('t', '')
        matched_name = mapping_lookup.get(u_clean)
        if matched_name: team_map[matched_name] = u_raw
    return team_map

def draw_match_info_box(ax, scoring_team_logo, opp_team_logo, date_str, score_str, min_str):
    """Tegner mindre logoer og info på én linje i nederste venstre hjørne."""
    # Logo 1 (Mindre størrelse: 0.05)
    if scoring_team_logo:
        ax_l1 = ax.inset_axes([0.02, 0.07, 0.05, 0.05], transform=ax.transAxes)
        ax_l1.imshow(scoring_team_logo)
        ax_l1.axis('off')
    
    # "vs." tekst - rykket tættere på
    ax.text(0.08, 0.095, "vs.", transform=ax.transAxes, fontsize=8, fontweight='bold', va='center')
    
    # Logo 2 (Mindre størrelse: 0.05)
    if opp_team_logo:
        ax_l2 = ax.inset_axes([0.10, 0.07, 0.05, 0.05], transform=ax.transAxes)
        ax_l2.imshow(opp_team_logo)
        ax_l2.axis('off')
    
    # Info på én linje under logoerne
    full_info = f"{date_str}  |  Resultat: {score_str}  ({min_str}. min)"
    ax.text(0.02, 0.04, full_info, transform=ax.transAxes, fontsize=8, color='#555555', va='top', fontweight='medium')

# --- 3. HOVEDFUNKTION ---

def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn: return

    with st.spinner("Henter data..."):
        df_matches = conn.query(f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'")
        
        sql_seq = f"""
            WITH GoalEvents AS (
                SELECT MATCH_OPTAUUID, EVENT_TIMESTAMP, SEQUENCEID, EVENT_CONTESTANT_OPTAUUID
                FROM {DB}.OPTA_EVENTS WHERE EVENT_TYPEID = 16
                AND MATCH_OPTAUUID IN (SELECT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}')
            )
            SELECT e.*, ge.EVENT_CONTESTANT_OPTAUUID as GOAL_TEAM_ID, q.QUALIFIER_LIST
            FROM {DB}.OPTA_EVENTS e
            JOIN GoalEvents ge ON e.MATCH_OPTAUUID = ge.MATCH_OPTAUUID
            LEFT JOIN (SELECT EVENT_OPTAUUID, LISTAGG(QUALIFIER_QID, ',') AS QUALIFIER_LIST FROM {DB}.OPTA_QUALIFIERS GROUP BY 1) q 
            ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE e.EVENT_TIMESTAMP BETWEEN (ge.EVENT_TIMESTAMP - INTERVAL '20 seconds') AND ge.EVENT_TIMESTAMP
        """
        df_sequences = conn.query(sql_seq)
        
        # Hent data til Tab 1 (Events) og Tab 3 (Topspillere)
        sql_all = f"SELECT * FROM {DB}.OPTA_EVENTS WHERE MATCH_OPTAUUID IN (SELECT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}')"
        df_all_events = conn.query(sql_all)

    team_map = build_team_map(df_matches)
    col_spacer, col_hold = st.columns([3, 1])
    with col_hold:
        valgt_hold = st.selectbox("Vælg hold", sorted(list(team_map.keys())), index=0, label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]

    t1, t2, t3 = st.tabs(["EVENTS", "MÅL-SEKVENSER", "TOPSPILLERE"])

    # --- TAB 1: EVENTS ---
    with t1:
        df_t1 = df_all_events[df_all_events['EVENT_CONTESTANT_OPTAUUID'] == valgt_uuid].copy()
        if not df_t1.empty:
            event_summary = df_t1['EVENT_TYPEID'].astype(str).map(lambda x: OPTA_EVENT_TYPES.get(x, x)).value_counts().reset_index()
            event_summary.columns = ['Aktion', 'Antal']
            st.dataframe(event_summary, use_container_width=True, hide_index=True)

    # --- TAB 2: MÅL-SEKVENSER ---
    with t2:
        team_seq = df_sequences[df_sequences['GOAL_TEAM_ID'] == valgt_uuid].copy()
        if not team_seq.empty:
            team_seq = team_seq.merge(
                df_matches[['MATCH_OPTAUUID', 'MATCH_LOCALDATE', 'CONTESTANTHOME_NAME', 'CONTESTANTAWAY_NAME', 
                           'CONTESTANTHOME_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID', 'TOTAL_HOME_SCORE', 'TOTAL_AWAY_SCORE']], 
                on='MATCH_OPTAUUID', how='left'
            )

            goal_list = team_seq[team_seq['EVENT_TYPEID'] == 16].drop_duplicates('SEQUENCEID')
            goal_options = {}
            for _, row in goal_list.iterrows():
                is_h = row['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
                opp_name = row['CONTESTANTAWAY_NAME'] if is_h else row['CONTESTANTHOME_NAME']
                opp_uuid = row['CONTESTANTAWAY_OPTAUUID'] if is_h else row['CONTESTANTHOME_OPTAUUID']
                score = f"{int(row['TOTAL_HOME_SCORE'])}-{int(row['TOTAL_AWAY_SCORE'])}"
                date = pd.to_datetime(row['MATCH_LOCALDATE']).strftime('%d/%m/%Y')
                
                goal_options[row['SEQUENCEID']] = {
                    'label': f"Mål vs. {opp_name} ({row['EVENT_TIMEMIN']}. min)",
                    'opp_uuid': opp_uuid, 'date': date, 'score': score, 'min': row['EVENT_TIMEMIN']
                }

            col_t, col_v = st.columns([2, 1])
            sel_id = col_v.selectbox("Vælg", list(goal_options.keys()), format_func=lambda x: goal_options[x]['label'], label_visibility="collapsed")
            
            this_goal = team_seq[team_seq['SEQUENCEID'] == sel_id].sort_values('EVENT_TIMESTAMP')
            col_b, col_tab = st.columns([2.5, 1])

            with col_b:
                pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='grey')
                fig, ax = pitch.draw(figsize=(10, 7))
                
                # INFO BOKS
                draw_match_info_box(
                    ax, 
                    get_logo_img(valgt_uuid), 
                    get_logo_img(goal_options[sel_id]['opp_uuid']),
                    goal_options[sel_id]['date'],
                    goal_options[sel_id]['score'],
                    goal_options[sel_id]['min']
                )

                for i in range(len(this_goal)):
                    row = this_goal.iloc[i]
                    is_g = row['EVENT_TYPEID'] == 16
                    ax.scatter(row['EVENT_X'], row['EVENT_Y'], color='#cc0000' if is_g else 'red', 
                               s=180 if is_g else 70, marker='s' if is_g else 'o', edgecolors='black', zorder=10)
                    ax.text(row['EVENT_X'], row['EVENT_Y'] + 2.5, row['PLAYER_NAME'], fontsize=8, ha='center',
                            bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
                    if i < len(this_goal) - 1:
                        n = this_goal.iloc[i+1]
                        pitch.arrows(row['EVENT_X'], row['EVENT_Y'], n['EVENT_X'], n['EVENT_Y'], width=1.5, color='grey', ax=ax, alpha=0.3)
                st.pyplot(fig)

            with col_tab:
                st.dataframe(this_goal[['PLAYER_NAME', 'EVENT_TYPEID']].iloc[::-1].rename(columns={'PLAYER_NAME':'Spiller','EVENT_TYPEID':'Aktion'}), hide_index=True)

    # --- TAB 3: TOPSPILLERE ---
    with t3:
        if not df_all_events.empty:
            df_goals = df_all_events[(df_all_events['EVENT_TYPEID'] == 16) & (df_all_events['EVENT_CONTESTANT_OPTAUUID'] == valgt_uuid)]
            top_scorers = df_goals['PLAYER_NAME'].value_counts().reset_index()
            top_scorers.columns = ['Spiller', 'Mål']
            st.dataframe(top_scorers, use_container_width=True, hide_index=True)
