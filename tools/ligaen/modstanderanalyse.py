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

def plot_custom_pitch(df, event_ids, title, zone='full', cmap='Reds', logo=None):
    plot_data = df[df['EVENT_TYPEID'].isin(event_ids)].copy()
    pitch = VerticalPitch(pitch_type='opta', half=False, pitch_color='#ffffff', line_color='#BDBDBD')
    fig, ax = pitch.draw(figsize=(5, 7))
    
    if zone == 'up':
        ax.set_ylim(0, 55)
        logo_pos = [0.04, 0.03, 0.08, 0.08]
        text_y = 0.05
    elif zone == 'down':
        ax.set_ylim(45, 100)
        logo_pos = [0.04, 0.90, 0.08, 0.08]
        text_y = 0.97
    else:
        logo_pos = [0.04, 0.90, 0.08, 0.08]
        text_y = 0.97

    if logo:
        ax_logo = ax.inset_axes(logo_pos, transform=ax.transAxes)
        ax_logo.imshow(logo)
        ax_logo.axis('off')

    ax.text(0.94, text_y, title, transform=ax.transAxes, fontsize=5.5, 
            fontweight='bold', ha='right', va='top', color='#333333')

    if not plot_data.empty:
        pitch.kdeplot(plot_data.EVENT_X, plot_data.EVENT_Y, ax=ax, cmap=cmap, fill=True, alpha=0.5, levels=100)
    
    return fig

