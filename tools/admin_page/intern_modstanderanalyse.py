import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch, VerticalPitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS
import requests
from PIL import Image
from io import BytesIO
from data.utils.mapping import get_action_label

# --- 1. KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '335', '328', '329', '43319', '331')"

st.set_page_config(page_title="HIF Taktisk Analyse", layout="wide")

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

def draw_match_info_box(ax, home_logo, away_logo, date_str, score_str, minute):
    if home_logo:
        ax_h = ax.inset_axes([0.30, 0.90, 0.08, 0.08], transform=ax.transAxes)
        ax_h.imshow(home_logo); ax_h.axis('off')
    if away_logo:
        ax_a = ax.inset_axes([0.62, 0.90, 0.08, 0.08], transform=ax.transAxes)
        ax_a.imshow(away_logo); ax_a.axis('off')
    ax.text(50, 94, score_str, fontsize=15, fontweight='bold', ha='center', va='center', 
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=3))
    ax.text(50, 89, f"{date_str} • Min: {minute}'", fontsize=8, ha='center', color='grey')

def draw_match_row(date, h_name, h_uuid, score, a_name, a_uuid, res_char):
    bg_color = "#2e7d32" if res_char == "W" else ("#757575" if res_char == "D" else "#c62828")
    cols = st.columns([0.5, 1.2, 0.25, 0.7, 0.25, 1.2, 0.3], vertical_alignment="center")
    flex_style = "display: flex; align-items: center; height: 30px; margin: 0;"
    with cols[0]: st.markdown(f"<div style='{flex_style} font-size:11px; color:#666;'>{date}</div>", unsafe_allow_html=True)
    with cols[1]: st.markdown(f"<div style='{flex_style} justify-content: flex-end; font-size:13px; font-weight:600;'>{h_name[:12]}</div>", unsafe_allow_html=True)
    with cols[2]:
        l_h = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == h_uuid), "")
        if l_h: st.image(l_h, width=18)
    with cols[3]: st.markdown(f"<div style='{flex_style} justify-content: center;'><div style='background:#f0f2f6; border-radius:3px; width: 100%; text-align:center; font-size:12px; font-weight:800; padding:2px 0;'>{score}</div></div>", unsafe_allow_html=True)
    with cols[4]:
        l_a = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == a_uuid), "")
        if l_a: st.image(l_a, width=18)
    with cols[5]: st.markdown(f"<div style='{flex_style} justify-content: flex-start; font-size:13px; font-weight:600;'>{a_name[:12]}</div>", unsafe_allow_html=True)
    with cols[6]: st.markdown(f"<div style='{flex_style} justify-content: center;'><div style='background-color:{bg_color}; color:white; border-radius:3px; text-align:center; font-weight:bold; font-size:11px; padding:2px 0; width:22px;'>{res_char}</div></div>", unsafe_allow_html=True)

def plot_custom_pitch(df, event_ids, title, zone='full', cmap='Reds', logo=None):
    plot_data = df[df['EVENT_TYPEID'].astype(str).isin([str(i) for i in event_ids])].copy()
    pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
    fig, ax = pitch.draw(figsize=(5, 7))
    if zone == 'up': ax.set_ylim(0, 55)
    elif zone == 'down': ax.set_ylim(45, 100)
    if logo:
        ax_l = ax.inset_axes([0.04, 0.90, 0.08, 0.08] if zone!='up' else [0.04, 0.03, 0.08, 0.08], transform=ax.transAxes)
        ax_l.imshow(logo); ax_l.axis('off')
    ax.text(0.94, 0.97 if zone!='up' else 0.05, title, transform=ax.transAxes, fontsize=6, fontweight='bold', ha='right')
    if not plot_data.empty: pitch.kdeplot(plot_data.EVENT_X, plot_data.EVENT_Y, ax=ax, cmap=cmap, fill=True, alpha=0.5, levels=100)
    return fig

