# tools/hifanalyse/modstander_common.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from PIL import Image
from io import BytesIO
import requests
from mplsoccer import Pitch, VerticalPitch

from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import (
    TEAMS,
    SEASONS,
    COMPETITIONS,
    SEASON_LEAGUE_MAPPER,
    COMPETITION_NAME
)
from data.utils.mapping import get_action_label
from data.players.player_mapping import player_mapping, PLAYER_MAPPING

DB = "KLUB_HVIDOVREIF.AXIS"

if not player_mapping.optauuid_to_name:
    player_mapping._load_data(PLAYER_MAPPING)

# ---------------------------------------------------------------------------
# VISUELLE HJÆLPEFUNKTIONER
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def get_logo_img(opta_uuid):
    if not opta_uuid: return None
    url = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), None)
    if not url: return None
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except Exception: return None

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
    """Genererer baneplot med korrekt zoom-håndtering og koordinat-swap."""
    plot_data = df[df['EVENT_TYPEID'].astype(str).isin([str(i) for i in event_ids])].copy()
    
    pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
    fig, ax = pitch.draw(figsize=(5, 7))

    if not plot_data.empty:
        # Efter swappet i fetch-funktionerne: X=bredde, Y=længde
        pitch.kdeplot(plot_data.EVENT_X, plot_data.EVENT_Y, ax=ax, cmap=cmap, fill=True, alpha=0.5, levels=100, linewidths=1.2)

    if logo:
        if zone == 'up': logo_pos, text_y = [0.04, 0.03, 0.08, 0.08], 0.05
        else: logo_pos, text_y = [0.04, 0.90, 0.08, 0.08], 0.97
        ax_l = ax.inset_axes(logo_pos, transform=ax.transAxes); ax_l.imshow(logo); ax_l.axis('off')
    else:
        text_y = 0.97

    ax.text(0.94, text_y, title, transform=ax.transAxes, fontsize=6, fontweight='bold', ha='right', va='top')

    if zone == 'up':
        ax.set_ylim(50, 100)
    elif zone == 'down':
        ax.set_ylim(0, 50)
    
    return fig

def resolve_player_names(df, conn):
    if df.empty or 'PLAYER_OPTAUUID' not in df.columns:
        return df['PLAYER_NAME'] if 'PLAYER_NAME' in df.columns else pd.Series(dtype=object, index=df.index)
    uuid_col = df['PLAYER_OPTAUUID'].astype(str).str.strip()
    valid_uuid = df['PLAYER_OPTAUUID'].notna() & ~uuid_col.isin(["", "None", "nan"])
    resolved = uuid_col.where(valid_uuid).map(player_mapping.optauuid_to_name)
    if 'PLAYER_NAME' in df.columns:
        resolved = resolved.fillna(df['PLAYER_NAME'])
    resolved = resolved.fillna('Ukendt').replace(["", "None", "nan"], "Ukendt")
    return resolved

# ---------------------------------------------------------------------------
# SÆSON/HOLD-VÆLGER
# ---------------------------------------------------------------------------

