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
HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

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

    with st.spinner("Synkroniserer kampdata..."):
        # 3.1 Hent kampe
        df_matches = conn.query(f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'")
        
        # 3.2 SQL til mål-sekvenser (Visualisering)
        sql_seq = f"""
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
        df_sequences = conn.query(sql_seq)

        # 3.3 SQL til Spiller-stats (RETTET: Skudsikker EXISTS logik)
        sql_stats = f"""
        WITH GoalPossessions AS (
            SELECT DISTINCT MATCH_OPTAUUID, POSSESSIONID 
            FROM {DB}.OPTA_EVENTS 
            WHERE EVENT_TYPEID = 16 AND TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        )
        SELECT 
            e.PLAYER_NAME as PLAYER,
            e.EVENT_CONTESTANT_OPTAUUID as TEAM_ID,
            COUNT(*) as TOTAL_ACTIONS_IN_GOALS,
            COUNT(DISTINCT e.MATCH_OPTAUUID || e.POSSESSIONID) as GOAL_INVOLVEMENTS,
            SUM(CASE WHEN e.EVENT_TYPEID = 16 THEN 1 ELSE 0 END) as GOALS,
            
            -- ASSISTS: Tjekker direkte efter Qualifier 213
            SUM(CASE WHEN EXISTS (
                SELECT 1 FROM {DB}.OPTA_QUALIFIERS q 
                WHERE q.EVENT_OPTAUUID = e.EVENT_OPTAUUID 
                AND q.QUALIFIER_QID = 213
            ) THEN 1 ELSE 0 END) as ASSISTS,
            
            -- PASNINGER: Type 1 (Pasning) minus dem der er assists
            SUM(CASE WHEN e.EVENT_TYPEID = 1 AND NOT EXISTS (
                SELECT 1 FROM {DB}.OPTA_QUALIFIERS q 
                WHERE q.EVENT_OPTAUUID = e.EVENT_OPTAUUID 
                AND q.QUALIFIER_QID = 213
            ) THEN 1 ELSE 0 END) as PASSES_IN_GOAL,
            
            SUM(CASE WHEN e.EVENT_TYPEID IN (3, 7, 44) THEN 1 ELSE 0 END) as DUELS_IN_GOAL,
            SUM(CASE WHEN e.EVENT_TYPEID = 8 THEN 1 ELSE 0 END) as INTERCEPTIONS_IN_GOAL
        FROM {DB}.OPTA_EVENTS e
        INNER JOIN GoalPossessions gp ON e.MATCH_OPTAUUID = gp.MATCH_OPTAUUID AND e.POSSESSIONID = gp.POSSESSIONID
        WHERE e.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        AND e.PLAYER_NAME IS NOT NULL
        GROUP BY e.PLAYER_NAME, e.EVENT_CONTESTANT_OPTAUUID
        ORDER BY GOAL_INVOLVEMENTS DESC
        """
        df_all_stats = conn.query(sql_stats)

    # 4. TEAM MAPPING & UI
    ids = pd.concat([df_matches['CONTESTANTHOME_OPTAUUID'], df_matches['CONTESTANTAWAY_OPTAUUID']]).unique()
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    team_map = {mapping_lookup.get(str(u).lower().replace('t','')): u for u in ids if mapping_lookup.get(str(u).lower().replace('t',''))}

    col_spacer, col_hold = st.columns([3, 1])
    valgt_hold = col_hold.selectbox("Vælg hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]

    t1, t2, t3 = st.tabs(["EVENTS", "MÅL-SEKVENSER", "SPILLEROVERSIGT"])

    with t2:
        team_seq = df_sequences[df_sequences['GOAL_TEAM_ID'] == valgt_uuid].copy()
        if not team_seq.empty:
            df_matches['MATCH_LOCALDATE'] = pd.to_datetime(df_matches['MATCH_LOCALDATE'])
            team_seq = team_seq.merge(df_matches[['MATCH_OPTAUUID', 'MATCH_LOCALDATE', 'CONTESTANTHOME_NAME', 'CONTESTANTAWAY_NAME', 'CONTESTANTHOME_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID']], on='MATCH_OPTAUUID', how='left')
            
            goal_list = team_seq[team_seq['EVENT_TYPEID'] == 16].drop_duplicates('GOAL_TIME').copy()
            goal_list = goal_list.sort_values(by=['MATCH_LOCALDATE', 'EVENT_TIMEMIN'], ascending=[False, True])
            
            goal_options = {row['GOAL_TIME']: {
                'label': f"{row['MATCH_LOCALDATE'].strftime('%d/%m/%Y')}: Mål vs. {row['CONTESTANTAWAY_NAME'] if row['CONTESTANTHOME_OPTAUUID']==valgt_uuid else row['CONTESTANTHOME_NAME']} ({row['EVENT_TIMEMIN']}. min)",
                'opp_uuid': row['CONTESTANTAWAY_OPTAUUID'] if row['CONTESTANTHOME_OPTAUUID']==valgt_uuid else row['CONTESTANTHOME_OPTAUUID'],
                'date': row['MATCH_LOCALDATE'].strftime('%d/%m/%Y'),
                'score': f"{int(row['H_SCORE'])}-{int(row['A_SCORE'])}",
                'min': row['EVENT_TIMEMIN']
            } for _, row in goal_list.iterrows()}

            sel_ts = st.selectbox("Vælg mål", list(goal_options.keys()), format_func=lambda x: goal_options[x]['label'])
            this_goal = team_seq[team_seq['GOAL_TIME'] == sel_ts].sort_values('EVENT_TIMESTAMP')
            
            col_b, col_tab = st.columns([2.5, 1])
            with col_b:
                pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='grey')
                fig, ax = pitch.draw(figsize=(10, 7))
                draw_match_info_box(ax, get_logo_img(valgt_uuid), get_logo_img(goal_options[sel_ts]['opp_uuid']), goal_options[sel_ts]['date'], goal_options[sel_ts]['score'], goal_options[sel_ts]['min'])

                for i in range(len(this_goal)):
                    row = this_goal.iloc[i]
                    is_g = row['EVENT_TYPEID'] == 16
                    ax.scatter(row['EVENT_X'], row['EVENT_Y'], color='#cc0000' if is_g else 'red', s=150 if is_g else 60, marker='s' if is_g else 'o', edgecolors='black', zorder=10)
                    ax.text(row['EVENT_X'], row['EVENT_Y'] + 2, row['PLAYER_NAME'], fontsize=7, ha='center', bbox=dict(facecolor='white', alpha=0.6, edgecolor='none'))
                    if i < len(this_goal) - 1:
                        n = this_goal.iloc[i+1]
                        pitch.arrows(row['EVENT_X'], row['EVENT_Y'], n['EVENT_X'], n['EVENT_Y'], width=1, color='black', ax=ax, alpha=0.2)
                st.pyplot(fig)
            with col_tab:
                this_goal['Aktion_Navn'] = this_goal['EVENT_TYPEID'].astype(str).map(OPTA_EVENT_TYPES)
                st.dataframe(this_goal[['PLAYER_NAME', 'Aktion_Navn']].iloc[::-1].rename(columns={'PLAYER_NAME':'Spiller','Aktion_Navn':'Aktion'}), hide_index=True)

    with t3:
        df_team_stats = df_all_stats[df_all_stats['TEAM_ID'] == valgt_uuid].drop(columns=['TEAM_ID']).copy()
        df_team_stats = df_team_stats.rename(columns={
            'PLAYER': 'Spiller',
            'TOTAL_ACTIONS_IN_GOALS': 'Alle aktioner (mål)',
            'GOAL_INVOLVEMENTS': 'Involveret i antal mål',
            'GOALS': 'Mål',
            'ASSISTS': 'Assists',
            'PASSES_IN_GOAL': 'Pasninger (mål)',
            'DUELS_IN_GOAL': 'Dueller (mål)',
            'INTERCEPTIONS_IN_GOAL': 'Interceptions (mål)'
        })
        st.dataframe(df_team_stats, use_container_width=True, hide_index=True)
