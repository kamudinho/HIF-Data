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
    col1, col2, col3, col4, col5, col6, col7 = st.columns([0.7, 1.6, 0.4, 1.1, 0.4, 1.6, 0.4])
    with col1: st.markdown(f"<p style='font-size:10px; margin:5px 0; color:#666;'>{date}</p>", unsafe_allow_html=True)
    with col2: st.markdown(f"<p style='font-size:11px; font-weight:600; margin:5px 0; text-align:right;'>{h_name[:12]}</p>", unsafe_allow_html=True)
    with col3:
        logo_h = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == h_uuid), "")
        if logo_h: st.image(logo_h, width=17)
    with col4: st.markdown(f"<p style='font-size:11px; font-weight:800; margin:5px 0; text-align:center; background:#f0f2f6; border-radius:3px;'>{score}</p>", unsafe_allow_html=True)
    with col5:
        logo_a = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == a_uuid), "")
        if logo_a: st.image(logo_a, width=17)
    with col6: st.markdown(f"<p style='font-size:11px; font-weight:600; margin:5px 0;'>{a_name[:12]}</p>", unsafe_allow_html=True)
    with col7: st.markdown(f"<div style='background-color:{bg_color}; color:white; border-radius:3px; text-align:center; font-weight:bold; margin-top:5px; font-size:10px; padding:1px 0;'>{res_char}</div>", unsafe_allow_html=True)

def draw_match_info_box(ax, scoring_team_logo, opp_team_logo, date_str, score_str, min_str):
    if scoring_team_logo:
        ax_l1 = ax.inset_axes([0.02, 0.08, 0.05, 0.05], transform=ax.transAxes)
        ax_l1.imshow(scoring_team_logo); ax_l1.axis('off')
    ax.text(0.08, 0.105, "vs.", transform=ax.transAxes, fontsize=8, fontweight='bold', va='center')
    if opp_team_logo:
        ax_l2 = ax.inset_axes([0.10, 0.08, 0.05, 0.05], transform=ax.transAxes)
        ax_l2.imshow(opp_team_logo); ax_l2.axis('off')
    ax.text(0.03, 0.07, f"{date_str} | Stilling: {score_str} ({min_str}. min)", transform=ax.transAxes, fontsize=8, color='#444444', va='top')

def plot_custom_pitch(df, event_ids, title, zone='full', cmap='Reds', logo=None):
    plot_data = df[df['EVENT_TYPEID'].isin(event_ids)].copy()
    pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
    fig, ax = pitch.draw(figsize=(5, 7))
    if zone == 'up': ax.set_ylim(0, 55); logo_pos, text_y = [0.04, 0.03, 0.08, 0.08], 0.05
    elif zone == 'down': ax.set_ylim(45, 100); logo_pos, text_y = [0.04, 0.90, 0.08, 0.08], 0.97
    else: logo_pos, text_y = [0.04, 0.90, 0.08, 0.08], 0.97
    if logo:
        ax_l = ax.inset_axes(logo_pos, transform=ax.transAxes); ax_l.imshow(logo); ax_l.axis('off')
    ax.text(0.94, text_y, title, transform=ax.transAxes, fontsize=6, fontweight='bold', ha='right', va='top')
    if not plot_data.empty: pitch.kdeplot(plot_data.EVENT_X, plot_data.EVENT_Y, ax=ax, cmap=cmap, fill=True, alpha=0.5, levels=100)
    return fig

def get_top_success(df, event_ids):
    relevant = df[df['EVENT_TYPEID'].isin(event_ids)].copy()
    if relevant.empty: return pd.DataFrame()
    stats = relevant.groupby('PLAYER_NAME').agg(TOTAL=('OUTCOME', 'count'), SUCCESS=('OUTCOME', lambda x: (x == 1).sum())).reset_index()
    stats['PCT'] = (stats['SUCCESS'] / stats['TOTAL'] * 100).round(1)
    return stats.sort_values('TOTAL', ascending=False).head(8)

