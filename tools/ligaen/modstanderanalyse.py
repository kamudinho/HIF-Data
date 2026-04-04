import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
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

def plot_pass_heatmap(df, direction="up"):
    # Filtrer pasninger (1) og fjern slettede (43)
    pass_df = df[(df['EVENT_TYPEID'] == 1) & (df['EVENT_TYPEID'] != 43)].copy()
    if pass_df.empty: return None
    
    # Vi bruger VerticalPitch for halvbaner
    pitch = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#BDBDBD')
    fig, ax = pitch.draw(figsize=(8, 10))
    
    if direction == "down":
        # Opbygning: Vi vender banen så de spiller "nedad" mod eget mål/fremad fra bunden
        ax.invert_yaxis()
        ax.invert_xaxis()
        cmap = 'Blues'
        # For 'down' viser vi typisk den defensive halvdel (0-50)
        plot_data = pass_df[pass_df['EVENT_X'] <= 50]
    else:
        # Gennembrud: Offensiv halvdel (50-100)
        cmap = 'Reds'
        plot_data = pass_df[pass_df['EVENT_X'] >= 50]
        
    if not plot_data.empty:
        # kdeplot er mere stabil til heatmaps end hexbin
        pitch.kdeplot(plot_data.EVENT_X, plot_data.EVENT_Y, ax=ax, 
                      cmap=cmap, fill=True, alpha=0.7, levels=100)
    return fig

