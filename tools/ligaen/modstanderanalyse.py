import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch, VerticalPitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS
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
    url = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), None)
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
    plot_data = df[df['EVENT_TYPEID'].isin(event_ids)].copy()
    pitch = VerticalPitch(pitch_type='opta', half=False, pitch_color='#ffffff', line_color='#BDBDBD')
    fig, ax = pitch.draw(figsize=(5, 7))
    
    if zone == 'up':
        ax.set_ylim(0, 55)
        logo_pos = [0.04, 0.03, 0.08, 0.08]
        text_y = 0.05
    elif zone == 'down':
        ax.set_ylim(45, 100)
        logo_pos = [0.04, 0.90, 0.08, 0.08]
        text_y = 0.97
    else:
        logo_pos = [0.04, 0.90, 0.08, 0.08]
        text_y = 0.97

    if logo:
        ax_logo = ax.inset_axes(logo_pos, transform=ax.transAxes)
        ax_logo.imshow(logo)
        ax_logo.axis('off')

    ax.text(0.94, text_y, title, transform=ax.transAxes, fontsize=5.5, 
            fontweight='bold', ha='right', va='top', color='#333333')

    if not plot_data.empty:
        pitch.kdeplot(plot_data.EVENT_X, plot_data.EVENT_Y, ax=ax, cmap=cmap, fill=True, alpha=0.5, levels=100)
    
    return fig

