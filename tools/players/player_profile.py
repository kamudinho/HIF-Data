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

def get_physical_data(player_opta_uuid, db_conn):
    # Renser ID: fjerner 'p' og gør det til ren tekst
    clean_id = str(player_opta_uuid).lower().replace('p', '').strip()
    
    # Vi bruger LIKE for at være maksimalt fleksible over for ID-formatet i Snowflake
    sql = f"""
        SELECT 
            MATCH_DATE,
            MATCH_TEAMS,
            MINUTES,
            DISTANCE,
            "HIGH SPEED RUNNING" as HSR,
            SPRINTING,
            TOP_SPEED,
            AVERAGE_SPEED,
            NO_OF_HIGH_INTENSITY_RUNS as HI_RUNS
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE "optaId" LIKE '%{clean_id}%'
        ORDER BY MATCH_DATE DESC
    """
    return db_conn.query(sql)

def vis_side(dp=None):
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 16px !important; text-align: center; font-weight: bold !important; width: 100%; }
        [data-testid="stMetricLabel"] { font-size: 10px !important; text-align: center; width: 100%; }
        [data-testid="stMetric"] { display: flex; flex-direction: column; align-items: center; }
        .player-header { font-size: 20px; font-weight: bold; margin-bottom: 10px; color: #1E1E1E; }
        .debug-box { background-color: #f0f2f6; border-radius: 5px; padding: 10px; font-family: monospace; font-size: 12px; margin-bottom: 20px; border-left: 5px solid #ff4b4b; }
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
    valgt_uuid_hold = team_map[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid_hold)

    # 2. HENT DATA
    with st.spinner("Henter data..."):
        sql = f"""
            SELECT 
                e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, 
                TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as VISNINGSNAVN, 
                e.PLAYER_OPTAUUID,
                e.MATCH_OPTAUUID, 
                TO_CHAR(e.EVENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS') as EVENT_TIMESTAMP_STR, 
                e.EVENT_OUTCOME as OUTCOME,
                LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
            FROM {DB}.OPTA_EVENTS e
            LEFT JOIN (SELECT DISTINCT PLAYER_OPTAUUID, FIRST_NAME, LAST_NAME FROM {DB}.OPTA_PLAYERS) p 
                ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
            LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid_hold}' 
            AND e.EVENT_TIMESTAMP >= '2025-07-01'
            AND p.FIRST_NAME IS NOT NULL
            GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
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
    
    valgt_player_uuid = df_all_h[df_all_h['VISNINGSNAVN'] == valgt_spiller]['PLAYER_OPTAUUID'].iloc[0]
    df_spiller = df_all_h[df_all_h['VISNINGSNAVN'] == valgt_spiller].copy()

    # --- TABS ---
    t_pitch, t_phys, t_stats, t_compare = st.tabs([
        "Spillerprofil", "Fysisk Data", "Statistik & Grafer", "Sammenligning"
    ])

    # --- TAB: SPILLERPROFIL (t_pitch) ---
    with t_pitch:
        # (Pitch kode uændret...)
        descriptions = {"Heatmap": "Viser bevægelsesmønster.", "Berøringer": "Alle touch.", "Afslutninger": "Skudforsøg.", "Mål": "Scoringer.", "Skudassists": "Key passes.", "Indlæg": "Crosses.", "Erobringer": "Defensive aktioner."}
        df_filtreret = df_spiller[~df_spiller['Action_Label'].isin(['Pasning', 'Indkast'])]
        akt_stats = df_filtreret.groupby('Action_Label').agg(Total=('OUTCOME', 'count'), Succes=('OUTCOME', 'sum')).sort_values('Total', ascending=False) if not df_filtreret.empty else pd.DataFrame()
        c_stats_side, _, c_pitch_side = st.columns([1, 0.05, 2.2])
        with c_stats_side:
            st.markdown(f'<div class="player-header">{valgt_spiller}</div>', unsafe_allow_html=True)
            m_r1 = st.columns(4)
            m_r1[0].metric("Aktion", len(df_spiller))
            # ... osv ...
        with c_pitch_side:
            visning = st.selectbox("Visning", list(descriptions.keys()), key="pitch_view_sel", label_visibility="collapsed")
            pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
            fig, ax = pitch.draw(figsize=(10, 7))
            draw_player_info_box(ax, hold_logo, valgt_spiller, "2025/2026", visning)
            st.pyplot(fig, use_container_width=True)

    # --- TAB: FYSISK DATA (t_phys) ---
    with t_phys:
        # DEBUG SEKTION
        clean_id_debug = str(valgt_player_uuid).lower().replace('p', '').strip()
        st.markdown(f"""
        <div class="debug-box">
            <b>DEBUG INFO:</b><br>
            Valgt spiller: {valgt_spiller}<br>
            Original ID: {valgt_player_uuid}<br>
            Renset ID brugt til søgning: {clean_id_debug}<br>
            Tabel: SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        </div>
        """, unsafe_allow_html=True)

        df_phys = get_physical_data(valgt_player_uuid, conn)
        
        if df_phys is not None and not df_phys.empty:
            latest = df_phys.iloc[0]
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Distance (km)", round(latest['DISTANCE']/1000, 2))
            m2.metric("HSR (m)", int(latest['HSR']))
            m3.metric("Sprint (m)", int(latest['SPRINTING']))
            m4.metric("Top Fart (km/t)", round(latest['TOP_SPEED'], 1))
            
            st.write(f"**Fysisk historik - {valgt_spiller}**")
            st.dataframe(df_phys, use_container_width=True, hide_index=True)
            st.line_chart(df_phys.set_index('MATCH_DATE')['HI_RUNS'])
        else:
            st.error(f"Ingen data fundet for ID: {clean_id_debug}")
            st.info("Dette skyldes ofte, at spilleren ikke har spillet kampe med tracking i denne sæson (f.eks. NordicBet Liga uden tracking).")

    # --- TAB: STATISTIK & GRAFER ---
    with t_stats:
        st.subheader(f"Sæsonudvikling: {valgt_spiller}")
        if not df_spiller.empty:
            df_spiller['DATO'] = df_spiller['EVENT_TIMESTAMP'].dt.date
            st.line_chart(df_spiller.groupby('DATO').size())

if __name__ == "__main__":
    vis_side()
