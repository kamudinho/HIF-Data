import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch, VerticalPitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS, TEAM_COLORS
import requests
from PIL import Image
from io import BytesIO

# --- 1. KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o"

# --- 2. HJÆLPEFUNKTIONER ---
@st.cache_data(ttl=3600)
def get_logo_img(opta_uuid):
    # Rens UUID for sammenligning
    clean_uuid = str(opta_uuid).strip().upper()
    url = next((info['logo'] for name, info in TEAMS.items() if str(info.get('opta_uuid')).strip().upper() == clean_uuid), None)
    if not url: return None
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except: return None

def plot_custom_pitch(df, event_ids, title, zone='full', cmap='Reds', logo=None):
    plot_data = df[df['EVENT_TYPEID'].isin(event_ids)].copy()
    pitch = VerticalPitch(pitch_type='opta', half=False, pitch_color='#ffffff', line_color='#BDBDBD')
    fig, ax = pitch.draw(figsize=(5, 7))
    
    # Juster visning baseret på zone
    if zone == 'up': ax.set_ylim(0, 55); logo_pos = [0.04, 0.03, 0.08, 0.08]; text_y = 0.05
    elif zone == 'down': ax.set_ylim(45, 100); logo_pos = [0.04, 0.90, 0.08, 0.08]; text_y = 0.97
    else: logo_pos = [0.04, 0.90, 0.08, 0.08]; text_y = 0.97

    if logo:
        ax_logo = ax.inset_axes(logo_pos, transform=ax.transAxes)
        ax_logo.imshow(logo)
        ax_logo.axis('off')

    ax.text(0.94, text_y, title, transform=ax.transAxes, fontsize=5.5, fontweight='bold', ha='right', va='top', color='#333333')
    if not plot_data.empty:
        pitch.kdeplot(plot_data.EVENT_X, plot_data.EVENT_Y, ax=ax, cmap=cmap, fill=True, alpha=0.5, levels=100)
    return fig

