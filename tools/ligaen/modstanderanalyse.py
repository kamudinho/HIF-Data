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

def plot_custom_pitch(df, event_ids, title, half=True, vertical=True, cmap='Reds', logo=None):
    # Filtrer data
    plot_data = df[df['EVENT_TYPEID'].isin(event_ids)].copy()
    
    if vertical:
        pitch = VerticalPitch(pitch_type='opta', half=half, pitch_color='#ffffff', line_color='#BDBDBD')
    else:
        pitch = Pitch(pitch_type='opta', half=half, pitch_color='#ffffff', line_color='#BDBDBD')
        
    fig, ax = pitch.draw(figsize=(6, 8))
    
    # Indsæt logo i øverste venstre hjørne af aksen
    if logo:
        ax_logo = ax.inset_axes([0.02, 0.88, 0.12, 0.12], transform=ax.transAxes)
        ax_logo.imshow(logo)
        ax_logo.axis('off')

    if not plot_data.empty:
        pitch.kdeplot(plot_data.EVENT_X, plot_data.EVENT_Y, ax=ax, cmap=cmap, fill=True, alpha=0.7, levels=100)
    
    ax.set_title(title, fontsize=10, pad=10)
    return fig

# --- 3. HOVEDFUNKTION ---
def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn: return

    # 3.1 Definition af hold
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'")
    ids = df_teams_raw['CONTESTANTHOME_OPTAUUID'].unique()
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    team_map = {mapping_lookup.get(str(u).lower().replace('t','')): u for u in ids if mapping_lookup.get(str(u).lower().replace('t',''))}

    col_spacer, col_hold = st.columns([3, 1])
    valgt_hold = col_hold.selectbox("Vælg hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid)

    # --- DATA-HENTNING ---
    with st.spinner(f"Henter data for {valgt_hold}..."):
        # Mål-sekvens data (Låst logik)
        sql_goals = f"""
        SELECT e.MATCH_OPTAUUID, e.EVENT_TIMESTAMP as GOAL_TIME, e.EVENT_CONTESTANT_OPTAUUID as SCORING_TEAM,
               e.EVENT_TIMEMIN as GOAL_MIN, m.CONTESTANTHOME_NAME, m.CONTESTANTAWAY_NAME,
               m.CONTESTANTHOME_OPTAUUID, m.CONTESTANTAWAY_OPTAUUID, m.MATCH_LOCALDATE
        FROM {DB}.OPTA_EVENTS e
        JOIN {DB}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
        LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
        WHERE e.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}' AND e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}'
        AND (e.EVENT_TYPEID = 16 OR q.QUALIFIER_QID = 28)
        QUALIFY ROW_NUMBER() OVER (PARTITION BY e.MATCH_OPTAUUID, e.EVENT_TIMESTAMP ORDER BY e.EVENT_EVENTID) = 1
        """
        df_goals = conn.query(sql_goals)

        sql_events = f"""
        WITH Goals AS ({sql_goals})
        SELECT e.*, g.GOAL_TIME, g.SCORING_TEAM as GOAL_TEAM_ID, g.GOAL_MIN,
               g.CONTESTANTHOME_NAME, g.CONTESTANTAWAY_NAME, g.CONTESTANTHOME_OPTAUUID, g.CONTESTANTAWAY_OPTAUUID, g.MATCH_LOCALDATE
        FROM {DB}.OPTA_EVENTS e
        INNER JOIN Goals g ON e.MATCH_OPTAUUID = g.MATCH_OPTAUUID
        WHERE e.EVENT_TIMESTAMP >= DATEADD(second, -12, g.GOAL_TIME) AND e.EVENT_TIMESTAMP <= g.GOAL_TIME
        AND e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND e.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        QUALIFY ROW_NUMBER() OVER (PARTITION BY e.EVENT_OPTAUUID, g.GOAL_TIME ORDER BY e.EVENT_TIMESTAMP DESC) = 1
        """
        df_all_events = conn.query(sql_events)
        
        # Generel event data til heatmaps
        sql_all_h = f"SELECT EVENT_X, EVENT_Y, EVENT_TYPEID FROM {DB}.OPTA_EVENTS WHERE EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"
        df_all_h = conn.query(sql_all_h)

    # --- 4. TABS ---
    t1, t2, t3, t4, t5 = st.tabs(["OVERSIGT", "MED BOLDEN", "UDEN BOLDEN", "MÅL-SEKVENSER", "SPILLEROVERSIGT"])

    # --- T1: OVERSIGT ---
    with t1:
        sql_res = f"""
            SELECT 
                MATCH_LOCALDATE as DATO, 
                CONTESTANTHOME_NAME as HJEMME, 
                CONTESTANTAWAY_NAME as UDE, 
                TOTAL_HOME_SCORE as "MÅL H", 
                TOTAL_AWAY_SCORE as "MÅL U" 
            FROM {DB}.OPTA_MATCHINFO 
            WHERE (CONTESTANTHOME_OPTAUUID = '{valgt_uuid}' OR CONTESTANTAWAY_OPTAUUID = '{valgt_uuid}') 
            AND TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}' 
            ORDER BY MATCH_LOCALDATE DESC LIMIT 5
        """
        st.dataframe(conn.query(sql_res), hide_index=True)

    # --- T2: MED BOLDEN (3 KOLONNER - HALVE BANER) ---
    with t2:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.pyplot(plot_custom_pitch(df_all_h, [1], "PASNINGER", half=True, cmap='Reds', logo=hold_logo))
        with c2:
            st.pyplot(plot_custom_pitch(df_all_h, [2, 15], "DRIBLINGER / SKUD", half=True, cmap='Oranges', logo=hold_logo))
        with c3:
            st.pyplot(plot_custom_pitch(df_all_h, [1], "GENNEMBRUD", half=True, cmap='YlOrRd', logo=hold_logo))

    # --- T3: UDEN BOLDEN (3 KOLONNER - 2 FULDE, 1 HALV) ---
    with t3:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.pyplot(plot_custom_pitch(df_all_h, [7, 8], "TACKLINGER & BLOKERINGER", half=False, cmap='Blues', logo=hold_logo))
        with c2:
            st.pyplot(plot_custom_pitch(df_all_h, [127, 12], "INTERCEPTIONS & CLEARANCES", half=False, cmap='GnBu', logo=hold_logo))
        with c3:
            st.pyplot(plot_custom_pitch(df_all_h, [7, 127], "DEFENSIV HALVLEJ", half=True, cmap='PuBu', logo=hold_logo))

    # --- T4: MÅL-SEKVENSER (LÅST) ---
    with t4:
        if not df_all_events.empty:
            goal_list = df_all_events.drop_duplicates(['MATCH_OPTAUUID', 'GOAL_TIME']).sort_values('GOAL_TIME', ascending=False)
            goal_options = {f"{row['MATCH_OPTAUUID']}_{row['GOAL_TIME']}": {
                'label': f"{pd.to_datetime(row['MATCH_LOCALDATE']).strftime('%d/%m/%Y')} vs. {row['CONTESTANTAWAY_NAME'] if row['CONTESTANTHOME_OPTAUUID']==valgt_uuid else row['CONTESTANTHOME_NAME']} ({row['GOAL_MIN']}. min)",
                'match_id': row['MATCH_OPTAUUID'], 'goal_ts': row['GOAL_TIME'],
                'opp_uuid': row['CONTESTANTAWAY_OPTAUUID'] if row['CONTESTANTHOME_OPTAUUID']==valgt_uuid else row['CONTESTANTHOME_OPTAUUID'],
                'min': row['GOAL_MIN'], 'date': pd.to_datetime(row['MATCH_LOCALDATE']).strftime('%d/%m/%Y')
            } for _, row in goal_list.iterrows()}

            sel_key = st.selectbox("Vælg mål", list(goal_options.keys()), format_func=lambda x: goal_options[x]['label'])
            sel_data = goal_options[sel_key]
            this_goal_events = df_all_events[(df_all_events['MATCH_OPTAUUID'] == sel_data['match_id']) & (df_all_events['GOAL_TIME'] == sel_data['goal_ts'])].sort_values('EVENT_TIMESTAMP')

            col_pitch, col_list = st.columns([2.5, 1])
            with col_pitch:
                pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='grey')
                fig, ax = pitch.draw(figsize=(10, 7))
                draw_match_info_box(ax, hold_logo, get_logo_img(sel_data['opp_uuid']), sel_data['date'], "Mål", sel_data['min'])
                for i in range(len(this_goal_events) - 1):
                    pitch.arrows(this_goal_events.iloc[i]['EVENT_X'], this_goal_events.iloc[i]['EVENT_Y'], this_goal_events.iloc[i+1]['EVENT_X'], this_goal_events.iloc[i+1]['EVENT_Y'], width=1, headwidth=3, color='black', alpha=0.15, ax=ax)
                for i, row in this_goal_events.iterrows():
                    color, marker, size = ('red', 's', 180) if row['EVENT_TYPEID'] == 16 else (('gold', 'P', 200) if row['EVENT_TYPEID'] == 5 else ('red', 'o', 80))
                    ax.scatter(row['EVENT_X'], row['EVENT_Y'], color=color, s=size, marker=marker, edgecolors='black', zorder=10)
                    ax.text(row['EVENT_X'], row['EVENT_Y'] + 2.5, row['PLAYER_NAME'], fontsize=7, ha='center', fontweight='bold', bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
                st.pyplot(fig)
            with col_list:
                this_goal_events['Aktion'] = this_goal_events['EVENT_TYPEID'].astype(str).map(OPTA_EVENT_TYPES)
                st.write("**Sekvens:**")
                st.dataframe(this_goal_events[['PLAYER_NAME', 'Aktion']].iloc[::-1], hide_index=True)

    # --- T5: SPILLEROVERSIGT (LÅST) ---
    with t5:
        if not df_all_events.empty:
            stats = df_all_events.groupby('PLAYER_NAME').agg({'EVENT_TYPEID': [lambda x: (x == 16).sum(), lambda x: (x == 7).sum(), lambda x: (x == 127).sum(), lambda x: (x == 1).sum()]})
            stats.columns = ['Mål', 'Tacklinger før mål', 'Interceptions før mål', 'Pasninger i mål-sekvens']
            st.dataframe(stats.sort_values('Mål', ascending=False))

if __name__ == "__main__":
    vis_side()
