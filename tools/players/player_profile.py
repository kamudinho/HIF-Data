import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from mplsoccer import Pitch
from data.data_load import _get_snowflake_conn
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

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
# Vi henter OPTA UUIDs fra din team_mapping.py via den globale kontrol
LIGA_IDS = f"('{COMPETITIONS[COMPETITION_NAME]['COMPETITION_OPTAUUID']}')"
CURRENT_SEASON = TOURNAMENTCALENDAR_NAME

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
    target_ssiid = TEAMS.get(valgt_hold_navn, {}).get('ssid', '56fa29c7-3a48-4186-9d14-dbf45fbc78d9')
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
        .player-header { font-size: 20px; font-weight: bold; margin-bottom: 10px; color: #1E1E1E; }
        .stat-row { display: flex; justify-content: space-between; font-size: 11px; padding: 5px 0; border-bottom: 0.5px solid #eee; }
        </style>
        """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn: return

    # 1. HOLDVALG
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
    mapping_lookup = {str(info['opta_uuid']).lower().replace('t', ''): name for name, info in TEAMS.items() if 'opta_uuid' in info}

    team_map = {}
    if df_teams_raw is not None:
        for _, r in df_teams_raw.iterrows():
            uuid_clean = str(r['CONTESTANTHOME_OPTAUUID']).lower().replace('t','')
            if uuid_clean in mapping_lookup:
                team_map[mapping_lookup[uuid_clean]] = r['CONTESTANTHOME_OPTAUUID']

    col_spacer_top, col_h_hold, col_h_spiller = st.columns([2, 1.2, 1.2])
    valgt_hold = col_h_hold.selectbox("Hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid_hold = team_map[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid_hold)

    # 2. HENT DATA
    sql = f"""
        SELECT 
            e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, 
            TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as VISNINGSNAVN, 
            e.PLAYER_OPTAUUID, e.EVENT_OUTCOME as OUTCOME,
            e.EVENT_TIMEMIN,
            TO_CHAR(e.EVENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS') as EVENT_TIMESTAMP_STR,
            LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS,
            MAX(CASE WHEN q.QUALIFIER_QID = 321 THEN TRY_TO_DOUBLE(q.QUALIFIER_VALUE) ELSE 0 END) as XG
        FROM {DB}.OPTA_EVENTS e
        JOIN (SELECT DISTINCT PLAYER_OPTAUUID, FIRST_NAME, LAST_NAME FROM {DB}.OPTA_PLAYERS WHERE FIRST_NAME IS NOT NULL) p 
            ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
        LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
        WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid_hold}' 
        AND e.EVENT_TIMESTAMP >= '2025-07-01'
        GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
    """
    df_all = conn.query(sql)
    if df_all is None or df_all.empty:
        st.warning("Ingen hændelsesdata fundet.")
        return

    df_all['qual_list'] = df_all['QUALIFIERS'].fillna('').str.split(',')
    df_all['Action_Label'] = df_all.apply(get_action_label, axis=1)

    spiller_liste = sorted(df_all['VISNINGSNAVN'].unique())
    valgt_spiller = col_h_spiller.selectbox("Spiller", spiller_liste, label_visibility="collapsed")
    valgt_player_uuid = df_all[df_all['VISNINGSNAVN'] == valgt_spiller]['PLAYER_OPTAUUID'].iloc[0]
    df_spiller = df_all[df_all['VISNINGSNAVN'] == valgt_spiller].copy()

    t_pitch, t_phys = st.tabs(["Spillerprofil", "Fysisk data"])

    with t_pitch:
        descriptions = {
            "Heatmap": "Bevægelsesmønster og intensitet.",
            "Berøringer": "Alle boldaktioner.",
            "Afslutninger": "Skudforsøg (Mål = kvadrat).",
            "Erobringer": "Tacklinger og interceptions."
        }
        
        c_stats_side, c_pitch_side = st.columns([1.2, 2.3])

        with c_stats_side:
            st.markdown(f'<div class="player-header">{valgt_spiller}</div>', unsafe_allow_html=True)
            
            # Progress bar integration (Pasninger)
            pas_df = df_spiller[df_spiller['EVENT_TYPEID'] == 1]
            pas_count = len(pas_df)
            pas_acc = (pas_df['OUTCOME'].sum() / pas_count) if pas_count > 0 else 0
            
            st.write(f"**Pasningspræcision: {int(pas_acc*100)}%**")
            st.progress(pas_acc)
            
            m1, m2 = st.columns(2)
            m1.metric("Aktioner", len(df_spiller))
            m2.metric("xG", f"{df_spiller['XG'].sum():.2f}")

            st.markdown("---")
            st.write("**Top Aktioner**")
            akt_stats = df_spiller.groupby('Action_Label').size().sort_values(ascending=False).head(6)
            for akt, count in akt_stats.items():
                rel_val = count / akt_stats.max()
                st.markdown(f"""
                    <div style="margin-bottom:8px;">
                        <div class="stat-row"><span>{akt}</span><b>{count}</b></div>
                        <div style="background:#eee; height:3px; border-radius:2px;">
                            <div style="background:#cc0000; width:{rel_val*100}%; height:100%;"></div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

        with c_pitch_side:
            visning = st.selectbox("Visning", list(descriptions.keys()), label_visibility="collapsed")
            pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
            fig, ax = pitch.draw(figsize=(10, 7))
            draw_player_info_box(ax, hold_logo, valgt_spiller, CURRENT_SEASON, visning)

            df_plot = df_spiller.dropna(subset=['EVENT_X', 'EVENT_Y'])
            if not df_plot.empty:
                if visning == "Heatmap":
                    pitch.kdeplot(df_plot.EVENT_X, df_plot.EVENT_Y, ax=ax, cmap='Blues', fill=True, alpha=0.6)
                elif visning == "Berøringer":
                    ax.scatter(df_plot.EVENT_X, df_plot.EVENT_Y, color='#084594', s=30, alpha=0.5)
                elif visning == "Afslutninger":
                    shots = df_plot[df_plot['EVENT_TYPEID'].isin([13, 14, 15, 16])]
                    ax.scatter(shots[shots['OUTCOME']==0].EVENT_X, shots[shots['OUTCOME']==0].EVENT_Y, color='grey', s=60, alpha=0.4)
                    ax.scatter(shots[shots['OUTCOME']==1].EVENT_X, shots[shots['OUTCOME']==1].EVENT_Y, color='#cc0000', s=100, marker='s')
                elif visning == "Erobringer":
                    erob = df_plot[df_plot['EVENT_TYPEID'].isin([7, 8, 12, 49])]
                    ax.scatter(erob.EVENT_X, erob.EVENT_Y, color='orange', s=80, edgecolors='black')
            st.pyplot(fig)

    with t_phys:
        df_phys = get_physical_data(valgt_spiller, valgt_player_uuid, valgt_hold, conn)
        if df_phys is not None and not df_phys.empty:
            st.dataframe(df_phys, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    vis_side()
