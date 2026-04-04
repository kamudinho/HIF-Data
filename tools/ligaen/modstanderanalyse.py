import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch, VerticalPitch
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

def plot_pass_heatmap(df, direction="up"):
    pass_df = df[(df['EVENT_TYPEID'] == 1) & (df['EVENT_TYPEID'] != 43)].copy()
    if pass_df.empty: return None
    
    pitch = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#BDBDBD')
    fig, ax = pitch.draw(figsize=(8, 10))
    
    if direction == "down":
        ax.invert_yaxis()
        ax.invert_xaxis()
        cmap = 'Blues'
        plot_data = pass_df[pass_df['EVENT_X'] <= 50]
    else:
        cmap = 'Reds'
        plot_data = pass_df[pass_df['EVENT_X'] >= 50]
        
    if not plot_data.empty:
        pitch.kdeplot(plot_data.EVENT_X, plot_data.EVENT_Y, ax=ax, cmap=cmap, fill=True, alpha=0.7, levels=100)
    return fig

# --- 3. HOVEDFUNKTION ---
def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn: return

    # 3.1 Initialisering og Holdvalg
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'")
    ids = df_teams_raw['CONTESTANTHOME_OPTAUUID'].unique()
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    team_map = {mapping_lookup.get(str(u).lower().replace('t','')): u for u in ids if mapping_lookup.get(str(u).lower().replace('t',''))}

    col_spacer, col_hold = st.columns([3, 1])
    valgt_hold = col_hold.selectbox("Vælg hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]

    # Faner
    t1, t2, t3, t4, t5 = st.tabs(["OVERSIGT", "MED BOLDEN", "UDEN BOLDEN", "MÅL-SEKVENSER", "SPILLEROVERSIGT"])

    # --- T1: OVERSIGT ---
    with t1:
        st.subheader(f"Præstationer: {valgt_hold}")
        sql_res = f"""
            SELECT MATCH_LOCALDATE as DATO, CONTESTANTHOME_NAME as HJEMME, CONTESTANTAWAY_NAME as UDE, 
                   TOTAL_HOME_SCORE as "MÅL H", TOTAL_AWAY_SCORE as "MÅL U"
            FROM {DB}.OPTA_MATCHINFO 
            WHERE (CONTESTANTHOME_OPTAUUID = '{valgt_uuid}' OR CONTESTANTAWAY_OPTAUUID = '{valgt_uuid}')
            AND TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
            ORDER BY MATCH_LOCALDATE DESC LIMIT 5
        """
        st.dataframe(conn.query(sql_res), hide_index=True)

    # --- T2: MED BOLDEN ---
    with t2:
        st.subheader("Positionsanalyse (Pasninger)")
        sql_passes = f"SELECT EVENT_X, EVENT_Y, EVENT_TYPEID FROM {DB}.OPTA_EVENTS WHERE EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND EVENT_TYPEID = 1 AND EVENT_TYPEID != 43 AND TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"
        df_passes = conn.query(sql_passes)
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Opbygningsspil**")
            fig_d = plot_pass_heatmap(df_passes, direction="down")
            if fig_d: st.pyplot(fig_d)
        with c2:
            st.write("**Gennembrudsspil**")
            fig_u = plot_pass_heatmap(df_passes, direction="up")
            if fig_u: st.pyplot(fig_u)

    # --- T3: UDEN BOLDEN ---
    with t3:
        st.subheader("Defensiv aktionsradius")
        sql_def = f"SELECT EVENT_X, EVENT_Y, EVENT_TYPEID FROM {DB}.OPTA_EVENTS WHERE EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND EVENT_TYPEID IN (7, 8, 12) AND EVENT_TYPEID != 43 AND TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"
        df_def = conn.query(sql_def)
        if not df_def.empty:
            pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='grey')
            fig, ax = pitch.draw()
            pitch.kdeplot(df_def.EVENT_X, df_def.EVENT_Y, ax=ax, cmap='Greens', fill=True, alpha=0.5, levels=10)
            st.pyplot(fig)

    # --- T4: MÅL-SEKVENSER ---
    with t4:
        # SQL til at finde mål og hændelser 12 sek. før (Din avancerede logik)
        sql_goals = f"""
            SELECT e.MATCH_OPTAUUID, e.EVENT_TIMESTAMP as GOAL_TIME, e.EVENT_CONTESTANT_OPTAUUID as SCORING_TEAM,
                   e.EVENT_TIMEMIN as GOAL_MIN, m.CONTESTANTHOME_NAME, m.CONTESTANTAWAY_NAME,
                   m.CONTESTANTHOME_OPTAUUID, m.CONTESTANTAWAY_OPTAUUID
            FROM {DB}.OPTA_EVENTS e
            JOIN {DB}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
            LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE e.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
            AND (e.EVENT_TYPEID = 16 OR q.QUALIFIER_QID = 28)
            AND e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}'
        """
        sql_events = f"""
            WITH Goals AS ({sql_goals})
            SELECT e.*, g.GOAL_TIME, g.GOAL_MIN, g.CONTESTANTHOME_NAME, g.CONTESTANTAWAY_NAME
            FROM {DB}.OPTA_EVENTS e
            JOIN Goals g ON e.MATCH_OPTAUUID = g.MATCH_OPTAUUID
            WHERE e.EVENT_TIMESTAMP >= DATEADD(second, -12, g.GOAL_TIME) AND e.EVENT_TIMESTAMP <= g.GOAL_TIME
            AND e.EVENT_TYPEID != 43
        """
        df_all_events = conn.query(sql_events)

        if not df_all_events.empty:
            goal_list = df_all_events.drop_duplicates(['MATCH_OPTAUUID', 'GOAL_TIME']).sort_values('GOAL_TIME', ascending=False)
            goal_labels = {f"{r.MATCH_OPTAUUID}_{r.GOAL_TIME}": f"vs. {r.CONTESTANTAWAY_NAME if r.CONTESTANTHOME_NAME==valgt_hold else r.CONTESTANTHOME_NAME} ({r.GOAL_MIN}. min)" for r in goal_list.itertuples()}
            sel_key = st.selectbox("Vælg mål", list(goal_labels.keys()), format_func=lambda x: goal_labels[x])
            
            m_id, g_ts = sel_key.split('_', 1)
            this_goal = df_all_events[(df_all_events.MATCH_OPTAUUID == m_id) & (df_all_events.GOAL_TIME == g_ts)].sort_values('EVENT_TIMESTAMP')

            col_p, col_l = st.columns([2.5, 1])
            with col_p:
                p = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='grey')
                fig, ax = p.draw(figsize=(10, 7))
                for i in range(len(this_goal)-1):
                    p.arrows(this_goal.iloc[i].EVENT_X, this_goal.iloc[i].EVENT_Y, this_goal.iloc[i+1].EVENT_X, this_goal.iloc[i+1].EVENT_Y, width=1.5, color='black', alpha=0.2, ax=ax)
                for i, row in this_goal.iterrows():
                    color = 'red' if row['EVENT_TYPEID'] == 16 else ('gold' if row['EVENT_TYPEID'] == 5 else ('#0000FF' if row['EVENT_TYPEID'] in [7, 127] else 'red'))
                    marker = 's' if row['EVENT_TYPEID'] == 16 else ('P' if row['EVENT_TYPEID'] == 5 else 'o')
                    ax.scatter(row['EVENT_X'], row['EVENT_Y'], color=color, s=150, marker=marker, edgecolors='black', zorder=10)
                    ax.text(row['EVENT_X'], row['EVENT_Y'] + 2.5, row['PLAYER_NAME'], fontsize=7, ha='center', fontweight='bold', bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
                st.pyplot(fig)
            with col_l:
                this_goal['Aktion'] = this_goal['EVENT_TYPEID'].astype(str).map(OPTA_EVENT_TYPES)
                st.dataframe(this_goal[['PLAYER_NAME', 'Aktion']].iloc[::-1], hide_index=True)

    # --- T5: SPILLEROVERSIGT ---
    with t5:
        if not df_all_events.empty:
            stats = df_all_events.groupby('PLAYER_NAME').agg({
                'EVENT_TYPEID': [
                    lambda x: (x == 16).sum(),
                    lambda x: (x == 7).sum(),
                    lambda x: (x == 1).sum()
                ]
            })
            stats.columns = ['Mål', 'Tacklinger før mål', 'Pasninger i mål-sekvens']
            st.dataframe(stats.sort_values('Mål', ascending=False))

if __name__ == "__main__":
    vis_side()
