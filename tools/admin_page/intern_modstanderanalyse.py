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
    valgt_hold = col_hold.selectbox("Vaely hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid)

    with st.spinner("Henter data..."):
        sql_res = f"SELECT MATCH_LOCALDATE, CONTESTANTHOME_NAME, CONTESTANTAWAY_NAME, TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE, CONTESTANTHOME_OPTAUUID, CONTESTANTAWAY_OPTAUUID, MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE (CONTESTANTHOME_OPTAUUID = '{valgt_uuid}' OR CONTESTANTAWAY_OPTAUUID = '{valgt_uuid}') AND TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS} AND (MATCH_STATUS ILIKE '%Played%' OR MATCH_STATUS ILIKE '%Full%') ORDER BY MATCH_LOCALDATE DESC LIMIT 10"
        df_res = conn.query(sql_res)
        
        if df_res is not None and not df_res.empty:
            m_ids = tuple(df_res['MATCH_OPTAUUID'].tolist())
            m_str = f"('{m_ids[0]}')" if len(m_ids) == 1 else str(m_ids)
            
            # Opdateret SQL med dine feltnavne: EVENT_TIMEMIN, EVENT_TIMESEC
            sql_all_h = f"SELECT e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME, e.MATCH_OPTAUUID, e.EVENT_TIMESTAMP, e.EVENT_OUTCOME as OUTCOME FROM {DB}.OPTA_EVENTS e JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND e.MATCH_OPTAUUID IN {m_str}"
            df_all_h = conn.query(sql_all_h)
            
            sql_seq = f"""
                WITH TargetGoals AS (
                    SELECT MATCH_OPTAUUID, EVENT_TIMESTAMP as G_TIME, EVENT_TIMEMIN as G_MIN, EVENT_OPTAUUID as GOAL_ID 
                    FROM {DB}.OPTA_EVENTS 
                    WHERE EVENT_TYPEID = 16 AND EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}'
                ) 
                SELECT 
                    e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME, 
                    e.EVENT_TIMESTAMP, e.MATCH_OPTAUUID, m.MATCH_LOCALDATE, m.CONTESTANTHOME_NAME, m.CONTESTANTAWAY_NAME, 
                    m.CONTESTANTHOME_OPTAUUID, m.CONTESTANTAWAY_OPTAUUID, m.TOTAL_HOME_SCORE, m.TOTAL_AWAY_SCORE, 
                    tg.G_TIME as GOAL_TIME, tg.G_MIN as GOAL_MIN, tg.GOAL_ID, 
                    LISTAGG(q.QUALIFIER_ID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_ID) as qual_list 
                FROM {DB}.OPTA_EVENTS e 
                JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID 
                JOIN {DB}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID 
                INNER JOIN TargetGoals tg ON e.MATCH_OPTAUUID = tg.MATCH_OPTAUUID 
                AND e.EVENT_TIMESTAMP >= DATEADD(second, -20, tg.G_TIME) AND e.EVENT_TIMESTAMP <= tg.G_TIME 
                LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
                WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' 
                GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16
            """
            df_all_events = conn.query(sql_seq)

    t1, t2, t3, t4, t5 = st.tabs(["OVERSIGT", "MED BOLDEN", "UDEN BOLDEN", "MAALSEKVENSER", "SPILLEROVERSIGT"])

    with t1:
        if df_res is not None:
            df_res['RES'] = df_res.apply(lambda r: "D" if r['TOTAL_HOME_SCORE'] == r['TOTAL_AWAY_SCORE'] else ("W" if ((r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid and r['TOTAL_HOME_SCORE'] > r['TOTAL_AWAY_SCORE']) or (r['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid and r['TOTAL_AWAY_SCORE'] > r['TOTAL_HOME_SCORE'])) else "L"), axis=1)
            for _, row in df_res.iterrows():
                draw_match_row(pd.to_datetime(row['MATCH_LOCALDATE']).strftime('%d/%m'), row['CONTESTANTHOME_NAME'], row['CONTESTANTHOME_OPTAUUID'], f"{int(row['TOTAL_HOME_SCORE'])}-{int(row['TOTAL_AWAY_SCORE'])}", row['CONTESTANTAWAY_NAME'], row['CONTESTANTAWAY_OPTAUUID'], row['RES'])

    with t4:
        if df_all_events is not None and not df_all_events.empty:
            gl = df_all_events.drop_duplicates(['MATCH_OPTAUUID', 'GOAL_TIME']).sort_values(['MATCH_LOCALDATE', 'GOAL_MIN'], ascending=[False, True])
            opts = {f"{r['MATCH_OPTAUUID']}_{r['GOAL_TIME']}": {
                'label': f"{pd.to_datetime(r['MATCH_LOCALDATE']).strftime('%d/%m')} vs {r['CONTESTANTAWAY_NAME'] if r['CONTESTANTHOME_OPTAUUID']==valgt_uuid else r['CONTESTANTHOME_NAME']} ({int(r['TOTAL_HOME_SCORE'])}-{int(r['TOTAL_AWAY_SCORE'])})", 
                'match_id': r['MATCH_OPTAUUID'], 'goal_ts': r['GOAL_TIME'], 
                'opp_uuid': r['CONTESTANTAWAY_OPTAUUID'] if r['CONTESTANTHOME_OPTAUUID']==valgt_uuid else r['CONTESTANTHOME_OPTAUUID'], 
                'min': int(r['GOAL_MIN']), 'date': pd.to_datetime(r['MATCH_LOCALDATE']).strftime('%d/%m/%Y'), 'score_str': f"{int(r['TOTAL_HOME_SCORE'])}-{int(r['TOTAL_AWAY_SCORE'])}"
            } for _, r in gl.iterrows()}
            sk = st.selectbox("Vaely maal", list(opts.keys()), format_func=lambda x: opts[x]['label'])
            sd = opts[sk]
            tge = df_all_events[(df_all_events['MATCH_OPTAUUID'] == sd['match_id']) & (df_all_events['GOAL_TIME'] == sd['goal_ts'])].sort_values('EVENT_TIMESTAMP').copy()
            
            p_c, l_c = st.columns([2.5, 1])
            p = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='grey')
            f, ax = p.draw(figsize=(10, 7))
            draw_match_info_box(ax, hold_logo, get_logo_img(sd['opp_uuid']), sd['date'], sd['score_str'], sd['min'])
            
            for i in range(len(tge)-1):
                p.arrows(tge.iloc[i]['EVENT_X'], tge.iloc[i]['EVENT_Y'], tge.iloc[i+1]['EVENT_X'], tge.iloc[i+1]['EVENT_Y'], width=1, color='black', alpha=0.15, ax=ax)
            
            # Rensede labels (ingen ikoner)
            def get_clean_label(row):
                eid = str(row['EVENT_TYPEID'])
                q_list = str(row['qual_list'])
                if eid == "16": return "STRAFFESPARK" if "9" in q_list else "MAAL"
                if "210" in q_list or "209" in q_list: return "Assist / Key Pass"
                l = get_action_label(row)
                return l if l else "Opbygning"

            tge['Aktion'] = tge.apply(get_clean_label, axis=1)
            p_c.pyplot(f)
            l_c.write("**Maalsekvens:**")
            l_c.dataframe(tge[['PLAYER_NAME', 'Aktion']].iloc[::-1].rename(columns={'PLAYER_NAME': 'Spiller'}), hide_index=True)

    with t5:
        if df_all_events is not None and not df_all_events.empty:
            ps = df_all_events.groupby('PLAYER_NAME').agg(Involveringer=('GOAL_ID', 'nunique')).reset_index()
            st.write("**Statistik i maalsekvenser**")
            st.dataframe(ps.sort_values('Involveringer', ascending=False), use_container_width=True, hide_index=True)

if __name__ == "__main__":
    vis_side()
