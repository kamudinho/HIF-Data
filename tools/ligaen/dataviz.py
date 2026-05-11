import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from mplsoccer import Pitch, VerticalPitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS, COMPETITIONS, TOURNAMENTCALENDAR_NAME
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
LIGA_UUID = f"('{COMPETITIONS['1. Division']['COMPETITION_OPTAUUID']}')"
SEASON = TOURNAMENTCALENDAR_NAME  # Låst til 2025/2026 fra din mapping

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

def plot_logo_comparison(df_plot, metric_col, title):
    """
    Laver en visualisering hvor logoer er placeret på x-aksen baseret på performance.
    """
    fig = go.Figure()

    # Find logoer for hver modstander i df_plot
    for i, row in df_plot.iterrows():
        # Find modstanderens UUID
        opp_uuid = row['CONTESTANTAWAY_OPTAUUID'] if row['CONTESTANTHOME_OPTAUUID'] == row['VALGT_UUID'] else row['CONTESTANTHOME_OPTAUUID']
        logo_url = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == opp_uuid), None)
        
        if logo_url:
            fig.add_layout_image(
                dict(
                    source=logo_url,
                    xref="x", yref="y",
                    x=row[metric_col], y=0, # Alle på samme linje
                    sizex=4, sizey=4, # Juster størrelsen her
                    xanchor="center", yanchor="middle"
                )
            )

    # Tilføj et usynligt scatter-lag for at styre aksen og hover-effekt
    fig.add_trace(go.Scatter(
        x=df_plot[metric_col],
        y=[0] * len(df_plot),
        mode='markers',
        marker=dict(size=30, opacity=0), # Usynlige prikker
        hovertext=df_plot['OPP_NAME'] + "<br>Værdi: " + df_plot[metric_col].astype(str),
        hoverinfo="text"
    ))

    fig.update_layout(
        title=f"<b>{title}</b>",
        height=200,
        margin=dict(t=40, b=40, l=20, r=20),
        xaxis=dict(showgrid=True, gridcolor="#eee", zeroline=False, title="Antal aktioner"),
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False, range=[-2, 2]),
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

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

# --- 3. HOVEDFUNKTION ---
def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn: return

    # Hent hold kun fra 1. Division
    nbl_teams = {name: info['opta_uuid'] for name, info in TEAMS.items() if info.get('league') == "1. Division"}
    
    col_spacer_top, col_hold = st.columns([3.5, 1])
    valgt_hold = col_hold.selectbox("Vælg hold", sorted(list(nbl_teams.keys())), label_visibility="collapsed")
    valgt_uuid = nbl_teams[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid)

    with st.spinner("Henter 1. Division data..."):
        sql_res = f"""
            SELECT MATCH_LOCALDATE, CONTESTANTHOME_NAME, CONTESTANTAWAY_NAME, 
                   TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE, CONTESTANTHOME_OPTAUUID, 
                   CONTESTANTAWAY_OPTAUUID, MATCH_OPTAUUID 
            FROM {DB}.OPTA_MATCHINFO 
            WHERE (CONTESTANTHOME_OPTAUUID = '{valgt_uuid}' OR CONTESTANTAWAY_OPTAUUID = '{valgt_uuid}') 
            AND TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_UUID}
            AND TOURNAMENTCALENDAR_NAME = '{SEASON}'
            AND (MATCH_STATUS ILIKE '%Played%' OR MATCH_STATUS ILIKE '%Full%' OR MATCH_STATUS ILIKE '%Finish%') 
            ORDER BY MATCH_LOCALDATE DESC LIMIT 10
        """
        df_res = conn.query(sql_res)
        
        if df_res is not None and not df_res.empty:
            match_ids = tuple(df_res['MATCH_OPTAUUID'].tolist())
            m_ids_str = f"('{match_ids[0]}')" if len(match_ids) == 1 else str(match_ids)
            
            sql_all_h = f"""
                SELECT e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, 
                       TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME, 
                       e.MATCH_OPTAUUID, e.EVENT_TIMESTAMP, e.EVENT_OUTCOME as OUTCOME
                FROM {DB}.OPTA_EVENTS e
                JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
                WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' 
                AND e.MATCH_OPTAUUID IN {m_ids_str}
            """
            df_all_h = conn.query(sql_all_h)

            # --- BEREGNING AF VOLUMEN ---
            df_vol = df_all_h.groupby('MATCH_OPTAUUID').agg(
                P_tot=('EVENT_TYPEID', lambda x: (x == 1).sum()),
                A_tot=('EVENT_TYPEID', lambda x: x.isin([13,14,15,16]).sum()),
                E_tot=('EVENT_TYPEID', lambda x: x.isin([12, 127, 49]).sum()),
                D_tot=('EVENT_TYPEID', lambda x: x.isin([7, 8]).sum())
            ).reset_index()

            df_plot = df_res.merge(df_vol, on='MATCH_OPTAUUID', how='left').fillna(0)
            df_plot['OPP_NAME'] = df_plot.apply(lambda r: r['CONTESTANTAWAY_NAME'] if r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid else r['CONTESTANTHOME_NAME'], axis=1)
            df_plot['VALGT_UUID'] = valgt_uuid

            # --- TABS ---
            t1, t2 = st.tabs(["OVERSIGT", "DETALJER"])
            
            with t1:
                m_col1, m_spacer, m_col2 = st.columns([1.3, 0.1, 2.0])
                
                with m_col1:
                    st.write("**Seneste 10 kampe**")
                    df_res['RES'] = df_res.apply(lambda r: "D" if r['TOTAL_HOME_SCORE'] == r['TOTAL_AWAY_SCORE'] else ("W" if ((r['CONTESTANTHOME_OPTAUUID'] == valgt_uuid and r['TOTAL_HOME_SCORE'] > r['TOTAL_AWAY_SCORE']) or (r['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid and r['TOTAL_AWAY_SCORE'] > r['TOTAL_HOME_SCORE'])) else "L"), axis=1)
                    for _, row in df_res.iterrows():
                        draw_match_row(pd.to_datetime(row['MATCH_LOCALDATE']).strftime('%d/%m'), row['CONTESTANTHOME_NAME'], row['CONTESTANTHOME_OPTAUUID'], f"{int(row['TOTAL_HOME_SCORE'])}-{int(row['TOTAL_AWAY_SCORE'])}", row['CONTESTANTAWAY_NAME'], row['CONTESTANTAWAY_OPTAUUID'], row['RES'])

                with m_col2:
                    kat_map = {"Pasninger": 'P_tot', "Afslutninger": 'A_tot', "Erobringer": 'E_tot', "Dueller": 'D_tot'}
                    val1 = st.selectbox("Vælg parameter", list(kat_map.keys()))
                    
                    fig = plot_logo_comparison(df_plot, kat_map[val1], f"Hvidovre IF {val1} vs Modstandere")
                    st.plotly_chart(fig, use_container_width=True)

        else:
            st.error("Ingen data fundet for dette hold.")