# --- 3. HOVEDFUNKTION ---
def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn: return

    # Team mapping (brug logik fra test_matches)
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == "1. Division"}
    h_list = sorted(liga_hold_options.keys())
    
    col_spacer, col_hold = st.columns([3, 1])
    valgt_hold = col_hold.selectbox("Vælg hold", h_list, label_visibility="collapsed")
    valgt_uuid = str(liga_hold_options[valgt_hold]).strip().upper()
    hold_logo = get_logo_img(valgt_uuid)

    # --- AVANCERET SQL (Inspireret af test_matches.py) ---
    sql_matches = f"""
        WITH MatchBase AS (
            SELECT MATCH_OPTAUUID, MATCH_DATE_FULL, CONTESTANTHOME_NAME, CONTESTANTAWAY_NAME,
                   TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE, CONTESTANTHOME_OPTAUUID, CONTESTANTAWAY_OPTAUUID, MATCH_STATUS
            FROM {DB}.OPTA_MATCHINFO
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
            AND (CONTESTANTHOME_OPTAUUID = '{valgt_uuid}' OR CONTESTANTAWAY_OPTAUUID = '{valgt_uuid}')
        ),
        Stats AS (
            SELECT MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
                   SUM(CASE WHEN STAT_TYPE = 'totalPass' THEN STAT_TOTAL ELSE 0 END) AS PASSES,
                   SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_TOTAL ELSE 0 END) AS SHOTS
            FROM {DB}.OPTA_MATCHSTATS GROUP BY 1, 2
        )
        SELECT b.*, s.PASSES, s.SHOTS
        FROM MatchBase b
        LEFT JOIN Stats s ON b.MATCH_OPTAUUID = s.MATCH_OPTAUUID AND s.CONTESTANT_OPTAUUID = '{valgt_uuid}'
        WHERE b.MATCH_STATUS ILIKE '%Full%' OR b.MATCH_STATUS ILIKE '%Played%'
        ORDER BY b.MATCH_DATE_FULL DESC LIMIT 10
    """

    with st.spinner("Henter analyse..."):
        df_res = conn.query(sql_matches)
        if df_res.empty:
            st.warning("Ingen data fundet for dette hold.")
            return

        # Rens data
        df_res['MATCH_OPTAUUID'] = df_res['MATCH_OPTAUUID'].astype(str).str.strip()
        match_ids = tuple(df_res['MATCH_OPTAUUID'].tolist())
        match_ids_str = f"('{match_ids[0]}')" if len(match_ids) == 1 else str(match_ids)

        # Hent hændelser til pitches (T2/T3)
        df_all_h = conn.query(f"SELECT EVENT_X, EVENT_Y, EVENT_TYPEID, PLAYER_NAME, MATCH_OPTAUUID FROM {DB}.OPTA_EVENTS WHERE EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND MATCH_OPTAUUID IN {match_ids_str}")

    t1, t2, t3, t4, t5 = st.tabs(["OVERSIGT", "MED BOLDEN", "UDEN BOLDEN", "MÅL-SEKVENSER", "SPILLEROVERSIGT"])

    # --- T1: OVERSIGT ---
    with t1:
        # Beregn resultater (W/D/L)
        def get_res(r):
            is_h = str(r['CONTESTANTHOME_OPTAUUID']).strip().upper() == valgt_uuid
            h_s, a_s = r['TOTAL_HOME_SCORE'], r['TOTAL_AWAY_SCORE']
            if h_s == a_s: return "D"
            return "W" if (is_h and h_s > a_s) or (not is_h and a_s > h_s) else "L"

        df_res['RES'] = df_res.apply(get_res, axis=1)
        
        # KPI Række
        k1, k2, k3, k4 = st.columns(4)
        last_5 = df_res.head(5)
        pts = (last_5['RES']=="W").sum()*3 + (last_5['RES']=="D").sum()
        k1.metric("Point (Sidste 5)", f"{pts}/15")
        k2.metric("Vundne (Sidste 10)", (df_res['RES']=="W").sum())
        
        mål_s = sum([r['TOTAL_HOME_SCORE'] if str(r['CONTESTANTHOME_OPTAUUID']).strip().upper() == valgt_uuid else r['TOTAL_AWAY_SCORE'] for _, r in df_res.iterrows()])
        mål_i = sum([r['TOTAL_AWAY_SCORE'] if str(r['CONTESTANTHOME_OPTAUUID']).strip().upper() == valgt_uuid else r['TOTAL_HOME_SCORE'] for _, r in df_res.iterrows()])
        k3.metric("Mål Scoret (10 k)", int(mål_s))
        k4.metric("Mål Imod (10 k)", int(mål_i))

        # Tabel over kampe
        st.dataframe(df_res[['MATCH_DATE_FULL', 'CONTESTANTHOME_NAME', 'TOTAL_HOME_SCORE', 'TOTAL_AWAY_SCORE', 'CONTESTANTAWAY_NAME', 'RES']], hide_index=True, use_container_width=True)
        
        # Grafer (Baseret på SQL Stats)
        df_plot = df_res.copy().iloc[::-1]
        df_plot['MODSTANDER'] = df_plot.apply(lambda r: r['CONTESTANTAWAY_NAME'] if str(r['CONTESTANTHOME_OPTAUUID']).strip().upper() == valgt_uuid else r['CONTESTANTHOME_NAME'], axis=1)

        g1, g2 = st.columns(2)
        with g1:
            st.write("**Pasninger pr. kamp**")
            st.bar_chart(df_plot, x='MODSTANDER', y='PASSES', color='#0047AB')
        with g2:
            st.write("**Afslutninger pr. kamp**")
            st.bar_chart(df_plot, x='MODSTANDER', y='SHOTS', color='#C8102E')

    # --- T2 & T3: Pitch-analyser (Brug df_all_h) ---
    with t2:
        cp, cs = st.columns([2, 1])
        with cs:
            v = st.selectbox("Fokus", ["Opbygning", "Gennembrud", "Afslutninger"])
            ids, tit, cm, zn = ([1], "OPBYGNING", "Blues", "up") if v=="Opbygning" else (([1], "GENNEMBRUD", "Reds", "down") if v=="Gennembrud" else ([13,14,15,16], "AFSLUTNINGER", "YlOrRd", "down"))
            
            df_top = df_all_h[df_all_h['EVENT_TYPEID'].isin(ids)].groupby('PLAYER_NAME').size().reset_index(name='N').sort_values('N', ascending=False).head(5)
            st.write(f"**Top 5: {v}**")
            for _, r in df_top.iterrows(): st.write(f"{int(r['N'])} **{r['PLAYER_NAME']}**")
        with cp: st.pyplot(plot_custom_pitch(df_all_h, ids, tit, zone=zn, cmap=cm, logo=hold_logo))

    with t3:
        cp, cs = st.columns([2, 1])
        with cs:
            v_uden = st.selectbox("Fokus", ["Dueller", "Erobringer"], key="uden_bold")
            ids, tit, cm = ([7, 8], "DUELLER", "Blues") if v_uden=="Dueller" else ([12, 127, 49], "EROBRINGER", "GnBu")
            df_top_u = df_all_h[df_all_h['EVENT_TYPEID'].isin(ids)].groupby('PLAYER_NAME').size().reset_index(name='N').sort_values('N', ascending=False).head(5)
            st.write(f"**Top 5: {v_uden}**")
            for _, r in df_top_u.iterrows(): st.write(f"{int(r['N'])} **{r['PLAYER_NAME']}**")
        with cp: st.pyplot(plot_custom_pitch(df_all_h, ids, tit, zone='up', cmap=cm, logo=hold_logo))

    # T4 og T5 forbliver som før, da de kræver specifikke sekvens-queries
    with t4: st.info("Vælg 'OVERSIGT' for at se seneste form.")
    with t5: st.write("**Spillerstatistik (Sidste 10 kampe)**"); st.dataframe(df_all_h.groupby('PLAYER_NAME').size().reset_index(name='Aktioner').sort_values('Aktioner', ascending=False), hide_index=True)

if __name__ == "__main__":
    vis_side()
