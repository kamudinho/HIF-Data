import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch, VerticalPitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS, TEAM_COLORS
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
    clean_uuid = str(opta_uuid).strip().upper()
    url = next((info['logo'] for name, info in TEAMS.items() if str(info.get('opta_uuid')).strip().upper() == clean_uuid), None)
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
    if df is None or df.empty: return plt.figure()
    plot_data = df[df['EVENT_TYPEID'].isin(event_ids)].copy()
    pitch = VerticalPitch(pitch_type='opta', half=False, pitch_color='#ffffff', line_color='#BDBDBD')
    fig, ax = pitch.draw(figsize=(5, 7))
    if zone == 'up': ax.set_ylim(0, 55)
    elif zone == 'down': ax.set_ylim(45, 100)
    if logo:
        ax_logo = ax.inset_axes([0.04, 0.90, 0.08, 0.08], transform=ax.transAxes)
        ax_logo.imshow(logo); ax_logo.axis('off')
    ax.text(0.94, 0.97, title, transform=ax.transAxes, fontsize=5.5, fontweight='bold', ha='right', va='top')
    if not plot_data.empty:
        pitch.kdeplot(plot_data.EVENT_X, plot_data.EVENT_Y, ax=ax, cmap=cmap, fill=True, alpha=0.5, levels=100)
    return fig

