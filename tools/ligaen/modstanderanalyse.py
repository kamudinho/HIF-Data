import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS
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
    """Tegner logoer og den korrekte beregnede stilling."""
    if scoring_team_logo:
        ax_l1 = ax.inset_axes([0.02, 0.08, 0.05, 0.05], transform=ax.transAxes)
        ax_l1.imshow(scoring_team_logo)
        ax_l1.axis('off')
    
    ax.text(0.08, 0.105, "vs.", transform=ax.transAxes, fontsize=8, fontweight='bold', va='center')
    
    if opp_team_logo:
        ax_l2 = ax.inset_axes([0.10, 0.08, 0.05, 0.05], transform=ax.transAxes)
        ax_l2.imshow(opp_team_logo)
        ax_l2.axis('off')
    
    full_info = f"{date_str}  |  Stilling: {score_str}  ({min_str}. min)"
    ax.text(0.03, 0.07, full_info, transform=ax.transAxes, fontsize=8, color='#444444', va='top', fontweight='medium')

# --- 3. HOVEDFUNKTION ---

def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn: return

    with st.spinner("Henter data..."):
        df_matches = conn.query(f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'")
        
        # SQL der beregner stilling korrekt per mål-event
        sql_smart = f"""
        WITH GoalEvents AS (
            SELECT 
                MATCH_OPTAUUID, 
                EVENT_TIMESTAMP, 
                EVENT_CONTESTANT_OPTAUUID,
                EVENT_TIMEMIN,
                EVENT_TYPEID,
                -- Her tæller vi mål kronologisk per kamp for det specifikke hold
                SUM(CASE WHEN EVENT_TYPEID = 16 THEN 1 ELSE 0 END) 
                    OVER (PARTITION BY MATCH_OPTAUUID, EVENT_CONTESTANT_OPTAUUID ORDER BY EVENT_TIMESTAMP, EVENT_EVENTID) as TEAM_SCORE_AT_TIME
            FROM {DB}.OPTA_EVENTS 
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        ),
        GoalDetails AS (
            SELECT 
                g.MATCH_OPTAUUID, 
                g.EVENT_TIMESTAMP as GOAL_TIME,
                g.EVENT_CONTESTANT_OPTAUUID as SCORING_TEAM,
                g.EVENT_TIMEMIN,
                m.CONTESTANTHOME_OPTAUUID,
                m.CONTESTANTAWAY_OPTAUUID,
                -- Find hjemmeholdets score på dette tidspunkt
                COALESCE((SELECT MAX(g2.TEAM_SCORE_AT_TIME) FROM GoalEvents g2 WHERE g2.MATCH_OPTAUUID = g.MATCH_OPTAUUID AND g2.EVENT_CONTESTANT_OPTAUUID = m.CONTESTANTHOME_OPTAUUID AND g2.EVENT_TIMESTAMP <= g.EVENT_TIMESTAMP), 0) as HOME_SCORE,
                -- Find udeholdets score på dette tidspunkt
                COALESCE((SELECT MAX(g3.TEAM_SCORE_AT_TIME) FROM GoalEvents g3 WHERE g3.MATCH_OPTAUUID = g.MATCH_OPTAUUID AND g3.EVENT_CONTESTANT_OPTAUUID = m.CONTESTANTAWAY_OPTAUUID AND g3.EVENT_TIMESTAMP <= g.EVENT_TIMESTAMP), 0) as AWAY_SCORE
            FROM GoalEvents g
            JOIN {DB}.OPTA_MATCHINFO m ON g.MATCH_OPTAUUID = m.MATCH_OPTAUUID
            WHERE g.EVENT_TYPEID = 16
        )
        SELECT 
            e.*, 
            gd.HOME_SCORE, 
            gd.AWAY_SCORE, 
            gd.GOAL_TIME, 
            gd.SCORING_TEAM as GOAL_TEAM_ID
        FROM {DB}.OPTA_EVENTS e
        JOIN GoalDetails gd ON e.MATCH_OPTAUUID = gd.MATCH_OPTAUUID
        WHERE e.EVENT_TIMESTAMP BETWEEN (gd.GOAL_TIME - INTERVAL '20 seconds') AND gd.GOAL_TIME
        """
        df_sequences = conn.query(sql_smart)
        
        # Data til topspillere (Tab 3)
        df_top_scorers_raw = conn.query(f"SELECT PLAYER_NAME, EVENT_CONTESTANT_OPTAUUID FROM {DB}.OPTA_EVENTS WHERE EVENT_TYPEID = 16 AND TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'")

    team_map = build_team_map(df_matches)
    col_spacer, col_hold = st.columns([3, 1])
    with col_hold:
        valgt_hold = st.selectbox("Vælg hold", sorted(list(team_map.keys())), index=0, label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]

    t1, t2, t3 = st.tabs(["EVENTS", "MÅL-SEKVENSER", "TOPSPILLERE"])

    with t2:
        team_seq = df_sequences[df_sequences['GOAL_TEAM_ID'] == valgt_uuid].copy()
        if not team_seq.empty:
            team_seq = team_seq.merge(
                df_matches[['MATCH_OPTAUUID', 'MATCH_LOCALDATE', 'CONTESTANTHOME_NAME', 'CONTESTANTAWAY_NAME', 
                           'CONTESTANTHOME_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID']], 
                on='MATCH_OPTAUUID', how='left'
            )

            # Grupper efter det unikke mål-tidspunkt
            goal_list = team_seq[team_seq['EVENT_TYPEID'] == 16].drop_duplicates('GOAL_TIME')
            goal_options = {}
            for _, row in goal_list.iterrows():
                is_h = row['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
                opp_name = row['CONTESTANTAWAY_NAME'] if is_h else row['CONTESTANTHOME_NAME']
                opp_uuid = row['CONTESTANTAWAY_OPTAUUID'] if is_h else row['CONTESTANTHOME_OPTAUUID']
                score = f"{int(row['HOME_SCORE'])}-{int(row['AWAY_SCORE'])}"
                date = pd.to_datetime(row['MATCH_LOCALDATE']).strftime('%d/%m/%Y')
                
                goal_options[row['GOAL_TIME']] = {
                    'label': f"Mål vs. {opp_name} ({row['EVENT_TIMEMIN']}. min)",
                    'opp_uuid': opp_uuid, 'date': date, 'score': score, 'min': row['EVENT_TIMEMIN']
                }

            col_t, col_v = st.columns([2, 1])
            sel_ts = col_v.selectbox("Vælg mål", list(goal_options.keys()), format_func=lambda x: goal_options[x]['label'], label_visibility="collapsed")
            
            this_goal = team_seq[team_seq['GOAL_TIME'] == sel_ts].sort_values('EVENT_TIMESTAMP')
            col_b, col_tab = st.columns([2.5, 1])

            with col_b:
                pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='grey')
                fig, ax = pitch.draw(figsize=(10, 7))
                draw_match_info_box(ax, get_logo_img(valgt_uuid), get_logo_img(goal_options[sel_ts]['opp_uuid']),
                                   goal_options[sel_ts]['date'], goal_options[sel_ts]['score'], goal_options[sel_ts]['min'])

                for i in range(len(this_goal)):
                    row = this_goal.iloc[i]
                    is_g = row['EVENT_TYPEID'] == 16
                    ax.scatter(row['EVENT_X'], row['EVENT_Y'], color='#cc0000' if is_g else 'red', 
                               s=180 if is_g else 70, marker='s' if is_g else 'o', edgecolors='black', zorder=10)
                    ax.text(row['EVENT_X'], row['EVENT_Y'] + 2.5, row['PLAYER_NAME'], fontsize=8, ha='center',
                            bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
                    if i < len(this_goal) - 1:
                        n = this_goal.iloc[i+1]
                        pitch.arrows(row['EVENT_X'], row['EVENT_Y'], n['EVENT_X'], n['EVENT_Y'], width=1.2, color='grey', ax=ax, alpha=0.3)
                st.pyplot(fig)

            with col_tab:
                st.dataframe(this_goal[['PLAYER_NAME', 'EVENT_TYPEID']].iloc[::-1].rename(columns={'PLAYER_NAME':'Spiller','EVENT_TYPEID':'Aktion'}), hide_index=True)

    with t3:
        # Genindsat Tab 3 funktionalitet
        df_goals = df_top_scorers_raw[df_top_scorers_raw['EVENT_CONTESTANT_OPTAUUID'] == valgt_uuid]
        if not df_goals.empty:
            top_scorers = df_goals['PLAYER_NAME'].value_counts().reset_index()
            top_scorers.columns = ['Spiller', 'Mål']
            st.dataframe(top_scorers, use_container_width=True, hide_index=True)
