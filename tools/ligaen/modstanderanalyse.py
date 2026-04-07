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
    # Ultra-kompakt layout til venstre side
    col1, col2, col3, col4, col5, col6, col7 = st.columns([0.7, 1.6, 0.4, 1.1, 0.4, 1.6, 0.4])
    with col1: st.markdown(f"<p style='font-size:10px; margin:10px 0; color:#666;'>{date}</p>", unsafe_allow_html=True)
    with col2: st.markdown(f"<p style='font-size:11px; font-weight:600; margin:10px 0; text-align:right;'>{h_name[:12]}</p>", unsafe_allow_html=True)
    with col3:
        logo_h = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == h_uuid), "")
        if logo_h: st.image(logo_h, width=18)
    with col4: st.markdown(f"<p style='font-size:11px; font-weight:800; margin:10px 0; text-align:center; background:#f0f2f6; border-radius:3px;'>{score}</p>", unsafe_allow_html=True)
    with col5:
        logo_a = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == a_uuid), "")
        if logo_a: st.image(logo_a, width=18)
    with col6: st.markdown(f"<p style='font-size:11px; font-weight:600; margin:10px 0;'>{a_name[:12]}</p>", unsafe_allow_html=True)
    with col7: st.markdown(f"<div style='background-color:{bg_color}; color:white; border-radius:3px; text-align:center; font-weight:bold; margin-top:9px; font-size:10px; padding:1px 0;'>{res_char}</div>", unsafe_allow_html=True)