def render_hold_saeson_selector():
    available_seasons = sorted(list(SEASONS.keys()), reverse=True)
    col_spacer_top, col_saeson, col_hold = st.columns([2.5, 1, 1])
    default_season_idx = available_seasons.index("2026/2027") if "2026/2027" in available_seasons else 0
    valgt_saeson = col_saeson.selectbox("Vælg sæson", available_seasons, index=default_season_idx, label_visibility="collapsed", key="saeson_select")
    
    LIGA_IDS_LIST = []
    for comp_data in COMPETITIONS.values():
        if "wyid" in comp_data and comp_data["wyid"]: LIGA_IDS_LIST.append(str(comp_data["wyid"]))
    
    if valgt_saeson in SEASONS:
        for comp_key, uuid_val in SEASONS[valgt_saeson].items():
            if uuid_val and "dummy" not in str(uuid_val).lower(): LIGA_IDS_LIST.append(str(uuid_val))
    
    liga_ids_sql = str(tuple(LIGA_IDS_LIST))
    allowed_team_names = SEASON_LEAGUE_MAPPER.get(valgt_saeson, {}).get(COMPETITION_NAME, [])
    
    team_map = {}
    for team_name, info in TEAMS.items():
        if not allowed_team_names or team_name in allowed_team_names:
            if "opta_uuid" in info and info["opta_uuid"]: team_map[team_name] = info["opta_uuid"]
    
    if not team_map: team_map = {name: info["opta_uuid"] for name, info in TEAMS.items() if info.get("opta_uuid")}
    
    sorted_teams = sorted(list(team_map.keys()))
    default_index = sorted_teams.index("Hvidovre") if "Hvidovre" in sorted_teams else 0
    valgt_hold_navn = col_hold.selectbox("Vælg hold", sorted_teams, index=default_index, label_visibility="collapsed", key="hold_select")
    
    valgt_uuid = team_map[valgt_hold_navn]
    hold_logo = get_logo_img(valgt_uuid)
    return valgt_saeson, valgt_hold_navn, valgt_uuid, hold_logo, liga_ids_sql

# ---------------------------------------------------------------------------
# DATAHENTNING
# ---------------------------------------------------------------------------

@st.cache_data(ttl=900, show_spinner=False)
def fetch_full_match_history(valgt_uuid, liga_ids_sql, valgt_saeson):
    conn = _get_snowflake_conn()
    sql = f"""
        SELECT MATCH_LOCALDATE, MATCH_DATE_FULL, CONTESTANTHOME_NAME, CONTESTANTAWAY_NAME,
               TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE, CONTESTANTHOME_OPTAUUID,
               CONTESTANTAWAY_OPTAUUID, MATCH_OPTAUUID, MATCH_STATUS
        FROM {DB}.OPTA_MATCHINFO
        WHERE (CONTESTANTHOME_OPTAUUID = '{valgt_uuid}' OR CONTESTANTAWAY_OPTAUUID = '{valgt_uuid}')
        AND TOURNAMENTCALENDAR_OPTAUUID IN {liga_ids_sql}
        AND TOURNAMENTCALENDAR_NAME = '{valgt_saeson}'
        ORDER BY COALESCE(MATCH_DATE_FULL, MATCH_LOCALDATE) ASC
    """
    return conn.query(sql, ttl=0)

@st.cache_data(ttl=900, show_spinner=False)
def fetch_event_data(valgt_uuid, match_ids):
    if not match_ids:
        return pd.DataFrame()

    conn = _get_snowflake_conn()
    m_ids_str = f"('{match_ids[0]}')" if len(match_ids) == 1 else str(tuple(match_ids))

    sql = f"""
       SELECT
           e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID,
           e.PLAYER_OPTAUUID,
           TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME,
           e.MATCH_OPTAUUID, e.EVENT_TIMESTAMP, e.EVENT_OUTCOME as OUTCOME,
           LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
       FROM {DB}.OPTA_EVENTS e
       LEFT JOIN (
           SELECT DISTINCT PLAYER_OPTAUUID, FIRST_NAME, LAST_NAME
           FROM {DB}.OPTA_MATCH_LINEUPS
           WHERE FIRST_NAME IS NOT NULL
       ) p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
       LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
       WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}'
       AND e.MATCH_OPTAUUID IN {m_ids_str}
       GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
   """
    df_all_h = conn.query(sql, ttl=0)
    if df_all_h is None or df_all_h.empty:
        return pd.DataFrame()

    # --- DEN RIGTIGE KOORDINAT FIX ---
    # 1. Vi swapper X og Y (for at få bredde og længde korrekt til VerticalPitch)
    # 2. Vi vender Y-aksen (100 - gammel_X), så modstanderens mål (100) lander i bunden (0)
    temp_x = df_all_h['EVENT_Y'].values
    temp_y = 100 - df_all_h['EVENT_X'].values
    df_all_h['EVENT_X'] = temp_x
    df_all_h['EVENT_Y'] = temp_y
    # ----------------------------------

    df_all_h['PLAYER_NAME'] = resolve_player_names(df_all_h, conn)
    df_all_h['qual_list'] = df_all_h['QUALIFIERS'].fillna('').str.split(',')
    df_all_h['Action_Label'] = df_all_h.apply(get_action_label, axis=1)
    df_all_h = df_all_h.dropna(subset=['Action_Label'])
    return df_all_h


