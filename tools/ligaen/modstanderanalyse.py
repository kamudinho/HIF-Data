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
        # Timeout tilføjet for stabilitet
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
    """Tegner små logoer og beregnet stilling."""
    if scoring_team_logo:
        ax_l1 = ax.inset_axes([0.02, 0.08, 0.05, 0.05], transform=ax.transAxes)
        ax_l1.imshow(scoring_team_logo)
        ax_l1.axis('off')
    
    ax.text(0.08, 0.105, "vs.", transform=ax.transAxes, fontsize=8, fontweight='bold', va='center')
    
    if opp_team_logo:
        ax_l2 = ax.inset_axes([0.10, 0.08, 0.05, 0.05], transform=ax.transAxes)
        ax_l2.imshow(opp_team_logo)
        ax_l2.axis('off')
    
    # Tekstlinjen er rykket op som ønsket
    full_info = f"{date_str}  |  Stilling: {score_str}  ({min_str}. min)"
    ax.text(0.03, 0.07, full_info, transform=ax.transAxes, fontsize=8, color='#444444', va='top', fontweight='medium')

# --- 3. HOVEDFUNKTION ---

def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn: return

    with st.spinner("Henter data..."):
        df_matches = conn.query(f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'")
        
        # Henter alle events for ligaen for at kunne beregne stillinger
        sql_all = f"SELECT * FROM {DB}.OPTA_EVENTS WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"
        df_all_events = conn.query(sql_all)
        
        # Filtrer målsekvenser (20 sek før mål)
        goal_events_base = df_all_events[df_all_events['EVENT_TYPEID'] == 16].copy()
        
        # Vi joiner sekvens-data manuelt i Python for bedre kontrol over logikken
        df_sequences = []
        for _, goal in goal_events_base.iterrows():
            mask = (df_all_events['MATCH_OPTAUUID'] == goal['MATCH_OPTAUUID']) & \
                   (df_all_events['EVENT_TIMESTAMP'] <= goal['EVENT_TIMESTAMP']) & \
                   (df_all_events['EVENT_TIMESTAMP'] >= (goal['EVENT_TIMESTAMP'] - pd.Timedelta(seconds=20)))
            seq = df_all_events[mask].copy()
            seq['GOAL_TEAM_ID'] = goal['EVENT_CONTESTANT_OPTAUUID']
            seq['SEQUENCE_GOAL_TIMESTAMP'] = goal['EVENT_TIMESTAMP']
            df_sequences.append(seq)
        
        df_sequences = pd.concat(df_sequences) if df_sequences else pd.DataFrame()

    team_map = build_team_map(df_matches)
    col_spacer, col_hold = st.columns([3, 1])
    with col_hold:
        valgt_hold = st.selectbox("Vælg hold", sorted(list(team_map.keys())), index=0, label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]

    t1, t2, t3 = st.tabs(["EVENTS", "MÅL-SEKVENSER", "TOPSPILLERE"])

    with t2:
        team_seq_all = df_sequences[df_sequences['GOAL_TEAM_ID'] == valgt_uuid].copy()
        if not team_seq_all.empty:
            team_seq_all = team_seq_all.merge(
                df_matches[['MATCH_OPTAUUID', 'MATCH_LOCALDATE', 'CONTESTANTHOME_NAME', 'CONTESTANTAWAY_NAME', 
                           'CONTESTANTHOME_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID']], 
                on='MATCH_OPTAUUID', how='left'
            )

            # Find unikke mål baseret på timestamp
            goal_list = team_seq_all[team_seq_all['EVENT_TYPEID'] == 16].drop_duplicates('SEQUENCE_GOAL_TIMESTAMP')
            
            goal_options = {}
            for _, row in goal_list.iterrows():
                # BEREGNING AF STILLING PÅ TIDSPUNKTET
                m_id = row['MATCH_OPTAUUID']
                g_time = row['SEQUENCE_GOAL_TIMESTAMP']
                h_uuid = row['CONTESTANTHOME_OPTAUUID']
                a_uuid = row['CONTESTANTAWAY_OPTAUUID']
                
                # Tæl alle mål i kampen op til (og med) dette mål
                prev_goals = df_all_events[(df_all_events['MATCH_OPTAUUID'] == m_id) & 
                                           (df_all_events['EVENT_TYPEID'] == 16) & 
                                           (df_all_events['EVENT_TIMESTAMP'] <= g_time)]
                
                h_score = len(prev_goals[prev_goals['EVENT_CONTESTANT_OPTAUUID'] == h_uuid])
                a_score = len(prev_goals[prev_goals['EVENT_CONTESTANT_OPTAUUID'] == a_uuid])
                
                is_h = h_uuid == valgt_uuid
                opp_name = row['CONTESTANTAWAY_NAME'] if is_h else row['CONTESTANTHOME_NAME']
                opp_uuid = row['CONTESTANTAWAY_OPTAUUID'] if is_h else row['CONTESTANTHOME_OPTAUUID']
                
                date = pd.to_datetime(row['MATCH_LOCALDATE']).strftime('%d/%m/%Y')
                
                goal_options[g_time] = {
                    'label': f"Mål vs. {opp_name} ({row['EVENT_TIMEMIN']}. min)",
                    'opp_uuid': opp_uuid, 
                    'date': date, 
                    'score': f"{h_score}-{a_score}", 
                    'min': row['EVENT_TIMEMIN']
                }

            col_t, col_v = st.columns([2, 1])
            sel_ts = col_v.selectbox("Vælg", list(goal_options.keys()), 
                                    format_func=lambda x: goal_options[x]['label'], label_visibility="collapsed")
            
            this_goal = team_seq_all[team_seq_all['SEQUENCE_GOAL_TIMESTAMP'] == sel_ts].sort_values('EVENT_TIMESTAMP')
            col_b, col_tab = st.columns([2.5, 1])

            with col_b:
                pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='grey')
                fig, ax = pitch.draw(figsize=(10, 7))
                
                draw_match_info_box(
                    ax, 
                    get_logo_img(valgt_uuid), 
                    get_logo_img(goal_options[sel_ts]['opp_uuid']),
                    goal_options[sel_ts]['date'],
                    goal_options[sel_ts]['score'],
                    goal_options[sel_ts]['min']
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
                        pitch.arrows(row['EVENT_X'], row['EVENT_Y'], n['EVENT_X'], n['EVENT_Y'], 
                                     width=1.5, color='grey', ax=ax, alpha=0.3, zorder=5)
                st.pyplot(fig)

            with col_tab:
                st.dataframe(this_goal[['PLAYER_NAME', 'EVENT_TYPEID']].iloc[::-1].rename(columns={'PLAYER_NAME':'Spiller','EVENT_TYPEID':'Aktion'}), hide_index=True)
