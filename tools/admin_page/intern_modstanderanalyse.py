import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
from mplsoccer import Pitch, VerticalPitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS
import requests
from PIL import Image
from io import BytesIO

# --- IMPORT FRA DIN MAPPING.PY ---
from data.utils.mapping import (
    OPTA_EVENT_TYPES, 
    OPTA_QUALIFIERS,
    get_action_label
)

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

def draw_match_row(date, h_name, h_uuid, score, a_name, a_uuid, res_char):
    bg_color = "#2e7d32" if res_char == "W" else ("#757575" if res_char == "D" else "#c62828")
    cols = st.columns([0.5, 1.2, 0.25, 0.7, 0.25, 1.2, 0.3], vertical_alignment="center")
    flex_style = "display: flex; align-items: center; height: 30px; margin: 0;"

    with cols[0]: st.markdown(f"<div style='{flex_style} font-size:11px; color:#666;'>{date}</div>", unsafe_allow_html=True)
    with cols[1]: st.markdown(f"<div style='{flex_style} justify-content: flex-end; font-size:13px; font-weight:600; text-align:right;'>{h_name[:12]}</div>", unsafe_allow_html=True)
    with cols[2]:
        logo_h = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == h_uuid), "")
        if logo_h: st.image(logo_h, width=18)
    with cols[3]: st.markdown(f"<div style='{flex_style} justify-content: center;'><div style='background:#f0f2f6; border-radius:3px; width: 100%; text-align:center; font-size:12px; font-weight:800; padding:2px 0;'>{score}</div></div>", unsafe_allow_html=True)
    with cols[4]:
        logo_a = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == a_uuid), "")
        if logo_a: st.image(logo_a, width=18)
    with cols[5]: st.markdown(f"<div style='{flex_style} justify-content: flex-start; font-size:13px; font-weight:600; text-align:left;'>{a_name[:12]}</div>", unsafe_allow_html=True)
    with cols[6]: st.markdown(f"<div style='{flex_style} justify-content: center;'><div style='background-color:{bg_color}; color:white; border-radius:3px; text-align:center; font-weight:bold; font-size:11px; padding:2px 0; width:22px;'>{res_char}</div></div>", unsafe_allow_html=True)

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
    plot_data = df[df['EVENT_TYPEID'].astype(str).isin([str(i) for i in event_ids])].copy()
    pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
    fig, ax = pitch.draw(figsize=(5, 7))
    
    if zone == 'up': 
        ax.set_ylim(0, 55)
        logo_pos, text_y = [0.04, 0.03, 0.08, 0.08], 0.05
    elif zone == 'down': 
        ax.set_ylim(45, 100)
        logo_pos, text_y = [0.04, 0.90, 0.08, 0.08], 0.97
    else: 
        logo_pos, text_y = [0.04, 0.90, 0.08, 0.08], 0.97
        
    if logo:
        ax_l = ax.inset_axes(logo_pos, transform=ax.transAxes); ax_l.imshow(logo); ax_l.axis('off')
    
    ax.text(0.94, text_y, title, transform=ax.transAxes, fontsize=6, fontweight='bold', ha='right', va='top')
    
    if not plot_data.empty: 
        pitch.kdeplot(plot_data.EVENT_X, plot_data.EVENT_Y, ax=ax, cmap=cmap, fill=True, alpha=0.5, levels=100)
    return fig