# --- 3. HOVEDFUNKTION (UNDERSIDE) ---
def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn: return

    # Team selection logic
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'")
    ids = df_teams_raw['CONTESTANTHOME_OPTAUUID'].unique()
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    team_map = {mapping_lookup.get(str(u).lower().replace('t','')): u for u in ids if mapping_lookup.get(str(u).lower().replace('t',''))}

    col_spacer, col_hold = st.columns([3, 1])
    valgt_hold = col_hold.selectbox("Vælg hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid)

    # --- GLOBAL DATA HENTNING (Sikrer 10 kampe) ---
    with st.spinner(f"Henter data for de seneste 10 kampe for {valgt_hold}..."):
        # 1. Oversigt over de seneste 10 kampe
        sql_res = f"""
            SELECT MATCH_LOCALDATE, CONTESTANTHOME_NAME, CONTESTANTAWAY_NAME, 
                   TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE, CONTESTANTHOME_OPTAUUID, 
                   CONTESTANTAWAY_OPTAUUID, MATCH_OPTAUUID 
            FROM {DB}.OPTA_MATCHINFO 
            WHERE (CONTESTANTHOME_OPTAUUID = '{valgt_uuid}' OR CONTESTANTAWAY_OPTAUUID = '{valgt_uuid}') 
            AND TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}' 
            ORDER BY MATCH_LOCALDATE DESC LIMIT 10
        """
        df_res = conn.query(sql_res)
        
        if df_res.empty:
            st.warning("Ingen data fundet.")
            return

        # Lav en tuple af de 10 MATCH_UUIDs til filtrering af alle andre kald
        match_ids_list = df_res['MATCH_OPTAUUID'].tolist()
        m_ids_str = f"('{match_ids_list[0]}')" if len(match_ids_list) == 1 else str(tuple(match_ids_list))

        # 2. Hent hændelser (Heatmaps + Volumen) for alle 10 kampe i ét hug
        df_all_h = conn.query(f"SELECT EVENT_X, EVENT_Y, EVENT_TYPEID, MATCH_OPTAUUID FROM {DB}.OPTA_EVENTS WHERE EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND MATCH_OPTAUUID IN {m_ids_str}")
        
        # 3. Mål-sekvenser (T4)
        sql_goals = f"SELECT e.MATCH_OPTAUUID, e.EVENT_TIMESTAMP as GOAL_TIME, e.EVENT_TIMEMIN as GOAL_MIN, m.CONTESTANTHOME_NAME, m.CONTESTANTAWAY_NAME, m.CONTESTANTHOME_OPTAUUID, m.MATCH_LOCALDATE FROM {DB}.OPTA_EVENTS e JOIN {DB}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID WHERE e.MATCH_OPTAUUID IN {m_ids_str} AND e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND e.EVENT_TYPEID = 16 QUALIFY ROW_NUMBER() OVER (PARTITION BY e.MATCH_OPTAUUID, e.EVENT_TIMESTAMP ORDER BY e.EVENT_EVENTID) = 1"
        df_goals = conn.query(sql_goals)
        
        df_all_events = pd.DataFrame()
        if not df_goals.empty:
            sql_events = f"WITH Goals AS ({sql_goals}) SELECT e.*, g.GOAL_TIME, g.GOAL_MIN, g.CONTESTANTHOME_NAME, g.CONTESTANTAWAY_NAME, g.MATCH_LOCALDATE FROM {DB}.OPTA_EVENTS e INNER JOIN Goals g ON e.MATCH_OPTAUUID = g.MATCH_OPTAUUID WHERE e.EVENT_TIMESTAMP >= DATEADD(second, -12, g.GOAL_TIME) AND e.EVENT_TIMESTAMP <= g.GOAL_TIME AND e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}'"
            df_all_events = conn.query(sql_events)

    t1, t2, t3, t4, t5 = st.tabs(["OVERSIGT", "MED BOLDEN", "UDEN BOLDEN", "MÅL-SEKVENSER", "SPILLEROVERSIGT"])

    # --- T1: OVERSIGT ---
    with t1:
        # KPI række
        df_res['TOTAL_HOME_SCORE'] = df_res['TOTAL_HOME_SCORE'].fillna(0).astype(int)
        df_res['TOTAL_AWAY_SCORE'] = df_res['TOTAL_AWAY_SCORE'].fillna(0).astype(int)
        
        def get_res_char(r):
            is_h = r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
            h, a = r['TOTAL_HOME_SCORE'], r['TOTAL_AWAY_SCORE']
            if h == a: return "D"
            return "W" if (is_h and h > a) or (not is_h and a > h) else "L"
        
        df_res['RES'] = df_res.apply(get_res_char, axis=1)
        
        k1, k2, k3, k4 = st.columns(4)
        l5 = df_res.head(5)
        k1.metric("Point (Sidste 5)", f"{(l5['RES'] == 'W').sum()*3 + (l5['RES'] == 'D').sum()}/15")
        k2.metric("Sejre (10 kampe)", (df_res['RES'] == 'W').sum())
        
        m_s = sum([r['TOTAL_HOME_SCORE'] if r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else r['TOTAL_AWAY_SCORE'] for _, r in df_res.iterrows()])
        m_i = sum([r['TOTAL_AWAY_SCORE'] if r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else r['TOTAL_HOME_SCORE'] for _, r in df_res.iterrows()])
        k3.metric("Mål Scoret (10 k)", m_s)
        k4.metric("Mål Imod (10 k)", m_i, delta=int(m_i), delta_color="inverse")

        # Tabel og Grafer i én container for at samle overblikket
        with st.container():
            st.dataframe(df_res[['MATCH_LOCALDATE', 'CONTESTANTHOME_NAME', 'TOTAL_HOME_SCORE', 'TOTAL_AWAY_SCORE', 'CONTESTANTAWAY_NAME', 'RES']], hide_index=True, use_container_width=True)
            
            # Beregn volumen pr. kamp fra df_all_h
            df_vol = df_all_h.groupby('MATCH_OPTAUUID').agg(
                PASNINGER=('EVENT_TYPEID', lambda x: (x == 1).sum()),
                AFSLUTNINGER=('EVENT_TYPEID', lambda x: x.isin([13,14,15,16]).sum())
            ).reset_index()
            
            df_plot = df_res.merge(df_vol, on='MATCH_OPTAUUID', how='left').fillna(0).iloc[::-1]
            df_plot['MODSTANDER'] = df_plot.apply(lambda r: r['CONTESTANTAWAY_NAME'] if r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else r['CONTESTANTHOME_NAME'], axis=1)

            g_col1, g_col2 = st.columns(2)
            with g_col1:
                st.write("**Pasninger pr. kamp**")
                st.bar_chart(df_plot, x='MODSTANDER', y='PASNINGER', color='#0047AB')
            with g_col2:
                st.write("**Afslutninger pr. kamp**")
                st.bar_chart(df_plot, x='MODSTANDER', y='AFSLUTNINGER', color='#C8102E')

    # --- T2 & T3 (Kortet ned for overblik) ---
    with t2:
        cp, cs = st.columns([2, 1])
        with cs:
            v_med = st.selectbox("Fokus", ["Opbygning", "Gennembrud", "Afslutninger"], key="ms")
            if v_med == "Opbygning": ids, tit, cm, zn = [1], "OPBYGNING", "Blues", "up"
            elif v_med == "Gennembrud": ids, tit, cm, zn = [1], "GENNEMBRUD", "Reds", "down"
            else: ids, tit, cm, zn = [13,14,15,16], "AFSLUTNINGER", "YlOrRd", "down"
        with cp: st.pyplot(plot_custom_pitch(df_all_h, ids, tit, zone=zn, cmap=cm, logo=hold_logo))

    with t3:
        cp, cs = st.columns([2, 1])
        with cs:
            v_uden = st.selectbox("Fokus", ["Dueller", "Erobringer", "Defensiv Zone"], key="us")
            if v_uden == "Dueller": ids, tit, cm, zn = [7, 8], "DUELLER", "Blues", "up"
            elif v_uden == "Erobringer": ids, tit, cm, zn = [127, 12, 49], "EROBRINGER", "GnBu", "up"
            else: ids, tit, cm, zn = [7, 12, 127], "DEFENSIV ZONE", "PuBu", "up"
        with cp: st.pyplot(plot_custom_pitch(df_all_h, ids, tit, zone=zn, cmap=cm, logo=hold_logo))

    # --- T4: MÅL-SEKVENSER ---
    with t4:
        if not df_all_events.empty:
            gl = df_all_events.drop_duplicates(['MATCH_OPTAUUID', 'GOAL_TIME']).sort_values('GOAL_TIME', ascending=False)
            opts = {f"{r['MATCH_OPTAUUID']}_{r['GOAL_TIME']}": f"{pd.to_datetime(r['MATCH_LOCALDATE']).strftime('%d/%m')} vs {r['CONTESTANTAWAY_NAME'] if r['CONTESTANTHOME_NAME']==valgt_hold else r['CONTESTANTHOME_NAME']} ({r['GOAL_MIN']}.min)" for _, r in gl.iterrows()}
            sk = st.selectbox("Vælg mål", list(opts.keys()), format_func=lambda x: opts[x])
            m_id, g_ts = sk.split('_')[0], sk.split('_')[1]
            tge = df_all_events[(df_all_events['MATCH_OPTAUUID'] == m_id) & (df_all_events['GOAL_TIME'] == g_ts)].sort_values('EVENT_TIMESTAMP')
            st.pyplot(plot_custom_pitch(tge, [1,16,13,14,15], "MÅL-SEKVENS", logo=hold_logo))

    # --- T5: SPILLEROVERSIGT ---
    with t5:
        if not df_all_h.empty:
            stats = df_all_h.groupby('PLAYER_NAME').agg(
                Aktioner=('EVENT_TYPEID', 'count'),
                Pasninger=('EVENT_TYPEID', lambda x: (x == 1).sum()),
                Afslutninger=('EVENT_TYPEID', lambda x: x.isin([13,14,15,16]).sum())
            ).sort_values('Aktioner', ascending=False)
            st.write(f"**Statistik for de seneste 10 kampe**")
            st.dataframe(stats, use_container_width=True)

if __name__ == "__main__":
    vis_side()
