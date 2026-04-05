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

# --- 3. HOVEDFUNKTION ---
def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn: return

    # Team selection
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'")
    ids = df_teams_raw['CONTESTANTHOME_OPTAUUID'].unique()
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    team_map = {mapping_lookup.get(str(u).lower().replace('t','')): u for u in ids if mapping_lookup.get(str(u).lower().replace('t',''))}

    col_spacer, col_hold = st.columns([3, 1])
    valgt_hold = col_hold.selectbox("Vælg hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid)

    with st.spinner(f"Henter data for {valgt_hold}..."):
        # 1. Hent 10 seneste kampe
        sql_res = f"SELECT MATCH_LOCALDATE, CONTESTANTHOME_NAME, CONTESTANTAWAY_NAME, TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE, CONTESTANTHOME_OPTAUUID, CONTESTANTAWAY_OPTAUUID, MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE (CONTESTANTHOME_OPTAUUID = '{valgt_uuid}' OR CONTESTANTAWAY_OPTAUUID = '{valgt_uuid}') AND TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}' ORDER BY MATCH_LOCALDATE DESC LIMIT 10"
        df_res = conn.query(sql_res)
        
        if df_res.empty:
            st.warning("Ingen data fundet.")
            return

        # VIGTIGT: Rens UUIDs med strip() for at sikre merge virker
        df_res['MATCH_OPTAUUID'] = df_res['MATCH_OPTAUUID'].astype(str).str.strip()
        match_ids = tuple(df_res['MATCH_OPTAUUID'].tolist())
        match_ids_str = f"('{match_ids[0]}')" if len(match_ids) == 1 else str(match_ids)

        # 2. Hent hændelser for alle 10 kampe (Vigtigt for T2/T3 volumen)
        df_all_h = conn.query(f"SELECT EVENT_X, EVENT_Y, EVENT_TYPEID, PLAYER_NAME, MATCH_OPTAUUID FROM {DB}.OPTA_EVENTS WHERE EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND MATCH_OPTAUUID IN {match_ids_str}")
        df_all_h['MATCH_OPTAUUID'] = df_all_h['MATCH_OPTAUUID'].astype(str).str.strip()

        # 3. Mål-sekvens data (Uændret som ønsket)
        sql_goals = f"SELECT e.MATCH_OPTAUUID, e.EVENT_TIMESTAMP as GOAL_TIME, e.EVENT_CONTESTANT_OPTAUUID as SCORING_TEAM, e.EVENT_TIMEMIN as GOAL_MIN, m.CONTESTANTHOME_NAME, m.CONTESTANTAWAY_NAME, m.CONTESTANTHOME_OPTAUUID, m.CONTESTANTAWAY_OPTAUUID, m.MATCH_LOCALDATE FROM {DB}.OPTA_EVENTS e JOIN {DB}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID WHERE e.MATCH_OPTAUUID IN {match_ids_str} AND e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND (e.EVENT_TYPEID = 16 OR q.QUALIFIER_QID = 28) QUALIFY ROW_NUMBER() OVER (PARTITION BY e.MATCH_OPTAUUID, e.EVENT_TIMESTAMP ORDER BY e.EVENT_EVENTID) = 1"
        sql_events = f"WITH Goals AS ({sql_goals}) SELECT e.*, g.GOAL_TIME, g.SCORING_TEAM as GOAL_TEAM_ID, g.GOAL_MIN, g.CONTESTANTHOME_NAME, g.CONTESTANTAWAY_NAME, g.CONTESTANTHOME_OPTAUUID, g.CONTESTANTAWAY_OPTAUUID, g.MATCH_LOCALDATE FROM {DB}.OPTA_EVENTS e INNER JOIN Goals g ON e.MATCH_OPTAUUID = g.MATCH_OPTAUUID WHERE e.EVENT_TIMESTAMP >= DATEADD(second, -12, g.GOAL_TIME) AND e.EVENT_TIMESTAMP <= g.GOAL_TIME AND e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' QUALIFY ROW_NUMBER() OVER (PARTITION BY e.EVENT_OPTAUUID, g.GOAL_TIME ORDER BY e.EVENT_TIMESTAMP DESC) = 1"
        df_all_events = conn.query(sql_events)

    t1, t2, t3, t4, t5 = st.tabs(["OVERSIGT", "MED BOLDEN", "UDEN BOLDEN", "MÅL-SEKVENSER", "SPILLEROVERSIGT"])

    # --- T1: OVERSIGT ---
    with t1:
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
        wins_5, draws_5 = (last_5['RES'] == "W").sum(), (last_5['RES'] == "D").sum()
        kpi1.metric("Point (Sidste 5)", f"{(wins_5*3)+draws_5}/15")
        kpi2.metric("Vundne (Sidste 10)", (df_res['RES'] == "W").sum())
        
        mål_s = sum([r['TOTAL_HOME_SCORE'] if r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else r['TOTAL_AWAY_SCORE'] for _, r in df_res.iterrows()])
        mål_i = sum([r['TOTAL_AWAY_SCORE'] if r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else r['TOTAL_HOME_SCORE'] for _, r in df_res.iterrows()])
        kpi3.metric("Mål Scoret (10 k)", mål_s)
        kpi4.metric("Mål Imod (10 k)", mål_i)

        st.dataframe(df_res[['MATCH_LOCALDATE', 'CONTESTANTHOME_NAME', 'TOTAL_HOME_SCORE', 'TOTAL_AWAY_SCORE', 'CONTESTANTAWAY_NAME', 'RES']], hide_index=True, use_container_width=True)
        
        # Grafer: Aggreger volumen pr. kamp
        df_vol = df_all_h.groupby('MATCH_OPTAUUID').agg(
            PASNINGER=('EVENT_TYPEID', lambda x: (x == 1).sum()),
            AFSLUTNINGER=('EVENT_TYPEID', lambda x: x.isin([13,14,15,16]).sum())
        ).reset_index()
        
        # Merge med kampskemaet for at få modstander-navne
        df_plot = df_res.merge(df_vol, on='MATCH_OPTAUUID', how='left').fillna(0).iloc[::-1]
        df_plot['MODSTANDER'] = df_plot.apply(lambda r: r['CONTESTANTAWAY_NAME'] if r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else r['CONTESTANTHOME_NAME'], axis=1)

        g1, g2 = st.columns(2)
        with g1:
            st.write("**Pasninger (Sidste 10)**")
            st.bar_chart(df_plot, x='MODSTANDER', y='PASNINGER', color='#0047AB')
        with g2:
            st.write("**Afslutninger (Sidste 10)**")
            st.bar_chart(df_plot, x='MODSTANDER', y='AFSLUTNINGER', color='#C8102E')

    # --- T2: MED BOLDEN (2000-3000 events) ---
    with t2:
        cp, cs = st.columns([2, 1])
        with cs:
            v_med = st.selectbox("Fokus", ["Opbygning", "Gennembrud", "Afslutninger"], key="ms")
            if v_med == "Opbygning":
                ids, tit, cm, zn = [1], "EGEN HALVDEL: OPBYGNING", "Blues", "up"
                filter_cond = df_all_h['EVENT_X'] <= 55
            elif v_med == "Gennembrud":
                ids, tit, cm, zn = [1], "OFF. HALVDEL: GENNEMBRUD", "Reds", "down"
                filter_cond = df_all_h['EVENT_X'] > 55
            else:
                ids, tit, cm, zn = [13, 14, 15, 16], "OFF. HALVDEL: AFSLUTNINGER", "YlOrRd", "down"
                filter_cond = True

            df_filtered = df_all_h[df_all_h['EVENT_TYPEID'].isin(ids) & filter_cond]
            df_top = df_filtered.groupby('PLAYER_NAME').size().reset_index(name='ANTAL').sort_values('ANTAL', ascending=False).head(5)
            
            st.write(f"**Top 5: {v_med}**")
            for _, r in df_top.iterrows(): st.write(f"{int(r['ANTAL'])} **{r['PLAYER_NAME']}**")
            st.caption(f"Baseret på {len(df_filtered)} aktioner over 10 kampe.")

        with cp: st.pyplot(plot_custom_pitch(df_all_h, ids, tit, zone=zn, cmap=cm, logo=hold_logo))

    # --- T3: UDEN BOLDEN (2000-3000 events) ---
    with t3:
        cp, cs = st.columns([2, 1])
        with cs:
            v_uden = st.selectbox("Fokus", ["Dueller", "Erobringer", "Defensiv Zone"], key="us")
            if v_uden == "Dueller":
                ids, tit, cm, zn = [7, 8], "DUELLER", "Blues", "up"
            elif v_uden == "Erobringer":
                ids, tit, cm, zn = [127, 12, 49], "EROBRINGER", "GnBu", "up"
            else:
                ids, tit, cm, zn = [7, 12, 127], "DEFENSIV ZONE", "PuBu", "up"
        
            df_filtered_u = df_all_h[df_all_h['EVENT_TYPEID'].isin(ids)]
            df_top_u = df_filtered_u.groupby('PLAYER_NAME').size().reset_index(name='ANTAL').sort_values('ANTAL', ascending=False).head(5)
            
            st.write(f"**Top 5: {v_uden}**")
            for _, r in df_top_u.iterrows(): st.write(f"{int(r['ANTAL'])} **{r['PLAYER_NAME']}**")
            st.caption(f"Baseret på {len(df_filtered_u)} aktioner over 10 kampe.")

        with cp: st.pyplot(plot_custom_pitch(df_all_h, ids, tit, zone=zn, cmap=cm, logo=hold_logo))

    # --- T4 & T5 (UÆNDRET) ---
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
            regain_ids = [7, 8, 12, 49, 67, 127, 73, 74]
            df_all_events['is_goal'] = (df_all_events['EVENT_TYPEID'] == 16).astype(int)
            df_all_events['is_pass'] = (df_all_events['EVENT_TYPEID'] == 1).astype(int)
            df_all_events['is_regain'] = df_all_events['EVENT_TYPEID'].isin(regain_ids).astype(int)
            df_all_events['is_touch'] = (df_all_events['EVENT_X'] > 66).astype(int)

            stats = df_all_events.groupby('PLAYER_NAME').agg({'is_pass': 'sum', 'is_regain': 'sum', 'is_touch': 'sum', 'is_goal': 'sum', 'EVENT_TYPEID': 'count'}).fillna(0)
            stats['Målinvolveringer'] = df_all_events.groupby('PLAYER_NAME')['GOAL_TIME'].nunique().fillna(0)
            stats = stats.rename(columns={'EVENT_TYPEID': 'Antal aktioner', 'is_pass': 'Pasninger', 'is_regain': 'Regains', 'is_touch': 'Touches', 'is_goal': 'Mål'})
            st.dataframe(stats[['Målinvolveringer', 'Antal aktioner', 'Pasninger', 'Regains', 'Touches', 'Mål']].astype(int).sort_values('Målinvolveringer', ascending=False), use_container_width=True)

if __name__ == "__main__":
    vis_side()
