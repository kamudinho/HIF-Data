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
    """Henter klublogo baseret på Opta UUID."""
    url = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), None)
    if not url: return None
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except: return None

def draw_match_info_box(ax, scoring_team_logo, opp_team_logo, date_str, score_str, min_str):
    """Tegner infoboksen under banen med logoer, dato og stilling."""
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

    with st.spinner("Henter og analyserer målsekvenser..."):
        # Hent generel kampinfo
        df_matches = conn.query(f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'")
        
        # SQL: Beregner live-stilling og henter events koblet på PossessionID
        sql_clean = f"""
        WITH GoalEvents AS (
            SELECT 
                MATCH_OPTAUUID, EVENT_TIMESTAMP, EVENT_CONTESTANT_OPTAUUID, EVENT_TIMEMIN, EVENT_TYPEID, POSSESSIONID, EVENT_EVENTID,
                SUM(CASE WHEN EVENT_TYPEID = 16 THEN 1 ELSE 0 END) 
                    OVER (PARTITION BY MATCH_OPTAUUID, EVENT_CONTESTANT_OPTAUUID ORDER BY EVENT_TIMESTAMP, EVENT_EVENTID) as TEAM_SCORE_AT_TIME
            FROM {DB}.OPTA_EVENTS 
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        ),
        GoalList AS (
            SELECT 
                g.MATCH_OPTAUUID, g.EVENT_TIMESTAMP as GOAL_TIME, g.EVENT_CONTESTANT_OPTAUUID as SCORING_TEAM,
                g.EVENT_TIMEMIN, g.POSSESSIONID, m.CONTESTANTHOME_OPTAUUID, m.CONTESTANTAWAY_OPTAUUID,
                COALESCE((SELECT MAX(g2.TEAM_SCORE_AT_TIME) FROM GoalEvents g2 WHERE g2.MATCH_OPTAUUID = g.MATCH_OPTAUUID AND g2.EVENT_CONTESTANT_OPTAUUID = m.CONTESTANTHOME_OPTAUUID AND g2.EVENT_TIMESTAMP <= g.EVENT_TIMESTAMP), 0) as H_SCORE,
                COALESCE((SELECT MAX(g3.TEAM_SCORE_AT_TIME) FROM GoalEvents g3 WHERE g3.MATCH_OPTAUUID = g.MATCH_OPTAUUID AND g3.EVENT_CONTESTANT_OPTAUUID = m.CONTESTANTAWAY_OPTAUUID AND g3.EVENT_TIMESTAMP <= g.EVENT_TIMESTAMP), 0) as A_SCORE
            FROM GoalEvents g
            JOIN {DB}.OPTA_MATCHINFO m ON g.MATCH_OPTAUUID = m.MATCH_OPTAUUID
            WHERE g.EVENT_TYPEID = 16
        )
        SELECT 
            e.*, gl.H_SCORE, gl.A_SCORE, gl.GOAL_TIME, gl.SCORING_TEAM as GOAL_TEAM_ID
        FROM {DB}.OPTA_EVENTS e
        JOIN GoalList gl ON e.MATCH_OPTAUUID = gl.MATCH_OPTAUUID 
            AND e.POSSESSIONID = gl.POSSESSIONID
        WHERE e.EVENT_TIMESTAMP <= gl.GOAL_TIME
        """
        df_sequences = conn.query(sql_clean)

    # Team Mapping
    ids = pd.concat([df_matches['CONTESTANTHOME_OPTAUUID'], df_matches['CONTESTANTAWAY_OPTAUUID']]).unique()
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    team_map = {mapping_lookup.get(str(u).lower().replace('t','')): u for u in ids if mapping_lookup.get(str(u).lower().replace('t',''))}

    # Holdvælger
    col_spacer, col_hold = st.columns([3, 1])
    valgt_hold = col_hold.selectbox("Vælg hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]

    t1, t2, t3 = st.tabs(["EVENTS", "MÅL-SEKVENSER", "TOPSPILLERE"])

    with t2:
        # Filtrer sekvenser for det valgte hold
        team_seq = df_sequences[df_sequences['GOAL_TEAM_ID'] == valgt_uuid].copy()
        
        if not team_seq.empty:
            # Sørg for korrekt dato-format til sortering
            df_matches['MATCH_LOCALDATE'] = pd.to_datetime(df_matches['MATCH_LOCALDATE'])
            
            team_seq = team_seq.merge(
                df_matches[['MATCH_OPTAUUID', 'MATCH_LOCALDATE', 'CONTESTANTHOME_NAME', 'CONTESTANTAWAY_NAME', 'CONTESTANTHOME_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID']], 
                on='MATCH_OPTAUUID', how='left'
            )
            
            # Find unikke mål og sorter: Nyeste kampe først, mål i kampen kronologisk
            goal_list = team_seq[team_seq['EVENT_TYPEID'] == 16].drop_duplicates('GOAL_TIME').copy()
            goal_list = goal_list.sort_values(by=['MATCH_LOCALDATE', 'EVENT_TIMEMIN'], ascending=[False, True])
            
            # Byg dropdown muligheder
            goal_options = {}
            for _, row in goal_list.iterrows():
                opp_name = row['CONTESTANTAWAY_NAME'] if row['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else row['CONTESTANTHOME_NAME']
                opp_uuid = row['CONTESTANTAWAY_OPTAUUID'] if row['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else row['CONTESTANTHOME_OPTAUUID']
                date_str = row['MATCH_LOCALDATE'].strftime('%d/%m/%Y')
                
                goal_options[row['GOAL_TIME']] = {
                    'label': f"{date_str}: Mål vs. {opp_name} ({row['EVENT_TIMEMIN']}. min)",
                    'opp_uuid': opp_uuid,
                    'date': date_str,
                    'score': f"{int(row['H_SCORE'])}-{int(row['A_SCORE'])}",
                    'min': row['EVENT_TIMEMIN']
                }

            sel_ts = st.selectbox("Vælg mål", list(goal_options.keys()), format_func=lambda x: goal_options[x]['label'])
            
            # Hent de sidste 8 aktioner i målangrebet for at holde banen ren
            this_goal = team_seq[team_seq['GOAL_TIME'] == sel_ts].sort_values('EVENT_TIMESTAMP').tail(8)
            
            col_b, col_tab = st.columns([2.5, 1])
            with col_b:
                pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='grey')
                fig, ax = pitch.draw(figsize=(10, 7))
                
                # Tegn infoboks
                draw_match_info_box(
                    ax, 
                    get_logo_img(valgt_uuid), 
                    get_logo_img(goal_options[sel_ts]['opp_uuid']), 
                    goal_options[sel_ts]['date'], 
                    goal_options[sel_ts]['score'], 
                    goal_options[sel_ts]['min']
                )

                # Tegn aktioner og pile
                for i in range(len(this_goal)):
                    row = this_goal.iloc[i]
                    is_g = row['EVENT_TYPEID'] == 16
                    
                    # Punkt for aktion
                    ax.scatter(row['EVENT_X'], row['EVENT_Y'], 
                               color='#cc0000' if is_g else 'red', 
                               s=150 if is_g else 60, 
                               marker='s' if is_g else 'o', 
                               edgecolors='black', zorder=10)
                    
                    # Spiller navn
                    ax.text(row['EVENT_X'], row['EVENT_Y'] + 2, row['PLAYER_NAME'], 
                            fontsize=7, ha='center', 
                            bbox=dict(facecolor='white', alpha=0.6, edgecolor='none'))
                    
                    # Pil til næste aktion
                    if i < len(this_goal) - 1:
                        n = this_goal.iloc[i+1]
                        pitch.arrows(row['EVENT_X'], row['EVENT_Y'], n['EVENT_X'], n['EVENT_Y'], 
                                     width=1, color='black', ax=ax, alpha=0.2)
                
                st.pyplot(fig)
            
            with col_tab:
                # Tabel over de viste aktioner
                st.dataframe(this_goal[['PLAYER_NAME', 'EVENT_TYPEID']].iloc[::-1].rename(
                    columns={'PLAYER_NAME':'Spiller','EVENT_TYPEID':'Aktion'}), 
                    hide_index=True, use_container_width=True)
        else:
            st.info("Ingen mål fundet for dette hold.")
