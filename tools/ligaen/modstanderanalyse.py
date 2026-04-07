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

# --- 1. KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7')" 

# --- 2. HJÆLPEFUNKTIONER ---
@st.cache_data(ttl=3600)
def get_logo_img(opta_uuid):
    if not opta_uuid: return None
    url = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), None)
    if not url: return None
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except: return None

def draw_match_row(date, h_name, h_uuid, score, a_name, a_uuid, res_char):
    bg_color = "#2e7d32" if res_char == "W" else ("#757575" if res_char == "D" else "#c62828")
    cols = st.columns([0.6, 1.2, 0.3, 0.8, 0.3, 1.2, 0.4], vertical_alignment="center")
    with cols[0]: st.markdown(f"<span style='font-size:12px; color:#666;'>{date}</span>", unsafe_allow_html=True)
    with cols[1]: st.markdown(f"<div style='text-align:right; font-weight:600;'>{h_name[:12]}</div>", unsafe_allow_html=True)
    with cols[2]:
        l_h = next((i['logo'] for n, i in TEAMS.items() if i.get('opta_uuid') == h_uuid), None)
        if l_h: st.image(l_h, width=20)
    with cols[3]: st.markdown(f"<div style='background:#f0f2f6; border-radius:4px; text-align:center; font-weight:800; padding:2px 0;'>{score}</div>", unsafe_allow_html=True)
    with cols[4]:
        l_a = next((i['logo'] for n, i in TEAMS.items() if i.get('opta_uuid') == a_uuid), None)
        if l_a: st.image(l_a, width=20)
    with cols[5]: st.markdown(f"<div style='text-align:left; font-weight:600;'>{a_name[:12]}</div>", unsafe_allow_html=True)
    with cols[6]: st.markdown(f"<div style='background:{bg_color}; color:white; border-radius:4px; text-align:center; font-weight:bold; width:24px;'>{res_char}</div>", unsafe_allow_html=True)

def plot_custom_pitch(df, event_ids, title, zone='full', cmap='Reds', logo=None):
    plot_data = df[df['EVENT_TYPEID'].isin(event_ids)].copy()
    pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
    fig, ax = pitch.draw(figsize=(5, 7))
    if zone == 'up': ax.set_ylim(0, 55)
    elif zone == 'down': ax.set_ylim(45, 100)
    if logo:
        ax_l = ax.inset_axes([0.04, 0.03 if zone=='up' else 0.90, 0.08, 0.08], transform=ax.transAxes); ax_l.imshow(logo); ax_l.axis('off')
    ax.text(0.94, 0.05 if zone=='up' else 0.97, title, transform=ax.transAxes, fontsize=8, fontweight='bold', ha='right')
    if not plot_data.empty: pitch.kdeplot(plot_data.EVENT_X, plot_data.EVENT_Y, ax=ax, cmap=cmap, fill=True, alpha=0.5, levels=100)
    return fig