# --- 3. HOVEDFUNKTION ---
def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn: return

    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == "1. Division"}
    h_list = sorted(liga_hold_options.keys())
    col_spacer, col_hold = st.columns([3, 1])
    valgt_hold = col_hold.selectbox("Vælg hold", h_list, label_visibility="collapsed")
    valgt_uuid = str(liga_hold_options[valgt_hold]).strip().upper()
    hold_logo = get_logo_img(valgt_uuid)

    # SQL til 10 seneste kampe inkl. Stats fra StatsPivot (Inspiration fra test_matches.py)
    sql_matches = f"""
        WITH MatchBase AS (
            SELECT MATCH_OPTAUUID, MATCH_DATE_FULL, CONTESTANTHOME_NAME, CONTESTANTAWAY_NAME,
                   TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE, CONTESTANTHOME_OPTAUUID, CONTESTANTAWAY_OPTAUUID, MATCH_STATUS
            FROM {DB}.OPTA_MATCHINFO
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
            AND (CONTESTANTHOME_OPTAUUID = '{valgt_uuid}' OR CONTESTANTAWAY_OPTAUUID = '{valgt_uuid}')
        ),
        StatsPivot AS (
            SELECT MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
                   SUM(CASE WHEN STAT_TYPE = 'totalPass' THEN STAT_TOTAL ELSE 0 END) AS PASSES,
                   SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_TOTAL ELSE 0 END) AS SHOTS
            FROM {DB}.OPTA_MATCHSTATS GROUP BY 1, 2
        )
        SELECT b.*, h.PASSES AS H_PASS, h.SHOTS AS H_SHOTS, a.PASSES AS A_PASS, a.SHOTS AS A_SHOTS
        FROM MatchBase b
        LEFT JOIN StatsPivot h ON b.MATCH_OPTAUUID = h.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = h.CONTESTANT_OPTAUUID
        LEFT JOIN StatsPivot a ON b.MATCH_OPTAUUID = a.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = a.CONTESTANT_OPTAUUID
        WHERE b.MATCH_STATUS ILIKE '%Full%' OR b.MATCH_STATUS ILIKE '%Played%' OR b.MATCH_STATUS ILIKE '%Finish%'
        ORDER BY b.MATCH_DATE_FULL DESC LIMIT 10
    """

    df_res = conn.query(sql_matches)
    if df_res is None or df_res.empty:
        st.warning("Ingen data fundet."); return

    df_res.columns = [c.upper() for c in df_res.columns]
    match_ids = tuple(df_res['MATCH_OPTAUUID'].astype(str).str.strip().tolist())
    match_ids_str = f"('{match_ids[0]}')" if len(match_ids) == 1 else str(match_ids)

    # Data til T2, T3 og T5
    df_all_h = conn.query(f"SELECT EVENT_X, EVENT_Y, EVENT_TYPEID, PLAYER_NAME, MATCH_OPTAUUID, EVENT_TIMESTAMP FROM {DB}.OPTA_EVENTS WHERE EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND MATCH_OPTAUUID IN {match_ids_str}")

    # SQL til T4: MÅL-SEKVENSER (DIN ORIGINALE QUERY)
    sql_goals = f"SELECT e.MATCH_OPTAUUID, e.EVENT_TIMESTAMP as GOAL_TIME, e.EVENT_CONTESTANT_OPTAUUID as SCORING_TEAM, e.EVENT_TIMEMIN as GOAL_MIN, m.CONTESTANTHOME_NAME, m.CONTESTANTAWAY_NAME, m.CONTESTANTHOME_OPTAUUID, m.CONTESTANTAWAY_OPTAUUID, m.MATCH_LOCALDATE FROM {DB}.OPTA_EVENTS e JOIN {DB}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID WHERE e.MATCH_OPTAUUID IN {match_ids_str} AND e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND (e.EVENT_TYPEID = 16 OR q.QUALIFIER_QID = 28) QUALIFY ROW_NUMBER() OVER (PARTITION BY e.MATCH_OPTAUUID, e.EVENT_TIMESTAMP ORDER BY e.EVENT_EVENTID) = 1"
    sql_events = f"WITH Goals AS ({sql_goals}) SELECT e.*, g.GOAL_TIME, g.SCORING_TEAM as GOAL_TEAM_ID, g.GOAL_MIN, g.CONTESTANTHOME_NAME, g.CONTESTANTAWAY_NAME, g.CONTESTANTHOME_OPTAUUID, g.CONTESTANTAWAY_OPTAUUID, g.MATCH_LOCALDATE FROM {DB}.OPTA_EVENTS e INNER JOIN Goals g ON e.MATCH_OPTAUUID = g.MATCH_OPTAUUID WHERE e.EVENT_TIMESTAMP >= DATEADD(second, -12, g.GOAL_TIME) AND e.EVENT_TIMESTAMP <= g.GOAL_TIME AND e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' QUALIFY ROW_NUMBER() OVER (PARTITION BY e.EVENT_OPTAUUID, g.GOAL_TIME ORDER BY e.EVENT_TIMESTAMP DESC) = 1"
    df_all_events = conn.query(sql_events)

    t1, t2, t3, t4, t5 = st.tabs(["OVERSIGT", "MED BOLDEN", "UDEN BOLDEN", "MÅL-SEKVENSER", "SPILLEROVERSIGT"])

    with t1:
        def check_res(r):
            is_h = str(r['CONTESTANTHOME_OPTAUUID']).strip().upper() == valgt_uuid
            h_s, a_s = int(r['TOTAL_HOME_SCORE'] or 0), int(r['TOTAL_AWAY_SCORE'] or 0)
            if h_s == a_s: return "D"
            return "W" if (is_h and h_s > a_s) or (not is_h and a_s > h_s) else "L"
        df_res['RES'] = df_res.apply(check_res, axis=1)
        
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Vundne", (df_res['RES']=="W").sum())
        k2.metric("Uafgjorte", (df_res['RES']=="D").sum())
        m_s = sum([r['TOTAL_HOME_SCORE'] if str(r['CONTESTANTHOME_OPTAUUID']).strip().upper() == valgt_uuid else r['TOTAL_AWAY_SCORE'] for _, r in df_res.iterrows()])
        m_i = sum([r['TOTAL_AWAY_SCORE'] if str(r['CONTESTANTHOME_OPTAUUID']).strip().upper() == valgt_uuid else r['TOTAL_HOME_SCORE'] for _, r in df_res.iterrows()])
        k3.metric("Mål Scoret", int(m_s)); k4.metric("Mål Imod", int(m_i))

        st.dataframe(df_res[['MATCH_DATE_FULL', 'CONTESTANTHOME_NAME', 'TOTAL_HOME_SCORE', 'TOTAL_AWAY_SCORE', 'CONTESTANTAWAY_NAME', 'RES']], hide_index=True, use_container_width=True)
        
        df_plot = df_res.copy().iloc[::-1]
        df_plot['MODSTANDER'] = df_plot.apply(lambda r: r['CONTESTANTAWAY_NAME'] if str(r['CONTESTANTHOME_OPTAUUID']).strip().upper() == valgt_uuid else r['CONTESTANTHOME_NAME'], axis=1)
        df_plot['P_VAL'] = df_plot.apply(lambda r: r['H_PASS'] if str(r['CONTESTANTHOME_OPTAUUID']).strip().upper() == valgt_uuid else r['A_PASS'], axis=1)
        df_plot['S_VAL'] = df_plot.apply(lambda r: r['H_SHOTS'] if str(r['CONTESTANTHOME_OPTAUUID']).strip().upper() == valgt_uuid else r['A_SHOTS'], axis=1)

        g1, g2 = st.columns(2)
        with g1: st.write("**Pasninger**"); st.bar_chart(df_plot, x='MODSTANDER', y='P_VAL', color='#0047AB')
        with g2: st.write("**Afslutninger**"); st.bar_chart(df_plot, x='MODSTANDER', y='S_VAL', color='#C8102E')

    with t2:
        cp, cs = st.columns([2, 1])
        with cs:
            v = st.selectbox("Fokus", ["Opbygning", "Gennembrud", "Afslutninger"])
            ids, tit, cm, zn = ([1], "OPBYGNING", "Blues", "up") if v=="Opbygning" else (([1], "GENNEMBRUD", "Reds", "down") if v=="Gennembrud" else ([13,14,15,16], "AFSLUTNINGER", "YlOrRd", "down"))
            df_top = df_all_h[df_all_h['EVENT_TYPEID'].isin(ids)].groupby('PLAYER_NAME').size().reset_index(name='N').sort_values('N', ascending=False).head(5)
            for _, r in df_top.iterrows(): st.write(f"{int(r['N'])} **{r['PLAYER_NAME']}**")
        with cp: st.pyplot(plot_custom_pitch(df_all_h, ids, tit, zone=zn, cmap=cm, logo=hold_logo))

    with t3:
        cp, cs = st.columns([2, 1])
        with cs:
            v_u = st.selectbox("Type", ["Dueller", "Erobringer"])
            ids, tit, cm = ([7, 8], "DUELLER", "Blues") if v_u=="Dueller" else ([12, 127, 49], "EROBRINGER", "GnBu")
            df_top_u = df_all_h[df_all_h['EVENT_TYPEID'].isin(ids)].groupby('PLAYER_NAME').size().reset_index(name='N').sort_values('N', ascending=False).head(5)
            for _, r in df_top_u.iterrows(): st.write(f"{int(r['N'])} **{r['PLAYER_NAME']}**")
        with cp: st.pyplot(plot_custom_pitch(df_all_h, ids, tit, zone='up', cmap=cm, logo=hold_logo))

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
        regain_ids = [7, 8, 12, 49, 67, 127, 73, 74]
        df_all_h['is_pass'] = (df_all_h['EVENT_TYPEID'] == 1).astype(int)
        df_all_h['is_regain'] = df_all_h['EVENT_TYPEID'].isin(regain_ids).astype(int)
        df_all_h['is_shot'] = df_all_h['EVENT_TYPEID'].isin([13,14,15,16]).astype(int)
        stats = df_all_h.groupby('PLAYER_NAME').agg({'is_pass': 'sum', 'is_regain': 'sum', 'is_shot': 'sum', 'EVENT_TYPEID': 'count'}).rename(columns={'EVENT_TYPEID': 'Total Aktioner', 'is_pass': 'Pasninger', 'is_regain': 'Erobringer', 'is_shot': 'Skud'}).sort_values('Total Aktioner', ascending=False)
        st.write("**Spillerstatistik (Sidste 10 kampe)**"); st.dataframe(stats, use_container_width=True)

if __name__ == "__main__":
    vis_side()
