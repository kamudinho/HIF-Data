import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS
import requests
from PIL import Image
from io import BytesIO
from data.utils.mapping import get_action_label

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '335', '328', '329', '43319', '331')"

@st.cache_data(ttl=3600)
def get_logo_img(opta_uuid):
    if not opta_uuid: return None
    url = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), None)
    if not url: return None
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except: return None

def draw_player_info_box(ax, team_logo, player_name, season_str, category_str):
    if team_logo:
        ax_l = ax.inset_axes([0.02, 0.88, 0.07, 0.07], transform=ax.transAxes)
        ax_l.imshow(team_logo); ax_l.axis('off')
    ax.text(0.10, 0.92, str(player_name).upper(), transform=ax.transAxes, 
            fontsize=10, fontweight='bold', color='black', va='center')
    ax.text(0.10, 0.89, f"{season_str} | {category_str}", transform=ax.transAxes, 
            fontsize=8, color='#666666', va='center')

def vis_side(dp=None):
    st.markdown("""
        <style>
        [data-testid="stMetric"] { text-align: center; display: flex; flex-direction: column; align-items: center; }
        [data-testid="stMetricValue"] { font-size: 18px !important; }
        [data-testid="stMetricLabel"] { font-size: 11px !important; }
        </style>
        """, unsafe_allow_html=True)
    
    conn = _get_snowflake_conn()
    if not conn: return

    # 1. Team Mapping (Vasker 't' og sikrer match)
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
    
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    team_map = {}
    for _, row in df_teams_raw.iterrows():
        uuid_clean = str(row['CONTESTANTHOME_OPTAUUID']).lower().replace('t', '')
        if uuid_clean in mapping_lookup:
            team_map[mapping_lookup[uuid_clean]] = row['CONTESTANTHOME_OPTAUUID']

    col_spacer, col_hold = st.columns([3.5, 1])
    valgt_hold = col_hold.selectbox("Vælg hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid)

    # 2. Hent Data - Med navne-oversættelse og koordinat-vask
    with st.spinner("Henter data..."):
        sql = f"""
            SELECT 
                e.EVENT_X, 
                e.EVENT_Y, 
                e.EVENT_TYPEID, 
                -- Oversætter navn ved at klistre First og Last name sammen
                TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as VISNINGSNAVN, 
                e.MATCH_OPTAUUID, 
                e.EVENT_OUTCOME as OUTCOME,
                LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
            FROM {DB}.OPTA_EVENTS e
            -- JOIN på bindeleddet og fjern dubletter i spiller-tabellen
            LEFT JOIN (
                SELECT DISTINCT PLAYER_OPTAUUID, FIRST_NAME, LAST_NAME 
                FROM {DB}.OPTA_PLAYERS
            ) p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
            LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' 
            AND e.EVENT_TIMESTAMP >= '2025-07-01'
            -- Vigtigt: Hold koordinater på banen
            AND e.EVENT_X BETWEEN 0 AND 100
            AND e.EVENT_Y BETWEEN 0 AND 100
            AND p.FIRST_NAME IS NOT NULL
            GROUP BY 1, 2, 3, 4, 5, 6
        """
        df_all_h = conn.query(sql)
        
        if df_all_h is not None and not df_all_h.empty:
            df_all_h['qual_list'] = df_all_h['QUALIFIERS'].fillna('').str.split(',')
            df_all_h['Action_Label'] = df_all_h.apply(get_action_label, axis=1)
        else:
            st.warning(f"Ingen data fundet for {valgt_hold}.")
            return

    t_pitch, t_stats = st.tabs(["Spillerprofil", "Statistik"])

    with t_pitch:
        spiller_liste = sorted(df_all_h['VISNINGSNAVN'].unique())
        t_col1, t_col2, _ = st.columns([1, 1, 1])
        valgt_spiller = t_col1.selectbox("Vælg spiller", spiller_liste, label_visibility="collapsed")
        visning = t_col2.selectbox("Visning", ["Heatmap", "Berøringer", "Afslutninger", "Erobringer"], label_visibility="collapsed")
        
        df_spiller = df_all_h[df_all_h['VISNINGSNAVN'] == valgt_spiller].copy()
        
        kampe = df_spiller['MATCH_OPTAUUID'].nunique()
        p90_factor = 1 / kampe if kampe > 0 else 1

        c_left, c_right = st.columns([1, 2.2])
        
        with c_left:
            st.markdown(f"#### {valgt_spiller}")
            m1, m2 = st.columns(2)
            m1.metric("Aktioner/90", round(len(df_spiller)*p90_factor, 1))
            m2.metric("Kampe", kampe)
            
            st.markdown("---")
            df_akt = df_spiller[~df_spiller['Action_Label'].isin(['Pasning', 'Indkast'])]
            if not df_akt.empty:
                stats = df_akt.groupby('Action_Label').size().sort_values(ascending=False).head(8)
                for akt, count in stats.items():
                    st.markdown(f"<div style='display:flex; justify-content:space-between; font-size:12px;'><span>{akt}</span><b>{count}</b></div>", unsafe_allow_html=True)

        with c_right:
            pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
            fig, ax = pitch.draw(figsize=(10, 7))
            draw_player_info_box(ax, hold_logo, valgt_spiller, "2025/2026", visning)
            
            if not df_spiller.empty:
                x, y = df_spiller.EVENT_X.astype(float), df_spiller.EVENT_Y.astype(float)
                
                if visning == "Heatmap":
                    pitch.kdeplot(x, y, ax=ax, cmap='Blues', fill=True, alpha=0.6, levels=50)
                elif visning == "Berøringer":
                    pitch.scatter(x, y, ax=ax, color='#084594', s=40, edgecolors='white', alpha=0.5)
                elif visning == "Afslutninger":
                    mål = df_spiller[df_spiller['EVENT_TYPEID']==16]
                    skud = df_spiller[df_spiller['EVENT_TYPEID'].isin([13,14,15])]
                    pitch.scatter(skud.EVENT_X, skud.EVENT_Y, ax=ax, color='red', s=80, alpha=0.6)
                    pitch.scatter(mål.EVENT_X, mål.EVENT_Y, ax=ax, color='gold', s=150, marker='*', edgecolors='black')
                elif visning == "Erobringer":
                    erob = df_spiller[df_spiller['EVENT_TYPEID'].isin([7, 8, 12, 49])]
                    pitch.scatter(erob.EVENT_X, erob.EVENT_Y, ax=ax, color='orange', s=100, edgecolors='white')
            
            st.pyplot(fig, use_container_width=True)

if __name__ == "__main__":
    vis_side()