# --- 3. HOVEDFUNKTION ---
def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn: return

    # --- 1. HENT HOLD MAPPING ---
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
    ids = df_teams_raw['CONTESTANTHOME_OPTAUUID'].unique()
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    
    team_map = {
        mapping_lookup.get(str(u).lower().replace('t','')): u 
        for u in ids 
        if mapping_lookup.get(str(u).lower().replace('t','')) is not None
    }

    col_spacer_top, col_hold = st.columns([3.5, 1])
    valgt_hold = col_hold.selectbox("Vælg hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid)

    with st.spinner("Henter data..."):
        # SQL for seneste 10 kampe
        sql_res = f"""
            SELECT MATCH_LOCALDATE, CONTESTANTHOME_NAME, CONTESTANTAWAY_NAME, 
                    TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE, CONTESTANTHOME_OPTAUUID, 
                    CONTESTANTAWAY_OPTAUUID, MATCH_OPTAUUID 
            FROM {DB}.OPTA_MATCHINFO 
            WHERE (CONTESTANTHOME_OPTAUUID = '{valgt_uuid}' OR CONTESTANTAWAY_OPTAUUID = '{valgt_uuid}') 
            AND TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS} 
            AND (MATCH_STATUS ILIKE '%Played%' OR MATCH_STATUS ILIKE '%Full%' OR MATCH_STATUS ILIKE '%Finish%') 
            ORDER BY MATCH_LOCALDATE DESC LIMIT 10
        """
        df_res = conn.query(sql_res)
        
        if df_res is not None and not df_res.empty:
            match_ids = tuple(df_res['MATCH_OPTAUUID'].tolist())
            m_ids_str = f"('{match_ids[0]}')" if len(match_ids) == 1 else str(match_ids)
            
            # --- SQL: HENTER EVENTS ---
            sql_all_h = f"""
                SELECT 
                    e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, 
                    TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME, 
                    e.MATCH_OPTAUUID, e.EVENT_TIMESTAMP, e.EVENT_OUTCOME as OUTCOME,
                    LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
                FROM {DB}.OPTA_EVENTS e
                JOIN (SELECT DISTINCT PLAYER_OPTAUUID, FIRST_NAME, LAST_NAME FROM {DB}.OPTA_PLAYERS WHERE FIRST_NAME IS NOT NULL) p 
                    ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
                LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
                WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' 
                AND e.MATCH_OPTAUUID IN {m_ids_str}
                GROUP BY 1, 2, 3, 4, 5, 6, 7
            """
            df_all_h = conn.query(sql_all_h)
            
            if df_all_h is not None and not df_all_h.empty:
                df_all_h['qual_list'] = df_all_h['QUALIFIERS'].fillna('').str.split(',')
                df_all_h['Action_Label'] = df_all_h.apply(get_action_label, axis=1)

            # --- SQL: MÅL-SEKVENSER (RETTET SORTERING) ---
            sql_seq = f"""
            WITH SeasonMatches AS (
                SELECT MATCH_OPTAUUID, CONTESTANTHOME_NAME, CONTESTANTAWAY_NAME, 
                       MATCH_LOCALDATE, CONTESTANTHOME_OPTAUUID, CONTESTANTAWAY_OPTAUUID,
                       TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE
                FROM {DB}.OPTA_MATCHINFO 
                WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}
            ),
            TargetGoals AS (
                SELECT MATCH_OPTAUUID, EVENT_TIMESTAMP as G_TIME, EVENT_TIMEMIN as G_MIN,
                       EVENT_OPTAUUID as GOAL_ID
                FROM {DB}.OPTA_EVENTS 
                WHERE EVENT_TYPEID = 16 AND EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}'
                AND MATCH_OPTAUUID IN (SELECT MATCH_OPTAUUID FROM SeasonMatches)
            )
            SELECT e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, 
                   TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME, 
                   e.EVENT_TIMESTAMP, e.MATCH_OPTAUUID,
                   m.MATCH_LOCALDATE, m.CONTESTANTHOME_NAME, m.CONTESTANTAWAY_NAME, 
                   m.CONTESTANTHOME_OPTAUUID, m.CONTESTANTAWAY_OPTAUUID,
                   m.TOTAL_HOME_SCORE, m.TOTAL_AWAY_SCORE,
                   tg.G_TIME as GOAL_TIME, tg.G_MIN as GOAL_MIN, tg.GOAL_ID,
                   LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
            FROM {DB}.OPTA_EVENTS e
            JOIN (SELECT DISTINCT PLAYER_OPTAUUID, FIRST_NAME, LAST_NAME FROM {DB}.OPTA_PLAYERS WHERE FIRST_NAME IS NOT NULL) p 
                ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
            JOIN SeasonMatches m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
            INNER JOIN TargetGoals tg ON e.MATCH_OPTAUUID = tg.MATCH_OPTAUUID
                AND e.EVENT_TIMESTAMP >= DATEADD(second, -20, tg.G_TIME)
                AND e.EVENT_TIMESTAMP <= tg.G_TIME
            LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}'
            GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16
            """
            df_all_events = conn.query(sql_seq)
            if df_all_events is not None and not df_all_events.empty:
                df_all_events['qual_list'] = df_all_events['QUALIFIERS'].fillna('').str.split(',')
        else:
            st.error("Ingen data fundet.")
            return

    # --- TABS ---
    t1, t2, t3, t4, t5 = st.tabs(["OVERSIGT", "MED BOLDEN", "UDEN BOLDEN", "MÅL-SEKVENSER", "SPILLEROVERSIGT"])

    with t1:
        # Resultat logik
        df_res['RES'] = df_res.apply(lambda r: "D" if r['TOTAL_HOME_SCORE'] == r['TOTAL_AWAY_SCORE'] else ("W" if ((r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid and r['TOTAL_HOME_SCORE'] > r['TOTAL_AWAY_SCORE']) or (r['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid and r['TOTAL_AWAY_SCORE'] > r['TOTAL_HOME_SCORE'])) else "L"), axis=1)
        
        df_vol = df_all_h.groupby('MATCH_OPTAUUID').agg(
            P_tot=('EVENT_TYPEID', lambda x: (x == 1).sum()),
            A_tot=('EVENT_TYPEID', lambda x: x.isin([13,14,15,16]).sum()),
            E_tot=('EVENT_TYPEID', lambda x: x.isin([7, 8, 12, 127, 49]).sum()),
            D_tot=('EVENT_TYPEID', lambda x: x.isin([7, 44]).sum()),
            F_tot=('EVENT_TYPEID', lambda x: (x == 4).sum())
        ).reset_index()

        df_plot = df_res.merge(df_vol, on='MATCH_OPTAUUID', how='left').fillna(0)
        df_plot['LABEL'] = pd.to_datetime(df_plot['MATCH_LOCALDATE']).dt.strftime('%d/%m')
        df_plot = df_plot.sort_values('MATCH_LOCALDATE')
        df_plot['OPP_NAME'] = df_plot.apply(lambda r: r['CONTESTANTAWAY_NAME'] if r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else r['CONTESTANTHOME_NAME'], axis=1)
        df_plot['X_AXIS_LABEL'] = df_plot['LABEL'] + "<br>" + df_plot['OPP_NAME'].str[:3].str.upper()

        st.markdown("<style>[data-testid='stMetric'] { text-align: center; align-items: center; }</style>", unsafe_allow_html=True)
        m_col1, m_spacer, m_col2 = st.columns([1.3, 0.1, 2.0])
        
        with m_col1:
            st.write("**Seneste 10 kampe**")
            with st.container(border=True):
                wins, draws = (df_res['RES'] == "W").sum(), (df_res['RES'] == "D").sum()
                met_cols = st.columns(3)
                met_cols[0].metric("Pts", (wins*3)+draws)
                met_cols[1].metric("V", wins)
                met_cols[2].metric("U", draws)
                st.markdown("<hr style='margin:10px 0'>", unsafe_allow_html=True)
                for _, row in df_res.iterrows():
                    draw_match_row(pd.to_datetime(row['MATCH_LOCALDATE']).strftime('%d/%m'), row['CONTESTANTHOME_NAME'], row['CONTESTANTHOME_OPTAUUID'], f"{int(row['TOTAL_HOME_SCORE'])}-{int(row['TOTAL_AWAY_SCORE'])}", row['CONTESTANTAWAY_NAME'], row['CONTESTANTAWAY_OPTAUUID'], row['RES'])

        with m_col2:
            kat_map = {"Pasninger": 'P', "Afslutninger": 'A', "Erobringer": 'E', "Dueller": 'D'}
            val1 = st.selectbox("Vælg Kategori", list(kat_map.keys()), key="val_top")
            c_key = kat_map[val1]
            fig1 = px.bar(df_plot, x='X_AXIS_LABEL', y=f"{c_key}_tot", text=f"{c_key}_tot", color_discrete_sequence=['#df003b'])
            fig1.update_layout(height=350, margin=dict(t=25, b=0, l=0, r=0), plot_bgcolor='rgba(0,0,0,0)', xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig1, use_container_width=True)

    with t2: # MED BOLDEN
        c_left, c_right = st.columns([2, 1])
        v_med = c_right.selectbox("Vælg Fokus", ["Opbygning", "Gennembrud", "Touches in Box", "Afslutninger"])
        
        if v_med == "Opbygning": df_f, ids, tit, zn = df_all_h[df_all_h['EVENT_X'] <= 50], [1], "OPBYGNING", "up"
        elif v_med == "Gennembrud": df_f, ids, tit, zn = df_all_h[df_all_h['EVENT_X'] > 50], [1], "GENNEMBRUD", "down"
        elif v_med == "Touches in Box": df_f, ids, tit, zn = df_all_h[(df_all_h['EVENT_X'] > 83) & (df_all_h['EVENT_Y'] > 21.1) & (df_all_h['EVENT_Y'] < 78.9)], [0], "BOX TOUCHES", "down"
        else: df_f, ids, tit, zn = df_all_h[df_all_h['EVENT_TYPEID'].isin([13,14,15,16])], [13,14,15,16], "AFSLUTNINGER", "down"

        with c_left: st.pyplot(plot_custom_pitch(df_f, df_f['EVENT_TYPEID'].unique().tolist() if v_med == "Touches in Box" else ids, tit, zone=zn, cmap="Blues", logo=hold_logo))

    with t3: # UDEN BOLDEN
        c_left, c_right = st.columns([2, 1])
        v_uden = c_right.selectbox("Vælg Fokus", ["Egen halvdel: Erobringer", "Off. halvdel: Pres"])
        if "Pres" in v_uden: df_f, ids, tit, zn = df_all_h[(df_all_h['EVENT_X'] > 50) & (df_all_h['EVENT_TYPEID'].isin([7,8,12,127]))], [7,8,12,127], "HØJT PRES", "down"
        else: df_f, ids, tit, zn = df_all_h[(df_all_h['EVENT_X'] <= 50) & (df_all_h['EVENT_TYPEID'].isin([7,8,12,127]))], [7,8,12,127], "DEF. EROBRINGER", "up"
        with c_left: st.pyplot(plot_custom_pitch(df_f, ids, tit, zone=zn, cmap="Oranges", logo=hold_logo))

    with t4: # MÅL-SEKVENSER (RETTET)
        if not df_all_events.empty:
            gl = df_all_events.drop_duplicates(['GOAL_ID']).sort_values(['MATCH_LOCALDATE', 'GOAL_TIME'], ascending=[False, False])
            opts = {str(r['GOAL_ID']): {
                'label': f"{pd.to_datetime(r['MATCH_LOCALDATE']).strftime('%d/%m')} vs {r['CONTESTANTAWAY_NAME'] if r['CONTESTANTHOME_OPTAUUID']==valgt_uuid else r['CONTESTANTHOME_NAME']} ({int(r['GOAL_MIN'])}')", 
                'match_id': r['MATCH_OPTAUUID'], 'goal_id': r['GOAL_ID'], 'opp_uuid': r['CONTESTANTAWAY_OPTAUUID'] if r['CONTESTANTHOME_OPTAUUID']==valgt_uuid else r['CONTESTANTHOME_OPTAUUID'],
                'min': int(r['GOAL_MIN']), 'date': pd.to_datetime(r['MATCH_LOCALDATE']).strftime('%d/%m/%Y'), 'score_str': f"{int(r['TOTAL_HOME_SCORE'])}-{int(r['TOTAL_AWAY_SCORE'])}"
            } for _, r in gl.iterrows()}

            sk = st.selectbox("Vælg mål", list(opts.keys()), format_func=lambda x: opts[x]['label'])
            sd = opts[sk]
            tge = df_all_events[df_all_events['GOAL_ID'] == sd['goal_id']].sort_values('EVENT_TIMESTAMP').copy()

            p_c, l_c = st.columns([2.5, 1])
            p = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='grey')
            f, ax = p.draw(figsize=(10, 7))
            draw_match_info_box(ax, hold_logo, get_logo_img(sd['opp_uuid']), sd['date'], sd['score_str'], sd['min'])
            
            for i in range(len(tge)-1):
                p.arrows(tge.iloc[i]['EVENT_X'], tge.iloc[i]['EVENT_Y'], tge.iloc[i+1]['EVENT_X'], tge.iloc[i+1]['EVENT_Y'], width=1, color='black', alpha=0.15, ax=ax)
            for _, r in tge.iterrows():
                is_goal = str(r['EVENT_TYPEID']) == "16"
                ax.scatter(r['EVENT_X'], r['EVENT_Y'], color='red' if is_goal else 'black', s=100, edgecolors='white', zorder=10)
                ax.text(r['EVENT_X'], r['EVENT_Y']+2, r['PLAYER_NAME'], fontsize=7, ha='center', fontweight='bold', bbox=dict(facecolor='white', alpha=0.6, edgecolor='none', pad=1))
            p_c.pyplot(f)
            l_c.dataframe(tge[['PLAYER_NAME', 'EVENT_TYPEID']].iloc[::-1], hide_index=True, use_container_width=True)

    with t5: # SPILLEROVERSIGT
        if not df_all_events.empty:
            df_mål_stats = df_all_events.copy()
            df_mål_stats['is_cross'] = df_mål_stats['qual_list'].apply(lambda x: '2' in x)
            df_mål_stats['is_shot_assist'] = df_mål_stats['qual_list'].apply(lambda x: '210' in x or '209' in x)
            df_mål_stats['is_goal'] = df_mål_stats['EVENT_TYPEID'] == 16
            
            total_goals_count = df_mål_stats['GOAL_ID'].nunique()
            player_stats = df_mål_stats.groupby('PLAYER_NAME').agg(
                Involveringer=('GOAL_ID', 'nunique'),
                Mål=('is_goal', 'sum'),
                Pasninger=('EVENT_TYPEID', lambda x: (x == 1).sum()),
                Indlæg=('is_cross', 'sum'),
                Erobringer=('EVENT_TYPEID', lambda x: x.isin([7, 8, 12, 127, 49]).sum())
            ).reset_index()
            player_stats['Involvering_Pct'] = (player_stats['Involveringer'] / total_goals_count * 100).round(1)
            player_stats = player_stats.sort_values('Involveringer', ascending=False)

            col_tabel, col_graf = st.columns([3, 1.5])
            with col_tabel:
                st.dataframe(player_stats, hide_index=True, use_container_width=True, column_config={
                    "PLAYER_NAME": "Spiller", "Involvering_Pct": st.column_config.NumberColumn("Involvering %", format="%.1f%%")
                })
            with col_graf:
                st.write(f"**Top Involveringer (Total: {total_goals_count})**")
                for _, r in player_stats.head(10).iterrows():
                    st.markdown(f"""<div style='font-size:11px; font-weight:600;'>{r['PLAYER_NAME']} ({int(r['Involveringer'])})</div>
                        <div style='background:#f0f2f6; height:5px; width:100%; border-radius:4px;'>
                        <div style='background:#df003b; height:5px; width:{r['Involvering_Pct']}%; border-radius:4px;'></div></div><br>""", unsafe_allow_html=True)

if __name__ == "__main__":
    vis_side()