# --- 3. HOVEDFUNKTION ---
def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn: return

    # --- TEAM SELECTION ---
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
    ids = df_teams_raw['CONTESTANTHOME_OPTAUUID'].unique()
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    team_map = {mapping_lookup.get(str(u).lower().replace('t','')): u for u in ids if mapping_lookup.get(str(u).lower().replace('t',''))}

    col_spacer, col_hold = st.columns([3, 1])
    valgt_hold = col_hold.selectbox("Vælg hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid)

    # --- DATA HENTNING ---
    sql_res = f"SELECT MATCH_LOCALDATE, CONTESTANTHOME_NAME, CONTESTANTAWAY_NAME, TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE, CONTESTANTHOME_OPTAUUID, CONTESTANTAWAY_OPTAUUID, MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE (CONTESTANTHOME_OPTAUUID = '{valgt_uuid}' OR CONTESTANTAWAY_OPTAUUID = '{valgt_uuid}') AND TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS} AND (MATCH_STATUS ILIKE '%Played%' OR MATCH_STATUS ILIKE '%Full%' OR MATCH_STATUS ILIKE '%Finish%') ORDER BY MATCH_LOCALDATE DESC LIMIT 10"
    df_res = conn.query(sql_res)
    if df_res is None or df_res.empty: return st.warning("Ingen kampe fundet.")

    match_ids = tuple(df_res['MATCH_OPTAUUID'].tolist())
    match_ids_str = f"('{match_ids[0]}')" if len(match_ids) == 1 else str(match_ids)
    
    # Hent alle events for holdet
    df_all_h = conn.query(f"SELECT EVENT_X, EVENT_Y, EVENT_TYPEID, PLAYER_NAME, MATCH_OPTAUUID, EVENT_TIMESTAMP, EVENT_OUTCOME as OUTCOME FROM {DB}.OPTA_EVENTS WHERE EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND MATCH_OPTAUUID IN {match_ids_str}")
    
    # Hent events til mål-sekvenser (RETTET SQL TIL SNOWFLAKE)
    df_all_events = conn.query(f"""
        SELECT e.*, m.MATCH_LOCALDATE, m.CONTESTANTHOME_NAME, m.CONTESTANTAWAY_NAME, m.CONTESTANTHOME_OPTAUUID, m.CONTESTANTAWAY_OPTAUUID,
        (SELECT MAX(EVENT_TIMESTAMP) FROM {DB}.OPTA_EVENTS e2 WHERE e2.MATCH_OPTAUUID = e.MATCH_OPTAUUID AND e2.EVENT_TYPEID = 16 AND e2.EVENT_TIMESTAMP >= e.EVENT_TIMESTAMP AND e2.EVENT_TIMESTAMP <= DATEADD(millisecond, 20000, e.EVENT_TIMESTAMP)) as GOAL_TIME,
        (SELECT MAX(EVENT_PERIODID) FROM {DB}.OPTA_EVENTS e3 WHERE e3.MATCH_OPTAUUID = e.MATCH_OPTAUUID AND e3.EVENT_TIMESTAMP = GOAL_TIME) as GOAL_PERIOD,
        (SELECT MAX(EVENT_MINUTE) FROM {DB}.OPTA_EVENTS e4 WHERE e4.MATCH_OPTAUUID = e.MATCH_OPTAUUID AND e4.EVENT_TIMESTAMP = GOAL_TIME) as GOAL_MIN
        FROM {DB}.OPTA_EVENTS e 
        JOIN {DB}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
        WHERE e.MATCH_OPTAUUID IN {match_ids_str} AND e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}'
    """)

    t1, t2, t3, t4, t5 = st.tabs(["OVERSIGT", "MED BOLDEN", "UDEN BOLDEN", "MÅL-SEKVENSER", "SPILLEROVERSIGT"])

    with t1:
        df_vol = df_all_h.groupby('MATCH_OPTAUUID').agg(
            P_tot=('EVENT_TYPEID', lambda x: (x == 1).sum()),
            A_tot=('EVENT_TYPEID', lambda x: x.isin([13,14,15,16]).sum()),
            E_tot=('EVENT_TYPEID', lambda x: x.isin([12, 127, 49]).sum()),
            D_tot=('EVENT_TYPEID', lambda x: x.isin([7, 8]).sum()),
            F_tot=('EVENT_TYPEID', lambda x: (x == 4).sum())
        ).reset_index()
        
        df_res['RES'] = df_res.apply(lambda r: "D" if r['TOTAL_HOME_SCORE'] == r['TOTAL_AWAY_SCORE'] else ("W" if ((r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid and r['TOTAL_HOME_SCORE'] > r['TOTAL_AWAY_SCORE']) or (r['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid and r['TOTAL_AWAY_SCORE'] > r['TOTAL_HOME_SCORE'])) else "L"), axis=1)
        df_plot = df_res.merge(df_vol, on='MATCH_OPTAUUID', how='left').fillna(0)
        df_plot['LABEL'] = pd.to_datetime(df_plot['MATCH_LOCALDATE']).dt.strftime('%d/%m')
        df_plot = df_plot.sort_values('MATCH_LOCALDATE')

        m1, m2 = st.columns([0.8, 1.2])
        with m1:
            wins, draws, losses = (df_res['RES'] == "W").sum(), (df_res['RES'] == "D").sum(), (df_res['RES'] == "L").sum()
            mål_s = sum([row['TOTAL_HOME_SCORE'] if row['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else row['TOTAL_AWAY_SCORE'] for _, row in df_res.iterrows()])
            mål_i = sum([row['TOTAL_AWAY_SCORE'] if row['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else row['TOTAL_HOME_SCORE'] for _, row in df_res.iterrows()])
            
            mc = st.columns(5)
            mc[0].markdown(f"<div style='text-align:center;'><p style='font-size:9px;color:#666;margin:0;'>PTS</p><p style='font-size:15px;font-weight:800;margin:0;'>{(wins*3)+draws}</p></div>", unsafe_allow_html=True)
            mc[1].markdown(f"<div style='text-align:center;'><p style='font-size:9px;color:#666;margin:0;'>V</p><p style='font-size:15px;font-weight:800;margin:0;'>{wins}</p></div>", unsafe_allow_html=True)
            mc[2].markdown(f"<div style='text-align:center;'><p style='font-size:9px;color:#666;margin:0;'>U</p><p style='font-size:15px;font-weight:800;margin:0;'>{draws}</p></div>", unsafe_allow_html=True)
            mc[3].markdown(f"<div style='text-align:center;'><p style='font-size:9px;color:#666;margin:0;'>T</p><p style='font-size:15px;font-weight:800;margin:0;'>{losses}</p></div>", unsafe_allow_html=True)
            mc[4].markdown(f"<div style='text-align:center;'><p style='font-size:9px;color:#666;margin:0;'>MÅL</p><p style='font-size:15px;font-weight:800;margin:0;'>{mål_s}-{mål_i}</p></div>", unsafe_allow_html=True)

            st.markdown("<p style='font-size:12px; font-weight:bold; margin:10px 0 5px 0;'>Seneste 10 kampe</p>", unsafe_allow_html=True)
            for _, row in df_res.iterrows():
                draw_match_row(pd.to_datetime(row['MATCH_LOCALDATE']).strftime('%d/%m'), row['CONTESTANTHOME_NAME'], row['CONTESTANTHOME_OPTAUUID'], f"{int(row['TOTAL_HOME_SCORE'])}-{int(row['TOTAL_AWAY_SCORE'])}", row['CONTESTANTAWAY_NAME'], row['CONTESTANTAWAY_OPTAUUID'], row['RES'])
                st.markdown("<hr style='margin:0; opacity:0.1'>", unsafe_allow_html=True)

        with m2:
            kat_map = {"Pasninger": 'P', "Afslutninger": 'A', "Erobringer": 'E', "Dueller": 'D', "Frispark": 'F'}
            colors = {"P": '#0047AB', "A": '#C8102E', "E": '#2E7D32', "D": '#FF9800', "F": '#D32F2F'}
            for i in range(2):
                h_c, d_c = st.columns([1.5, 1])
                v_k = d_c.selectbox(f"Stat {i}", list(kat_map.keys()), index=i, key=f"gs_{i}", label_visibility="collapsed")
                c_code = kat_map[v_k]
                avg = df_plot[f"{c_code}_tot"].mean()
                h_c.markdown(f"<p style='font-size:12px; font-weight:bold; margin-top:5px;'>{v_k} (Gns: {round(avg, 1)})</p>", unsafe_allow_html=True)
                fig = px.bar(df_plot, x='LABEL', y=f"{c_code}_tot", text=f"{c_code}_tot")
                fig.update_traces(marker_color=colors[c_code], textposition='outside', textfont_size=9)
                fig.update_layout(height=180, margin=dict(t=20, b=0, l=0, r=0), plot_bgcolor='rgba(0,0,0,0)', xaxis_title=None, yaxis_title=None)
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"pc_{i}")

    with t2:
        cp, cs = st.columns([2, 1])
        v_med = cs.selectbox("Fokus", ["Opbygning", "Gennembrud", "Afslutninger"], key="ms")
        if v_med == "Opbygning": ids, tit, cm, zn, df_f = [1], "EGEN HALVDEL", "Blues", "up", df_all_h[df_all_h['EVENT_X'] <= 50]
        elif v_med == "Gennembrud": ids, tit, cm, zn, df_f = [1], "OFF. HALVDEL", "Reds", "down", df_all_h[df_all_h['EVENT_X'] > 50]
        else: ids, tit, cm, zn, df_f = [13, 14, 15, 16], "AFSLUTNINGER", "YlOrRd", "down", df_all_h
        df_top = get_top_success(df_f, ids)
        if not df_top.empty:
            for _, r in df_top.iterrows(): cs.write(f"{int(r['SUCCESS'])}/{int(r['TOTAL'])} ({int(r['PCT'])}%) **{r['PLAYER_NAME']}**")
        cp.pyplot(plot_custom_pitch(df_f, ids, tit, zone=zn, cmap=cm, logo=hold_logo))

    with t3:
        cp, cs = st.columns([2, 1])
        v_uden = cs.selectbox("Fokus", ["Dueller", "Erobringer"], key="us")
        ids, tit, cm = ([7, 8], "DUELLER", "Blues") if v_uden == "Dueller" else ([127, 12, 49], "EROBRINGER", "GnBu")
        df_top_u = get_top_success(df_all_h, ids)
        if not df_top_u.empty:
            for _, r in df_top_u.iterrows(): cs.write(f"{int(r['SUCCESS'])}/{int(r['TOTAL'])} ({int(r['PCT'])}%) **{r['PLAYER_NAME']}**")
        cp.pyplot(plot_custom_pitch(df_all_h, ids, tit, zone="up", cmap=cm, logo=hold_logo))

    with t4:
        if not df_all_events.empty and 'GOAL_TIME' in df_all_events.columns:
            gl = df_all_events.dropna(subset=['GOAL_TIME']).drop_duplicates(['MATCH_OPTAUUID', 'GOAL_TIME']).sort_values('MATCH_LOCALDATE', ascending=False)
            if not gl.empty:
                opts = {f"{r['MATCH_OPTAUUID']}_{r['GOAL_TIME']}": {'match_id': r['MATCH_OPTAUUID'], 'goal_ts': r['GOAL_TIME'], 'opp_uuid': r['CONTESTANTAWAY_OPTAUUID'] if r['CONTESTANTHOME_OPTAUUID']==valgt_uuid else r['CONTESTANTHOME_OPTAUUID'], 'min': r['GOAL_MIN'], 'date': pd.to_datetime(r['MATCH_LOCALDATE']).strftime('%d/%m/%Y')} for _, r in gl.iterrows()}
                sk = st.selectbox("Vælg mål", list(opts.keys()), format_func=lambda x: f"{opts[x]['date']} ({opts[x]['min']}. min)")
                sd = opts[sk]
                tge = df_all_events[(df_all_events['MATCH_OPTAUUID'] == sd['match_id']) & (df_all_events['GOAL_TIME'] == sd['goal_ts'])].sort_values('EVENT_TIMESTAMP')
                p_c, l_c = st.columns([2.5, 1])
                p = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='grey')
                f, ax = p.draw(figsize=(10, 7))
                draw_match_info_box(ax, hold_logo, get_logo_img(sd['opp_uuid']), sd['date'], "Mål", sd['min'])
                for i in range(len(tge)-1): p.arrows(tge.iloc[i]['EVENT_X'], tge.iloc[i]['EVENT_Y'], tge.iloc[i+1]['EVENT_X'], tge.iloc[i+1]['EVENT_Y'], width=1, headwidth=3, color='black', alpha=0.15, ax=ax)
                for _, r in tge.iterrows():
                    c, m, s = ('red', 's', 180) if r['EVENT_TYPEID'] == 16 else (('gold', 'P', 200) if r['EVENT_TYPEID'] == 5 else ('red', 'o', 80))
                    ax.scatter(r['EVENT_X'], r['EVENT_Y'], color=c, s=s, marker=m, edgecolors='black', zorder=10)
                p_c.pyplot(f)
                tge['Aktion'] = tge['EVENT_TYPEID'].astype(str).map(OPTA_EVENT_TYPES)
                l_c.write("**Sekvens:**"); l_c.dataframe(tge[['PLAYER_NAME', 'Aktion']].iloc[::-1], hide_index=True)
            else: st.info("Ingen mål fundet i perioden.")

    with t5:
        if not df_all_h.empty:
            df_all_h['Pasninger'] = (df_all_h['EVENT_TYPEID'] == 1).astype(int)
            df_all_h['Erobringer'] = df_all_h['EVENT_TYPEID'].isin([7, 8, 12, 49, 127]).astype(int)
            df_all_h['Skud'] = df_all_h['EVENT_TYPEID'].isin([13,14,15,16]).astype(int)
            stats = df_all_h.groupby('PLAYER_NAME').agg({'Pasninger': 'sum', 'Erobringer': 'sum', 'Skud': 'sum', 'EVENT_TYPEID': 'count'}).rename(columns={'EVENT_TYPEID': 'Total'}).sort_values('Total', ascending=False)
            st.dataframe(stats, use_container_width=True)

if __name__ == "__main__":
    vis_side()
