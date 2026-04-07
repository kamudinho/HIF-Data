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
    cols = st.columns([0.5, 1.2, 0.25, 0.7, 0.25, 1.2, 0.3], vertical_alignment="center")
    flex_style = "display: flex; align-items: center; height: 30px; margin: 0;"

    with cols[0]: 
        st.markdown(f"<div style='{flex_style} font-size:11px; color:#666;'>{date}</div>", unsafe_allow_html=True)
    with cols[1]: 
        st.markdown(f"<div style='{flex_style} justify-content: flex-end; font-size:13px; font-weight:600; text-align:right;'>{h_name[:12]}</div>", unsafe_allow_html=True)
    with cols[2]:
        logo_h = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == h_uuid), "")
        if logo_h: st.image(logo_h, width=18)
    with cols[3]: 
        st.markdown(f"<div style='{flex_style} justify-content: center;'><div style='background:#f0f2f6; border-radius:3px; width: 100%; text-align:center; font-size:12px; font-weight:800; padding:2px 0;'>{score}</div></div>", unsafe_allow_html=True)
    with cols[4]:
        logo_a = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == a_uuid), "")
        if logo_a: st.image(logo_a, width=18)
    with cols[5]: 
        st.markdown(f"<div style='{flex_style} justify-content: flex-start; font-size:13px; font-weight:600; text-align:left;'>{a_name[:12]}</div>", unsafe_allow_html=True)
    with cols[6]: 
        st.markdown(f"<div style='{flex_style} justify-content: center;'><div style='background-color:{bg_color}; color:white; border-radius:3px; text-align:center; font-weight:bold; font-size:11px; padding:2px 0; width:22px;'>{res_char}</div></div>", unsafe_allow_html=True)

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

    # Team mapping
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
    ids = df_teams_raw['CONTESTANTHOME_OPTAUUID'].unique()
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    team_map = {mapping_lookup.get(str(u).lower().replace('t','')): u for u in ids if mapping_lookup.get(str(u).lower().replace('t',''))}

    col_spacer_top, col_hold = st.columns([3.5, 1])
    valgt_hold = col_hold.selectbox("Vælg hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid)

    with st.spinner("Henter data..."):
        sql_res = f"SELECT MATCH_LOCALDATE, CONTESTANTHOME_NAME, CONTESTANTAWAY_NAME, TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE, CONTESTANTHOME_OPTAUUID, CONTESTANTAWAY_OPTAUUID, MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE (CONTESTANTHOME_OPTAUUID = '{valgt_uuid}' OR CONTESTANTAWAY_OPTAUUID = '{valgt_uuid}') AND TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS} AND (MATCH_STATUS ILIKE '%Played%' OR MATCH_STATUS ILIKE '%Full%' OR MATCH_STATUS ILIKE '%Finish%') ORDER BY MATCH_LOCALDATE DESC LIMIT 10"
        df_res = conn.query(sql_res)
        
        if df_res is not None and not df_res.empty:
            match_ids = tuple(df_res['MATCH_OPTAUUID'].tolist())
            m_ids_str = f"('{match_ids[0]}')" if len(match_ids) == 1 else str(match_ids)
            df_all_h = conn.query(f"SELECT EVENT_X, EVENT_Y, EVENT_TYPEID, PLAYER_NAME, MATCH_OPTAUUID, EVENT_TIMESTAMP, EVENT_OUTCOME as OUTCOME FROM {DB}.OPTA_EVENTS WHERE EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND MATCH_OPTAUUID IN {m_ids_str}")
            
            sql_seq = f"WITH Goals AS (SELECT MATCH_OPTAUUID, EVENT_TIMESTAMP as G_TIME, EVENT_TIMEMIN as G_MIN FROM {DB}.OPTA_EVENTS WHERE EVENT_TYPEID = 16 AND MATCH_OPTAUUID IN {m_ids_str} AND EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}') SELECT e.*, m.MATCH_LOCALDATE, m.CONTESTANTHOME_NAME, m.CONTESTANTAWAY_NAME, m.CONTESTANTHOME_OPTAUUID, m.CONTESTANTAWAY_OPTAUUID, g.G_TIME as GOAL_TIME, g.G_MIN as GOAL_MIN FROM {DB}.OPTA_EVENTS e JOIN {DB}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID INNER JOIN Goals g ON e.MATCH_OPTAUUID = g.MATCH_OPTAUUID AND e.EVENT_TIMESTAMP >= DATEADD(second, -15, g.G_TIME) AND e.EVENT_TIMESTAMP <= g.G_TIME WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}'"
            try: df_all_events = conn.query(sql_seq)
            except: df_all_events = pd.DataFrame()
        else: return

    t1, t2, t3, t4, t5 = st.tabs(["OVERSIGT", "MED BOLDEN", "UDEN BOLDEN", "MÅL-SEKVENSER", "SPILLEROVERSIGT"])

    with t1:
        # --- 1. DATA BEREGNING ---
        df_res['RES'] = df_res.apply(lambda r: "D" if r['TOTAL_HOME_SCORE'] == r['TOTAL_AWAY_SCORE'] else ("W" if ((r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid and r['TOTAL_HOME_SCORE'] > r['TOTAL_AWAY_SCORE']) or (r['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid and r['TOTAL_AWAY_SCORE'] > r['TOTAL_HOME_SCORE'])) else "L"), axis=1)
        
        df_vol = df_all_h.groupby('MATCH_OPTAUUID').agg(
            P_tot=('EVENT_TYPEID', lambda x: (x == 1).sum()),
            P_suc=('EVENT_TYPEID', lambda x: ((df_all_h.loc[x.index, 'EVENT_TYPEID'] == 1) & (df_all_h.loc[x.index, 'OUTCOME'] == 1)).sum()),
            A_tot=('EVENT_TYPEID', lambda x: x.isin([13,14,15,16]).sum()),
            A_suc=('EVENT_TYPEID', lambda x: (df_all_h.loc[x.index, 'EVENT_TYPEID'] == 16).sum()),
            E_tot=('EVENT_TYPEID', lambda x: x.isin([12, 127, 49]).sum()),
            E_suc=('EVENT_TYPEID', lambda x: ((df_all_h.loc[x.index, 'EVENT_TYPEID'].isin([12, 127, 49])) & (df_all_h.loc[x.index, 'OUTCOME'] == 1)).sum()),
            D_tot=('EVENT_TYPEID', lambda x: x.isin([7, 8]).sum()),
            D_suc=('EVENT_TYPEID', lambda x: ((df_all_h.loc[x.index, 'EVENT_TYPEID'].isin([7, 8])) & (df_all_h.loc[x.index, 'OUTCOME'] == 1)).sum()),
            F_tot=('EVENT_TYPEID', lambda x: (x == 4).sum()),
            F_suc=('EVENT_TYPEID', lambda x: (x == 4).sum())
        ).reset_index()

        df_plot = df_res.merge(df_vol, on='MATCH_OPTAUUID', how='left').fillna(0)
        df_plot['LABEL'] = pd.to_datetime(df_plot['MATCH_LOCALDATE']).dt.strftime('%d/%m')
        df_plot = df_plot.sort_values('MATCH_LOCALDATE')
        df_plot['OPP_NAME'] = df_plot.apply(lambda r: r['CONTESTANTAWAY_NAME'] if r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else r['CONTESTANTHOME_NAME'], axis=1)
        df_plot['X_AXIS_LABEL'] = df_plot['LABEL'] + "<br>" + df_plot['OPP_NAME'].str[:3].str.upper()

        # --- 2. FINPUDSES CSS ---
        st.markdown("""
            <style>
            /* Centrerer ALT indhold i metrics (både label og tal) */
            [data-testid="stMetric"] {
                text-align: center;
                display: flex;
                flex-direction: column;
                align-items: center;
            }
            [data-testid="stMetricLabel"] {
                justify-content: center;
                font-size: 11px !important;
                margin-bottom: -5px !important; /* Trækker tallet tættere på overskriften */
            }
            [data-testid="stMetricValue"] {
                font-size: 20px !important;
                font-weight: 700;
                justify-content: center;
            }
            /* Justerer margener i boksen for at minimere luft ved divideren */
            .metric-row-wrapper {
                margin-top: -15px;
                margin-bottom: -10px;
            }
            .divider-line {
                margin-top: 5px; 
                margin-bottom: 10px; 
                border-top: 1px solid #f0f2f6;
            }
            </style>
            """, unsafe_allow_html=True)

        # --- 3. LAYOUT ---
        m_col1, m_spacer, m_col2 = st.columns([1.3, 0.1, 2.0])
        
        with m_col1:
            st.write("**Seneste 10 kampe**")
            
            with st.container(border=True):
                # Metrics række
                st.markdown('<div class="metric-row-wrapper">', unsafe_allow_html=True)
                wins, draws, losses = (df_res['RES'] == "W").sum(), (df_res['RES'] == "D").sum(), (df_res['RES'] == "L").sum()
                mål_s = sum([row['TOTAL_HOME_SCORE'] if row['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else row['TOTAL_AWAY_SCORE'] for _, row in df_res.iterrows()])
                mål_i = sum([row['TOTAL_AWAY_SCORE'] if row['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else row['TOTAL_HOME_SCORE'] for _, row in df_res.iterrows()])

                met_cols = st.columns(5)
                met_cols[0].metric("Pts", (wins*3)+draws)
                met_cols[1].metric("V", wins)
                met_cols[2].metric("U", draws)
                met_cols[3].metric("T", losses)
                met_cols[4].metric("Mål", f"{int(mål_s)}-{int(mål_i)}")
                st.markdown('</div>', unsafe_allow_html=True)

                # Custom divider med mindre luft
                st.markdown('<div class="divider-line"></div>', unsafe_allow_html=True)
                
                # Kampliste
                for _, row in df_res.iterrows():
                    draw_match_row(
                        pd.to_datetime(row['MATCH_LOCALDATE']).strftime('%d/%m'), 
                        row['CONTESTANTHOME_NAME'], row['CONTESTANTHOME_OPTAUUID'], 
                        f"{int(row['TOTAL_HOME_SCORE'])}-{int(row['TOTAL_AWAY_SCORE'])}", 
                        row['CONTESTANTAWAY_NAME'], row['CONTESTANTAWAY_OPTAUUID'], 
                        row['RES']
                    )
                    st.markdown("<hr style='margin:2px 0; opacity:0.05'>", unsafe_allow_html=True)

        with m_col2:
            kat_map = {"Pasninger": 'P', "Afslutninger": 'A', "Erobringer": 'E', "Dueller": 'D', "Frispark": 'F'}
            col_map = {'P': '#084594', 'A': '#cb181d', 'E': '#238b45', 'D': '#ec7014', 'F': '#6a51a3'}

            def draw_stat_chart(chart_key, default_idx):
                h_c, d_c = st.columns([2, 1])
                val = d_c.selectbox("Vælg", list(kat_map.keys()), index=default_idx, key=f"s_{chart_key}", label_visibility="collapsed")
                c_key = kat_map[val]
                avg = df_plot[f'{c_key}_tot'].mean()
                
                h_c.markdown(f"**{val} (Gns: {round(avg, 1)})**")
                
                fig = px.bar(df_plot, x='X_AXIS_LABEL', y=f"{c_key}_tot", text=f"{c_key}_tot",
                              hover_data={'X_AXIS_LABEL': False, 'OPP_NAME': True, f'{c_key}_tot': True})
                
                # Gns linje med lav opacity (0.2)
                fig.add_hline(y=avg, line_dash="dot", line_color="rgba(0,0,0,0.2)", line_width=1,
                              annotation_text="Gns", annotation_position="top right")
                
                fig.update_traces(marker_color=col_map[c_key], textposition='outside', cliponaxis=False)
                fig.update_layout(height=280, margin=dict(t=50, b=0, l=0, r=0), plot_bgcolor='rgba(0,0,0,0)', 
                                  xaxis_title=None, yaxis_title=None, yaxis_showgrid=True, yaxis_gridcolor='#eee')
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

            draw_stat_chart("c1", 0)
            st.markdown("<div style='margin-top:25px;'></div>", unsafe_allow_html=True)
            draw_stat_chart("c2", 1)
            
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
        if v_uden == "Dueller": ids, tit, cm = [7, 8], "DUELLER", "Oranges"
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
            opts = {f"{r['MATCH_OPTAUUID']}_{r['GOAL_TIME']}": {'label': f"{pd.to_datetime(r['MATCH_LOCALDATE']).strftime('%d/%m')} vs {r['CONTESTANTAWAY_NAME'] if r['CONTESTANTHOME_OPTAUUID']==valgt_uuid else r['CONTESTANTHOME_NAME']} ({int(r['GOAL_MIN'])}. min)", 'match_id': r['MATCH_OPTAUUID'], 'goal_ts': r['GOAL_TIME'], 'opp_uuid': r['CONTESTANTAWAY_OPTAUUID'] if r['CONTESTANTHOME_OPTAUUID']==valgt_uuid else r['CONTESTANTHOME_OPTAUUID'], 'min': int(r['GOAL_MIN']), 'date': pd.to_datetime(r['MATCH_LOCALDATE']).strftime('%d/%m/%Y')} for _, r in gl.iterrows()}
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
