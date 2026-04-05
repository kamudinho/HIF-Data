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
    """
    zone: 'up' (0-55), 'down' (55-105), eller 'full'
    """
    plot_data = df[df['EVENT_TYPEID'].isin(event_ids)].copy()
    
    # Konfigurer bane - vi tegner altid en fuld bane internt, men klipper visningen
    pitch = VerticalPitch(pitch_type='opta', half=False, pitch_color='#ffffff', line_color='#BDBDBD')
    fig, ax = pitch.draw(figsize=(5, 7))
    
    # Zoom ind på de ønskede zoner
    if zone == 'up': # Opbygning (0 til 55)
        ax.set_ylim(0, 55)
    elif zone == 'down': # Gennembrud (55 til 105)
        ax.set_ylim(55, 105)
    
    # Overskrift i øverste højre hjørne af det SYNLIGE område
    ax.text(0.95, 0.95, title, transform=ax.transAxes, fontsize=7, 
            fontweight='bold', ha='right', va='top', color='#333333')
    
    # Logo i øverste venstre hjørne af det SYNLIGE område
    if logo:
        ax_logo = ax.inset_axes([0.04, 0.88, 0.08, 0.08], transform=ax.transAxes)
        ax_logo.imshow(logo)
        ax_logo.axis('off')

    if not plot_data.empty:
        pitch.kdeplot(plot_data.EVENT_X, plot_data.EVENT_Y, ax=ax, cmap=cmap, fill=True, alpha=0.5, levels=100)
    
    return fig

