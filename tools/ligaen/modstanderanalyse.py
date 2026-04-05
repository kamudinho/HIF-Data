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
    
    if zone == 'up': 
        ax.set_ylim(0, 55)
        logo_pos = [0.04, 0.03, 0.08, 0.08]
    elif zone == 'down': 
        ax.set_ylim(45, 100)
        logo_pos = [0.04, 0.90, 0.08, 0.08]
    else: 
        logo_pos = [0.04, 0.90, 0.08, 0.08]

    if logo:
        ax_logo = ax.inset_axes(logo_pos, transform=ax.transAxes)
        ax_logo.imshow(logo)
        ax_logo.axis('off')

    ax.text(0.94, 0.97 if zone != 'up' else 0.05, title, transform=ax.transAxes, 
            fontsize=5.5, fontweight='bold', ha='right', va='top', color='#333333')
    
    if not plot_data.empty:
        pitch.kdeplot(plot_data.EVENT_X, plot_data.EVENT_Y, ax=ax, cmap=cmap, fill=True, alpha=0.5, levels=100)
    return fig

# --- 3. HOVEDFUNKTION ---
def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn: return

    # Team mapping fra din test_matches.py logik
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == "1. Division"}
    h_list = sorted(liga_hold_options.keys())
    
    col_spacer, col_hold = st.columns([3, 1])
    valgt_hold = col_hold.selectbox("Vælg hold", h_list, label_visibility="collapsed")
    valgt_uuid = str(liga_hold_options[valgt_hold]).strip().upper()
    hold_logo = get_logo_img(valgt_uuid)

    # SQL baseret 100% på din test_matches.py struktur
    sql = f"""
        WITH MatchBase AS (
            SELECT 
                MATCH_OPTAUUID, MATCH_DATE_FULL, MATCH_STATUS,
                CONTESTANTHOME_OPTAUUID, CONTESTANTHOME_NAME,
                CONTESTANTAWAY_OPTAUUID, CONTESTANTAWAY_NAME,
                TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE
            FROM {DB}.OPTA_MATCHINFO
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        ),
        StatsPivot AS (
            SELECT 
                MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
                SUM(CASE WHEN STAT_TYPE = 'totalPass' THEN STAT_TOTAL ELSE 0 END) AS PASSES,
                SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_TOTAL ELSE 0 END) AS SHOTS
            FROM {DB}.OPTA_MATCHSTATS
            GROUP BY 1, 2
        )
        SELECT 
            b.*,
            h.PASSES AS HOME_PASSES, h.SHOTS AS HOME_SHOTS,
            a.PASSES AS AWAY_PASSES, a.SHOTS AS AWAY_SHOTS
        FROM MatchBase b
        LEFT JOIN StatsPivot h ON b.MATCH_OPTAUUID = h.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = h.CONTESTANT_OPTAUUID
        LEFT JOIN StatsPivot a ON b.MATCH_OPTAUUID = a.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = a.CONTESTANT_OPTAUUID
        WHERE (b.CONTESTANTHOME_OPTAUUID = '{valgt_uuid}' OR b.CONTESTANTAWAY_OPTAUUID = '{valgt_uuid}')
        AND (b.MATCH_STATUS ILIKE '%Full%' OR b.MATCH_STATUS ILIKE '%Played%' OR b.MATCH_STATUS ILIKE '%Finish%')
        ORDER BY b.MATCH_DATE_FULL DESC
        LIMIT 10
    """

    with st.spinner(f"Analyserer {valgt_hold}..."):
        df_res = conn.query(sql)
        
        if df_res is None or df_res.empty:
            st.warning(f"Ingen spillede kampe fundet for {valgt_hold} i databasen.")
            return

        # Sørg for kolonnenavne er konsistente
        df_res.columns = [c.upper() for c in df_res.columns]
        df_res['MATCH_OPTAUUID'] = df_res['MATCH_OPTAUUID'].astype(str).str.strip()
        
        match_ids = tuple(df_res['MATCH_OPTAUUID'].tolist())
        match_ids_str = f"('{match_ids[0]}')" if len(match_ids) == 1 else str(match_ids)

        # Hent hændelser til pitches
        df_all_h = conn.query(f"""
            SELECT EVENT_X, EVENT_Y, EVENT_TYPEID, PLAYER_NAME, MATCH_OPTAUUID 
            FROM {DB}.OPTA_EVENTS 
            WHERE EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' 
            AND MATCH_OPTAUUID IN {match_ids_str}
        """)

    t1, t2, t3, t4, t5 = st.tabs(["OVERSIGT", "MED BOLDEN", "UDEN BOLDEN", "MÅL-SEKVENSER", "SPILLEROVERSIGT"])

    with t1:
        # Resultat logik
        def get_res(r):
            is_h = str(r['CONTESTANTHOME_OPTAUUID']).strip().upper() == valgt_uuid
            h_s, a_s = int(r['TOTAL_HOME_SCORE'] or 0), int(r['TOTAL_AWAY_SCORE'] or 0)
            if h_s == a_s: return "D"
            return "W" if (is_h and h_s > a_s) or (not is_h and a_s > h_s) else "L"

        df_res['RES'] = df_res.apply(get_res, axis=1)
        
        k1, k2, k3, k4 = st.columns(4)
        last_5 = df_res.head(5)
        pts = (last_5['RES']=="W").sum()*3 + (last_5['RES']=="D").sum()
        k1.metric("Point (Sidste 5)", f"{pts}/15")
        k2.metric("Vundne (Sidste 10)", (df_res['RES']=="W").sum())
        
        # Mål beregning
        m_s = sum([r['TOTAL_HOME_SCORE'] if str(r['CONTESTANTHOME_OPTAUUID']).strip().upper() == valgt_uuid else r['TOTAL_AWAY_SCORE'] for _, r in df_res.iterrows()])
        m_i = sum([r['TOTAL_AWAY_SCORE'] if str(r['CONTESTANTHOME_OPTAUUID']).strip().upper() == valgt_uuid else r['TOTAL_HOME_SCORE'] for _, r in df_res.iterrows()])
        k3.metric("Mål Scoret (10 k)", int(m_s))
        k4.metric("Mål Imod (10 k)", int(m_i))

        st.dataframe(df_res[['MATCH_DATE_FULL', 'CONTESTANTHOME_NAME', 'TOTAL_HOME_SCORE', 'TOTAL_AWAY_SCORE', 'CONTESTANTAWAY_NAME', 'RES']], hide_index=True, use_container_width=True)
        
        # Grafer med data fra StatsPivot
        df_plot = df_res.copy().iloc[::-1]
        df_plot['MODSTANDER'] = df_plot.apply(lambda r: r['CONTESTANTAWAY_NAME'] if str(r['CONTESTANTHOME_OPTAUUID']).strip().upper() == valgt_uuid else r['CONTESTANTHOME_NAME'], axis=1)
        df_plot['TEAM_PASSES'] = df_plot.apply(lambda r: r['HOME_PASSES'] if str(r['CONTESTANTHOME_OPTAUUID']).strip().upper() == valgt_uuid else r['AWAY_PASSES'], axis=1)
        df_plot['TEAM_SHOTS'] = df_plot.apply(lambda r: r['HOME_SHOTS'] if str(r['CONTESTANTHOME_OPTAUUID']).strip().upper() == valgt_uuid else r['AWAY_SHOTS'], axis=1)

        g1, g2 = st.columns(2)
        with g1:
            st.write("**Pasninger pr. kamp**")
            st.bar_chart(df_plot, x='MODSTANDER', y='TEAM_PASSES', color='#0047AB')
        with g2:
            st.write("**Afslutninger pr. kamp**")
            st.bar_chart(df_plot, x='MODSTANDER', y='TEAM_SHOTS', color='#C8102E')

    # De øvrige tabs (T2-T5) følger samme mønster som tidligere
    with t2:
        cp, cs = st.columns([2, 1])
        with cs:
            v = st.selectbox("Fokus", ["Opbygning", "Gennembrud", "Afslutninger"])
            ids, tit, cm, zn = ([1], "OPBYGNING", "Blues", "up") if v=="Opbygning" else (([1], "GENNEMBRUD", "Reds", "down") if v=="Gennembrud" else ([13,14,15,16], "AFSLUTNINGER", "YlOrRd", "down"))
            if not df_all_h.empty:
                df_top = df_all_h[df_all_h['EVENT_TYPEID'].isin(ids)].groupby('PLAYER_NAME').size().reset_index(name='N').sort_values('N', ascending=False).head(5)
                for _, r in df_top.iterrows(): st.write(f"{int(r['N'])} **{r['PLAYER_NAME']}**")
        with cp: st.pyplot(plot_custom_pitch(df_all_h, ids, tit, zone=zn, cmap=cm, logo=hold_logo))

    with t3:
        cp, cs = st.columns([2, 1])
        with cs:
            v_uden = st.selectbox("Fokus", ["Dueller", "Erobringer"], key="uden_bold")
            ids, tit, cm = ([7, 8], "DUELLER", "Blues") if v_uden=="Dueller" else ([12, 127, 49], "EROBRINGER", "GnBu")
            if not df_all_h.empty:
                df_top_u = df_all_h[df_all_h['EVENT_TYPEID'].isin(ids)].groupby('PLAYER_NAME').size().reset_index(name='N').sort_values('N', ascending=False).head(5)
                for _, r in df_top_u.iterrows(): st.write(f"{int(r['N'])} **{r['PLAYER_NAME']}**")
        with cp: st.pyplot(plot_custom_pitch(df_all_h, ids, tit, zone='up', cmap=cm, logo=hold_logo))

if __name__ == "__main__":
    vis_side()
