import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from mplsoccer import Pitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS
import requests
from PIL import Image
from io import BytesIO

# --- IMPORT FRA MAPPING ---
from data.utils.mapping import (
    OPTA_EVENT_TYPES, 
    OPTA_QUALIFIERS,
    get_action_label
)

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '335', '328', '329', '43319', '331')"
CURRENT_SEASON = "2025/2026"

# --- HJÆLPEFUNKTIONER ---
@st.cache_data(ttl=3600)
def get_logo_img(opta_uuid):
    if not opta_uuid: return None
    uuid_clean = str(opta_uuid).lower().replace('t', '')
    url = next((info['logo'] for name, info in TEAMS.items() if str(info.get('opta_uuid', '')).lower().replace('t','') == uuid_clean), None)
    if not url: return None
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except: return None

def draw_player_info_box(ax, team_logo, player_name, season_str, category_str):
    if team_logo:
        ax_l = ax.inset_axes([0.02, 0.88, 0.07, 0.07], transform=ax.transAxes)
        ax_l.imshow(team_logo)
        ax_l.axis('off')
    ax.text(0.10, 0.92, str(player_name).upper(), transform=ax.transAxes, 
            fontsize=10, fontweight='bold', color='black', va='center')
    ax.text(0.10, 0.89, f"{season_str} | {category_str}", transform=ax.transAxes, 
            fontsize=8, color='#666666', va='center')

def get_physical_data(player_name, player_opta_uuid, valgt_hold_navn, db_conn):
    target_ssiid = TEAMS.get(valgt_hold_navn, {}).get('ssid')
    if not target_ssiid:
        target_ssiid = '56fa29c7-3a48-4186-9d14-dbf45fbc78d9'

    clean_id = str(player_opta_uuid).lower().replace('p', '').strip()
    navne_dele = [n.strip() for n in player_name.split(' ') if len(n.strip()) > 2]
    name_conditions = " OR ".join([f"PLAYER_NAME ILIKE '%{n}%'" for n in navne_dele])

    sql = f"""
        SELECT 
            p.MATCH_DATE,
            ANY_VALUE(p.MATCH_TEAMS) as MATCH_TEAMS,
            MAX(p.MINUTES) as MINUTES,
            SUM(p.DISTANCE) as DISTANCE,
            SUM(p."HIGH SPEED RUNNING") as HSR,
            SUM(p.SPRINTING) as SPRINTING,
            MAX(p.TOP_SPEED) as TOP_SPEED,
            SUM(p.NO_OF_HIGH_INTENSITY_RUNS) as HI_RUNS
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS p
        WHERE (({name_conditions}) OR ("optaId" LIKE '%{clean_id}%'))
          AND p.MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'
          AND p.MATCH_SSIID IN (
              SELECT MATCH_SSIID 
              FROM {DB}.SECONDSPECTRUM_GAME_METADATA
              WHERE HOME_SSIID = '{target_ssiid}' 
                 OR AWAY_SSIID = '{target_ssiid}'
          )
        GROUP BY p.MATCH_DATE, p.PLAYER_NAME
        ORDER BY p.MATCH_DATE DESC
    """
    return db_conn.query(sql)