# --- 3. HOVEDFUNKTION ---
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

    with st.spinner(f"Henter data for {valgt_hold}..."):
        # Hent basis data til heatmaps
        df_all_h = conn.query(f"SELECT EVENT_X, EVENT_Y, EVENT_TYPEID FROM {DB}.OPTA_EVENTS WHERE EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'")
        
        # Mål-sekvenser (Data til T4)
        sql_goals = f"SELECT e.MATCH_OPTAUUID, e.EVENT_TIMESTAMP as GOAL_TIME, e.EVENT_CONTESTANT_OPTAUUID as SCORING_TEAM, e.EVENT_TIMEMIN as GOAL_MIN, m.CONTESTANTHOME_NAME, m.CONTESTANTAWAY_NAME, m.CONTESTANTHOME_OPTAUUID, m.CONTESTANTAWAY_OPTAUUID, m.MATCH_LOCALDATE FROM {DB}.OPTA_EVENTS e JOIN {DB}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID WHERE e.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}' AND e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND (e.EVENT_TYPEID = 16 OR q.QUALIFIER_QID = 28) QUALIFY ROW_NUMBER() OVER (PARTITION BY e.MATCH_OPTAUUID, e.EVENT_TIMESTAMP ORDER BY e.EVENT_EVENTID) = 1"
        sql_events = f"WITH Goals AS ({sql_goals}) SELECT e.*, g.GOAL_TIME, g.SCORING_TEAM as GOAL_TEAM_ID, g.GOAL_MIN, g.CONTESTANTHOME_NAME, g.CONTESTANTAWAY_NAME, g.CONTESTANTHOME_OPTAUUID, g.CONTESTANTAWAY_OPTAUUID, g.MATCH_LOCALDATE FROM {DB}.OPTA_EVENTS e INNER JOIN Goals g ON e.MATCH_OPTAUUID = g.MATCH_OPTAUUID WHERE e.EVENT_TIMESTAMP >= DATEADD(second, -12, g.GOAL_TIME) AND e.EVENT_TIMESTAMP <= g.GOAL_TIME AND e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND e.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}' QUALIFY ROW_NUMBER() OVER (PARTITION BY e.EVENT_OPTAUUID, g.GOAL_TIME ORDER BY e.EVENT_TIMESTAMP DESC) = 1"
        df_all_events = conn.query(sql_events)

    t1, t2, t3, t4, t5 = st.tabs(["OVERSIGT", "MED BOLDEN", "UDEN BOLDEN", "MÅL-SEKVENSER", "SPILLEROVERSIGT"])

    with t1:
        sql_res = f"SELECT MATCH_LOCALDATE as DATO, CONTESTANTHOME_NAME as HJEMME, CONTESTANTAWAY_NAME as UDE, TOTAL_HOME_SCORE as \"MÅL H\", TOTAL_AWAY_SCORE as \"MÅL U\" FROM {DB}.OPTA_MATCHINFO WHERE (CONTESTANTHOME_OPTAUUID = '{valgt_uuid}' OR CONTESTANTAWAY_OPTAUUID = '{valgt_uuid}') AND TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}' ORDER BY MATCH_LOCALDATE DESC LIMIT 5"
        st.dataframe(conn.query(sql_res), hide_index=True)

    # --- T2: MED BOLDEN ---
    with t2:
        cp, cs = st.columns([2, 1])
        with cs:
            v_med = st.selectbox("Fokus", ["Opbygning", "Gennembrud", "Afleveringer (Alt)"], key="ms")
            st.divider()
            
        if v_med == "Opbygning":
            ids, tit, cm, zn = [1], "OPBYGNING (0-55)", "Blues", "up"
            sql = f"SELECT PLAYER_NAME, COUNT(*) as ANTAL FROM {DB}.OPTA_EVENTS WHERE EVENT_CONTESTANT_OPTAUUID='{valgt_uuid}' AND EVENT_TYPEID=1 AND EVENT_X <= 55 AND TOURNAMENTCALENDAR_OPTAUUID='{LIGA_UUID}' GROUP BY 1 ORDER BY 2 DESC LIMIT 5"
        elif v_med == "Gennembrud":
            ids, tit, cm, zn = [1], "GENNEMBRUD (55-105)", "Reds", "down"
            sql = f"SELECT PLAYER_NAME, COUNT(*) as ANTAL FROM {DB}.OPTA_EVENTS WHERE EVENT_CONTESTANT_OPTAUUID='{valgt_uuid}' AND EVENT_TYPEID=1 AND EVENT_X > 55 AND TOURNAMENTCALENDAR_OPTAUUID='{LIGA_UUID}' GROUP BY 1 ORDER BY 2 DESC LIMIT 5"
        else:
            ids, tit, cm, zn = [1], "AFLEVERINGER (ALT)", "Greens", "full"
            sql = f"SELECT PLAYER_NAME, COUNT(*) as ANTAL FROM {DB}.OPTA_EVENTS WHERE EVENT_CONTESTANT_OPTAUUID='{valgt_uuid}' AND EVENT_TYPEID=1 AND TOURNAMENTCALENDAR_OPTAUUID='{LIGA_UUID}' GROUP BY 1 ORDER BY 2 DESC LIMIT 5"

        with cp: st.pyplot(plot_custom_pitch(df_all_h, ids, tit, zone=zn, cmap=cm, logo=hold_logo))
        with cs:
            st.write(f"**Top 5: {v_med}**")
            df_r = conn.query(sql)
            for _, r in df_r.iterrows(): st.write(f"{int(r['ANTAL'])} **{r['PLAYER_NAME']}**")

    # --- T3: UDEN BOLDEN ---
    with t3:
        cp, cs = st.columns([2, 1])
        with cs:
            v_uden = st.selectbox("Fokus", ["Tacklinger", "Erobringer", "Defensiv Zone"], key="us")
            st.divider()
        if v_uden == "Tacklinger":
            ids, tit, cm, zn = [7, 8], "TACKLINGER", "Blues", "up" # Defensivt fokus (0-55)
        elif v_uden == "Erobringer":
            ids, tit, cm, zn = [127, 12], "EROBRINGER", "GnBu", "full"
        else:
            ids, tit, cm, zn = [7, 127, 12], "DEF. ZONE", "PuBu", "up"
        
        sql_u = f"SELECT PLAYER_NAME, COUNT(*) as ANTAL FROM {DB}.OPTA_EVENTS WHERE EVENT_CONTESTANT_OPTAUUID='{valgt_uuid}' AND EVENT_TYPEID IN {tuple(ids) if len(ids)>1 else '('+str(ids[0])+')'} AND TOURNAMENTCALENDAR_OPTAUUID='{LIGA_UUID}' GROUP BY 1 ORDER BY 2 DESC LIMIT 5"
        
        with cp: st.pyplot(plot_custom_pitch(df_all_h, ids, tit, zone=zn, cmap=cm, logo=hold_logo))
        with cs:
            st.write(f"**Top 5: {v_uden}**")
            df_r = conn.query(sql_u)
            for _, r in df_r.iterrows(): st.write(f"{int(r['ANTAL'])} **{r['PLAYER_NAME']}**")

    # --- T4 & T5 forbliver som før ---
    with t4:
        if not df_all_events.empty:
            gl = df_all_events.drop_duplicates(['MATCH_OPTAUUID', 'GOAL_TIME']).sort_values('GOAL_TIME', ascending=False)
            opts = {f"{r['MATCH_OPTAUUID']}_{r['GOAL_TIME']}": {'label': f"{pd.to_datetime(r['MATCH_LOCALDATE']).strftime('%d/%m/%Y')} vs. {r['CONTESTANTAWAY_NAME'] if r['CONTESTANTHOME_OPTAUUID']==valgt_uuid else r['CONTESTANTHOME_NAME']} ({r['GOAL_MIN']}. min)", 'match_id': r['MATCH_OPTAUUID'], 'goal_ts': r['GOAL_TIME'], 'opp_uuid': r['CONTESTANTAWAY_OPTAUUID'] if r['CONTESTANTHOME_OPTAUUID']==valgt_uuid else r['CONTESTANTHOME_OPTAUUID'], 'min': r['GOAL_MIN'], 'date': pd.to_datetime(r['MATCH_LOCALDATE']).strftime('%d/%m/%Y')} for _, r in gl.iterrows()}
            sk = st.selectbox("Vælg mål", list(opts.keys()), format_func=lambda x: opts[x]['label'])
            sd = opts[sk]
            tge = df_all_events[(df_all_events['MATCH_OPTAUUID'] == sd['match_id']) & (df_all_events['GOAL_TIME'] == sd['goal_ts'])].sort_values('EVENT_TIMESTAMP')
            p_c, l_c = st.columns([2.5, 1])
            with p_c:
                p = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='grey')
                f, ax = p.draw(figsize=(10, 7))
                draw_match_info_box(ax, hold_logo, get_logo_img(sd['opp_uuid']), sd['date'], "Mål", sd['min'])
                for i in range(len(tge)-1): p.arrows(tge.iloc[i]['EVENT_X'], tge.iloc[i]['EVENT_Y'], tge.iloc[i+1]['EVENT_X'], tge.iloc[i+1]['EVENT_Y'], width=1, headwidth=3, color='black', alpha=0.15, ax=ax)
                for _, r in tge.iterrows():
                    c, m, s = ('red', 's', 180) if r['EVENT_TYPEID'] == 16 else (('gold', 'P', 200) if r['EVENT_TYPEID'] == 5 else ('red', 'o', 80))
                    ax.scatter(r['EVENT_X'], r['EVENT_Y'], color=c, s=s, marker=m, edgecolors='black', zorder=10)
                    ax.text(r['EVENT_X'], r['EVENT_Y']+2.5, r['PLAYER_NAME'], fontsize=7, ha='center', fontweight='bold', bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
                st.pyplot(f)
            with l_c:
                tge['Aktion'] = tge['EVENT_TYPEID'].astype(str).map(OPTA_EVENT_TYPES)
                st.write("**Sekvens:**"); st.dataframe(tge[['PLAYER_NAME', 'Aktion']].iloc[::-1], hide_index=True)

    with t5:
        if not df_all_events.empty:
            stats = df_all_events.groupby('PLAYER_NAME').agg({'EVENT_TYPEID': [lambda x: (x == 16).sum(), lambda x: (x == 7).sum(), lambda x: (x == 127).sum(), lambda x: (x == 1).sum()]})
            stats.columns = ['Mål', 'Tacklinger før mål', 'Interceptions før mål', 'Pasninger i mål-sekvens']
            st.dataframe(stats.sort_values('Mål', ascending=False))

if __name__ == "__main__":
    vis_side()