# (plot_custom_pitch, get_top_success, draw_match_info_box bibeholdes)

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
    df_all_h = conn.query(f"SELECT EVENT_X, EVENT_Y, EVENT_TYPEID, PLAYER_NAME, MATCH_OPTAUUID, EVENT_TIMESTAMP, EVENT_OUTCOME as OUTCOME FROM {DB}.OPTA_EVENTS WHERE EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND MATCH_OPTAUUID IN {match_ids_str}")

    # --- TABS ---
    t1, t2, t3, t4, t5 = st.tabs(["OVERSIGT", "MED BOLDEN", "UDEN BOLDEN", "MÅL-SEKVENSER", "SPILLEROVERSIGT"])

    with t1:
        # Forbered df_plot til graferne
        df_vol = df_all_h.groupby('MATCH_OPTAUUID').agg(
            P_tot=('EVENT_TYPEID', lambda x: (x == 1).sum()),
            P_suc=('EVENT_TYPEID', lambda x: ((df_all_h.loc[x.index, 'EVENT_TYPEID'] == 1) & (df_all_h.loc[x.index, 'OUTCOME'] == 1)).sum()),
            A_tot=('EVENT_TYPEID', lambda x: x.isin([13,14,15,16]).sum()),
            A_suc=('EVENT_TYPEID', lambda x: (df_all_h.loc[x.index, 'EVENT_TYPEID'] == 16).sum()),
            E_tot=('EVENT_TYPEID', lambda x: x.isin([12, 127, 49]).sum()),
            E_suc=('EVENT_TYPEID', lambda x: ((df_all_h.loc[x.index, 'EVENT_TYPEID'].isin([12, 127, 49])) & (df_all_h.loc[x.index, 'OUTCOME'] == 1)).sum()),
            D_tot=('EVENT_TYPEID', lambda x: x.isin([7, 8]).sum()),
            D_suc=('EVENT_TYPEID', lambda x: ((df_all_h.loc[x.index, 'EVENT_TYPEID'].isin([7, 8])) & (df_all_h.loc[x.index, 'OUTCOME'] == 1)).sum())
        ).reset_index()
        
        df_res['RES'] = df_res.apply(lambda r: "D" if r['TOTAL_HOME_SCORE'] == r['TOTAL_AWAY_SCORE'] else ("W" if ((r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid and r['TOTAL_HOME_SCORE'] > r['TOTAL_AWAY_SCORE']) or (r['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid and r['TOTAL_AWAY_SCORE'] > r['TOTAL_HOME_SCORE'])) else "L"), axis=1)
        df_plot = df_res.merge(df_vol, on='MATCH_OPTAUUID', how='left').fillna(0)
        df_plot['MATCH_LOCALDATE'] = pd.to_datetime(df_plot['MATCH_LOCALDATE'])
        df_plot = df_plot.sort_values('MATCH_LOCALDATE')
        df_plot['LABEL'] = df_plot['MATCH_LOCALDATE'].dt.strftime('%d/%m')

        # Layout: [Venstre (metrics + kampe), Højre (grafer)]
        main_col1, main_col2 = st.columns([0.8, 1.2])

        with main_col1:
            # Metrics Række
            wins, draws, losses = (df_res['RES'] == "W").sum(), (df_res['RES'] == "D").sum(), (df_res['RES'] == "L").sum()
            mål_s = sum([r['TOTAL_HOME_SCORE'] if r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else r['TOTAL_AWAY_SCORE'] for _, r in df_res.iterrows()])
            mål_i = sum([r['TOTAL_AWAY_SCORE'] if r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else r['TOTAL_HOME_SCORE'] for _, r in df_res.iterrows()])

            metric_style = "<div style='text-align:center;'><p style='font-size:9px; color:#666; margin:0; font-weight:bold;'>{label}</p><p style='font-size:15px; font-weight:800; margin:0;'>{value}</p></div>"
            m_cols = st.columns(5)
            m_cols[0].markdown(metric_style.format(label="PTS", value=(wins*3)+draws), unsafe_allow_html=True)
            m_cols[1].markdown(metric_style.format(label="V", value=wins), unsafe_allow_html=True)
            m_cols[2].markdown(metric_style.format(label="U", value=draws), unsafe_allow_html=True)
            m_cols[3].markdown(metric_style.format(label="T", value=losses), unsafe_allow_html=True)
            m_cols[4].markdown(metric_style.format(label="MÅL", value=f"{mål_s}-{mål_i}"), unsafe_allow_html=True)

            st.markdown("<br><p style='font-size:13px; font-weight:bold; margin-bottom:5px;'>Seneste 10 kampe</p>", unsafe_allow_html=True)
            for _, row in df_res.iterrows():
                draw_match_row(pd.to_datetime(row['MATCH_LOCALDATE']).strftime('%d/%m'), row['CONTESTANTHOME_NAME'], row['CONTESTANTHOME_OPTAUUID'], f"{int(row['TOTAL_HOME_SCORE'])}-{int(row['TOTAL_AWAY_SCORE'])}", row['CONTESTANTAWAY_NAME'], row['CONTESTANTAWAY_OPTAUUID'], row['RES'])
                st.markdown("<hr style='margin:0; opacity:0.1'>", unsafe_allow_html=True)

        with main_col2:
            # Dropdowns + Grafer (Løsning: st.columns inde i loopet)
            kat_map = {
                "Pasninger": {'col': 'P', 'color': '#0047AB', 'round': 0}, 
                "Afslutninger": {'col': 'A', 'color': '#C8102E', 'round': 1}, 
                "Erobringer": {'col': 'E', 'color': '#2E7D32', 'round': 0}
            }
            for i, (default_name, info) in enumerate(kat_map.items()):
                # Header række med dropdown til højre
                h_col, d_col = st.columns([1.8, 1])
                valgt_kat = d_col.selectbox(f"Vælg {i}", list(kat_map.keys()), index=i, key=f"sel_{i}", label_visibility="collapsed")
                
                # Opdater info baseret på dropdown-valg
                current_info = kat_map[valgt_kat]
                avg = df_plot[f"{current_info['col']}_tot"].mean()
                
                h_col.markdown(f"<p style='font-size:12px; font-weight:bold; margin-top:5px;'>{valgt_kat} (Gns: {round(avg, current_info['round'])})</p>", unsafe_allow_html=True)
                
                df_plot['TXT'] = df_plot.apply(lambda r: f"{int(r[f'{current_info['col']}_tot'])}", axis=1)
                fig = px.bar(df_plot, x='LABEL', y=f"{current_info['col']}_tot", text='TXT')
                fig.update_traces(marker_color=current_info['color'], textposition='outside', textfont_size=9)
                fig.update_layout(height=170, margin=dict(t=20, b=0, l=0, r=0), plot_bgcolor='rgba(0,0,0,0)', xaxis_title=None, yaxis_title=None)
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                if i < 2: st.markdown("<div style='margin-bottom:15px;'></div>", unsafe_allow_html=True)

    with t2:
        cp, cs = st.columns([2, 1])
        v_med = cs.selectbox("Fokus", ["Opbygning", "Gennembrud", "Afslutninger"], key="ms")
        if v_med == "Opbygning": ids, tit, cm, zn, df_f = [1], "EGEN HALVDEL: OPBYGNING", "Blues", "up", df_all_h[df_all_h['EVENT_X'] <= 50]
        elif v_med == "Gennembrud": ids, tit, cm, zn, df_f = [1], "OFF. HALVDEL: GENNEMBRUD", "Reds", "down", df_all_h[df_all_h['EVENT_X'] > 50]
        else: ids, tit, cm, zn, df_f = [13, 14, 15, 16], "AFSLUTNINGER", "YlOrRd", "down", df_all_h
        
        cs.write("**Top 8:**")
        df_top = get_top_success(df_f, ids)
        if not df_top.empty:
            for _, r in df_top.iterrows(): cs.write(f"{int(r['SUCCESS'])} / {int(r['TOTAL'])} ({int(r['PCT'])}%) **{r['PLAYER_NAME']}**")
        cp.pyplot(plot_custom_pitch(df_f, ids, tit, zone=zn, cmap=cm, logo=hold_logo))

    with t3:
        cp, cs = st.columns([2, 1])
        v_uden = cs.selectbox("Fokus", ["Dueller", "Erobringer", "Defensiv Zone"], key="us")
        if v_uden == "Dueller": ids, tit, cm = [7, 8], "DUELLER", "Blues"
        elif v_uden == "Erobringer": ids, tit, cm = [127, 12, 49], "EROBRINGER", "GnBu"
        else: ids, tit, cm = [7, 12, 127], "DEFENSIV ZONE", "PuBu"
        
        cs.write("**Top 8:**")
        df_top_u = get_top_success(df_all_h, ids)
        if not df_top_u.empty:
            for _, r in df_top_u.iterrows(): cs.write(f"{int(r['SUCCESS'])} / {int(r['TOTAL'])} ({int(r['PCT'])}%) **{r['PLAYER_NAME']}**")
        cp.pyplot(plot_custom_pitch(df_all_h, ids, tit, zone="up", cmap=cm, logo=hold_logo))

    with t4:
        if not df_all_events.empty:
            gl = df_all_events.drop_duplicates(['MATCH_OPTAUUID', 'GOAL_TIME']).sort_values('GOAL_TIME', ascending=False)
            opts = {f"{r['MATCH_OPTAUUID']}_{r['GOAL_TIME']}": {'label': f"{pd.to_datetime(r['MATCH_LOCALDATE']).strftime('%d/%m/%Y')} vs. {r['CONTESTANTAWAY_NAME'] if r['CONTESTANTHOME_OPTAUUID']==valgt_uuid else r['CONTESTANTHOME_NAME']} ({r['GOAL_MIN']}. min)", 'match_id': r['MATCH_OPTAUUID'], 'goal_ts': r['GOAL_TIME'], 'opp_uuid': r['CONTESTANTAWAY_OPTAUUID'] if r['CONTESTANTHOME_OPTAUUID']==valgt_uuid else r['CONTESTANTHOME_OPTAUUID'], 'min': r['GOAL_MIN'], 'date': pd.to_datetime(r['MATCH_LOCALDATE']).strftime('%d/%m/%Y')} for _, r in gl.iterrows()}
            sk = st.selectbox("Vælg mål", list(opts.keys()), format_func=lambda x: opts[x]['label'])
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
                ax.text(r['EVENT_X'], r['EVENT_Y']+2.5, r['PLAYER_NAME'], fontsize=7, ha='center', fontweight='bold', bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
            p_c.pyplot(f)
            tge['Aktion'] = tge['EVENT_TYPEID'].astype(str).map(OPTA_EVENT_TYPES)
            l_c.write("**Sekvens:**"); l_c.dataframe(tge[['PLAYER_NAME', 'Aktion']].iloc[::-1], hide_index=True)
        else: st.info("Ingen mål fundet.")

    with t5:
        if not df_all_h.empty:
            df_all_h['is_pass'] = (df_all_h['EVENT_TYPEID'] == 1).astype(int)
            df_all_h['is_regain'] = df_all_h['EVENT_TYPEID'].isin([7, 8, 12, 49, 127]).astype(int)
            df_all_h['is_shot'] = df_all_h['EVENT_TYPEID'].isin([13,14,15,16]).astype(int)
            stats = df_all_h.groupby('PLAYER_NAME').agg({'is_pass': 'sum', 'is_regain': 'sum', 'is_shot': 'sum', 'EVENT_TYPEID': 'count'}).rename(columns={'EVENT_TYPEID': 'Aktioner', 'is_pass': 'Pasninger', 'is_regain': 'Erobringer', 'is_shot': 'Skud'}).sort_values('Aktioner', ascending=False)
            st.dataframe(stats, use_container_width=True)

if __name__ == "__main__":
    vis_side()
