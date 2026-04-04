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

    with st.spinner("Henter data..."):
        # 3.1 Hent kampe
        df_matches = conn.query(f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'")
        
        # 3.2 SQL til mål-sekvenser (RETTET OG FEJLSIKRET)
        sql_seq = f"""
        WITH GoalPossessions AS (
            SELECT DISTINCT MATCH_OPTAUUID, POSSESSIONID 
            FROM {DB}.OPTA_EVENTS 
            WHERE EVENT_TYPEID = 16 AND TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        ),
        GoalMetadata AS (
            SELECT 
                MATCH_OPTAUUID, EVENT_TIMESTAMP, EVENT_CONTESTANT_OPTAUUID,
                EVENT_TIMEMIN, POSSESSIONID
            FROM {DB}.OPTA_EVENTS 
            WHERE EVENT_TYPEID = 16 AND TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        )
        SELECT e.*, gm.EVENT_CONTESTANT_OPTAUUID as GOAL_TEAM_ID, gm.EVENT_TIMESTAMP as GOAL_TIME, gm.EVENT_TIMEMIN as GOAL_MIN
        FROM {DB}.OPTA_EVENTS e
        INNER JOIN GoalPossessions gp ON e.MATCH_OPTAUUID = gp.MATCH_OPTAUUID AND e.POSSESSIONID = gp.POSSESSIONID
        LEFT JOIN GoalMetadata gm ON e.MATCH_OPTAUUID = gm.MATCH_OPTAUUID AND e.POSSESSIONID = gm.POSSESSIONID
        WHERE e.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        """
        df_sequences = conn.query(sql_seq)

        # 3.3 SQL til Spiller-stats (QID 213 LOGIK)
        # 3.3 SQL til Spiller-stats (INKLUDERER NU INVOLVERINGER / QID 30)
        sql_stats = f"""
        WITH GoalPoss AS (
            SELECT DISTINCT MATCH_OPTAUUID, POSSESSIONID 
            FROM {DB}.OPTA_EVENTS 
            WHERE EVENT_TYPEID = 16 
            AND TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        ),
        QualifiersData AS (
            -- Vi henter både 29 (Assist) og 30 (Involveret)
            SELECT 
                EVENT_OPTAUUID,
                MAX(CASE WHEN QUALIFIER_QID = 29 THEN 1 ELSE 0 END) as IS_ASSIST,
                MAX(CASE WHEN QUALIFIER_QID = 30 THEN 1 ELSE 0 END) as IS_INVOLVED
            FROM {DB}.OPTA_QUALIFIERS 
            WHERE QUALIFIER_QID IN (29, 30)
            AND TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
            GROUP BY EVENT_OPTAUUID
        )
        SELECT 
            e.PLAYER_NAME as PLAYER,
            e.EVENT_CONTESTANT_OPTAUUID as TEAM_ID,
            -- Officielle mål
            COUNT(DISTINCT CASE WHEN e.EVENT_TYPEID = 16 THEN e.EVENT_OPTAUUID END) as GOALS,
            -- Officielle Assists (QID 29)
            COUNT(DISTINCT CASE WHEN qd.IS_ASSIST = 1 THEN e.EVENT_OPTAUUID END) as ASSISTS,
            -- Involveringer (QID 30) - Dette er ofte den "skjulte" assist
            COUNT(DISTINCT CASE WHEN qd.IS_INVOLVED = 1 AND qd.IS_ASSIST = 0 THEN e.EVENT_OPTAUUID END) as INVOLVEMENTS,
            -- Almindelige pasninger i sekvensen (uden 29/30 tag)
            COUNT(DISTINCT CASE WHEN e.EVENT_TYPEID = 1 AND qd.EVENT_OPTAUUID IS NULL THEN e.EVENT_OPTAUUID END) as BUILDUP_PASSES
        FROM {DB}.OPTA_EVENTS e
        INNER JOIN GoalPoss gp 
            ON e.MATCH_OPTAUUID = gp.MATCH_OPTAUUID 
            AND e.POSSESSIONID = gp.POSSESSIONID
        LEFT JOIN QualifiersData qd 
            ON e.EVENT_OPTAUUID = qd.EVENT_OPTAUUID
        WHERE e.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        AND e.PLAYER_NAME IS NOT NULL
        GROUP BY 1, 2
        HAVING (GOALS > 0 OR ASSISTS > 0 OR INVOLVEMENTS > 0)
        ORDER BY GOALS DESC, ASSISTS DESC, INVOLVEMENTS DESC
        """
        df_all_stats = conn.query(sql_stats)

    # 4. MAPPING OG UI
    ids = pd.concat([df_matches['CONTESTANTHOME_OPTAUUID'], df_matches['CONTESTANTAWAY_OPTAUUID']]).unique()
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    team_map = {mapping_lookup.get(str(u).lower().replace('t','')): u for u in ids if mapping_lookup.get(str(u).lower().replace('t',''))}

    col_hold = st.columns([3, 1])[1]
    valgt_hold = col_hold.selectbox("Vælg hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]

    t1, t2, t3 = st.tabs(["EVENTS", "MÅL-SEKVENSER", "SPILLEROVERSIGT"])

    with t2:
        team_seq = df_sequences[df_sequences['GOAL_TEAM_ID'] == valgt_uuid].copy()
        if not team_seq.empty:
            df_matches['MATCH_LOCALDATE'] = pd.to_datetime(df_matches['MATCH_LOCALDATE'])
            team_seq = team_seq.merge(df_matches[['MATCH_OPTAUUID', 'MATCH_LOCALDATE', 'CONTESTANTHOME_NAME', 'CONTESTANTAWAY_NAME', 'CONTESTANTHOME_OPTAUUID', 'TOTAL_HOME_SCORE', 'TOTAL_AWAY_SCORE']], on='MATCH_OPTAUUID', how='left')
            
            # Rens for dubletter og sorter
            goal_list = team_seq[team_seq['EVENT_TYPEID'] == 16].drop_duplicates(['MATCH_OPTAUUID', 'POSSESSIONID'])
            
            goal_options = {row['GOAL_TIME']: {
                'label': f"{row['MATCH_LOCALDATE'].strftime('%d/%m/%Y')}: vs. {row['CONTESTANTAWAY_NAME'] if row['CONTESTANTHOME_OPTAUUID']==valgt_uuid else row['CONTESTANTHOME_NAME']} ({row['GOAL_MIN']}. min)",
                'opp_uuid': row['CONTESTANTHOME_OPTAUUID'] if row['CONTESTANTHOME_OPTAUUID'] != valgt_uuid else "unknown", # Simpelt fallback
                'date': row['MATCH_LOCALDATE'].strftime('%d/%m/%Y'),
                'score': f"{int(row['TOTAL_HOME_SCORE'])}-{int(row['TOTAL_AWAY_SCORE'])}",
                'min': row['GOAL_MIN']
            } for _, row in goal_list.iterrows()}

            if goal_options:
                sel_ts = st.selectbox("Vælg mål", list(goal_options.keys()), format_func=lambda x: goal_options[x]['label'])
                this_goal = team_seq[team_seq['GOAL_TIME'] == sel_ts].sort_values('EVENT_TIMESTAMP')
                
                col_b, col_tab = st.columns([2.5, 1])
                with col_b:
                    pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='grey')
                    fig, ax = pitch.draw(figsize=(10, 7))
                    draw_match_info_box(ax, get_logo_img(valgt_uuid), None, goal_options[sel_ts]['date'], goal_options[sel_ts]['score'], goal_options[sel_ts]['min'])

                    for i, row in this_goal.iterrows():
                        is_g = row['EVENT_TYPEID'] == 16
                        ax.scatter(row['EVENT_X'], row['EVENT_Y'], color='#cc0000' if is_g else 'red', s=100 if is_g else 40, zorder=10)
                        ax.text(row['EVENT_X'], row['EVENT_Y'] + 2, row['PLAYER_NAME'], fontsize=7)
                    st.pyplot(fig)
                with col_tab:
                    st.dataframe(this_goal[['PLAYER_NAME', 'EVENT_TIMEMIN']].rename(columns={'PLAYER_NAME':'Spiller'}), hide_index=True)

    with t3:
        df_team_stats = df_all_stats[df_all_stats['TEAM_ID'] == valgt_uuid].drop(columns=['TEAM_ID']).copy()
        st.dataframe(df_team_stats.rename(columns={'PLAYER':'Spiller','GOALS':'Mål','ASSISTS':'Assists','PASSES_IN_GOAL':'Pasninger'}), use_container_width=True, hide_index=True)
