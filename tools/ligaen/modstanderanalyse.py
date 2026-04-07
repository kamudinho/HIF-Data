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
        # Seneste 10 kampe til t1
        sql_res = f"SELECT MATCH_LOCALDATE, CONTESTANTHOME_NAME, CONTESTANTAWAY_NAME, TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE, CONTESTANTHOME_OPTAUUID, CONTESTANTAWAY_OPTAUUID, MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE (CONTESTANTHOME_OPTAUUID = '{valgt_uuid}' OR CONTESTANTAWAY_OPTAUUID = '{valgt_uuid}') AND TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS} AND (MATCH_STATUS ILIKE '%Played%' OR MATCH_STATUS ILIKE '%Full%' OR MATCH_STATUS ILIKE '%Finish%') ORDER BY MATCH_LOCALDATE DESC LIMIT 10"
        df_res = conn.query(sql_res)
        
        if df_res is not None and not df_res.empty:
            match_ids = tuple(df_res['MATCH_OPTAUUID'].tolist())
            m_ids_str = f"('{match_ids[0]}')" if len(match_ids) == 1 else str(match_ids)
            df_all_h = conn.query(f"SELECT EVENT_X, EVENT_Y, EVENT_TYPEID, PLAYER_NAME, MATCH_OPTAUUID, EVENT_TIMESTAMP, EVENT_OUTCOME as OUTCOME FROM {DB}.OPTA_EVENTS WHERE EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND MATCH_OPTAUUID IN {m_ids_str}")
            
            # --- NY LOGIK TIL T4: HENT ALLE MÅL FOR SÆSONEN ---
            sql_seq = f"""
            WITH Goals AS (
                SELECT MATCH_OPTAUUID, EVENT_TIMESTAMP as G_TIME, EVENT_TIMEMIN as G_MIN 
                FROM {DB}.OPTA_EVENTS 
                WHERE EVENT_TYPEID = 16 
                  AND EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}'
                  AND MATCH_OPTAUUID IN (SELECT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS})
            ) 
            SELECT e.*, m.MATCH_LOCALDATE, m.CONTESTANTHOME_NAME, m.CONTESTANTAWAY_NAME, m.CONTESTANTHOME_OPTAUUID, m.CONTESTANTAWAY_OPTAUUID, g.G_TIME as GOAL_TIME, g.G_MIN as GOAL_MIN 
            FROM {DB}.OPTA_EVENTS e 
            JOIN {DB}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID 
            INNER JOIN Goals g ON e.MATCH_OPTAUUID = g.MATCH_OPTAUUID 
                AND e.EVENT_TIMESTAMP >= DATEADD(second, -20, g.G_TIME) 
                AND e.EVENT_TIMESTAMP <= g.G_TIME 
            WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}'
            """
            try: df_all_events = conn.query(sql_seq)
            except: df_all_events = pd.DataFrame()
        else: return

    t1, t2, t3, t4, t5 = st.tabs(["OVERSIGT", "MED BOLDEN", "UDEN BOLDEN", "MÅL-SEKVENSER", "SPILLEROVERSIGT"])

    with t1:
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

        st.markdown("""<style>[data-testid="stMetric"] { text-align: center; display: flex; flex-direction: column; align-items: center; width: 100%; } [data-testid="stMetricLabel"] { display: flex; justify-content: center; align-items: center; width: 100%; font-size: 11px !important; margin-bottom: -10px !important; } [data-testid="stMetricValue"] { display: flex; justify-content: center; align-items: center; width: 100%; font-size: 20px !important; font-weight: 700; } .metric-row-wrapper { margin-top: -35px; margin-bottom: -25px; } .compact-divider { margin-top: -5px; margin-bottom: 5px; border-top: 1px solid #f0f2f6; }</style>""", unsafe_allow_html=True)

        m_col1, m_spacer, m_col2 = st.columns([1.3, 0.1, 2.0])
        with m_col1:
            st.write("**Seneste 10 kampe**")
            with st.container(border=True):
                st.markdown('<div class="metric-row-wrapper">', unsafe_allow_html=True)
                wins, draws, losses = (df_res['RES'] == "W").sum(), (df_res['RES'] == "D").sum(), (df_res['RES'] == "L").sum()
                mål_s = sum([row['TOTAL_HOME_SCORE'] if row['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else row['TOTAL_AWAY_SCORE'] for _, row in df_res.iterrows()])
                mål_i = sum([row['TOTAL_AWAY_SCORE'] if row['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else row['TOTAL_HOME_SCORE'] for _, row in df_res.iterrows()])
                met_cols = st.columns(5)
                met_cols[0].metric("Pts", (wins*3)+draws); met_cols[1].metric("V", wins); met_cols[2].metric("U", draws); met_cols[3].metric("T", losses); met_cols[4].metric("Mål", f"{int(mål_s)}-{int(mål_i)}")
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('<div class="compact-divider"></div>', unsafe_allow_html=True)
                for _, row in df_res.iterrows():
                    draw_match_row(pd.to_datetime(row['MATCH_LOCALDATE']).strftime('%d/%m'), row['CONTESTANTHOME_NAME'], row['CONTESTANTHOME_OPTAUUID'], f"{int(row['TOTAL_HOME_SCORE'])}-{int(row['TOTAL_AWAY_SCORE'])}", row['CONTESTANTAWAY_NAME'], row['CONTESTANTAWAY_OPTAUUID'], row['RES'])
                    st.markdown("<hr style='margin:2px 0; opacity:0.05'>", unsafe_allow_html=True)

        with m_col2:
            kat_map, col_map = {"Pasninger": 'P', "Afslutninger": 'A', "Erobringer": 'E', "Dueller": 'D', "Frispark": 'F'}, {'P': '#084594', 'A': '#cb181d', 'E': '#238b45', 'D': '#ec7014', 'F': '#6a51a3'}
            h_c1, d_c1 = st.columns([2, 1])
            val1 = d_c1.selectbox("Vælg", list(kat_map.keys()), index=0, key="val_top", label_visibility="collapsed")
            c_key1, avg1 = kat_map[val1], df_plot[f'{kat_map[val1]}_tot'].mean()
            h_c1.markdown(f"**{val1} (Gns: {round(avg1, 1)})**")
            fig1 = px.bar(df_plot, x='X_AXIS_LABEL', y=f"{c_key1}_tot", text=f"{c_key1}_tot")
            fig1.add_hline(y=avg1, line_dash="dot", line_color="rgba(0,0,0,0.2)", line_width=1); fig1.update_traces(marker_color=col_map[c_key1], textposition='outside'); fig1.update_layout(height=300, margin=dict(t=25, b=0, l=0, r=0), plot_bgcolor='rgba(0,0,0,0)', xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})
            
            options_2 = [k for k in kat_map.keys() if k != val1]
            h_c2, d_c2 = st.columns([2, 1])
            val2 = d_c2.selectbox("Vælg", options_2, index=0, key="val_bot", label_visibility="collapsed")
            c_key2, avg2 = kat_map[val2], df_plot[f'{kat_map[val2]}_tot'].mean()
            h_c2.markdown(f"**{val2} (Gns: {round(avg2, 1)})**")
            fig2 = px.bar(df_plot, x='X_AXIS_LABEL', y=f"{c_key2}_tot", text=f"{c_key2}_tot")
            fig2.add_hline(y=avg2, line_dash="dot", line_color="rgba(0,0,0,0.2)", line_width=1); fig2.update_traces(marker_color=col_map[c_key2], textposition='outside'); fig2.update_layout(height=300, margin=dict(t=25, b=0, l=0, r=0), plot_bgcolor='rgba(0,0,0,0)', xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})

    with t2:
        st.markdown("""<style>[data-testid="stHorizontalBlock"] [data-testid="stMetric"] { text-align: center; align-items: center; justify-content: center; width: 100%; } [data-testid="stMetricLabel"] { justify-content: center !important; font-size: 10px !important; white-space: nowrap; margin-bottom: -3px !important; } [data-testid="stMetricValue"] { justify-content: center !important; font-size: 14px !important; font-weight: 700; }</style>""", unsafe_allow_html=True)
        c_left, c_right = st.columns([2, 1])
        v_med = c_right.selectbox("Vælg Fokusområde", ["Opbygning", "Gennembrud", "Touches in Box", "Afslutninger"], key="ms_t2", label_visibility="collapsed")
        n_matches, total_minutes = df_all_h['MATCH_OPTAUUID'].nunique(), df_all_h['MATCH_OPTAUUID'].nunique() * 90
        
        if v_med == "Opbygning": ids, tit, cm, zn, df_f = [1], "OPBYGNING", "Blues", "up", df_all_h[(df_all_h['EVENT_X'] <= 50) & (df_all_h['EVENT_TYPEID'] == 1)].copy()
        elif v_med == "Gennembrud": ids, tit, cm, zn, df_f = [1], "GENNEMBRUD", "Blues", "down", df_all_h[(df_all_h['EVENT_X'] > 50) & (df_all_h['EVENT_TYPEID'] == 1)].copy()
        elif v_med == "Touches in Box": ids, tit, cm, zn, df_f = [0], "TOUCHES IN BOX", "Blues", "down", df_all_h[(df_all_h['EVENT_X'] > 83) & (df_all_h['EVENT_Y'] > 21.1) & (df_all_h['EVENT_Y'] < 78.9)].copy(); df_shots = df_all_h[df_all_h['EVENT_TYPEID'].isin([13, 14, 15, 16])].copy()
        else: ids, tit, cm, zn, df_f = [13, 14, 15, 16], "AFSLUTNINGER", "YlOrRd", "down", df_all_h[df_all_h['EVENT_TYPEID'].isin([13, 14, 15, 16])].copy()

        c_left.pyplot(plot_custom_pitch(df_f, df_f['EVENT_TYPEID'].unique().tolist() if v_med == "Touches in Box" else ids, tit, zone=zn, cmap=cm, logo=hold_logo))
        with c_right:
            if v_med == "Touches in Box":
                m_cols = st.columns(3); m_cols[0].metric("Touches", len(df_f)); m_cols[1].metric("p90", round(len(df_f)/total_minutes*90, 1)); m_cols[2].metric("Afsl/Box %", f"{int(len(df_shots)/len(df_f)*100)}%")
            elif v_med == "Afslutninger":
                goals = len(df_f[df_f['EVENT_TYPEID'] == 16])
                m_cols = st.columns(5); m_cols[0].metric("Skud", len(df_f)); m_cols[1].metric("p90", round(len(df_f)/total_minutes*90,1)); m_cols[2].metric("Mål", goals); m_cols[3].metric("p90", round(goals/total_minutes*90,1)); m_cols[4].metric("Konv %", f"{int(goals/len(df_f)*100)}%")
            else:
                m_cols = st.columns(3); m_cols[0].metric("Total", len(df_f)); m_cols[1].metric("Gns p90", round(len(df_f)/total_minutes*90,1)); m_cols[2].metric("Succes", f"{int(df_f['OUTCOME'].sum()/len(df_f)*100)}%")
            
            st.markdown("<div style='margin-top:10px; border-top: 1px solid #eee; padding-top: 10px;'></div>", unsafe_allow_html=True)
            st.write(f"**Top 8: {v_med}**")
            if not df_f.empty:
                if v_med == "Touches in Box":
                    df_top = df_f.groupby('PLAYER_NAME').size().to_frame('BOX').join(df_shots.groupby('PLAYER_NAME').size().to_frame('SHOTS'), how='left').fillna(0)
                    df_top['PCT'] = (df_top['SHOTS'] / df_top['BOX'] * 100).fillna(0).astype(int); df_top = df_top.sort_values('BOX', ascending=False).head(8).reset_index()
                    for _, r in df_top.iterrows(): st.markdown(f"""<div style="margin-bottom: 12px;"><div style="display: flex; justify-content: space-between; font-size: 11px; font-weight: 600; margin-bottom: 2px;"><span>{r['PLAYER_NAME']}</span><span>{int(r['SHOTS'])} / {int(r['BOX'])} ({r['PCT']}%)</span></div><div style="background-color: #f0f2f6; border-radius: 4px; height: 5px; width: 100%;"><div style="background-color: #238b45; height: 5px; width: {min(r['PCT'], 100)}%; border-radius: 4px;"></div></div></div>""", unsafe_allow_html=True)
                else:
                    df_top = df_f.groupby('PLAYER_NAME').agg(TOTAL=('EVENT_TYPEID' if v_med=="Afslutninger" else 'OUTCOME', 'count'), SUCCESS=('EVENT_TYPEID' if v_med=="Afslutninger" else 'OUTCOME', lambda x: (x==16).sum() if v_med=="Afslutninger" else (x==1).sum())).reset_index()
                    df_top['PCT'] = (df_top['SUCCESS'] / df_top['TOTAL'] * 100).round(1); df_top = df_top.sort_values('TOTAL', ascending=False).head(8)
                    for _, r in df_top.iterrows(): st.markdown(f"""<div style="margin-bottom: 12px;"><div style="display: flex; justify-content: space-between; font-size: 11px; font-weight: 600; margin-bottom: 2px;"><span>{r['PLAYER_NAME']}</span><span>{int(r['SUCCESS'])} / {int(r['TOTAL'])} ({int(r['PCT'])}%)</span></div><div style="background-color: #f0f2f6; border-radius: 4px; height: 5px; width: 100%;"><div style="background-color: {'#d73027' if v_med=='Afslutninger' else '#084594'}; height: 5px; width: {r['PCT']}%; border-radius: 4px;"></div></div></div>""", unsafe_allow_html=True)

    with t3:
        c_left, c_right = st.columns([2, 1])
        v_uden = c_right.selectbox("Vælg Fokusområde", ["Egen halvdel: Erobringer", "Off. halvdel: Pres", "Egen halvdel: Dueller", "Off. halvdel: Dueller"], key="ms_t3", label_visibility="collapsed")
        e_ids, d_ids = [7, 8, 12, 127], [7, 44]
        if "Erobringer" in v_uden: ids, tit, zn, df_f = e_ids, "Egen halvdel: EROBRINGER", "up", df_all_h[(df_all_h['EVENT_X'] > 17) & (df_all_h['EVENT_X'] <= 50) & (df_all_h['EVENT_TYPEID'].isin(e_ids))].copy()
        elif "Pres" in v_uden: ids, tit, zn, df_f = e_ids, "Off. halvdel: PRES", "down", df_all_h[(df_all_h['EVENT_X'] > 50) & (df_all_h['EVENT_TYPEID'].isin(e_ids))].copy()
        elif "Egen halvdel: Dueller" in v_uden: ids, tit, zn, df_f = d_ids, "Egen halvdel: DUELLER", "up", df_all_h[(df_all_h['EVENT_X'] > 17) & (df_all_h['EVENT_X'] <= 50) & (df_all_h['EVENT_TYPEID'].isin(d_ids))].copy()
        else: ids, tit, zn, df_f = d_ids, "Off. halvdel: DUELLER", "down", df_all_h[(df_all_h['EVENT_X'] > 50) & (df_all_h['EVENT_TYPEID'].isin(d_ids))].copy()

        c_left.pyplot(plot_custom_pitch(df_f, ids, tit, zone=zn, cmap="Oranges", logo=hold_logo))
        with c_right:
            m_cols = st.columns(3); m_cols[0].metric("Total", len(df_f)); m_cols[1].metric("p90", round(len(df_f)/total_minutes*90, 1)); m_cols[2].metric("Succes", f"{int(df_f['OUTCOME'].sum()/len(df_f)*100)}%")
            st.markdown("<div style='margin-top:10px; border-top: 1px solid #eee; padding-top: 10px;'></div>", unsafe_allow_html=True)
            if not df_f.empty:
                df_top = df_f.groupby('PLAYER_NAME').agg(TOTAL=('OUTCOME', 'count'), SUCCESS=('OUTCOME', lambda x: (x==1).sum())).reset_index()
                df_top['PCT'] = (df_top['SUCCESS'] / df_top['TOTAL'] * 100).round(1); df_top = df_top.sort_values('TOTAL', ascending=False).head(8)
                for _, r in df_top.iterrows(): st.markdown(f"""<div style="margin-bottom: 12px;"><div style="display: flex; justify-content: space-between; font-size: 11px; font-weight: 600; margin-bottom: 2px;"><span>{r['PLAYER_NAME']}</span><span>{int(r['SUCCESS'])} / {int(r['TOTAL'])} ({int(r['PCT'])}%)</span></div><div style="background-color: #f0f2f6; border-radius: 4px; height: 5px; width: 100%;"><div style="background-color: #ec7014; height: 5px; width: {r['PCT']}%; border-radius: 4px;"></div></div></div>""", unsafe_allow_html=True)

    with t4:
        if not df_all_events.empty:
            gl = df_all_events.drop_duplicates(['MATCH_OPTAUUID', 'GOAL_TIME']).sort_values('GOAL_TIME', ascending=False)
            opts = {f"{r['MATCH_OPTAUUID']}_{r['GOAL_TIME']}": {'label': f"{pd.to_datetime(r['MATCH_LOCALDATE']).strftime('%d/%m')} vs {r['CONTESTANTAWAY_NAME'] if r['CONTESTANTHOME_OPTAUUID']==valgt_uuid else r['CONTESTANTHOME_NAME']} ({int(r['GOAL_MIN'])}. min)", 'match_id': r['MATCH_OPTAUUID'], 'goal_ts': r['GOAL_TIME'], 'opp_uuid': r['CONTESTANTAWAY_OPTAUUID'] if r['CONTESTANTHOME_OPTAUUID']==valgt_uuid else r['CONTESTANTHOME_OPTAUUID'], 'min': int(r['GOAL_MIN']), 'date': pd.to_datetime(r['MATCH_LOCALDATE']).strftime('%d/%m/%Y')} for _, r in gl.iterrows()}
            sk = st.selectbox("Vælg mål (Hele sæsonen)", list(opts.keys()), format_func=lambda x: opts[x]['label'])
            sd = opts[sk]; tge = df_all_events[(df_all_events['MATCH_OPTAUUID'] == sd['match_id']) & (df_all_events['GOAL_TIME'] == sd['goal_ts'])].sort_values('EVENT_TIMESTAMP')
            p_c, l_c = st.columns([2.5, 1]); p = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='grey'); f, ax = p.draw(figsize=(10, 7))
            draw_match_info_box(ax, hold_logo, get_logo_img(sd['opp_uuid']), sd['date'], "Mål", sd['min'])
            for i in range(len(tge)-1): p.arrows(tge.iloc[i]['EVENT_X'], tge.iloc[i]['EVENT_Y'], tge.iloc[i+1]['EVENT_X'], tge.iloc[i+1]['EVENT_Y'], width=1, headwidth=3, color='black', alpha=0.15, ax=ax)
            for _, r in tge.iterrows():
                c, m, s = ('red', 's', 180) if r['EVENT_TYPEID'] == 16 else (('gold', 'P', 200) if r['EVENT_TYPEID'] == 5 else ('red', 'o', 80))
                ax.scatter(r['EVENT_X'], r['EVENT_Y'], color=c, s=s, marker=m, edgecolors='black', zorder=10); ax.text(r['EVENT_X'], r['EVENT_Y']+2.5, r['PLAYER_NAME'], fontsize=7, ha='center', fontweight='bold', bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
            p_c.pyplot(f); tge['Aktion'] = tge['EVENT_TYPEID'].astype(str).map(OPTA_EVENT_TYPES)
            l_c.write("**Sekvens:**"); l_c.dataframe(tge[['PLAYER_NAME', 'Aktion']].iloc[::-1], hide_index=True)
        else: st.info("Ingen mål fundet for dette hold i sæsonen.")

    with t5:
        if not df_all_h.empty:
            df_all_h['is_pass'], df_all_h['is_regain'], df_all_h['is_shot'] = (df_all_h['EVENT_TYPEID'] == 1).astype(int), df_all_h['EVENT_TYPEID'].isin([7, 8, 12, 49, 127]).astype(int), df_all_h['EVENT_TYPEID'].isin([13,14,15,16]).astype(int)
            stats = df_all_h.groupby('PLAYER_NAME').agg({'is_pass': 'sum', 'is_regain': 'sum', 'is_shot': 'sum', 'EVENT_TYPEID': 'count'}).rename(columns={'EVENT_TYPEID': 'Aktioner', 'is_pass': 'Pasninger', 'is_regain': 'Erobringer', 'is_shot': 'Skud'}).sort_values('Aktioner', ascending=False)
            st.dataframe(stats, use_container_width=True)

if __name__ == "__main__":
    vis_side()
