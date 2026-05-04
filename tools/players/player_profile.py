import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from mplsoccer import Pitch
from data.data_load import _get_snowflake_conn
# Vi bruger din globale kontrol fra team_mapping.py
from data.utils.team_mapping import TEAMS, COMPETITIONS, COMPETITION_NAME, TOURNAMENTCALENDAR_NAME
import requests
from PIL import Image
from io import BytesIO

# --- IMPORT FRA MAPPING ---
from data.utils.mapping import (
    OPTA_EVENT_TYPES, 
    OPTA_QUALIFIERS,
    get_action_label
)

# --- KONFIGURATION (Fra din globale kontrol) ---
DB = "KLUB_HVIDOVREIF.AXIS"
SEASONNAME = TOURNAMENTCALENDAR_NAME
# Vi finder den præcise OPTA UUID for ligaen (fx 1. Division)
CURRENT_COMP_UUID = COMPETITIONS[COMPETITION_NAME]["COMPETITION_OPTAUUID"]

# --- HJÆLPEFUNKTIONER (ALLE BEVARET) ---
@st.cache_data(ttl=3600)
def get_logo_img(url):
    if not url: return None
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except: return None

def draw_player_info_box(ax, logo, player_name, season, view_name):
    """Tegner din originale mørkeblå info-boks"""
    ax.add_patch(plt.Rectangle((1, 85), 38, 14, color='#003366', alpha=0.9, zorder=10))
    ax.text(12, 95, str(player_name).upper(), color='white', fontsize=10, fontweight='bold', zorder=11)
    ax.text(12, 91, f"{season} | {view_name}", color='white', fontsize=8, alpha=0.8, zorder=11)
    if logo:
        logo_arr = np.array(logo)
        newax = ax.inset_axes([0.02, 0.87, 0.08, 0.1], zorder=12)
        newax.imshow(logo_arr)
        newax.axis('off')

def create_relative_donut(player_val, max_val, label, color="#003366"):
    """Din originale logik til sammenligning med truppens maks"""
    base_max = max(max_val, player_val, 1)
    reminder = max(0, base_max - player_val)
    fig = go.Figure(go.Pie(
        values=[player_val, reminder],
        hole=0.7,
        marker_colors=[color, "#EEEEEE"],
        textinfo='none',
        hoverinfo='none'
    ))
    pct = int((player_val / base_max) * 100) if base_max > 0 else 0
    fig.update_layout(
        showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=130, width=130,
        annotations=[dict(text=f"{player_val}<br><span style='font-size:10px;'>{pct}%</span>", 
                     x=0.5, y=0.5, font_size=14, showarrow=False, font_family="Arial Black")]
    )
    return fig

