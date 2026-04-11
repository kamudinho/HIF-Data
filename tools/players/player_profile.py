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

# --- IMPORT FRA MAPPING ---
from data.utils.mapping import (
    OPTA_EVENT_TYPES, 
    OPTA_QUALIFIERS,
    get_action_label
)

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '335', '328', '329', '43319', '331')"

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

def vis_side(dp=None):
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 16px !important; }
        [data-testid="stMetricLabel"] { font-size: 10px !important; }
        .player-header { font-size: 20px; font-weight: bold; margin-bottom: 10px; color: #1E1E1E; }
        </style>
        """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn: return

    # 1. HENT HOLD MAPPING
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    team_map = {}
    for _, row in df_teams_raw.iterrows():
        uuid_clean = str(row['CONTESTANTHOME_OPTAUUID']).lower().replace('t', '')
        if uuid_clean in mapping_lookup:
            team_map[mapping_lookup[uuid_clean]] = row['CONTESTANTHOME_OPTAUUID']

    # --- TOPBAR ---
    col_spacer_top, col_h_hold, col_h_spiller = st.columns([2, 1.2, 1.2])
    valgt_hold = col_h_hold.selectbox("Hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid)

    # 2. HENT DATA
    with st.spinner("Indlæser data..."):
        sql = f"""
            SELECT 
                e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, 
                TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as VISNINGSNAVN, 
                e.MATCH_OPTAUUID, 
                TO_CHAR(e.EVENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS') as EVENT_TIMESTAMP_STR, 
                e.EVENT_OUTCOME as OUTCOME,
                LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
            FROM {DB}.OPTA_EVENTS e
            LEFT JOIN (SELECT DISTINCT PLAYER_OPTAUUID, FIRST_NAME, LAST_NAME FROM {DB}.OPTA_PLAYERS) p 
                ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
            LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' 
            AND e.EVENT_TIMESTAMP >= '2025-07-01'
            AND p.FIRST_NAME IS NOT NULL
            GROUP BY 1, 2, 3, 4, 5, 6, 7
        """
        df_all_h = conn.query(sql)
        if df_all_h is None or df_all_h.empty:
            st.warning("Ingen data fundet.")
            return

        df_all_h['EVENT_TIMESTAMP'] = pd.to_datetime(df_all_h['EVENT_TIMESTAMP_STR'])
        df_all_h['qual_list'] = df_all_h['QUALIFIERS'].fillna('').str.split(',')
        df_all_h['Action_Label'] = df_all_h.apply(get_action_label, axis=1)

    spiller_liste = sorted(df_all_h['VISNINGSNAVN'].unique())
    valgt_spiller = col_h_spiller.selectbox("Spiller", spiller_liste, label_visibility="collapsed")
    df_spiller = df_all_h[df_all_h['VISNINGSNAVN'] == valgt_spiller].copy()

    # --- TABS ---
    t_pitch, t_phys, t_stats, t_compare = st.tabs([
        "Spillerprofil", "Fysisk Data", "Statistik & Grafer", "Sammenligning"
    ])

    # --- TAB: SPILLERPROFIL ---
    with t_pitch:
        descriptions = {
            "Heatmap": "Bevægelsesmønster og intensitet på banen.",
            "Berøringer": "Alle tekniske aktioner med bolden.",
            "Afslutninger": "Skudforsøg (Mål = Guldstjerne).",
            "Mål": "Visualisering af spillerens scoringer.",
            "Skudassists": "Afleveringer til afslutning.",
            "Indlæg": "Bolde spillet ind i modstanderens felt.",
            "Erobringer": "Vundne tacklinger og interceptions."
        }

        # HOVEDLAYOUT
        c_stats_side, c_pitch_side = st.columns([1, 2.2])
        
        with c_stats_side:
            # NAVN OG METRICS
            st.markdown(f'<div class="player-header">{valgt_spiller}</div>', unsafe_allow_html=True)
            
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            m_col1.metric("Kampe", df_spiller['MATCH_OPTAUUID'].nunique())
            m_col2.metric("Aktioner", len(df_spiller))
            m_col3.metric("Mål", len(df_spiller[df_spiller['EVENT_TYPEID']==16]))
            m_col4.metric("Chancer", len(df_spiller[df_spiller['qual_list'].apply(lambda x: '210' in x)]))
            
            m_col3, m_col4 = st.columns(2)
            m_col3.metric("Mål", len(df_spiller[df_spiller['EVENT_TYPEID']==16]))
            m_col4.metric("Chancer", len(df_spiller[df_spiller['qual_list'].apply(lambda x: '210' in x)]))
            
            st.markdown("---")
            st.write("**Top 10: Aktioner**")
            df_filtreret = df_spiller[~df_spiller['Action_Label'].isin(['Pasning', 'Indkast'])]
            if not df_filtreret.empty:
                akt_stats = df_filtreret.groupby('Action_Label').agg(
                    Total=('OUTCOME', 'count')
                ).sort_values('Total', ascending=False).head(10)
                
                for akt, row in akt_stats.iterrows():
                    total = int(row['Total'])
                    st.markdown(f"<div style='display:flex; justify-content:space-between; font-size:13px; padding:3px 0; border-bottom:0.5px solid #eee;'><span>{akt}</span><b>{total}</b></div>", unsafe_allow_html=True)

        with c_pitch_side:
            # Kontrolpanel over banen i højre kolonne
            c_desc_sub, c_vis_sel_sub = st.columns([2, 1])
            visning = c_vis_sel_sub.selectbox("Vælg visning", list(descriptions.keys()), label_visibility="collapsed")
            c_desc_sub.write(f"**{visning}:** {descriptions[visning]}")
            
            # Bane tegnes
            pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
            fig, ax = pitch.draw(figsize=(10, 7))
            draw_player_info_box(ax, hold_logo, valgt_spiller, "2025/2026", visning)
            
            x, y = df_spiller.EVENT_X.astype(float), df_spiller.EVENT_Y.astype(float)
            if visning == "Heatmap":
                pitch.kdeplot(x, y, ax=ax, cmap='Blues', fill=True, alpha=0.6, levels=50)
            elif visning == "Berøringer":
                ax.scatter(x, y, color='#084594', s=40, edgecolors='white', alpha=0.5)
            elif visning == "Afslutninger":
                g = df_spiller[df_spiller['EVENT_TYPEID'] == 16]
                m = df_spiller[df_spiller['EVENT_TYPEID'].isin([13, 14, 15])]
                ax.scatter(m.EVENT_X, m.EVENT_Y, color='red', s=80, alpha=0.6)
                ax.scatter(g.EVENT_X, g.EVENT_Y, color='gold', s=150, marker='*', edgecolors='black')
            elif visning == "Erobringer":
                e = df_spiller[df_spiller['EVENT_TYPEID'].isin([7, 8, 12, 49])]
                ax.scatter(e.EVENT_X, e.EVENT_Y, color='orange', s=100, edgecolors='white')
            
            st.pyplot(fig, use_container_width=True)

    # --- TAB: STATISTIK & GRAFER ---
    with t_stats:
        st.subheader("Sæsonudvikling")
        if not df_spiller.empty:
            df_spiller['DATO'] = df_spiller['EVENT_TIMESTAMP'].dt.date
            trend = df_spiller.groupby('DATO').size()
            st.line_chart(trend)
            st.bar_chart(df_spiller['Action_Label'].value_counts())

if __name__ == "__main__":
    vis_side()