# --- 3. HOVEDFUNKTION (UNDERSIDE) ---
def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn: return

    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'")
    ids = df_teams_raw['CONTESTANTHOME_OPTAUUID'].unique()
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    team_map = {mapping_lookup.get(str(u).lower().replace('t','')): u for u in ids if mapping_lookup.get(str(u).lower().replace('t',''))}

    col_spacer, col_hold = st.columns([3, 1])
    valgt_hold = col_hold.selectbox("Vælg hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid)

    with st.spinner("Henter data..."):
        df_all_h = conn.query(f"SELECT EVENT_X, EVENT_Y, EVENT_TYPEID FROM {DB}.OPTA_EVENTS WHERE EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'")
        
        sql_goals = f"SELECT e.MATCH_OPTAUUID, e.EVENT_TIMESTAMP as GOAL_TIME, e.EVENT_CONTESTANT_OPTAUUID as SCORING_TEAM, e.EVENT_TIMEMIN as GOAL_MIN, m.CONTESTANTHOME_NAME, m.CONTESTANTAWAY_NAME, m.CONTESTANTHOME_OPTAUUID, m.CONTESTANTAWAY_OPTAUUID, m.MATCH_LOCALDATE FROM {DB}.OPTA_EVENTS e JOIN {DB}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID WHERE e.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}' AND e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND (e.EVENT_TYPEID = 16 OR q.QUALIFIER_QID = 28) QUALIFY ROW_NUMBER() OVER (PARTITION BY e.MATCH_OPTAUUID, e.EVENT_TIMESTAMP ORDER BY e.EVENT_EVENTID) = 1"
        sql_events = f"WITH Goals AS ({sql_goals}) SELECT e.*, g.GOAL_TIME, g.SCORING_TEAM as GOAL_TEAM_ID, g.GOAL_MIN, g.CONTESTANTHOME_NAME, g.CONTESTANTAWAY_NAME, g.CONTESTANTHOME_OPTAUUID, g.CONTESTANTAWAY_OPTAUUID, g.MATCH_LOCALDATE FROM {DB}.OPTA_EVENTS e INNER JOIN Goals g ON e.MATCH_OPTAUUID = g.MATCH_OPTAUUID WHERE e.EVENT_TIMESTAMP >= DATEADD(second, -12, g.GOAL_TIME) AND e.EVENT_TIMESTAMP <= g.GOAL_TIME AND e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND e.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}' QUALIFY ROW_NUMBER() OVER (PARTITION BY e.EVENT_OPTAUUID, g.GOAL_TIME ORDER BY e.EVENT_TIMESTAMP DESC) = 1"
        df_all_events = conn.query(sql_events)

    t1, t2, t3, t4, t5 = st.tabs(["OVERSIGT", "MED BOLDEN", "UDEN BOLDEN", "MÅL-SEKVENSER", "SPILLEROVERSIGT"])

    # --- T1: OVERSIGT ---
    with t1:
        sql_res = f"SELECT MATCH_LOCALDATE, CONTESTANTHOME_NAME, CONTESTANTAWAY_NAME, TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE, CONTESTANTHOME_OPTAUUID, CONTESTANTAWAY_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE (CONTESTANTHOME_OPTAUUID = '{valgt_uuid}' OR CONTESTANTAWAY_OPTAUUID = '{valgt_uuid}') AND TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}' ORDER BY MATCH_LOCALDATE DESC LIMIT 10"
        df_res = conn.query(sql_res)
        
        if not df_res.empty:
            # Fix NaN før beregning
            df_res['TOTAL_HOME_SCORE'] = df_res['TOTAL_HOME_SCORE'].fillna(0).astype(int)
            df_res['TOTAL_AWAY_SCORE'] = df_res['TOTAL_AWAY_SCORE'].fillna(0).astype(int)

            def get_result(row):
                is_home = row['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
                h_goal, a_goal = row['TOTAL_HOME_SCORE'], row['TOTAL_AWAY_SCORE']
                if h_goal == a_goal: return "D"
                if is_home: return "W" if h_goal > a_goal else "L"
                else: return "W" if a_goal > h_goal else "L"

            df_res['RES'] = df_res.apply(get_result, axis=1)
            
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            last_5 = df_res.head(5)
            wins, draws = (last_5['RES'] == "W").sum(), (last_5['RES'] == "D").sum()
            kpi1.metric("Point (Sidste 5)", f"{(wins*3)+draws}/15")
            kpi2.metric("Sejre", wins)
            
            mål_s = sum([r['TOTAL_HOME_SCORE'] if r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else r['TOTAL_AWAY_SCORE'] for _, r in last_5.iterrows()])
            mål_i = sum([r['TOTAL_AWAY_SCORE'] if r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else r['TOTAL_HOME_SCORE'] for _, r in last_5.iterrows()])
            kpi3.metric("Mål Scoret", mål_s)
            kpi4.metric("Mål Imod", mål_i, delta=int(mål_i), delta_color="inverse")

            st.dataframe(df_res[['MATCH_LOCALDATE', 'CONTESTANTHOME_NAME', 'TOTAL_HOME_SCORE', 'TOTAL_AWAY_SCORE', 'CONTESTANTAWAY_NAME', 'RES']], hide_index=True, use_container_width=True)

    # --- T2 & T3 (Med Fix til NaN i loops) ---
    for tab, focus_list, key in zip([t2, t3], [["Opbygning", "Gennembrud", "Afslutninger"], ["Dueller", "Erobringer", "Defensiv Zone"]], ["ms", "us"]):
        with tab:
            cp, cs = st.columns([2, 1])
            with cs:
                v = st.selectbox("Fokus", focus_list, key=key)
                # ... (Her indsættes din eksisterende SQL-logik for T2/T3)
                df_r = conn.query(sql) # Antager sql er defineret i din logik
                if not df_r.empty:
                    df_r['ANTAL'] = df_r['ANTAL'].fillna(0)
                    for _, r in df_r.iterrows(): st.write(f"{int(r['ANTAL'])} **{r['PLAYER_NAME']}**")

    # --- T4: MÅL-SEKVENSER ---
    with t4:
        # (Din eksisterende T4 kode fungerer fint, da den bruger rå event_x/y)
        pass 

    # --- T5: SPILLEROVERSIGT (Fixet kolonne-orden og NaN) ---
    with t5:
        if not df_all_events.empty:
            regain_ids = [7, 8, 12, 49, 67, 127, 73, 74]
            df_all_events['is_goal'] = (df_all_events['EVENT_TYPEID'] == 16).astype(int)
            df_all_events['is_pass'] = (df_all_events['EVENT_TYPEID'] == 1).astype(int)
            df_all_events['is_regain'] = df_all_events['EVENT_TYPEID'].isin(regain_ids).astype(int)
            df_all_events['is_touch'] = (df_all_events['EVENT_X'] > 66).astype(int)

            stats = df_all_events.groupby('PLAYER_NAME').agg({
                'is_pass': 'sum', 'is_regain': 'sum', 'is_touch': 'sum', 'is_goal': 'sum', 'EVENT_TYPEID': 'count'
            }).fillna(0)

            stats['Målinvolveringer'] = df_all_events.groupby('PLAYER_NAME')['GOAL_TIME'].nunique().fillna(0)
            
            stats = stats.rename(columns={'EVENT_TYPEID': 'Antal aktioner', 'is_pass': 'Pasninger', 'is_regain': 'Regains', 'is_touch': 'Touches', 'is_goal': 'Mål'})
            
            # Endelig orden: Målinvolveringer, Antal aktioner, Pasninger, Regains, Touches, Mål
            final_df = stats[['Målinvolveringer', 'Antal aktioner', 'Pasninger', 'Regains', 'Touches', 'Mål']].astype(int)
            st.dataframe(final_df.sort_values('Målinvolveringer', ascending=False), use_container_width=True)

if __name__ == "__main__":
    vis_side()