def get_physical_data(player_name, player_opta_uuid, valgt_hold_navn, db_conn):
    """Henter dine fysiske stats via Second Spectrum logikken"""
    # Vi henter ssid fra din TEAMS mapping
    target_ssiid = TEAMS.get(valgt_hold_navn, {}).get('ssid')
    if not target_ssiid: return None
    
    clean_id = str(player_opta_uuid).lower().replace('p', '').strip()
    navne_dele = [n.strip() for n in player_name.split(' ') if len(n.strip()) > 2]
    name_conditions = " OR ".join([f"PLAYER_NAME ILIKE '%{n}%'" for n in navne_dele])

    sql_phys = f"""
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
    return db_conn.query(sql_phys)

def vis_side(dp=None):
    # CSS
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 16px !important; text-align: center; font-weight: bold !important; width: 100%; }
        [data-testid="stMetricLabel"] { font-size: 10px !important; text-align: center; width: 100%; }
        .player-header { font-size: 22px; font-weight: bold; margin-bottom: 10px; color: #1E1E1E; }
        </style>
        """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn: return

    # 1. HOLDVALG (Baseret på din globale COMPETITION_NAME)
    hold_muligheder = [name for name, info in TEAMS.items() if info.get("league") == COMPETITION_NAME]
    
    col_spacer, col_h_hold, col_h_spiller = st.columns([2, 1.2, 1.2])
    valgt_hold_navn = col_h_hold.selectbox("Hold", sorted(hold_muligheder), label_visibility="collapsed")
    
    hold_info = TEAMS[valgt_hold_navn]
    valgt_hold_uuid = hold_info["opta_uuid"]
    hold_logo = get_logo_img(hold_info["logo"])

    # 2. HENT SPILLERDATA (Præcis som din original med joins og qualifiers)
    sql_all = f"""
        SELECT 
            e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, 
            TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as VISNINGSNAVN, 
            e.PLAYER_OPTAUUID, e.EVENT_OUTCOME as OUTCOME,
            TO_CHAR(e.EVENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS') as EVENT_TIMESTAMP_STR,
            LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
        FROM {DB}.OPTA_EVENTS e
        JOIN (SELECT DISTINCT PLAYER_OPTAUUID, FIRST_NAME, LAST_NAME FROM {DB}.OPTA_PLAYERS WHERE FIRST_NAME IS NOT NULL) p 
            ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
        LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
        WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_hold_uuid}' 
        AND e.EVENT_TIMESTAMP >= '2025-07-01'
        GROUP BY 1, 2, 3, 4, 5, 6, 7
    """
    
    df_all = conn.query(sql_all)
    if df_all is None or df_all.empty:
        st.warning("Ingen data fundet.")
        return

    df_all['qual_list'] = df_all['QUALIFIERS'].fillna('').str.split(',')
    df_all['Action_Label'] = df_all.apply(get_action_label, axis=1)

    spiller_liste = sorted(df_all['VISNINGSNAVN'].unique())
    valgt_spiller = col_h_spiller.selectbox("Spiller", spiller_liste, label_visibility="collapsed")
    valgt_player_uuid = df_all[df_all['VISNINGSNAVN'] == valgt_spiller]['PLAYER_OPTAUUID'].iloc[0]
    df_spiller = df_all[df_all['VISNINGSNAVN'] == valgt_spiller].copy()

    # 3. TABS
    t_profile, t_pitch, t_phys = st.tabs(["Spillerprofil", "Aktioner", "Fysisk data"])

    with t_profile:
        # Din donut-sammenligning
        truppen_stats = df_all.groupby('VISNINGSNAVN').agg(
            raw_pasninger=('EVENT_TYPEID', lambda x: (x == 1).sum())
        )
        maks_pas = truppen_stats['raw_pasninger'].max()
        
        col_l, col_r = st.columns([1, 3.5])
        with col_l:
            st.markdown(f'<div class="player-header">{valgt_spiller}</div>', unsafe_allow_html=True)
            if hold_logo: st.image(hold_logo, width=100)
        
        with col_r:
            pas_spiller = len(df_spiller[df_spiller['EVENT_TYPEID'] == 1])
            st.plotly_chart(create_relative_donut(pas_spiller, maks_pas, "Pasninger"), config={'displayModeBar': False})

    with t_pitch:
        pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
        fig, ax = pitch.draw(figsize=(10, 7))
        draw_player_info_box(ax, hold_logo, valgt_spiller, SEASONNAME, "Aktioner")
        
        df_coords = df_spiller.dropna(subset=['EVENT_X', 'EVENT_Y'])
        if not df_coords.empty:
            pitch.kdeplot(df_coords.EVENT_X, df_coords.EVENT_Y, ax=ax, cmap='Blues', fill=True, alpha=0.5)
        st.pyplot(fig)

    with t_phys:
        df_phys = get_physical_data(valgt_spiller, valgt_player_uuid, valgt_hold_navn, conn)
        if df_phys is not None and not df_phys.empty:
            st.dataframe(df_phys, use_container_width=True)

if __name__ == "__main__":
    vis_side()