# --- 3. HOVEDFUNKTION ---
def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn: return

    # 3.1 Hent holdliste
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'")
    ids = df_teams_raw['CONTESTANTHOME_OPTAUUID'].unique()
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    team_map = {mapping_lookup.get(str(u).lower().replace('t','')): u for u in ids if mapping_lookup.get(str(u).lower().replace('t',''))}

    col_spacer, col_hold = st.columns([3, 1])
    valgt_hold = col_hold.selectbox("Vælg hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]

    # DEFINITION AF FANER (STRENG OVERHOLDELSE AF DIN STRUKTUR)
    t1, t2, t3, t4, t5 = st.tabs(["OVERSIGT", "MED BOLDEN", "UDEN BOLDEN", "MÅL-SEKVENSER", "SPILLEROVERSIGT"])

    # --- T1: OVERSIGT ---
    with t1:
        st.subheader(f"Præstationer: {valgt_hold}")
        sql_res = f"""
            SELECT MATCH_LOCALDATE as DATO, CONTESTANTHOME_NAME as HJEMME, CONTESTANTAWAY_NAME as UDE, 
                   TOTAL_HOME_SCORE as "MÅL H", TOTAL_AWAY_SCORE as "MÅL U"
            FROM {DB}.OPTA_MATCHINFO 
            WHERE (CONTESTANTHOME_OPTAUUID = '{valgt_uuid}' OR CONTESTANTAWAY_OPTAUUID = '{valgt_uuid}')
            AND TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
            ORDER BY MATCH_LOCALDATE DESC LIMIT 5
        """
        st.dataframe(conn.query(sql_res), hide_index=True)

    # --- T2: MED BOLDEN ---
    with t2:
        st.subheader("Positionsanalyse (Pasninger)")
        sql_passes = f"SELECT EVENT_X, EVENT_Y, EVENT_TYPEID FROM {DB}.OPTA_EVENTS WHERE EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND EVENT_TYPEID = 1 AND EVENT_TYPEID != 43 AND TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"
        df_passes = conn.query(sql_passes)
        
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Opbygningsspil**")
            fig_d = plot_pass_heatmap(df_passes, direction="down")
            if fig_d: st.pyplot(fig_d)
        with c2:
            st.write("**Gennembrudsspil**")
            fig_u = plot_pass_heatmap(df_passes, direction="up")
            if fig_u: st.pyplot(fig_u)

    # --- T3: UDEN BOLDEN ---
    with t3:
        st.subheader("Defensiv aktionsradius")
        sql_def = f"SELECT EVENT_X, EVENT_Y, EVENT_TYPEID FROM {DB}.OPTA_EVENTS WHERE EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND EVENT_TYPEID IN (7, 8, 12) AND EVENT_TYPEID != 43 AND TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"
        df_def = conn.query(sql_def)
        if not df_def.empty:
            pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='grey')
            fig, ax = pitch.draw()
            pitch.kdeplot(df_def.EVENT_X, df_def.EVENT_Y, ax=ax, cmap='Greens', fill=True, alpha=0.5, levels=10)
            st.pyplot(fig)

    # --- T4: MÅL-SEKVENSER ---
    with t4:
        sql_goals_base = f"""
            SELECT e.MATCH_OPTAUUID, e.EVENT_TIMESTAMP as GOAL_TIME, e.EVENT_TIMEMIN as GOAL_MIN, 
                   m.CONTESTANTHOME_NAME, m.CONTESTANTAWAY_NAME, m.MATCH_LOCALDATE,
                   m.CONTESTANTHOME_OPTAUUID, m.CONTESTANTAWAY_OPTAUUID
            FROM {DB}.OPTA_EVENTS e
            JOIN {DB}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
            WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND e.EVENT_TYPEID = 16 
            AND e.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
            QUALIFY ROW_NUMBER() OVER (PARTITION BY e.MATCH_OPTAUUID, e.EVENT_TIMESTAMP ORDER BY e.EVENT_EVENTID) = 1
        """
        sql_seq = f"""
            WITH G AS ({sql_goals_base})
            SELECT e.*, g.GOAL_TIME, g.GOAL_MIN, g.CONTESTANTHOME_NAME, g.CONTESTANTAWAY_NAME, g.MATCH_LOCALDATE
            FROM {DB}.OPTA_EVENTS e
            INNER JOIN G g ON e.MATCH_OPTAUUID = g.MATCH_OPTAUUID
            WHERE e.EVENT_TIMESTAMP >= DATEADD(second, -12, g.GOAL_TIME) AND e.EVENT_TIMESTAMP <= g.GOAL_TIME
            AND e.EVENT_TYPEID != 43
            QUALIFY ROW_NUMBER() OVER (PARTITION BY e.EVENT_OPTAUUID, g.GOAL_TIME ORDER BY e.EVENT_TIMESTAMP DESC) = 1
        """
        df_all_seq = conn.query(sql_seq)

        if not df_all_seq.empty:
            goal_list = df_all_seq.drop_duplicates(['MATCH_OPTAUUID', 'GOAL_TIME']).sort_values('GOAL_TIME', ascending=False)
            goal_labels = {f"{r.MATCH_OPTAUUID}_{r.GOAL_TIME}": f"{pd.to_datetime(r.MATCH_LOCALDATE).strftime('%d/%m')} vs {r.CONTESTANTAWAY_NAME if r.CONTESTANTHOME_NAME==valgt_hold else r.CONTESTANTHOME_NAME} ({r.GOAL_MIN}')" for r in goal_list.itertuples()}
            sel_goal_key = st.selectbox("Vælg mål", list(goal_labels.keys()), format_func=lambda x: goal_labels[x])
            
            m_id, g_ts = sel_goal_key.split('_', 1)
            this_goal = df_all_seq[(df_all_seq.MATCH_OPTAUUID == m_id) & (df_all_seq.GOAL_TIME == g_ts)].sort_values('EVENT_TIMESTAMP')
            
            cp, cl = st.columns([2, 1])
            with cp:
                p = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='grey')
                fig, ax = p.draw()
                for i in range(len(this_goal)-1):
                    p.arrows(this_goal.iloc[i].EVENT_X, this_goal.iloc[i].EVENT_Y, this_goal.iloc[i+1].EVENT_X, this_goal.iloc[i+1].EVENT_Y, color='black', alpha=0.3, ax=ax, width=1)
                p.scatter(this_goal.EVENT_X, this_goal.EVENT_Y, s=120, color='red', edgecolors='black', ax=ax, zorder=10)
                st.pyplot(fig)
            with cl:
                this_goal['Aktion'] = this_goal['EVENT_TYPEID'].astype(str).map(OPTA_EVENT_TYPES)
                st.dataframe(this_goal[['PLAYER_NAME', 'Aktion']].iloc[::-1], hide_index=True)

    # --- T5: SPILLEROVERSIGT ---
    with t5:
        if not df_all_seq.empty:
            st.write("**Mål-involveringer (Sidste 12 sekunder af alle målsekvenser):**")
            stats = df_all_seq.groupby('PLAYER_NAME').size().reset_index(name='Involveringer').sort_values('Involveringer', ascending=False)
            st.dataframe(stats, hide_index=True)

if __name__ == "__main__":
    vis_side()