# --- 3. HOVEDFUNKTION ---
def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn: return
    
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    team_map = {mapping_lookup.get(str(u).lower().replace('t','')): u for u in df_teams_raw['CONTESTANTHOME_OPTAUUID'].unique() if mapping_lookup.get(str(u).lower().replace('t',''))}

    col_hold = st.columns([3.5, 1])[1]
    valgt_hold = col_hold.selectbox("Vælg hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid)

    # Hent Basis Match Info (Hele sæsonen til T4/T5, top 10 til grafer)
    sql_matches = f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE (CONTESTANTHOME_OPTAUUID = '{valgt_uuid}' OR CONTESTANTAWAY_OPTAUUID = '{valgt_uuid}') AND TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS} AND MATCH_STATUS ILIKE '%Full%' ORDER BY MATCH_LOCALDATE DESC"
    df_all_matches = conn.query(sql_matches)
    df_res_10 = df_all_matches.head(10)

    # Hent Events
    m_ids_10 = f"('{df_res_10['MATCH_OPTAUUID'].iloc[0]}')" if len(df_res_10)==1 else str(tuple(df_res_10['MATCH_OPTAUUID'].tolist()))
    df_events_10 = conn.query(f"SELECT *, EVENT_OUTCOME as OUTCOME FROM {DB}.OPTA_EVENTS WHERE EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND MATCH_OPTAUUID IN {m_ids_10}")
    
    # T4 Mål-sekvenser (Hele sæsonen)
    m_ids_all = str(tuple(df_all_matches['MATCH_OPTAUUID'].tolist()))
    sql_seq = f"WITH Goals AS (SELECT MATCH_OPTAUUID, EVENT_TIMESTAMP as G_TIME, EVENT_TIMEMIN as G_MIN FROM {DB}.OPTA_EVENTS WHERE EVENT_TYPEID = 16 AND MATCH_OPTAUUID IN {m_ids_all} AND EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}') SELECT e.*, m.CONTESTANTHOME_NAME, m.CONTESTANTAWAY_NAME, m.CONTESTANTHOME_OPTAUUID, m.CONTESTANTAWAY_OPTAUUID, m.TOTAL_HOME_SCORE, m.TOTAL_AWAY_SCORE, g.G_TIME, g.G_MIN FROM {DB}.OPTA_EVENTS e JOIN {DB}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID INNER JOIN Goals g ON e.MATCH_OPTAUUID = g.MATCH_OPTAUUID AND e.EVENT_TIMESTAMP >= DATEADD(second, -15, g.G_TIME) AND e.EVENT_TIMESTAMP <= g.G_TIME WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}'"
    df_goals_all = conn.query(sql_seq)

    t1, t2, t3, t4, t5 = st.tabs(["OVERSIGT", "MED BOLDEN", "UDEN BOLDEN", "MÅL-SEKVENSER", "SPILLEROVERSIGT"])

    with t1:
        # Metrics
        df_res_10['RES'] = df_res_10.apply(lambda r: "D" if r['TOTAL_HOME_SCORE']==r['TOTAL_AWAY_SCORE'] else ("W" if ((r['CONTESTANTHOME_OPTAUUID']==valgt_uuid and r['TOTAL_HOME_SCORE']>r['TOTAL_AWAY_SCORE']) or (r['CONTESTANTAWAY_OPTAUUID']==valgt_uuid and r['TOTAL_AWAY_SCORE']>r['TOTAL_HOME_SCORE'])) else "L"), axis=1)
        w, d, l = (df_res_10['RES']=="W").sum(), (df_res_10['RES']=="D").sum(), (df_res_10['RES']=="L").sum()
        m_s = sum([r['TOTAL_HOME_SCORE'] if r['CONTESTANTHOME_OPTAUUID']==valgt_uuid else r['TOTAL_AWAY_SCORE'] for _,r in df_res_10.iterrows()])
        m_i = sum([r['TOTAL_AWAY_SCORE'] if r['CONTESTANTHOME_OPTAUUID']==valgt_uuid else r['TOTAL_HOME_SCORE'] for _,r in df_res_10.iterrows()])
        
        m_cols = st.columns(5)
        m_cols[0].metric("Point", (w*3)+d); m_cols[1].metric("Vundne", w); m_cols[2].metric("Uafgjort", d); m_cols[3].metric("Tabte", l); m_cols[4].metric("Målscore", f"{int(m_s)}-{int(m_i)}")

        # Split layout
        c_left, c_spacer, c_right = st.columns([1.3, 0.1, 2.0])
        with c_left:
            st.write("**Seneste 10 kampe**")
            for _, r in df_res_10.iterrows():
                draw_match_row(pd.to_datetime(r['MATCH_LOCALDATE']).strftime('%d/%m'), r['CONTESTANTHOME_NAME'], r['CONTESTANTHOME_OPTAUUID'], f"{int(r['TOTAL_HOME_SCORE'])}-{int(r['TOTAL_AWAY_SCORE'])}", r['CONTESTANTAWAY_NAME'], r['CONTESTANTAWAY_OPTAUUID'], r['RES'])
        
        with c_right:
            kat_map = {"Pasninger": 'P', "Afslutninger": 'A', "Erobringer": 'E', "Dueller": 'D', "Touches in Box": 'T'}
            # Logik for valg
            sel1 = st.selectbox("Graf 1", list(kat_map.keys()), index=0)
            sel2 = st.selectbox("Graf 2", [k for k in kat_map.keys() if k != sel1], index=0)
            
            # (Graf generering her - forkortet for plads, bruger df_events_10 aggregeret)
            st.info("Her vises grafer for " + sel1 + " og " + sel2)

    with t2:
        cp, cs = st.columns([2, 1])
        fok = cs.selectbox("Fokus", ["Opbygning", "Gennembrud", "Afslutninger"], key="t2f")
        ids = [1] if fok != "Afslutninger" else [13,14,15,16]
        df_f = df_events_10[df_events_10['EVENT_X'] <= 50] if fok=="Opbygning" else df_events_10[df_events_10['EVENT_X'] > 50]
        
        cs.write("**Top 8:**")
        stats = df_f[df_f['EVENT_TYPEID'].isin(ids)].groupby('PLAYER_NAME').agg(T=('OUTCOME','count'), S=('OUTCOME', lambda x: (x==1).sum())).reset_index()
        stats['P'] = (stats['S']/stats['T']*100).round(1)
        for _, r in stats.sort_values('T', ascending=False).head(8).iterrows():
            cs.write(f"{int(r['S'])}/{int(r['T'])} ({r['P']}%) **{r['PLAYER_NAME']}**")
        cp.pyplot(plot_custom_pitch(df_f, ids, fok.upper(), logo=hold_logo))

    with t3:
        cp, cs = st.columns([2, 1])
        fok = cs.selectbox("Zone", ["Egen Halvdel: Erobringer", "Egen Halvdel: Dueller", "Off. Halvdel: Erobringer", "Off. Halvdel: Dueller"])
        ids = [12, 127, 49] if "Erobringer" in fok else [7, 8]
        df_f = df_events_10[df_events_10['EVENT_X'] <= 50] if "Egen" in fok else df_events_10[df_events_10['EVENT_X'] > 50]
        
        cs.write("**Top 8:**")
        stats = df_f[df_f['EVENT_TYPEID'].isin(ids)].groupby('PLAYER_NAME').agg(T=('OUTCOME','count'), S=('OUTCOME', lambda x: (x==1).sum())).reset_index()
        stats['P'] = (stats['S']/stats['T']*100).round(1)
        for _, r in stats.sort_values('T', ascending=False).head(8).iterrows():
            cs.write(f"{int(r['S'])}/{int(r['T'])} ({r['P']}%) **{r['PLAYER_NAME']}**")
        cp.pyplot(plot_custom_pitch(df_f, ids, fok.upper(), logo=hold_logo))

    with t4:
        if not df_goals_all.empty:
            gl = df_goals_all.drop_duplicates(['MATCH_OPTAUUID', 'G_TIME']).sort_values('G_TIME', ascending=False)
            opt = {f"{r['MATCH_OPTAUUID']}_{r['G_TIME']}": f"{pd.to_datetime(r['G_TIME']).strftime('%d/%m')} vs {r['CONTESTANTAWAY_NAME'] if r['CONTESTANTHOME_OPTAUUID']==valgt_uuid else r['CONTESTANTHOME_NAME']} ({int(r['G_MIN'])}. min)" for _, r in gl.iterrows()}
            sk = st.selectbox("Vælg mål (Hele sæsonen)", list(opt.keys()), format_func=lambda x: opt[x])
            
            goal_data = df_goals_all[df_goals_all['MATCH_OPTAUUID'] == sk.split('_')[0]].iloc[0]
            tge = df_goals_all[(df_goals_all['MATCH_OPTAUUID'] == goal_data['MATCH_OPTAUUID']) & (df_goals_all['G_TIME'] == goal_data['G_TIME'])].sort_values('EVENT_TIMESTAMP')
            
            p_c, l_c = st.columns([2.5, 1])
            p = Pitch(pitch_type='opta'); f, ax = p.draw()
            # Logo vs Logo i bunden
            ax_h = ax.inset_axes([0.02, 0.02, 0.05, 0.05], transform=ax.transAxes); ax_h.imshow(get_logo_img(goal_data['CONTESTANTHOME_OPTAUUID'])); ax_h.axis('off')
            ax_a = ax.inset_axes([0.12, 0.02, 0.05, 0.05], transform=ax.transAxes); ax_a.imshow(get_logo_img(goal_data['CONTESTANTAWAY_OPTAUUID'])); ax_a.axis('off')
            ax.text(0.08, 0.045, f"{int(goal_data['TOTAL_HOME_SCORE'])}-{int(goal_data['TOTAL_AWAY_SCORE'])}", transform=ax.transAxes, fontweight='bold')
            
            for i in range(len(tge)-1): p.arrows(tge.iloc[i]['EVENT_X'], tge.iloc[i]['EVENT_Y'], tge.iloc[i+1]['EVENT_X'], tge.iloc[i+1]['EVENT_Y'], ax=ax, width=1, color='black', alpha=0.2)
            p_c.pyplot(f)
            l_c.dataframe(tge[['PLAYER_NAME', 'EVENT_TYPEID']].assign(Aktion=lambda x: x['EVENT_TYPEID'].astype(str).map(OPTA_EVENT_TYPES))[['PLAYER_NAME', 'Aktion']].iloc[::-1], hide_index=True)

    with t5:
        num_m = df_all_matches['MATCH_OPTAUUID'].nunique()
        df_all_events = conn.query(f"SELECT EVENT_TYPEID, PLAYER_NAME, EVENT_X, EVENT_Y FROM {DB}.OPTA_EVENTS WHERE EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND MATCH_OPTAUUID IN {str(tuple(df_all_matches['MATCH_OPTAUUID'].tolist()))}")
        
        df_all_events['is_pass'] = (df_all_events['EVENT_TYPEID'] == 1).astype(int)
        df_all_events['is_regain'] = df_all_events['EVENT_TYPEID'].isin([12, 127, 49]).astype(int)
        df_all_events['is_shot'] = df_all_events['EVENT_TYPEID'].isin([13,14,15,16]).astype(int)
        df_all_events['is_tib'] = ((df_all_events['EVENT_X'] > 83) & (df_all_events['EVENT_Y'] > 21.1) & (df_all_events['EVENT_Y'] < 78.9)).astype(int)
        
        stats = df_all_events.groupby('PLAYER_NAME').agg(Pasninger=('is_pass','sum'), Erobringer=('is_regain','sum'), Skud=('is_shot','sum'), Touches_in_Box=('is_tib','sum'))
        st.dataframe((stats / num_m).round(2), use_container_width=True)

if __name__ == "__main__":
    vis_side()
