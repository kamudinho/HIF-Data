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

def plot_custom_pitch(df, event_ids, title, zone='full', cmap='Reds', logo=None):
    """Genererer baneplot med korrekt zoom-håndtering og koordinat-swap."""
    plot_data = df[df['EVENT_TYPEID'].astype(str).isin([str(i) for i in event_ids])].copy()
    
    # Vi bruger VerticalPitch (Y er længden, X er bredden)
    pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
    fig, ax = pitch.draw(figsize=(5, 7))

    # 1. Tegn heatmap (KDE)
    if not plot_data.empty:
        # Efter swappet i fetch_data: 
        # plot_data.EVENT_X er nu bredde, plot_data.EVENT_Y er nu længde
        pitch.kdeplot(plot_data.EVENT_X, plot_data.EVENT_Y, ax=ax, cmap=cmap, fill=True, alpha=0.5, levels=100, linewidths=1.2)

    # 2. Tegn logo og tekst
    if logo:
        if zone == 'up': 
            logo_pos = [0.04, 0.03, 0.08, 0.08]
            text_y = 0.05
        else: 
            logo_pos = [0.04, 0.90, 0.08, 0.08]
            text_y = 0.97
        ax_l = ax.inset_axes(logo_pos, transform=ax.transAxes)
        ax_l.imshow(logo)
        ax_l.axis('off')
    else:
        text_y = 0.97

    ax.text(0.94, text_y, title, transform=ax.transAxes, fontsize=6, fontweight='bold', ha='right', va='top')

    # 3. ZOOM (Skal ske efter alt andet er tegnet)
    # Da vi har swappet, er det Y-aksen (længden), vi zoomer på
    if zone == 'up':
        ax.set_ylim(50, 100) # Modstanderens mål (øverst på banen)
    elif zone == 'down':
        ax.set_ylim(0, 50)   # Eget mål (nederst på banen)
    
    return fig

# ---------------------------------------------------------------------------
# DATAHENTNING
# ---------------------------------------------------------------------------

@st.cache_data(ttl=900, show_spinner=False)
def resolve_player_names(df, conn):
    """Matcher Opta UUIDs til navne via database/mapping."""
    if df.empty: return df['PLAYER_OPTAUUID']
    uuids = tuple(df['PLAYER_OPTAUUID'].unique())
    sql = f"SELECT PLAYER_OPTAUUID, FIRST_NAME, LAST_NAME FROM {DB}.OPTA_MATCH_LINEUPS WHERE PLAYER_OPTAUUID IN {uuids}"
    try:
        mapping_df = conn.query(sql, ttl=0)
        if mapping_df is not None and not mapping_df.empty:
            mapping_df['FULL_NAME'] = mapping_df['FIRST_NAME'].fillna('') + ' ' + mapping_df['LAST_NAME'].fillna('')
            name_map = dict(zip(mapping_df['PLAYER_OPTAUUID'], mapping_df['FULL_NAME']))
            return df['PLAYER_OPTAUUID'].map(name_map).fillna(df['PLAYER_OPTAUUID'].astype(str))
    except:
        pass
    return df['PLAYER_OPTAUUID'].astype(str)

@st.cache_data(ttl=900, show_spinner=False)
def fetch_event_data(valgt_uuid, match_ids):
    if not match_ids: return pd.DataFrame()
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
    df = conn.query(sql, ttl=0)
    if df is None or df.empty: return pd.DataFrame()

    # --- DET KORREKTE SWAP ---
    # Da Snowflake X = Længde og Y = Bredde, 
    # bytter vi om så X = Bredde og Y = Længde til mplsoccer
    df[['EVENT_X', 'EVENT_Y']] = df[['EVENT_Y', 'EVENT_X']].values

    df['PLAYER_NAME'] = resolve_player_names(df, conn)
    df['qual_list'] = df['QUALIFIERS'].fillna('').str.split(',')
    df['Action_Label'] = df.apply(get_action_label, axis=1)
    df = df.dropna(subset=['Action_Label'])
    return df

@st.cache_data(ttl=900, show_spinner=False)
def fetch_goal_sequences(valgt_uuid, match_ids):
    if not match_ids: return pd.DataFrame()
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
        ORDER BY e.EVENT_TIMESTAMP ASC
    """
    try:
        df = conn.query(sql, ttl=0)
    except Exception: 
        return pd.DataFrame()
        
    if df is None or df.empty: return pd.DataFrame()
    
    # --- DET KORREKTE SWAP ---
    df[['EVENT_X', 'EVENT_Y']] = df[['EVENT_Y', 'EVENT_X']].values

    df['PLAYER_NAME'] = resolve_player_names(df, conn)
    df['qual_list'] = df['QUALIFIERS'].fillna('').str.split(',')
    return df
