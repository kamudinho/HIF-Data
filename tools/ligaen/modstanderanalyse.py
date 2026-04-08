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

# --- IMPORT FRA DIN MAPPING.PY (Korrekt nu) ---
from data.utils.mapping import (
    OPTA_EVENT_TYPES, 
    OPTA_QUALIFIERS,
    get_action_label
)

# --- 1. KONFIGURATION (OPDATERET 2026) ---
DB = "KLUB_HVIDOVREIF.AXIS"
# Liga-ID'er for Superliga, NordicBet, 2. div, 3. div og Pokalen
LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '335', '328', '329', '43319', '331')"

# --- 2. HJÆLPEFUNKTIONER ---
@st.cache_data(ttl=3600)
def get_logo_img(opta_uuid):
    """Henter klublogo fra din TEAMS mapping eller via URL"""
    if not opta_uuid: return None
    url = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), None)
    if not url: return None
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except: return None

def draw_match_row(date, h_name, h_uuid, score, a_name, a_uuid, res_char):
    """Tegner en række i kampoversigten med logoer og farvet resultat-badge"""
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
    """Tegner info-boks ved mål-sekvenser"""
    if scoring_team_logo:
        ax_l1 = ax.inset_axes([0.02, 0.08, 0.05, 0.05], transform=ax.transAxes)
        ax_l1.imshow(scoring_team_logo); ax_l1.axis('off')
    ax.text(0.08, 0.105, "vs.", transform=ax.transAxes, fontsize=8, fontweight='bold', va='center')
    if opp_team_logo:
        ax_l2 = ax.inset_axes([0.10, 0.08, 0.05, 0.05], transform=ax.transAxes)
        ax_l2.imshow(opp_team_logo); ax_l2.axis('off')
    ax.text(0.03, 0.07, f"{date_str} | Stilling: {score_str} ({min_str}. min)", transform=ax.transAxes, fontsize=8, color='#444444', va='top')

def draw_player_info_box(ax, team_logo, player_name, season_str, category_str):
    """Tegner spiller-info overlay på banen for spillerprofilen"""
    if team_logo:
        ax_l = ax.inset_axes([0.02, 0.88, 0.07, 0.07], transform=ax.transAxes)
        ax_l.imshow(team_logo)
        ax_l.axis('off')
    ax.text(0.10, 0.92, player_name.upper(), transform=ax.transAxes, 
            fontsize=10, fontweight='bold', color='black', va='center')
    info_text = f"{season_str} | {category_str}"
    ax.text(0.10, 0.89, info_text, transform=ax.transAxes, 
            fontsize=8, color='#666666', va='center')