@st.cache_data(ttl=900, show_spinner=False)
def fetch_goal_sequences(valgt_uuid, liga_ids_sql):
    conn = _get_snowflake_conn()
    sql = f"""
       WITH SeasonMatches AS (
           SELECT MATCH_OPTAUUID, CONTESTANTHOME_NAME, CONTESTANTAWAY_NAME,
                  MATCH_LOCALDATE, CONTESTANTHOME_OPTAUUID, CONTESTANTAWAY_OPTAUUID,
                  TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE
           FROM {DB}.OPTA_MATCHINFO
           WHERE TOURNAMENTCALENDAR_OPTAUUID IN {liga_ids_sql}
       ),
       TargetGoals AS (
           SELECT MATCH_OPTAUUID, EVENT_TIMESTAMP as G_TIME, EVENT_TIMEMIN as G_MIN
           FROM {DB}.OPTA_EVENTS
           WHERE EVENT_TYPEID = 16 AND EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}'
           AND MATCH_OPTAUUID IN (SELECT MATCH_OPTAUUID FROM SeasonMatches)
       )
       SELECT e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID,
              e.PLAYER_OPTAUUID,
              TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME,
              e.EVENT_TIMESTAMP, e.MATCH_OPTAUUID,
              m.MATCH_LOCALDATE, m.CONTESTANTHOME_NAME, m.CONTESTANTAWAY_NAME,
              m.CONTESTANTHOME_OPTAUUID, m.CONTESTANTAWAY_OPTAUUID,
              m.TOTAL_HOME_SCORE, m.TOTAL_AWAY_SCORE,
              tg.G_TIME as GOAL_TIME, tg.G_MIN as GOAL_MIN,
              LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
       FROM {DB}.OPTA_EVENTS e
       LEFT JOIN (
           SELECT DISTINCT PLAYER_OPTAUUID, FIRST_NAME, LAST_NAME
           FROM {DB}.OPTA_MATCH_LINE_UPS
           WHERE FIRST_NAME IS NOT NULL
       ) p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
       JOIN SeasonMatches m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
       INNER JOIN TargetGoals tg ON e.MATCH_OPTAUUID = tg.MATCH_OPTAUUID
           AND e.EVENT_TIMESTAMP >= DATEADD(second, -20, tg.G_TIME)
           AND e.EVENT_TIMESTAMP <= tg.G_TIME
       LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
       WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}'
       GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16
   """
    try:
        df_all_events = conn.query(sql, ttl=0)
    except Exception:
        return pd.DataFrame()

    if df_all_events is None or df_all_events.empty:
        return pd.DataFrame()

    # --- DEN RIGTIGE KOORDINAT FIX (Samme som ovenfor) ---
    temp_x = df_all_events['EVENT_Y'].values
    temp_y = 100 - df_all_events['EVENT_X'].values
    df_all_events['EVENT_X'] = temp_x
    df_all_events['EVENT_Y'] = temp_y
    # ----------------------------------------------------

    df_all_events['PLAYER_NAME'] = resolve_player_names(df_all_events, conn)
    df_all_events['qual_list'] = df_all_events['QUALIFIERS'].fillna('').str.split(',')
    return df_all_events

# ---------------------------------------------------------------------------
# PLACEHOLDER FOR MANGlENDE FUNKTION
# ---------------------------------------------------------------------------

@st.cache_data(ttl=900, show_spinner=False)
def fetch_zone_aggregates(valgt_uuid, match_ids, zone_type):
    """
    ADVARSEL: Denne funktion er en midlertidig placeholder for at undgå Import Error.
    Du skal finde den rigtige version af 'fetch_zone_aggregates' i din gamle backup 
    og erstatte denne placeholder med den rigtige kode.
    """
    return pd.DataFrame()
