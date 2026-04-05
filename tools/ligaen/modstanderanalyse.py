import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
from mplsoccer import Pitch, VerticalPitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS
from data.utils.mapping import OPTA_EVENT_TYPES
import requests
from PIL import Image
from io import BytesIO

# --- 1. KONFIGURATION & CSS ---
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7')" 

st.set_page_config(layout="wide")

st.markdown("""
    <style>
        [data-testid="stDataFrame"] { border: 1px solid #e6e9ef; border-radius: 10px; }
        .block-container { padding-top: 1.5rem; padding-bottom: 0rem; }
        [data-testid="stMetricValue"] { font-size: 22px; font-weight: 700; }
        /* Gør tabs mere kompakte */
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] { height: 38px; background-color: #f0f2f6; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

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
        ax_l1.imshow(scoring_team_logo); ax_l1.axis('off')
    ax.text(0.08, 0.105, "vs.", transform=ax.transAxes, fontsize=8, fontweight='bold', va='center')
    if opp_team_logo:
        ax_l2 = ax.inset_axes([0.10, 0.08, 0.05, 0.05], transform=ax.transAxes)
        ax_l2.imshow(opp_team_logo); ax_l2.axis('off')
    ax.text(0.03, 0.07, f"{date_str} | {score_str} ({min_str}. min)", transform=ax.transAxes, fontsize=8, color='#444444', va='top')

def plot_custom_pitch(df, event_ids, title, zone='full', cmap='Reds', logo=None):
    plot_data = df[df['EVENT_TYPEID'].isin(event_ids)].copy()
    pitch = VerticalPitch(pitch_type='opta', half=False, pitch_color='#ffffff', line_color='#BDBDBD')
    fig, ax = pitch.draw(figsize=(5, 7))
    if zone == 'up': ax.set_ylim(0, 55); logo_pos, text_y = [0.04, 0.03, 0.08, 0.08], 0.05
    else: ax.set_ylim(45, 100) if zone == 'down' else None; logo_pos, text_y = [0.04, 0.90, 0.08, 0.08], 0.97
    if logo:
        ax_logo = ax.inset_axes(logo_pos, transform=ax.transAxes)
        ax_logo.imshow(logo); ax_logo.axis('off')
    ax.text(0.94, text_y, title, transform=ax.transAxes, fontsize=6, fontweight='bold', ha='right', color='#333333')
    if not plot_data.empty:
        pitch.kdeplot(plot_data.EVENT_X, plot_data.EVENT_Y, ax=ax, cmap=cmap, fill=True, alpha=0.5, levels=100)
    return fig

# --- 3. HOVEDFUNKTION ---
def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn: return

    # Team mapping
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
    ids = df_teams_raw['CONTESTANTHOME_OPTAUUID'].unique()
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    team_map = {mapping_lookup.get(str(u).lower().replace('t','')): u for u in ids if mapping_lookup.get(str(u).lower().replace('t',''))}

    c_sp, c_hold = st.columns([3, 1])
    valgt_hold = c_hold.selectbox("Vælg hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid)

    with st.spinner("Henter data..."):
        # Seneste 10 kampe
        sql_res = f"SELECT MATCH_LOCALDATE, CONTESTANTHOME_NAME, CONTESTANTAWAY_NAME, TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE, CONTESTANTHOME_OPTAUUID, CONTESTANTAWAY_OPTAUUID, MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE (CONTESTANTHOME_OPTAUUID = '{valgt_uuid}' OR CONTESTANTAWAY_OPTAUUID = '{valgt_uuid}') AND TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS} AND (MATCH_STATUS ILIKE '%Played%' OR MATCH_STATUS ILIKE '%Full%') ORDER BY MATCH_LOCALDATE DESC LIMIT 10"
        df_res = conn.query(sql_res)
        if df_res is None or df_res.empty: return st.warning("Ingen data fundet.")

        m_ids = tuple(df_res['MATCH_OPTAUUID'].tolist())
        m_ids_str = f"('{m_ids[0]}')" if len(m_ids) == 1 else str(m_ids)

        # Alle events for volumen og tabeller
        df_all_h = conn.query(f"SELECT EVENT_X, EVENT_Y, EVENT_TYPEID, PLAYER_NAME, MATCH_OPTAUUID, EVENT_TIMESTAMP FROM {DB}.OPTA_EVENTS WHERE EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND MATCH_OPTAUUID IN {m_ids_str}")
        
        # Mål-sekvenser (Din fulde query)
        sql_goals = f"SELECT e.MATCH_OPTAUUID, e.EVENT_TIMESTAMP as GOAL_TIME, e.EVENT_TIMEMIN as GOAL_MIN, m.CONTESTANTHOME_NAME, m.CONTESTANTAWAY_NAME, m.CONTESTANTHOME_OPTAUUID, m.CONTESTANTAWAY_OPTAUUID, m.MATCH_LOCALDATE FROM {DB}.OPTA_EVENTS e JOIN {DB}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID WHERE e.MATCH_OPTAUUID IN {m_ids_str} AND e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND (e.EVENT_TYPEID = 16 OR q.QUALIFIER_QID = 28) QUALIFY ROW_NUMBER() OVER (PARTITION BY e.MATCH_OPTAUUID, e.EVENT_TIMESTAMP ORDER BY e.EVENT_EVENTID) = 1"
        sql_events = f"WITH Goals AS ({sql_goals}) SELECT e.*, g.GOAL_TIME, g.GOAL_MIN, g.CONTESTANTHOME_NAME, g.CONTESTANTAWAY_NAME, g.CONTESTANTHOME_OPTAUUID, g.CONTESTANTAWAY_OPTAUUID, g.MATCH_LOCALDATE FROM {DB}.OPTA_EVENTS e INNER JOIN Goals g ON e.MATCH_OPTAUUID = g.MATCH_OPTAUUID WHERE e.EVENT_TIMESTAMP >= DATEADD(second, -12, g.GOAL_TIME) AND e.EVENT_TIMESTAMP <= g.GOAL_TIME AND e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}'"
        df_all_events = conn.query(sql_events)

    t1, t2, t3, t4, t5 = st.tabs(["OVERSIGT", "MED BOLDEN", "UDEN BOLDEN", "MÅL-SEKVENSER", "SPILLEROVERSIGT"])

    with t1:
        # KPI og Tabel
        df_res['RES'] = df_res.apply(lambda r: "D" if r['TOTAL_HOME_SCORE'] == r['TOTAL_AWAY_SCORE'] else ("W" if (r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid and r['TOTAL_HOME_SCORE'] > r['TOTAL_AWAY_SCORE']) or (r['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid and r['TOTAL_AWAY_SCORE'] > r['TOTAL_HOME_SCORE']) else "L"), axis=1)
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Point (10k)", (df_res['RES']=="W").sum()*3 + (df_res['RES']=="D").sum())
        k2.metric("Vundne", (df_res['RES']=="W").sum())
        k3.metric("Mål Scoret", int(df_res.apply(lambda r: r['TOTAL_HOME_SCORE'] if r['CONTESTANTHOME_OPTAUUID']==valgt_uuid else r['TOTAL_AWAY_SCORE'], axis=1).sum()))
        k4.metric("Mål Imod", int(df_res.apply(lambda r: r['TOTAL_AWAY_SCORE'] if r['CONTESTANTHOME_OPTAUUID']==valgt_uuid else r['TOTAL_HOME_SCORE'], axis=1).sum()))

        st.dataframe(df_res[['MATCH_LOCALDATE', 'CONTESTANTHOME_NAME', 'TOTAL_HOME_SCORE', 'TOTAL_AWAY_SCORE', 'CONTESTANTAWAY_NAME', 'RES']], hide_index=True, use_container_width=True, height=200)

        # Plotly Grafer (Fikset for Duplicate Labels)
        df_vol = df_all_h.groupby('MATCH_OPTAUUID').agg(P=('EVENT_TYPEID', lambda x: (x == 1).sum()), A=('EVENT_TYPEID', lambda x: x.isin([13,14,15,16]).sum())).reset_index()
        df_p = df_res.merge(df_vol, on='MATCH_OPTAUUID', how='left').fillna(0).sort_values('MATCH_LOCALDATE')
        df_p['X'] = pd.to_datetime(df_p['MATCH_LOCALDATE']).dt.strftime('%d/%m') + " " + df_p.apply(lambda r: r['CONTESTANTAWAY_NAME'] if r['CONTESTANTHOME_OPTAUUID']==valgt_uuid else r['CONTESTANTHOME_NAME'], axis=1).str[:3]

        g1, g2 = st.columns(2)
        l_cfg = dict(height=180, margin=dict(t=5, b=5, l=0, r=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis=dict(showgrid=False, tickfont_size=10, type='category'), yaxis=dict(showgrid=False, visible=False))
        
        with g1:
            st.caption("**Pasninger**")
            fig = px.bar(df_p, x='X', y='P', text='P'); fig.update_traces(textposition='outside', marker_color='#0047AB'); fig.update_layout(**l_cfg)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        with g2:
            st.caption("**Afslutninger**")
            fig = px.bar(df_p, x='X', y='A', text='A'); fig.update_traces(textposition='outside', marker_color='#C8102E'); fig.update_layout(**l_cfg)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    with t2:
        cp, cs = st.columns([2, 1])
        with cs:
            v_med = st.selectbox("Fokus", ["Opbygning", "Gennembrud", "Afslutninger"])
            ids, tit, cm, zn = ([1], "OPBYGNING", "Blues", "up") if v_med=="Opbygning" else (([1], "GENNEMBRUD", "Reds", "down") if v_med=="Gennembrud" else ([13,14,15,16], "AFSLUTNINGER", "YlOrRd", "down"))
            df_t = df_all_h[df_all_h['EVENT_TYPEID'].isin(ids)].groupby('PLAYER_NAME').size().reset_index(name='n').sort_values('n', ascending=False).head(5)
            for _, r in df_t.iterrows(): st.write(f"{int(r['n'])} **{r['PLAYER_NAME']}**")
        with cp: st.pyplot(plot_custom_pitch(df_all_h, ids, tit, zone=zn, cmap=cm, logo=hold_logo))

    with t3:
        cp, cs = st.columns([2, 1])
        with cs:
            v_u = st.selectbox("Fokus ", ["Dueller", "Erobringer", "Defensiv Zone"])
            ids, tit, cm = ([7,8], "DUELLER", "Blues") if v_u=="Dueller" else (([127,12,49], "EROBRINGER", "GnBu") if v_u=="Erobringer" else ([7,12,127], "DEFENSIV ZONE", "PuBu"))
            df_t = df_all_h[df_all_h['EVENT_TYPEID'].isin(ids)].groupby('PLAYER_NAME').size().reset_index(name='n').sort_values('n', ascending=False).head(5)
            for _, r in df_t.iterrows(): st.write(f"{int(r['n'])} **{r['PLAYER_NAME']}**")
        with cp: st.pyplot(plot_custom_pitch(df_all_h, ids, tit, zone='up', cmap=cm, logo=hold_logo))

    with t4:
        if df_all_events is not None and not df_all_events.empty:
            gl = df_all_events.drop_duplicates(['MATCH_OPTAUUID', 'GOAL_TIME']).sort_values('GOAL_TIME', ascending=False)
            opts = {f"{r['MATCH_OPTAUUID']}_{r['GOAL_TIME']}": {'label': f"{pd.to_datetime(r['MATCH_LOCALDATE']).strftime('%d/%m')} vs {r['CONTESTANTAWAY_NAME'] if r['CONTESTANTHOME_OPTAUUID']==valgt_uuid else r['CONTESTANTHOME_NAME']} ({r['GOAL_MIN']}. min)", 'match_id': r['MATCH_OPTAUUID'], 'goal_ts': r['GOAL_TIME'], 'opp': r['CONTESTANTAWAY_OPTAUUID'] if r['CONTESTANTHOME_OPTAUUID']==valgt_uuid else r['CONTESTANTHOME_OPTAUUID'], 'min': r['GOAL_MIN'], 'date': pd.to_datetime(r['MATCH_LOCALDATE']).strftime('%d/%m/%Y')} for _, r in gl.iterrows()}
            sk = st.selectbox("Vælg mål", list(opts.keys()), format_func=lambda x: opts[x]['label'])
            sd = opts[sk]; tge = df_all_events[(df_all_events['MATCH_OPTAUUID'] == sd['match_id']) & (df_all_events['GOAL_TIME'] == sd['goal_ts'])].sort_values('EVENT_TIMESTAMP')
            p_c, l_c = st.columns([2.5, 1])
            with p_c:
                p = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='grey'); f, ax = p.draw(figsize=(10, 7))
                draw_match_info_box(ax, hold_logo, get_logo_img(sd['opp']), sd['date'], "Mål", sd['min'])
                for i in range(len(tge)-1): p.arrows(tge.iloc[i]['EVENT_X'], tge.iloc[i]['EVENT_Y'], tge.iloc[i+1]['EVENT_X'], tge.iloc[i+1]['EVENT_Y'], width=1, color='black', alpha=0.15, ax=ax)
                for _, r in tge.iterrows():
                    c, m, s = ('red', 's', 180) if r['EVENT_TYPEID'] == 16 else (('gold', 'P', 200) if r['EVENT_TYPEID'] == 5 else ('red', 'o', 80))
                    ax.scatter(r['EVENT_X'], r['EVENT_Y'], color=c, s=s, marker=m, edgecolors='black', zorder=10)
                    ax.text(r['EVENT_X'], r['EVENT_Y']+2.5, r['PLAYER_NAME'], fontsize=7, ha='center', fontweight='bold')
                st.pyplot(f)
            with l_c:
                tge['Aktion'] = tge['EVENT_TYPEID'].astype(str).map(OPTA_EVENT_TYPES)
                st.write("**Sekvens:**"); st.dataframe(tge[['PLAYER_NAME', 'Aktion']].iloc[::-1], hide_index=True)
        else: st.info("Ingen mål fundet i de seneste 10 kampe.")

    with t5:
        if not df_all_h.empty:
            df_all_h['Pasninger'] = (df_all_h['EVENT_TYPEID'] == 1).astype(int)
            df_all_h['Erobringer'] = df_all_h['EVENT_TYPEID'].isin([7,8,12,49,67,127,73,74]).astype(int)
            df_all_h['Skud'] = df_all_h['EVENT_TYPEID'].isin([13,14,15,16]).astype(int)
            stats = df_all_h.groupby('PLAYER_NAME').agg({'Pasninger': 'sum', 'Erobringer': 'sum', 'Skud': 'sum', 'EVENT_TYPEID': 'count'}).rename(columns={'EVENT_TYPEID': 'Total'}).sort_values('Total', ascending=False)
            st.dataframe(stats, use_container_width=True)

if __name__ == "__main__":
    vis_side()