def plot_custom_pitch(df, event_ids, title, zone='full', cmap='Reds', logo=None):
    """Genererer banerplot (KDE/Heatmap)"""
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

    # Team Mapping
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
            
            # SQL for alle events med qualifiers samlet via LISTAGG
            sql_all_h = f"""
                SELECT 
                    e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, e.PLAYER_NAME, e.MATCH_OPTAUUID, 
                    e.EVENT_TIMESTAMP, e.EVENT_OUTCOME as OUTCOME,
                    LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
                FROM {DB}.OPTA_EVENTS e
                LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
                WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' 
                AND e.MATCH_OPTAUUID IN {m_ids_str}
                GROUP BY 1, 2, 3, 4, 5, 6, 7
            """
            df_all_h = conn.query(sql_all_h)
            
            # --- DATA-VASK I MODSTANDERANALYSE.PY ---
            if not df_all_h.empty:
                # 1. Lav qual_list (vigtigt for get_action_label)
                df_all_h['qual_list'] = df_all_h['QUALIFIERS'].fillna('').str.split(',')
                
                # 2. Påfør din hjerte-logik
                df_all_h['Action_Label'] = df_all_h.apply(get_action_label, axis=1)
                
                # 3. Fjern alt det, din whitelist i mapping.py har markeret som None
                df_all_h = df_all_h.dropna(subset=['Action_Label'])

            # SQL for Mål-sekvenser
            sql_seq = f"""
            WITH SeasonMatches AS (
                SELECT MATCH_OPTAUUID, CONTESTANTHOME_NAME, CONTESTANTAWAY_NAME, 
                       MATCH_LOCALDATE, CONTESTANTHOME_OPTAUUID, CONTESTANTAWAY_OPTAUUID,
                       TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE  -- <--- RETTET HER
                FROM {DB}.OPTA_MATCHINFO 
                WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}
            ),
            TargetGoals AS (
                SELECT MATCH_OPTAUUID, EVENT_TIMESTAMP as G_TIME, EVENT_TIMEMIN as G_MIN 
                FROM {DB}.OPTA_EVENTS 
                WHERE EVENT_TYPEID = 16 AND EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}'
                AND MATCH_OPTAUUID IN (SELECT MATCH_OPTAUUID FROM SeasonMatches)
            )
            SELECT e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, e.PLAYER_NAME, e.EVENT_TIMESTAMP, e.MATCH_OPTAUUID,
                   m.MATCH_LOCALDATE, m.CONTESTANTHOME_NAME, m.CONTESTANTAWAY_NAME, 
                   m.CONTESTANTHOME_OPTAUUID, m.CONTESTANTAWAY_OPTAUUID,
                   m.TOTAL_HOME_SCORE, m.TOTAL_AWAY_SCORE, -- <--- RETTET HER
                   tg.G_TIME as GOAL_TIME, tg.G_MIN as GOAL_MIN,
                   LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
            FROM {DB}.OPTA_EVENTS e
            JOIN SeasonMatches m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
            INNER JOIN TargetGoals tg ON e.MATCH_OPTAUUID = tg.MATCH_OPTAUUID
                AND e.EVENT_TIMESTAMP >= DATEADD(second, -20, tg.G_TIME)
                AND e.EVENT_TIMESTAMP <= tg.G_TIME
            LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}'
            GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15
            """
            
            try: 
                df_all_events = _get_snowflake_conn().query(sql_seq)
                if not df_all_events.empty:
                    df_all_events['qual_list'] = df_all_events['QUALIFIERS'].fillna('').str.split(',')
                    # Vi venter med Action_Label til selve loopet for at sikre Penalty-tjek
            except Exception as e:
                st.error(f"Fejl i SQL: {e}")
                df_all_events = pd.DataFrame()
        else:
            st.error("Ingen data fundet for det valgte hold.")
            return

    t1, t2, t3, t4, t5, t6 = st.tabs(["OVERSIGT", "MED BOLDEN", "UDEN BOLDEN", "MÅL-SEKVENSER", "SPILLEROVERSIGT", "SPILLERPROFIL"])
    
    # --- HER STARTER TABS INTEGRATIONEN ---
    
    with t1:
        # 1. Resultat logik
        df_res['RES'] = df_res.apply(lambda r: "D" if r['TOTAL_HOME_SCORE'] == r['TOTAL_AWAY_SCORE'] else ("W" if ((r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid and r['TOTAL_HOME_SCORE'] > r['TOTAL_AWAY_SCORE']) or (r['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid and r['TOTAL_AWAY_SCORE'] > r['TOTAL_HOME_SCORE'])) else "L"), axis=1)
        
        # 2. Volumen beregninger baseret på din mapping
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

        st.markdown("""
            <style>
            [data-testid="stMetric"] { text-align: center; display: flex; flex-direction: column; align-items: center; width: 100%; }
            [data-testid="stMetricLabel"] { display: flex; justify-content: center; align-items: center; width: 100%; font-size: 11px !important; margin-bottom: -10px !important; }
            [data-testid="stMetricValue"] { display: flex; justify-content: center; align-items: center; width: 100%; font-size: 20px !important; font-weight: 700; }
            .metric-row-wrapper { margin-top: -35px; margin-bottom: -25px; }
            .compact-divider { margin-top: -5px; margin-bottom: 5px; border-top: 1px solid #f0f2f6; }
            </style>
            """, unsafe_allow_html=True)

        m_col1, m_spacer, m_col2 = st.columns([1.3, 0.1, 2.0])
        
        with m_col1:
            st.write("**Seneste 10 kampe**")
            with st.container(border=True):
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
                st.markdown('<div class="compact-divider"></div>', unsafe_allow_html=True)
                for _, row in df_res.iterrows():
                    draw_match_row(pd.to_datetime(row['MATCH_LOCALDATE']).strftime('%d/%m'), row['CONTESTANTHOME_NAME'], row['CONTESTANTHOME_OPTAUUID'], f"{int(row['TOTAL_HOME_SCORE'])}-{int(row['TOTAL_AWAY_SCORE'])}", row['CONTESTANTAWAY_NAME'], row['CONTESTANTAWAY_OPTAUUID'], row['RES'])
                    st.markdown("<hr style='margin:2px 0; opacity:0.05'>", unsafe_allow_html=True)

        with m_col2:
            kat_map = {"Pasninger": 'P', "Afslutninger": 'A', "Erobringer": 'E', "Dueller": 'D', "Frispark": 'F'}
            col_map = {'P': '#084594', 'A': '#cb181d', 'E': '#238b45', 'D': '#ec7014', 'F': '#6a51a3'}
            h_c1, d_c1 = st.columns([2, 1])
            val1 = d_c1.selectbox("Vælg", list(kat_map.keys()), index=0, key="val_top", label_visibility="collapsed")
            c_key1 = kat_map[val1]
            avg1 = df_plot[f'{c_key1}_tot'].mean()
            h_c1.markdown(f"**{val1} (Gns: {round(avg1, 1)})**")
            fig1 = px.bar(df_plot, x='X_AXIS_LABEL', y=f"{c_key1}_tot", text=f"{c_key1}_tot")
            fig1.add_hline(y=avg1, line_dash="dot", line_color="rgba(0,0,0,0.2)", line_width=1)
            fig1.update_traces(marker_color=col_map[c_key1], textposition='outside')
            fig1.update_layout(height=300, margin=dict(t=25, b=0, l=0, r=0), plot_bgcolor='rgba(0,0,0,0)', xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})

            options_2 = [k for k in kat_map.keys() if k != val1]
            h_c2, d_c2 = st.columns([2, 1])
            val2 = d_c2.selectbox("Vælg", options_2, index=0, key="val_bot", label_visibility="collapsed")
            c_key2 = kat_map[val2]
            avg2 = df_plot[f'{c_key2}_tot'].mean()
            h_c2.markdown(f"**{val2} (Gns: {round(avg2, 1)})**")
            fig2 = px.bar(df_plot, x='X_AXIS_LABEL', y=f"{c_key2}_tot", text=f"{c_key2}_tot")
            fig2.add_hline(y=avg2, line_dash="dot", line_color="rgba(0,0,0,0.2)", line_width=1)
            fig2.update_traces(marker_color=col_map[c_key2], textposition='outside')
            fig2.update_layout(height=300, margin=dict(t=25, b=0, l=0, r=0), plot_bgcolor='rgba(0,0,0,0)', xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})
            
    with t2:
        st.markdown("""
            <style>
            [data-testid="stHorizontalBlock"] [data-testid="stMetric"] { text-align: center; align-items: center; justify-content: center; width: 100%; }
            [data-testid="stMetricLabel"] { justify-content: center !important; font-size: 10px !important; white-space: nowrap; margin-bottom: -3px !important; }
            [data-testid="stMetricValue"] { justify-content: center !important; font-size: 14px !important; font-weight: 700; }
            </style>
            """, unsafe_allow_html=True)

        kat_options = ["Opbygning", "Gennembrud", "Touches in Box", "Afslutninger"]
        c_left, c_right = st.columns([2, 1])
        v_med = c_right.selectbox("Vælg Fokusområde", kat_options, key="ms_t2", label_visibility="collapsed")
        
        n_matches = df_all_h['MATCH_OPTAUUID'].nunique()
        total_minutes = n_matches * 90

        if v_med == "Opbygning":
            ids, tit, cm, zn = [1], "OPBYGNING", "Blues", "up"
            df_f = df_all_h[(df_all_h['EVENT_X'] <= 50) & (df_all_h['EVENT_TYPEID'] == 1)].copy()
        elif v_med == "Gennembrud":
            ids, tit, cm, zn = [1], "GENNEMBRUD", "Blues", "down"
            df_f = df_all_h[(df_all_h['EVENT_X'] > 50) & (df_all_h['EVENT_TYPEID'] == 1)].copy()
        elif v_med == "Touches in Box":
            ids, tit, cm, zn = [0], "TOUCHES IN BOX", "Blues", "down"
            df_f = df_all_h[(df_all_h['EVENT_X'] > 83) & (df_all_h['EVENT_Y'] > 21.1) & (df_all_h['EVENT_Y'] < 78.9)].copy()
            df_shots = df_all_h[df_all_h['EVENT_TYPEID'].isin([13, 14, 15, 16])].copy()
        else: # Afslutninger
            ids, tit, cm, zn = [13, 14, 15, 16], "AFSLUTNINGER", "YlOrRd", "down"
            df_f = df_all_h[df_all_h['EVENT_TYPEID'].isin(ids)].copy()

        total_act = len(df_f)

        with c_left:
            st.pyplot(plot_custom_pitch(df_f, df_f['EVENT_TYPEID'].unique().tolist() if v_med == "Touches in Box" else ids, tit, zone=zn, cmap=cm, logo=hold_logo))

        with c_right:
            if v_med == "Touches in Box":
                shots_total = len(df_shots)
                touches_p90 = (total_act / total_minutes * 90) if total_minutes > 0 else 0
                conv_box = (shots_total / total_act * 100) if total_act > 0 else 0
                m_cols = st.columns(3)
                m_cols[0].metric("Touches", total_act)
                m_cols[1].metric("p90", round(touches_p90, 1))
                m_cols[2].metric("Afsl/Box %", f"{int(conv_box)}%")
            elif v_med == "Afslutninger":
                goals = len(df_f[df_f['EVENT_TYPEID'] == 16])
                shots_p90 = (total_act / total_minutes * 90) if total_minutes > 0 else 0
                goals_p90 = (goals / total_minutes * 90) if total_minutes > 0 else 0
                conv_rate = (goals / total_act * 100) if total_act > 0 else 0
                m_cols = st.columns(5)
                m_cols[0].metric("Skud", total_act); m_cols[1].metric("p90", round(shots_p90, 1))
                m_cols[2].metric("Mål", goals); m_cols[3].metric("p90", round(goals_p90, 1))
                m_cols[4].metric("Konv %", f"{int(conv_rate)}%")
            else:
                acc_pct = (df_f['OUTCOME'].sum() / total_act * 100) if total_act > 0 else 0
                avg_p90 = (total_act / total_minutes * 90) if total_minutes > 0 else 0
                m_cols = st.columns(3)
                m_cols[0].metric("Total", total_act); m_cols[1].metric("Gns p90", round(avg_p90, 1)); m_cols[2].metric("Succes", f"{int(acc_pct)}%")
            
            st.markdown("<div style='margin-top:10px; border-top: 1px solid #eee; padding-top: 10px;'></div>", unsafe_allow_html=True)
            st.write(f"**Top 8: {v_med}**")
            
            if not df_f.empty:
                df_top = df_f.groupby('PLAYER_NAME').agg(
                    TOTAL=('EVENT_TYPEID', 'count'),
                    SUCCESS=('OUTCOME', 'sum')
                ).reset_index()

                if v_med == "Afslutninger":
                    df_top['SUCCESS'] = df_f[df_f['EVENT_TYPEID'] == 16].groupby('PLAYER_NAME').size().reindex(df_top['PLAYER_NAME'], fill_value=0).values
                
                df_top['RATE'] = (df_top['SUCCESS'] / df_top['TOTAL'] * 100).fillna(0)
                df_top = df_top.sort_values('TOTAL', ascending=False).head(8)

                for _, r in df_top.iterrows():
                    rate = int(r['RATE'])
                    st.markdown(f"""
                        <div style="margin-bottom: 12px;">
                            <div style="display: flex; justify-content: space-between; font-size: 11px; font-weight: 600; margin-bottom: 2px;">
                                <span>{r['PLAYER_NAME']}</span>
                                <span>{int(r['SUCCESS'])} / {int(r['TOTAL'])} ({rate}%)</span>
                            </div>
                            <div style="background-color: #f0f2f6; border-radius: 4px; height: 5px; width: 100%;">
                                <div style="background-color: #084594; height: 5px; width: {rate}%; border-radius: 4px;"></div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

    with t3:
        uden_options = ["Egen halvdel: Erobringer", "Off. halvdel: Pres", "Egen halvdel: Dueller", "Off. halvdel: Dueller"]
        c_left, c_right = st.columns([2, 1])
        v_uden = c_right.selectbox("Vælg Fokusområde", uden_options, key="ms_t3", label_visibility="collapsed")
        
        erobring_ids = [7, 8, 12, 127] 
        duel_ids = [7, 44] 

        if "Erobringer" in v_uden:
            ids, tit, cm, zn = erobring_ids, "Egen halvdel: EROBRINGER", "Oranges", "up"
            df_f = df_all_h[(df_all_h['EVENT_X'] > 17) & (df_all_h['EVENT_X'] <= 50) & (df_all_h['EVENT_TYPEID'].isin(ids))].copy()
        elif "Pres" in v_uden:
            ids, tit, cm, zn = erobring_ids, "Off. halvdel: PRES", "Oranges", "down"
            df_f = df_all_h[(df_all_h['EVENT_X'] > 50) & (df_all_h['EVENT_TYPEID'].isin(ids))].copy()
        elif "Egen halvdel: Dueller" in v_uden:
            ids, tit, cm, zn = duel_ids, "Egen halvdel: DUELLER", "Oranges", "up"
            df_f = df_all_h[(df_all_h['EVENT_X'] > 17) & (df_all_h['EVENT_X'] <= 50) & (df_all_h['EVENT_TYPEID'].isin(ids))].copy()
        else: # Off. halvdel: Dueller
            ids, tit, cm, zn = duel_ids, "Off. halvdel: DUELLER", "Oranges", "down"
            df_f = df_all_h[(df_all_h['EVENT_X'] > 50) & (df_all_h['EVENT_TYPEID'].isin(ids))].copy()

        total_act = len(df_f)

        with c_left:
            st.pyplot(plot_custom_pitch(df_f, ids, tit, zone=zn, cmap=cm, logo=hold_logo))

        with c_right:
            acc_pct = (df_f['OUTCOME'].sum() / total_act * 100) if total_act > 0 else 0
            avg_p90 = (total_act / total_minutes * 90) if total_minutes > 0 else 0
            m_cols = st.columns(3)
            m_cols[0].metric("Total", total_act); m_cols[1].metric("p90", round(avg_p90, 1)); m_cols[2].metric("Succes", f"{int(acc_pct)}%")
            
            st.markdown("<div style='margin-top:10px; border-top: 1px solid #eee; padding-top: 10px;'></div>", unsafe_allow_html=True)
            st.write(f"**Top 8: {v_uden}**")
            
            if not df_f.empty:
                df_top = df_f.groupby('PLAYER_NAME').agg(
                    TOTAL=('EVENT_TYPEID', 'count'),
                    SUCCESS=('OUTCOME', 'sum')
                ).reset_index()
    
                df_top['RATE'] = (df_top['SUCCESS'] / df_top['TOTAL'] * 100).fillna(0)
                df_top = df_top.sort_values('TOTAL', ascending=False).head(8)
    
                for _, r in df_top.iterrows():
                    rate = int(r['RATE'])
                    st.markdown(f"""
                        <div style="margin-bottom: 12px;">
                            <div style="display: flex; justify-content: space-between; font-size: 11px; font-weight: 600; margin-bottom: 2px;">
                                <span>{r['PLAYER_NAME']}</span>
                                <span>{int(r['SUCCESS'])} / {int(r['TOTAL'])} ({rate}%)</span>
                            </div>
                            <div style="background-color: #f0f2f6; border-radius: 4px; height: 5px; width: 100%;">
                                <div style="background-color: #ec7014; height: 5px; width: {rate}%; border-radius: 4px;"></div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                
    with t4:
        if not df_all_events.empty:
            gl = df_all_events.drop_duplicates(['MATCH_OPTAUUID', 'GOAL_TIME']).sort_values(
                ['MATCH_LOCALDATE', 'GOAL_MIN'], ascending=[False, True]
            )
            
            opts = {f"{r['MATCH_OPTAUUID']}_{r['GOAL_TIME']}": {
                # RETTET TIL TOTAL_HOME_SCORE OG TOTAL_AWAY_SCORE HERUNDER:
                'label': f"{pd.to_datetime(r['MATCH_LOCALDATE']).strftime('%d/%m')} vs {r['CONTESTANTAWAY_NAME'] if r['CONTESTANTHOME_OPTAUUID']==valgt_uuid else r['CONTESTANTHOME_NAME']} ({int(r['TOTAL_HOME_SCORE'])}-{int(r['TOTAL_AWAY_SCORE'])})", 
                'match_id': r['MATCH_OPTAUUID'], 
                'goal_ts': r['GOAL_TIME'], 
                'opp_uuid': r['CONTESTANTAWAY_OPTAUUID'] if r['CONTESTANTHOME_OPTAUUID']==valgt_uuid else r['CONTESTANTHOME_OPTAUUID'], 
                'min': int(r['GOAL_MIN']), 
                'date': pd.to_datetime(r['MATCH_LOCALDATE']).strftime('%d/%m/%Y'),
                'score_str': f"{int(r['TOTAL_HOME_SCORE'])}-{int(r['TOTAL_AWAY_SCORE'])}"
            } for _, r in gl.iterrows()}
            
            sk = st.selectbox("Vælg mål", list(opts.keys()), format_func=lambda x: opts[x]['label'])
            sd = opts[sk]
    
            # 2. Filtrér sekvensen
            tge = df_all_events[(df_all_events['MATCH_OPTAUUID'] == sd['match_id']) & 
                                (df_all_events['GOAL_TIME'] == sd['goal_ts'])].sort_values('EVENT_TIMESTAMP').copy()
    
            # 3. Tegn Pitch
            p_c, l_c = st.columns([2.5, 1])
            p = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='grey')
            f, ax = p.draw(figsize=(10, 7))
            
            # BRUGER DIN FUNKTION HER - nu med score_str direkte
            draw_match_info_box(ax, hold_logo, get_logo_img(sd['opp_uuid']), sd['date'], sd['score_str'], sd['min'])
    
            # Pile og spillernavne
            for i in range(len(tge)-1):
                p.arrows(tge.iloc[i]['EVENT_X'], tge.iloc[i]['EVENT_Y'], 
                         tge.iloc[i+1]['EVENT_X'], tge.iloc[i+1]['EVENT_Y'], 
                         width=1, color='black', alpha=0.15, ax=ax)
            
            for _, r in tge.iterrows():
                is_goal = str(r['EVENT_TYPEID']) == "16"
                ax.scatter(r['EVENT_X'], r['EVENT_Y'], color='red' if is_goal else 'black', s=100, edgecolors='white', zorder=10)
                ax.text(r['EVENT_X'], r['EVENT_Y']+2.5, r['PLAYER_NAME'], fontsize=7, ha='center', fontweight='bold', bbox=dict(facecolor='white', alpha=0.6, edgecolor='none', pad=1), zorder=11)
            
            p_c.pyplot(f)
    
            # 4. Tabel med omdøbning og Penalty-tjek
            def get_final_label_t4(row):
                if str(row['EVENT_TYPEID']) == "16" and "9" in row['qual_list']:
                    return "STRAFFESPARK"
                label = get_action_label(row)
                return label if label else "Opbygning"
    
            tge['Aktion'] = tge.apply(get_final_label_t4, axis=1)
            
            l_c.write("**Målsekvens:**")
            l_c.dataframe(
                tge[['PLAYER_NAME', 'Aktion']].iloc[::-1].rename(columns={'PLAYER_NAME': 'Spiller'}), 
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("Ingen mål fundet for denne sæson.")
            
    with t5:
        # Ny CSS der specifikt rammer st.table (som genererer ren HTML)
        st.markdown("""
            <style>
                /* Centrerer tekst i alle header-celler i st.table */
                [data-testid="stTable"] th {
                    text-align: center !important;
                    vertical-align: middle !important;
                }
                /* Centrerer alle celler */
                [data-testid="stTable"] td {
                    text-align: center !important;
                    vertical-align: middle !important;
                }
                /* Tvinger dog første kolonne (Spiller) til at være venstrestillet */
                [data-testid="stTable"] td:first-child, 
                [data-testid="stTable"] th:first-child {
                    text-align: left !important;
                }
            </style>
        """, unsafe_allow_html=True)

        if not df_all_events.empty:
            # 1. Databehandling (samme som før)
            df_mål_stats = df_all_events.copy()
            df_mål_stats['is_cross'] = df_mål_stats['qual_list'].apply(lambda x: '2' in x)
            df_mål_stats['is_shot_assist'] = df_mål_stats['qual_list'].apply(lambda x: '210' in x or '209' in x)
            df_mål_stats['is_shot'] = df_mål_stats['EVENT_TYPEID'].isin([13, 14, 15])
            df_mål_stats['is_goal'] = df_mål_stats['EVENT_TYPEID'] == 16

            total_goals_count = df_mål_stats['GOAL_TIME'].nunique()

            player_stats = df_mål_stats.groupby('PLAYER_NAME').agg(
                Involveringer=('GOAL_TIME', 'nunique'),
                Aktioner=('EVENT_TYPEID', 'count'),
                Mål=('is_goal', 'sum'),
                Pasninger=('EVENT_TYPEID', lambda x: (x == 1).sum()),
                Indlæg=('is_cross', 'sum'),
                Skud=('is_shot', 'sum'),
                Skud_Ass=('is_shot_assist', 'sum'),
                Erobringer=('EVENT_TYPEID', lambda x: x.isin([7, 8, 12, 127, 49]).sum())
            ).reset_index()

            player_stats['Involvering_Pct'] = (player_stats['Involveringer'] / total_goals_count * 100).round(1)
            player_stats = player_stats.sort_values('Involveringer', ascending=False)

            # 2. Layout
            col_tabel, col_graf = st.columns([3.5, 1])

            with col_tabel:
                st.write("**Statistik i målsekvenser**")
                
                # Vi klargør præcis de kolonner der skal vises
                df_visning = player_stats.rename(columns={
                    'PLAYER_NAME': 'Spiller',
                    'Skud_Ass': 'Skud Ass.'
                })[['Spiller', 'Involveringer', 'Aktioner', 'Mål', 'Pasninger', 'Indlæg', 'Skud', 'Skud Ass.', 'Erobringer']]
                
                # Vi bruger st.table i stedet for st.dataframe for at få CSS-kontrol over overskrifterne
                st.table(df_visning)

            with col_graf:
                st.write(f"**Top involvering (Hold total: {total_goals_count} mål)**")
                top_8_players = player_stats.head(8)

                for _, r in top_8_players.iterrows():
                    rel_width = r['Involvering_Pct']
                    st.markdown(f"""
                        <div style="margin-bottom: 12px;">
                            <div style="display: flex; justify-content: space-between; font-size: 11px; font-weight: 600; margin-bottom: 2px;">
                                <span>{r['PLAYER_NAME']}</span>
                                <span>{int(r['Involveringer'])} involveringer ({int(r['Involvering_Pct'])}%)</span>
                            </div>
                            <div style="background-color: #f0f2f6; border-radius: 4px; height: 5px; width: 100%;">
                                <div style="background-color: #df003b; height: 5px; width: {rel_width}%; border-radius: 4px;"></div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("Ingen data fundet for de valgte målsekvenser.")
            
    with t6:
        if not df_all_h.empty:
            # --- 1. Top-kontrolbar ---
            spiller_liste = sorted([n for n in df_all_h['PLAYER_NAME'].unique() if n is not None])
            
            descriptions = {
                "Heatmap": "Viser spillerens generelle bevægelsesmønster og intensitet på banen.",
                "Berøringer": "Alle aktioner hvor spilleren har været i kontakt med bolden.",
                "Afslutninger": "Oversigt over alle skudforsøg (Mål markeres med stjerne).",
                "Mål": "Kun de aktioner der resulterede i scoring.",
                "Assists": "Afleveringer der direkte førte til en afslutning og mål.",
                "Indlæg": "Bolde spillet fra kanten ind i feltet.",
                "Erobringer": "Tacklinger, bolderobringer og opsnappede afleveringer."
            }

            t_col1, t_col2, t_col3 = st.columns([0.9, 0.9, 1.2])
            with t_col1:
                valgt_spiller = st.selectbox("Vælg spiller", spiller_liste, key="player_profile_select_final_v5", label_visibility="collapsed")
            with t_col2:
                visning = st.selectbox("Visning", list(descriptions.keys()), key="pitch_view_final_v5", label_visibility="collapsed")
            with t_col3:
                st.caption(f"{descriptions.get(visning)}")
        
            # --- 2. Dataforberedelse ---
            df_spiller = df_all_h[df_all_h['PLAYER_NAME'] == valgt_spiller].copy()
    
            # --- 3. Hovedlayout ---
            c_p1, c_buffer, c_p2 = st.columns([0.9, 0.1, 2.2])
            
            with c_p1:
                # METRICS BEREGNING (Vi bruger Action_Label som er vasket)
                total_akt = len(df_spiller)
                pas_df = df_spiller[df_spiller['EVENT_TYPEID'] == 1]
                pas_count = len(pas_df)
                pas_acc = (pas_df['OUTCOME'].sum() / pas_count * 100) if pas_count > 0 else 0
                
                # Fanger "Målgivende assist", "Key Pass (Chance skabt)" og "Stor chance"
                chancer_skabt = len(df_spiller[df_spiller['Action_Label'].str.contains("assist|Key Pass|Stor chance", case=False, na=False)])
                
                shots_count = len(df_spiller[df_spiller['EVENT_TYPEID'].isin([13, 14, 15, 16])])
                cross_count = len(df_spiller[df_spiller['qual_list'].apply(lambda x: "2" in x)])
                erob_count = len(df_spiller[df_spiller['EVENT_TYPEID'].isin([7, 8, 12, 49])])
                
                touch_ids = [1, 3, 7, 10, 11, 12, 13, 14, 15, 16, 42, 44, 49, 50, 51, 54, 61, 73]
                touch_count = len(df_spiller[df_spiller['EVENT_TYPEID'].isin(touch_ids)])

                st.markdown(f"#### {valgt_spiller}")
                
                m_row1 = st.columns(4)
                m_row1[0].metric("Aktion", total_akt)
                m_row1[1].metric("Berøringer", touch_count)
                m_row1[2].metric("Pasninger", pas_count)
                m_row1[3].metric("Pasning %", f"{int(pas_acc)}%")
                
                m_row2 = st.columns(4)
                m_row2[0].metric("Afslutninger", shots_count)
                m_row2[1].metric("Chancer", chancer_skabt)
                m_row2[2].metric("Indlæg", cross_count)
                m_row2[3].metric("Erobringer", erob_count)
    
                st.markdown("<hr style='margin: 8px 0; opacity: 0.7;'>", unsafe_allow_html=True)                
                st.write("**Top 10: Aktioner**")
                
                # Her tæller vi direkte på de vaskede labels
                akt_counts = df_spiller['Action_Label'].value_counts().head(10)
                
                for akt, count in akt_counts.items():
                    st.markdown(f'''
                        <div style="display: flex; justify-content: space-between; font-size: 11px; border-bottom: 0.5px solid #eee; padding: 4px 0;">
                            <span>{akt}</span><b>{count}</b>
                        </div>''', unsafe_allow_html=True)
    
            with c_p2:
                p = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
                f, ax = p.draw(figsize=(10, 7))
                draw_player_info_box(ax, hold_logo, valgt_spiller, "2025/2026", visning)
                
                df_plot = df_spiller.dropna(subset=['EVENT_X', 'EVENT_Y'])
                if not df_plot.empty:
                    if visning == "Heatmap":
                        p.kdeplot(df_plot.EVENT_X, df_plot.EVENT_Y, ax=ax, cmap='Blues', fill=True, alpha=0.6, levels=50)
                    elif visning == "Berøringer":
                        d = df_plot[df_plot['EVENT_TYPEID'].isin(touch_ids)]
                        ax.scatter(d.EVENT_X, d.EVENT_Y, color='#084594', s=40, edgecolors='white', alpha=0.5)
                    elif visning == "Afslutninger":
                        d = df_plot[df_plot['EVENT_TYPEID'].isin([13, 14, 15, 16])]
                        goals = d[d['EVENT_TYPEID'] == 16]; misses = d[d['EVENT_TYPEID'] != 16]
                        ax.scatter(misses.EVENT_X, misses.EVENT_Y, color='red', s=100, edgecolors='black', alpha=0.6)
                        ax.scatter(goals.EVENT_X, goals.EVENT_Y, color='gold', s=200, marker='*', edgecolors='black', zorder=5)
                    elif visning == "Assists":
                        # Viser alt med qualifier 210 (Key Pass og Assists)
                        d = df_plot[df_plot['qual_list'].apply(lambda x: "210" in x)]
                        ax.scatter(d.EVENT_X, d.EVENT_Y, color='#00ffcc', s=150, marker='P', edgecolors='black')
                    elif visning == "Indlæg":
                        d = df_plot[df_plot['qual_list'].apply(lambda x: "2" in x)]
                        ax.scatter(d.EVENT_X, d.EVENT_Y, color='#cc00ff', s=80, edgecolors='white')
                    elif visning == "Erobringer":
                        d = df_plot[df_plot['EVENT_TYPEID'].isin([7, 8, 12, 49])]
                        ax.scatter(d.EVENT_X, d.EVENT_Y, color='orange', s=100, marker='D', edgecolors='white')
    
                st.pyplot(f, use_container_width=True)
            
if __name__ == "__main__":
    vis_side()
