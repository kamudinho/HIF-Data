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
# NordicBet Liga bruger forskellige UUIDs for grundspil, oprykning og nedrykning
LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7')" 

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

def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn: return

    # Initialisér variabler
    df_all_events = None 

    # --- 1. TEAM SELECTION ---
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
    ids = df_teams_raw['CONTESTANTHOME_OPTAUUID'].unique()
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    team_map = {mapping_lookup.get(str(u).lower().replace('t','')): u for u in ids if mapping_lookup.get(str(u).lower().replace('t',''))}

    col_spacer, col_hold = st.columns([3, 1])
    valgt_hold = col_hold.selectbox("Vælg hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid)

    # --- 2. DATA HENTNING ---
    with st.spinner(f"Henter data for {valgt_hold}..."):
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
        
        if df_res is None or df_res.empty:
            st.warning("Ingen spillede kampe fundet.")
            return

        match_ids = tuple(df_res['MATCH_OPTAUUID'].tolist())
        match_ids_str = f"('{match_ids[0]}')" if len(match_ids) == 1 else str(match_ids)

        # RETTET: Kolonnen hedder EVENT_OUTCOME i jeres OPTA_EVENTS tabel
        df_all_h = conn.query(f"""
            SELECT EVENT_X, EVENT_Y, EVENT_TYPEID, PLAYER_NAME, MATCH_OPTAUUID, EVENT_TIMESTAMP, EVENT_OUTCOME 
            FROM {DB}.OPTA_EVENTS 
            WHERE EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' 
            AND MATCH_OPTAUUID IN {match_ids_str}
        """)
        
        # Omdøb kolonnen internt i DataFrame for at matche din logik
        if df_all_h is not None and not df_all_h.empty:
            df_all_h = df_all_h.rename(columns={'EVENT_OUTCOME': 'OUTCOME'})

        try:
            sql_goals = f"SELECT e.MATCH_OPTAUUID, e.EVENT_TIMESTAMP as GOAL_TIME, e.EVENT_CONTESTANT_OPTAUUID as SCORING_TEAM, e.EVENT_TIMEMIN as GOAL_MIN, m.CONTESTANTHOME_NAME, m.CONTESTANTAWAY_NAME, m.CONTESTANTHOME_OPTAUUID, m.CONTESTANTAWAY_OPTAUUID, m.MATCH_LOCALDATE FROM {DB}.OPTA_EVENTS e JOIN {DB}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID WHERE e.MATCH_OPTAUUID IN {match_ids_str} AND e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' AND (e.EVENT_TYPEID = 16 OR q.QUALIFIER_QID = 28) QUALIFY ROW_NUMBER() OVER (PARTITION BY e.MATCH_OPTAUUID, e.EVENT_TIMESTAMP ORDER BY e.EVENT_EVENTID) = 1"
            sql_events = f"WITH Goals AS ({sql_goals}) SELECT e.*, g.GOAL_TIME, g.SCORING_TEAM as GOAL_TEAM_ID, g.GOAL_MIN, g.CONTESTANTHOME_NAME, g.CONTESTANTAWAY_NAME, g.CONTESTANTHOME_OPTAUUID, g.CONTESTANTAWAY_OPTAUUID, g.MATCH_LOCALDATE FROM {DB}.OPTA_EVENTS e INNER JOIN Goals g ON e.MATCH_OPTAUUID = g.MATCH_OPTAUUID WHERE e.EVENT_TIMESTAMP >= DATEADD(second, -12, g.GOAL_TIME) AND e.EVENT_TIMESTAMP <= g.GOAL_TIME AND e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' QUALIFY ROW_NUMBER() OVER (PARTITION BY e.EVENT_OPTAUUID, g.GOAL_TIME ORDER BY e.EVENT_TIMESTAMP DESC) = 1"
            df_all_events = conn.query(sql_events)
        except:
            df_all_events = pd.DataFrame()

    # --- 3. UI LAYOUT ---
    t1, t2, t3, t4, t5 = st.tabs(["OVERSIGT", "MED BOLDEN", "UDEN BOLDEN", "MÅL-SEKVENSER", "SPILLEROVERSIGT"])

    with t1:
        # Vi opretter to hovedkolonner for hele siden
        # [1.2, 1] giver lidt mere plads til tabellen i venstre side
        main_col1, main_col2 = st.columns([1.2, 1])

        with main_col1:
            # --- 1. VENSTRE SIDE: METRICS & TABEL ---
            df_res['TOTAL_HOME_SCORE'] = df_res['TOTAL_HOME_SCORE'].fillna(0).astype(int)
            df_res['TOTAL_AWAY_SCORE'] = df_res['TOTAL_AWAY_SCORE'].fillna(0).astype(int)
            df_res['RESULTAT'] = df_res['TOTAL_HOME_SCORE'].astype(str) + " - " + df_res['TOTAL_AWAY_SCORE'].astype(str)
            
            def get_result(row):
                is_home = row['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
                h, a = row['TOTAL_HOME_SCORE'], row['TOTAL_AWAY_SCORE']
                if h == a: return "D"
                return "W" if (is_home and h > a) or (not is_home and a > h) else "L"
            df_res['RES'] = df_res.apply(get_result, axis=1)

            # Metrics i små kolonner inde i main_col1
            m1, m2, m3 = st.columns(3)
            wins = (df_res['RES'] == "W").sum()
            draws = (df_res['RES'] == "D").sum()
            m1.metric("Point (10)", (wins*3)+draws)
            m2.metric("Vundne", wins)
            mål_s = sum([r['TOTAL_HOME_SCORE'] if r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else r['TOTAL_AWAY_SCORE'] for _, r in df_res.iterrows()])
            mål_i = sum([r['TOTAL_AWAY_SCORE'] if r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else r['TOTAL_HOME_SCORE'] for _, r in df_res.iterrows()])
            m3.metric("Målscore", f"{mål_s}-{mål_i}")

            # Tabellen under metrics
            st.dataframe(df_res[['MATCH_LOCALDATE', 'CONTESTANTHOME_NAME', 'RESULTAT', 'CONTESTANTAWAY_NAME', 'RES']], 
                         use_container_width=True, hide_index=True, height=450)

        with main_col2:
            # --- 2. HØJRE SIDE: TREND GRAFER (STABLET VERTIKALT) ---
            kat_map = {
                "Pasninger": {'col': 'P', 'color': '#0047AB', 'round': 0},
                "Afslutninger": {'col': 'A', 'color': '#C8102E', 'round': 1},
                "Erobringer": {'col': 'E', 'color': '#2E7D32', 'round': 0},
                "Dueller": {'col': 'D', 'color': '#FF9800', 'round': 0},
                "Frispark": {'col': 'F', 'color': '#D32F2F', 'round': 0}
            }
            alle_kategorier = list(kat_map.keys())

            # Data aggregering (behold din eksisterende df_vol logik her)
            # ... (indsæt din df_vol og df_plot beregning her) ...

            # Graf 1
            h_c1, d_c1 = st.columns([1.8, 1])
            v1 = d_c1.selectbox("Stat 1", alle_kategorier, index=0, key="v1_side", label_visibility="collapsed")
            info1 = kat_map[v1]
            avg1 = df_plot[f"{info1['col']}_tot"].mean()
            h_c1.markdown(f"**{v1} (Gns: {round(avg1, info1['round'])})**")
            
            fig1 = px.bar(df_plot, x='LABEL', y=f"{info1['col']}_tot", text=df_plot.apply(lambda r: f"{int(r[f'{info1['col']}_tot'])}<br>({int(r[f'{info1['col']}_suc']/r[f'{info1['col']}_tot']*100) if r[f'{info1['col']}_tot']>0 else 0}%)", axis=1))
            fig1.update_layout(height=280, margin=dict(t=30, b=0, l=0, r=0), plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})

            st.divider() # Lille adskiller mellem graferne

            # Graf 2
            h_c2, d_c2 = st.columns([1.8, 1])
            mulige_v2 = [k for k in alle_kategorier if k != v1]
            v2 = d_c2.selectbox("Stat 2", mulige_v2, index=0, key="v2_side", label_visibility="collapsed")
            info2 = kat_map[v2]
            avg2 = df_plot[f"{info2['col']}_tot"].mean()
            h_c2.markdown(f"**{v2} (Gns: {round(avg2, info2['round'])})**")
            
            fig2 = px.bar(df_plot, x='LABEL', y=f"{info2['col']}_tot", text=df_plot.apply(lambda r: f"{int(r[f'{info2['col']}_tot'])}<br>({int(r[f'{info2['col']}_suc']/r[f'{info2['col']}_tot']*100) if r[f'{info2['col']}_tot']>0 else 0}%)", axis=1))
            fig2.update_layout(height=280, margin=dict(t=30, b=0, l=0, r=0), plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})

    # --- HJÆLPEFUNKTION TIL SUCCES-RATE ---
    def get_top_success(df, event_ids):
        relevant = df[df['EVENT_TYPEID'].isin(event_ids)].copy()
        if relevant.empty: return pd.DataFrame()
        stats = relevant.groupby('PLAYER_NAME').agg(
            TOTAL=('OUTCOME', 'count'),
            SUCCESS=('OUTCOME', lambda x: (x == 1).sum())
        ).reset_index()
        stats['PCT'] = (stats['SUCCESS'] / stats['TOTAL'] * 100).round(1)
        return stats.sort_values('TOTAL', ascending=False).head(8)

    with t2:
        cp, cs = st.columns([2, 1])
        with cs:
            v_med = st.selectbox("Fokus", ["Opbygning", "Gennembrud", "Afslutninger"], key="ms")
            
            if v_med == "Opbygning":
                ids, tit, cm, zn = [1], "EGEN HALVDEL: OPBYGNING", "Blues", "up"
                df_fokuseret = df_all_h[df_all_h['EVENT_X'] <= 50]
                # Her bruger vi standard get_top_success (OUTCOME 1 = præcis aflevering)
                df_top = get_top_success(df_fokuseret, ids)
                label_txt = "Succesfulde / Antal"
                
            elif v_med == "Gennembrud":
                ids, tit, cm, zn = [1], "OFF. HALVDEL: GENNEMBRUD", "Reds", "down"
                df_fokuseret = df_all_h[df_all_h['EVENT_X'] > 50]
                df_top = get_top_success(df_fokuseret, ids)
                label_txt = "Succes / Antal"
                
            else: # AFSLUTNINGER
                ids, tit, cm, zn = [13, 14, 15, 16], "AFSLUTNINGER", "YlOrRd", "down"
                df_fokuseret = df_all_h
                
                # Special-beregning for konverteringsrate (Mål / Alle skud)
                relevant_shots = df_fokuseret[df_fokuseret['EVENT_TYPEID'].isin(ids)].copy()
                if not relevant_shots.empty:
                    df_top = relevant_shots.groupby('PLAYER_NAME').agg(
                        TOTAL=('EVENT_TYPEID', 'count'),
                        SUCCESS=('EVENT_TYPEID', lambda x: (x == 16).sum()) # Kun Type 16 er mål
                    ).reset_index()
                    df_top['PCT'] = (df_top['SUCCESS'] / df_top['TOTAL'] * 100).round(1)
                    df_top = df_top.sort_values('TOTAL', ascending=False).head(5)
                else:
                    df_top = pd.DataFrame()
                label_txt = "Mål / Skud (Konvertering %)"

            st.write(f"**Top 8 ({label_txt}):**")
            
            if not df_top.empty:
                for _, r in df_top.iterrows():
                    # Vi viser konverteringsraten her
                    st.write(f"{int(r['SUCCESS'])} / {int(r['TOTAL'])} ({int(r['PCT'])}%) **{r['PLAYER_NAME']}**")
            else:
                st.info("Ingen data fundet.")

        with cp: 
            st.pyplot(plot_custom_pitch(df_fokuseret, ids, tit, zone=zn, cmap=cm, logo=hold_logo))
            
    with t3:
        cp, cs = st.columns([2, 1])
        with cs:
            v_uden = st.selectbox("Fokus", ["Dueller", "Erobringer", "Defensiv Zone"], key="us")
            if v_uden == "Dueller": ids, tit, cm, zn = [7, 8], "DUELLER", "Blues", "up"
            elif v_uden == "Erobringer": ids, tit, cm, zn = [127, 12, 49], "EROBRINGER", "GnBu", "up"
            else: ids, tit, cm, zn = [7, 12, 127], "DEFENSIV ZONE", "PuBu", "up"
            
            st.write("**Top 8 (Succesfulde / Antal):**")
            df_top_u = get_top_success(df_all_h, ids)
            if not df_top_u.empty:
                for _, r in df_top_u.iterrows():
                    st.write(f"{int(r['SUCCESS'])} / {int(r['TOTAL'])} ({int(r['PCT'])}%) **{r['PLAYER_NAME']}**")
        with cp: st.pyplot(plot_custom_pitch(df_all_h, ids, tit, zone=zn, cmap=cm, logo=hold_logo))

    # T4 og T5 forbliver som før...
    with t4:
        if df_all_events is not None and not df_all_events.empty:
            gl = df_all_events.drop_duplicates(['MATCH_OPTAUUID', 'GOAL_TIME']).sort_values('GOAL_TIME', ascending=False)
            opts = {f"{r['MATCH_OPTAUUID']}_{r['GOAL_TIME']}": {'label': f"{pd.to_datetime(r['MATCH_LOCALDATE']).strftime('%d/%m/%Y')} vs. {r['CONTESTANTAWAY_NAME'] if r['CONTESTANTHOME_OPTAUUID']==valgt_uuid else r['CONTESTANTHOME_NAME']} ({r['GOAL_MIN']}. min)", 'match_id': r['MATCH_OPTAUUID'], 'goal_ts': r['GOAL_TIME'], 'opp_uuid': r['CONTESTANTAWAY_OPTAUUID'] if r['CONTESTANTHOME_OPTAUUID']==valgt_uuid else r['CONTESTANTHOME_OPTAUUID'], 'min': r['GOAL_MIN'], 'date': pd.to_datetime(r['MATCH_LOCALDATE']).strftime('%d/%m/%Y')} for _, r in gl.iterrows()}
            sk = st.selectbox("Vælg mål", list(opts.keys()), format_func=lambda x: opts[x]['label'])
            sd = opts[sk]
            tge = df_all_events[(df_all_events['MATCH_OPTAUUID'] == sd['match_id']) & (df_all_events['GOAL_TIME'] == sd['goal_ts'])].sort_values('EVENT_TIMESTAMP')
            p_c, l_c = st.columns([2.5, 1])
            with p_c:
                p = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='grey')
                f, ax = p.draw(figsize=(10, 7))
                draw_match_info_box(ax, hold_logo, get_logo_img(sd['opp_uuid']), sd['date'], "Mål", sd['min'])
                for i in range(len(tge)-1): p.arrows(tge.iloc[i]['EVENT_X'], tge.iloc[i]['EVENT_Y'], tge.iloc[i+1]['EVENT_X'], tge.iloc[i+1]['EVENT_Y'], width=1, headwidth=3, color='black', alpha=0.15, ax=ax)
                for _, r in tge.iterrows():
                    c, m, s = ('red', 's', 180) if r['EVENT_TYPEID'] == 16 else (('gold', 'P', 200) if r['EVENT_TYPEID'] == 5 else ('red', 'o', 80))
                    ax.scatter(r['EVENT_X'], r['EVENT_Y'], color=c, s=s, marker=m, edgecolors='black', zorder=10)
                    ax.text(r['EVENT_X'], r['EVENT_Y']+2.5, r['PLAYER_NAME'], fontsize=7, ha='center', fontweight='bold', bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
                st.pyplot(f)
            with l_c:
                tge['Aktion'] = tge['EVENT_TYPEID'].astype(str).map(OPTA_EVENT_TYPES)
                st.write("**Sekvens:**"); st.dataframe(tge[['PLAYER_NAME', 'Aktion']].iloc[::-1], hide_index=True)
        else: st.info("Ingen mål-sekvenser fundet.")

    with t5:
        if not df_all_h.empty:
            regain_ids = [7, 8, 12, 49, 67, 127, 73, 74]
            df_all_h['is_pass'] = (df_all_h['EVENT_TYPEID'] == 1).astype(int)
            df_all_h['is_regain'] = df_all_h['EVENT_TYPEID'].isin(regain_ids).astype(int)
            df_all_h['is_shot'] = df_all_h['EVENT_TYPEID'].isin([13,14,15,16]).astype(int)
            stats = df_all_h.groupby('PLAYER_NAME').agg({'is_pass': 'sum', 'is_regain': 'sum', 'is_shot': 'sum', 'EVENT_TYPEID': 'count'}).rename(columns={'EVENT_TYPEID': 'Aktioner', 'is_pass': 'Pasninger', 'is_regain': 'Erobringer', 'is_shot': 'Skud'}).sort_values('Aktioner', ascending=False)
            st.dataframe(stats, use_container_width=True)
            
if __name__ == "__main__":
    vis_side()