# --- 3. HOVEDFUNKTION ---
def vis_side():
    conn = _get_snowflake_conn()
    if not conn: return

    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
    ids = df_teams_raw['CONTESTANTHOME_OPTAUUID'].unique()
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    team_map = {mapping_lookup.get(str(u).lower().replace('t','')): u for u in ids if mapping_lookup.get(str(u).lower().replace('t','')) is not None}

    col_hold = st.columns([3.5, 1])[1]
    valgt_hold = col_hold.selectbox("Vælg hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid)

    with st.spinner("Henter data..."):
        sql_res = f"SELECT MATCH_LOCALDATE, CONTESTANTHOME_NAME, CONTESTANTAWAY_NAME, TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE, CONTESTANTHOME_OPTAUUID, CONTESTANTAWAY_OPTAUUID, MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE (CONTESTANTHOME_OPTAUUID = '{valgt_uuid}' OR CONTESTANTAWAY_OPTAUUID = '{valgt_uuid}') AND TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS} AND (MATCH_STATUS ILIKE '%Played%' OR MATCH_STATUS ILIKE '%Full%') ORDER BY MATCH_LOCALDATE DESC LIMIT 10"
        df_res = conn.query(sql_res)
        
        if df_res is not None and not df_res.empty:
            m_ids = tuple(df_res['MATCH_OPTAUUID'].tolist())
            m_str = f"('{m_ids[0]}')" if len(m_ids) == 1 else str(m_ids)
            
            sql_all_h = f"SELECT e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME, e.MATCH_OPTAUUID, e.EVENT_TIMESTAMP, e.EVENT_OUTCOME as OUTCOME FROM {DB}.OPTA_EVENTS e JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND e.MATCH_OPTAUUID IN {m_str}"
            df_all_h = conn.query(sql_all_h)
            
            sql_seq = f"""
                WITH TargetGoals AS (SELECT MATCH_OPTAUUID, EVENT_TIMESTAMP as G_TIME, EVENT_TIMEMIN as G_MIN, EVENT_OPTAUUID as GOAL_ID FROM {DB}.OPTA_EVENTS WHERE EVENT_TYPEID = 16 AND EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}') 
                SELECT e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME, e.EVENT_TIMESTAMP, e.MATCH_OPTAUUID, m.MATCH_LOCALDATE, m.CONTESTANTHOME_NAME, m.CONTESTANTAWAY_NAME, m.CONTESTANTHOME_OPTAUUID, m.CONTESTANTAWAY_OPTAUUID, m.TOTAL_HOME_SCORE, m.TOTAL_AWAY_SCORE, tg.G_TIME as GOAL_TIME, tg.G_MIN as GOAL_MIN, tg.GOAL_ID, LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as qual_list 
                FROM {DB}.OPTA_EVENTS e JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID JOIN {DB}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID INNER JOIN TargetGoals tg ON e.MATCH_OPTAUUID = tg.MATCH_OPTAUUID AND e.EVENT_TIMESTAMP >= DATEADD(second, -20, tg.G_TIME) AND e.EVENT_TIMESTAMP <= tg.G_TIME WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16
            """
            df_all_events = conn.query(sql_seq)

    t1, t2, t3, t4, t5 = st.tabs(["OVERSIGT", "MED BOLDEN", "UDEN BOLDEN", "MÅL-SEKVENSER", "SPILLEROVERSIGT"])

    with t1: # OVERSIGT
        df_res['RES'] = df_res.apply(lambda r: "D" if r['TOTAL_HOME_SCORE'] == r['TOTAL_AWAY_SCORE'] else ("W" if ((r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid and r['TOTAL_HOME_SCORE'] > r['TOTAL_AWAY_SCORE']) or (r['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid and r['TOTAL_AWAY_SCORE'] > r['TOTAL_HOME_SCORE'])) else "L"), axis=1)
        for _, row in df_res.iterrows():
            draw_match_row(pd.to_datetime(row['MATCH_LOCALDATE']).strftime('%d/%m'), row['CONTESTANTHOME_NAME'], row['CONTESTANTHOME_OPTAUUID'], f"{int(row['TOTAL_HOME_SCORE'])}-{int(row['TOTAL_AWAY_SCORE'])}", row['CONTESTANTAWAY_NAME'], row['CONTESTANTAWAY_OPTAUUID'], row['RES'])

    with t2: # MED BOLDEN
        c_l, c_r = st.columns([2, 1])
        v_med = c_r.selectbox("Fokusområde", ["Opbygning", "Gennembrud", "Afslutninger"])
        if v_med == "Opbygning": df_f, ids, tit, cmap = df_all_h[df_all_h['EVENT_X'] <= 50], [1], "OPBYGNING", "Blues"
        elif v_med == "Gennembrud": df_f, ids, tit, cmap = df_all_h[df_all_h['EVENT_X'] > 50], [1], "GENNEMBRUD", "Blues"
        else: df_f, ids, tit, cmap = df_all_h[df_all_h['EVENT_TYPEID'].isin([13,14,15,16])], [13,14,15,16], "AFSLUTNINGER", "YlOrRd"
        c_l.pyplot(plot_custom_pitch(df_f, ids, tit, cmap=cmap, logo=hold_logo))
        df_t = df_f.groupby('PLAYER_NAME').agg(T=('OUTCOME','count'), S=('OUTCOME','sum')).reset_index()
        df_t['R'] = (df_t['S']/df_t['T']*100).fillna(0).astype(int)
        for _, r in df_t.sort_values('T', ascending=False).head(8).iterrows():
            c_r.markdown(f"<div style='display:flex; justify-content:space-between; font-size:11px;'><span>{r['PLAYER_NAME']}</span><span>{r['R']}%</span></div>", unsafe_allow_html=True)
            c_r.progress(r['R']/100)

    with t3: # UDEN BOLDEN
        c_l, c_r = st.columns([2, 1])
        v_uden = c_r.selectbox("Defensiv aktion", ["Erobringer", "Interceptions", "Vundne Dueller"])
        d_map = {"Erobringer": [7, 8], "Interceptions": [12], "Vundne Dueller": [4]}
        c_l.pyplot(plot_custom_pitch(df_all_h, d_map[v_uden], v_uden.upper(), cmap="Greens", logo=hold_logo))
        df_d = df_all_h[df_all_h['EVENT_TYPEID'].isin(d_map[v_uden])].groupby('PLAYER_NAME').size().reset_index(name='C')
        for _, r in df_d.sort_values('C', ascending=False).head(8).iterrows():
            c_r.markdown(f"<div style='font-size:11px;'>{r['PLAYER_NAME']}: {r['C']}</div>", unsafe_allow_html=True)
            c_r.progress(min(r['C']/10, 1.0))

    with t4: # MÅL-SEKVENSER
        if not df_all_events.empty:
            gl = df_all_events.drop_duplicates(['MATCH_OPTAUUID', 'GOAL_TIME']).sort_values(['MATCH_LOCALDATE', 'GOAL_MIN'], ascending=[False, True])
            opts = {f"{r['MATCH_OPTAUUID']}_{r['GOAL_TIME']}": {
                'label': f"{pd.to_datetime(r['MATCH_LOCALDATE']).strftime('%d/%m')} vs {r['CONTESTANTAWAY_NAME'] if r['CONTESTANTHOME_OPTAUUID']==valgt_uuid else r['CONTESTANTHOME_NAME']} ({int(r['TOTAL_HOME_SCORE'])}-{int(r['TOTAL_AWAY_SCORE'])})", 
                'match_id': r['MATCH_OPTAUUID'], 'goal_ts': r['GOAL_TIME'], 
                'opp_uuid': r['CONTESTANTAWAY_OPTAUUID'] if r['CONTESTANTHOME_OPTAUUID']==valgt_uuid else r['CONTESTANTHOME_OPTAUUID'], 
                'min': int(r['GOAL_MIN']), 'date': pd.to_datetime(r['MATCH_LOCALDATE']).strftime('%d/%m/%Y'), 'score_str': f"{int(r['TOTAL_HOME_SCORE'])}-{int(r['TOTAL_AWAY_SCORE'])}"
            } for _, r in gl.iterrows()}
            sk = st.selectbox("Vælg mål", list(opts.keys()), format_func=lambda x: opts[x]['label'])
            sd = opts[sk]
            tge = df_all_events[(df_all_events['MATCH_OPTAUUID'] == sd['match_id']) & (df_all_events['GOAL_TIME'] == sd['goal_ts'])].sort_values('EVENT_TIMESTAMP').copy()
            p_c, l_c = st.columns([2.5, 1])
            p = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='grey')
            f, ax = p.draw(figsize=(10, 7))
            draw_match_info_box(ax, hold_logo, get_logo_img(sd['opp_uuid']), sd['date'], sd['score_str'], sd['min'])
            for i in range(len(tge)-1):
                p.arrows(tge.iloc[i]['EVENT_X'], tge.iloc[i]['EVENT_Y'], tge.iloc[i+1]['EVENT_X'], tge.iloc[i+1]['EVENT_Y'], width=1, color='black', alpha=0.15, ax=ax)
            for _, r in tge.iterrows():
                is_g = str(r['EVENT_TYPEID']) == "16"
                ax.scatter(r['EVENT_X'], r['EVENT_Y'], color='red' if is_g else 'black', s=100, edgecolors='white', zorder=10)
                ax.text(r['EVENT_X'], r['EVENT_Y']+2.5, r['PLAYER_NAME'], fontsize=7, ha='center', fontweight='bold', bbox=dict(facecolor='white', alpha=0.6, edgecolor='none', pad=1), zorder=11)
            p_c.pyplot(f)
            tge['Aktion'] = tge.apply(lambda row: "STRAFFESPARK" if str(row['EVENT_TYPEID'])=="16" and "9" in row['qual_list'] else (get_action_label(row) if get_action_label(row) else "Opbygning"), axis=1)
            l_c.write("**Målsekvens:**")
            l_c.dataframe(tge[['PLAYER_NAME', 'Aktion']].iloc[::-1].rename(columns={'PLAYER_NAME': 'Spiller'}), hide_index=True, use_container_width=True)

    with t5: # SPILLEROVERSIGT
        if not df_all_events.empty:
            df_ms = df_all_events.copy()
            df_ms['is_cross'] = df_ms['qual_list'].apply(lambda x: '2' in x)
            df_ms['is_sa'] = df_ms['qual_list'].apply(lambda x: '210' in x or '209' in x)
            df_ms['is_g'] = df_ms['EVENT_TYPEID'] == 16
            total_g = df_ms['GOAL_TIME'].nunique()
            ps = df_ms.groupby('PLAYER_NAME').agg(Inv=('GOAL_TIME', 'nunique'), Akt=('EVENT_TYPEID', 'count'), Mål=('is_g', 'sum'), Pas=('EVENT_TYPEID', lambda x: (x == 1).sum()), Indl=('is_cross', 'sum'), Skud=('EVENT_TYPEID', lambda x: x.isin([13,14,15]).sum()), SkudAss=('is_sa', 'sum'), Erob=('EVENT_TYPEID', lambda x: x.isin([7,8,12,49]).sum())).reset_index()
            ps['Pct'] = (ps['Inv'] / total_g * 100).round(1)
            c_t, c_g = st.columns([3.5, 1])
            with c_t: st.dataframe(ps.sort_values('Inv', ascending=False), use_container_width=True, hide_index=True)
            with c_g:
                st.write(f"**Målinvolveringer ({total_g})**")
                for _, r in ps.sort_values('Inv', ascending=False).head(10).iterrows():
                    st.markdown(f"<div style='font-size:11px;'>{r['PLAYER_NAME']} ({int(r['Pct'])}%)</div>", unsafe_allow_html=True)
                    st.progress(r['Pct']/100)

    # --- 4. DYNAMISK TAKTISK MATCH-PLAN ---
    st.markdown("---")
    with st.container(border=True):
        st.subheader(f"🛡️ Taktisk Match-Plan: Hvordan slår vi {valgt_hold}?")
        avg_succ = df_all_h['OUTCOME'].mean() * 100
        avg_shots = (df_all_h['EVENT_TYPEID'].isin([13,14,15,16]).sum()) / df_all_h['MATCH_OPTAUUID'].nunique()
        arkitekt = ps.iloc[0] if not ps.empty else {'PLAYER_NAME': 'N/A', 'Pct': 0}
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Modstander Niveau", f"{avg_succ:.1f}%")
            st.caption("Lav succes = Højt pres. Høj succes = Lav blok.")
        with c2:
            st.metric("Skud-trussel", f"{avg_shots:.1f} / kamp")
            st.caption("Vigtigt at blokere skud, hvis de snitter over 10.")
        with c3:
            st.metric("Nøglespiller", arkitekt['PLAYER_NAME'])
            st.caption(f"Involveret i {arkitekt['Pct']}% af deres mål.")

if __name__ == "__main__":
    vis_side()