def vis_side(dp=None):
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 16px !important; text-align: center; font-weight: bold !important; width: 100%; }
        [data-testid="stMetricLabel"] { font-size: 10px !important; text-align: center; width: 100%; }
        [data-testid="stMetric"] { display: flex; flex-direction: column; align-items: center; }
        .player-header { font-size: 20px; font-weight: bold; margin-bottom: 10px; color: #1E1E1E; }
        </style>
        """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn: return

    # 1. HOLDVALG
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
    
    # Robust mapping: fjerner 't' fra UUIDs for at sikre match
    mapping_lookup = {str(info['opta_uuid']).lower().replace('t', ''): name for name, info in TEAMS.items() if 'opta_uuid' in info}

    team_map = {}
    if df_teams_raw is not None:
        for _, r in df_teams_raw.iterrows():
            uuid_clean = str(r['CONTESTANTHOME_OPTAUUID']).lower().replace('t','')
            if uuid_clean in mapping_lookup:
                team_map[mapping_lookup[uuid_clean]] = r['CONTESTANTHOME_OPTAUUID']

    col_spacer_top, col_h_hold, col_h_spiller = st.columns([2, 1.2, 1.2])
    
    if not team_map:
        st.error("Kunne ikke mappe hold-UUIDs. Tjek din TEAMS mapping.")
        return

    valgt_hold = col_h_hold.selectbox("Hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid_hold = team_map[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid_hold)

    # 2. HENT DATA (Med rettet MINUTE kolonne)
    with st.spinner("Henter spillerdata..."):
        sql = f"""
            SELECT 
                e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, 
                TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as VISNINGSNAVN, 
                e.PLAYER_OPTAUUID, e.EVENT_OUTCOME as OUTCOME,
                e.EVENT_TIMEMIN AS EVENT_MINUTE,
                e.EVENT_CONTESTANT_OPTAUUID,
                m.CONTESTANTHOME_OPTAUUID as HOMECONTESTANT_OPTAUUID,
                m.CONTESTANTHOME_NAME as HOMECONTESTANT_NAME,
                m.CONTESTANTAWAY_OPTAUUID as AWAYCONTESTANT_OPTAUUID,
                m.CONTESTANTAWAY_NAME as AWAYCONTESTANT_NAME,
                TO_CHAR(e.EVENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS') as EVENT_TIMESTAMP_STR,
                LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS,
                MAX(CASE WHEN q.QUALIFIER_QID = 321 THEN TRY_TO_DOUBLE(q.QUALIFIER_VALUE) ELSE 0 END) as XG
            FROM {DB}.OPTA_EVENTS e
            JOIN (SELECT DISTINCT PLAYER_OPTAUUID, FIRST_NAME, LAST_NAME FROM {DB}.OPTA_PLAYERS WHERE FIRST_NAME IS NOT NULL) p 
                ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
            JOIN {DB}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
            LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid_hold}' 
            AND e.EVENT_TIMESTAMP >= '2025-07-01'
            GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13
        """
        df_all = conn.query(sql)
        
        if df_all is None or df_all.empty:
            st.warning("Ingen hændelsesdata fundet for dette hold.")
            return

        df_all = df_all.dropna(subset=['VISNINGSNAVN'])
        df_all['EVENT_TIMESTAMP'] = pd.to_datetime(df_all['EVENT_TIMESTAMP_STR'])
        df_all['qual_list'] = df_all['QUALIFIERS'].fillna('').str.split(',')
        df_all['Action_Label'] = df_all.apply(get_action_label, axis=1)

    spiller_liste = sorted(df_all['VISNINGSNAVN'].unique())
    valgt_spiller = col_h_spiller.selectbox("Spiller", spiller_liste, label_visibility="collapsed")
    valgt_player_uuid = df_all[df_all['VISNINGSNAVN'] == valgt_spiller]['PLAYER_OPTAUUID'].iloc[0]
    df_spiller = df_all[df_all['VISNINGSNAVN'] == valgt_spiller].copy()

    t_pitch, t_phys, t_stats, t_compare = st.tabs(["Spillerprofil", "Fysisk data", "Statistik", "Sammenligning"])

    with t_pitch:
        # --- UI Layout ---
        # Vi holder fast i din opdeling, men gør venstre side mere ren
        c_stats_side, c_buffer, c_pitch_side = st.columns([1, 0.05, 2.2])

        # 1. VENSTRE SIDE: Top Aktioner (Forenklet visning)
        with c_stats_side:
            st.markdown('<p class="player-header">Top Aktioner</p>', unsafe_allow_html=True)
            
            # Vi tæller alle aktioner for spilleren
            if not df_spiller.empty:
                # Vi bruger 'Action_Label' til at gruppere de mest hyppige handlinger
                top_actions = df_spiller['Action_Label'].value_counts().head(10)
                
                for action, count in top_actions.items():
                    # Opretter rækker der minder om dem i Skærmbillede 2026-05-04 kl. 20.58.53.png
                    col_txt, col_num = st.columns([3, 1])
                    with col_txt:
                        st.markdown(f"**{action}**")
                    with col_num:
                        st.markdown(f'<div style="text-align: right;">{count}</div>', unsafe_allow_html=True)
                    st.markdown("<hr style='margin: 5px 0; opacity: 0.2;'>", unsafe_allow_html=True)
            else:
                st.info("Ingen hændelser fundet for denne spiller.")

        # 2. HØJRE SIDE: Bane-visualisering med Overlay-fix
        with c_pitch_side:
            descriptions = {
                "Heatmap": "Viser spillerens generelle bevægelsesmønster.",
                "Berøringer": "Alle aktioner i kontakt med bolden.",
                "Afslutninger": "Oversigt over skudforsøg (Mål = kvadrat).",
                "Erobringer": "Tacklinger, interceptions og recoveries."
            }
            
            # Menu og beskrivelse i toppen
            c_side_spacer, c_desc_col, c_menu_col = st.columns([0.1, 2.1, 1.0])
            with c_menu_col:
                visning = st.selectbox("Visning", list(descriptions.keys()), key="pitch_view_sel", label_visibility="collapsed")
            with c_desc_col:
                st.markdown(f'<div style="text-align: right; margin-top: 8px;"><span style="color: #666; font-size: 0.85rem;">{descriptions.get(visning)}</span></div>', unsafe_allow_html=True)

            # Pitch setup
            pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
            fig_static, ax = pitch.draw(figsize=(10, 7))
            draw_player_info_box(ax, hold_logo, valgt_spiller, CURRENT_SEASON, visning)

            df_plot = df_spiller.dropna(subset=['EVENT_X', 'EVENT_Y'])

            if visning == "Afslutninger":
                # Vi filtrerer skud-hændelser
                d = df_plot[df_plot['EVENT_TYPEID'].isin([13, 14, 15, 16])].copy()
                if not d.empty:
                    # Statisk tegning (Matplotlib)
                    goals = d[d['EVENT_TYPEID'] == 16]
                    misses = d[d['EVENT_TYPEID'] != 16]
                    ax.scatter(misses.EVENT_X, misses.EVENT_Y, color='grey', s=80, edgecolors='black', alpha=0.4)
                    ax.scatter(goals.EVENT_X, goals.EVENT_Y, color='#cc0000', s=150, marker='s', edgecolors='black', zorder=5)

                    # Interaktivt lag (Plotly) - Dette sikrer hover-effekt
                    fig_overlay = go.Figure()
                    fig_overlay.add_trace(go.Scatter(
                        x=d.EVENT_X, y=d.EVENT_Y,
                        mode='markers',
                        marker=dict(size=22, color='rgba(0,0,0,0)'),
                        hovertemplate="<b>Type: %{customdata[0]}</b><br>Resultat: %{customdata[1]}<extra></extra>",
                        customdata=np.stack((d['Action_Label'], d['OUTCOME']), axis=-1)
                    ))
                    fig_overlay.update_layout(
                        xaxis=dict(range=[0, 100], visible=False, fixedrange=True),
                        yaxis=dict(range=[0, 100], visible=False, fixedrange=True),
                        margin=dict(l=0, r=0, t=0, b=0),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
                    )
                    
                    # Sammenfletning af de to lag
                    st.markdown('<div style="position: relative;">', unsafe_allow_html=True)
                    st.pyplot(fig_static)
                    st.markdown('<div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 10;">', unsafe_allow_html=True)
                    st.plotly_chart(fig_overlay, use_container_width=True, config={'displayModeBar': False})
                    st.markdown('</div></div>', unsafe_allow_html=True)
                else:
                    st.pyplot(fig_static)

            elif visning == "Erobringer":
                # Defensive aktioner (Type 7, 8, 12, 49)
                d_def = df_plot[df_plot['EVENT_TYPEID'].isin([7, 8, 12, 49])]
                ax.scatter(d_def.EVENT_X, d_def.EVENT_Y, color='#e67e22', s=80, edgecolors='black', alpha=0.7)
                st.pyplot(fig_static, use_container_width=True)

            elif visning == "Heatmap":
                pitch.kdeplot(df_plot.EVENT_X, df_plot.EVENT_Y, ax=ax, cmap='Blues', fill=True, alpha=0.6, levels=50)
                st.pyplot(fig_static, use_container_width=True)

            elif visning == "Berøringer":
                d_touch = df_plot[df_plot['EVENT_TYPEID'].isin([1, 3, 7, 10, 11, 12, 13, 14, 15, 16])]
                ax.scatter(d_touch.EVENT_X, d_touch.EVENT_Y, color='#084594', s=40, edgecolors='white', alpha=0.5)
                st.pyplot(fig_static, use_container_width=True)
                
    with t_phys:
        df_phys = get_physical_data(valgt_spiller, valgt_player_uuid, valgt_hold, conn)
        if df_phys is not None and not df_phys.empty:
            df_phys['MATCH_DATE'] = pd.to_datetime(df_phys['MATCH_DATE'])
            df_phys = df_phys.sort_values('MATCH_DATE', ascending=False)
            avg_dist = df_phys['DISTANCE'].mean()
            avg_hsr = df_phys['HSR'].mean()
            latest = df_phys.iloc[0]

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Seneste Distance", f"{round(latest['DISTANCE']/1000, 2)} km", delta=f"{round((latest['DISTANCE'] - avg_dist)/1000, 2)} km")
            m2.metric("HSR Meter", f"{int(latest['HSR'])} m", delta=f"{int(latest['HSR'] - avg_hsr)} m")
            m3.metric("Topfart", f"{round(latest['TOP_SPEED'], 1)} km/t")
            m4.metric("Højintense Akt.", int(latest['HI_RUNS']))

            t_sub_log, t_sub_charts = st.tabs(["Kampoversigt", "Grafer"])

            with t_sub_charts:
                cat_choice = st.segmented_control("Vælg metrik", options=["HSR (m)", "Sprint (m)", "Distance (km)", "Topfart (km/t)"], default="HSR (m)", key="phys_graph_control")
                mapping = {"HSR (m)": ("HSR", 1, "m"), "Sprint (m)": ("SPRINTING", 1, "m"), "Distance (km)": ("DISTANCE", 1000, "km"), "Topfart (km/t)": ("TOP_SPEED", 1, "km/t")}
                col, div, suffix = mapping[cat_choice]

                df_chart = df_phys[df_phys['MATCH_DATE'] >= '2025-07-01'].copy()
                df_chart = df_chart.drop_duplicates(subset=['MATCH_DATE', 'MATCH_TEAMS'])
                df_chart = df_chart.sort_values('MATCH_DATE', ascending=True)

                if not df_chart.empty:
                    def get_opponent(teams_str, my_team):
                        if not teams_str: return "?"
                        parts = [p.strip() for p in teams_str.split('-')]
                        if len(parts) < 2: return teams_str
                        return parts[1] if parts[0].lower() in my_team.lower() else parts[0]

                    df_chart['Opponent'] = df_chart['MATCH_TEAMS'].apply(lambda x: get_opponent(x, valgt_hold))
                    df_chart['Label'] = df_chart['Opponent'] + "<br>" + df_chart['MATCH_DATE'].dt.strftime('%d/%m')
                    y_vals = df_chart[col] / div
                    season_avg = y_vals.mean()

                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=df_chart['Label'], 
                        y=y_vals,
                        text=y_vals.apply(lambda x: f"{x:.0f}" if x > 100 else f"{x:.1f}"),
                        textposition='outside', 
                        marker_color='#cc0000', 
                        textfont=dict(size=9, color="black"),
                        cliponaxis=False
                    ))

                    fig.add_shape(type="line", x0=-0.5, x1=len(df_chart)-0.5, y0=season_avg, y1=season_avg, 
                                 line=dict(color="#D3D3D3", width=2, dash="dash"))

                    fig.update_layout(
                        plot_bgcolor="white", 
                        height=400, 
                        margin=dict(t=50, b=80, l=10, r=10),
                        xaxis=dict(showgrid=False, tickangle=-45, tickfont=dict(size=10), type='category'),
                        yaxis=dict(showgrid=True, gridcolor='#f0f0f0', showticklabels=False, zeroline=False, range=[0, y_vals.max() * 1.3]),
                        showlegend=False
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.info("Ingen fysiske data fundet for denne sæson.")

            with t_sub_log:
                st.data_editor(df_phys, hide_index=True, use_container_width=True, disabled=True)

if __name__ == "__main__":
    vis_side()
