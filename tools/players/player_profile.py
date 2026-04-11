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

def get_physical_data(player_name, player_opta_uuid, db_conn):
    """
    Søger ekstremt bredt efter spilleren. 
    Matcher hvis bare ét af navnene (fornavn, mellemnavn eller efternavn) findes.
    """
    clean_id = str(player_opta_uuid).lower().replace('p', '').strip()
    
    # Split navnet op i alle dets dele (f.eks. ['Morten', 'Brander', 'Knudsen'])
    navne_dele = [del_navn.strip() for del_navn in player_name.split(' ') if len(del_navn.strip()) > 2]
    
    # Opbyg en række LIKE statements forbundet med OR
    # Det betyder: Find rækker hvor navnet indeholder 'Morten' ELLER 'Brander' ELLER 'Knudsen'
    name_conditions = " OR ".join([f"PLAYER_NAME ILIKE '%{n}%'" for n in navne_dele])
    
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
        WHERE ({name_conditions})
           OR ("optaId" LIKE '%{clean_id}%')
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
        .debug-box { background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 10px; border-radius: 5px; font-family: monospace; font-size: 11px; margin-bottom: 20px; }
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
    with st.spinner("Henter spillerdata..."):
        sql = f"""
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
            WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid_hold}' 
            AND e.EVENT_TIMESTAMP >= '2025-07-01'
            GROUP BY 1, 2, 3, 4, 5, 6, 7
        """
        df_all = conn.query(sql)
        if df_all is None or df_all.empty:
            st.warning("Ingen hændelsesdata fundet.")
            return
        
        df_all = df_all.dropna(subset=['VISNINGSNAVN'])
        df_all['EVENT_TIMESTAMP'] = pd.to_datetime(df_all['EVENT_TIMESTAMP_STR'])
        df_all['qual_list'] = df_all['QUALIFIERS'].fillna('').str.split(',')
        df_all['Action_Label'] = df_all.apply(get_action_label, axis=1)

    spiller_liste = sorted(df_all['VISNINGSNAVN'].unique())
    valgt_spiller = col_h_spiller.selectbox("Spiller", spiller_liste, label_visibility="collapsed")
    
    valgt_player_uuid = df_all[df_all['VISNINGSNAVN'] == valgt_spiller]['PLAYER_OPTAUUID'].iloc[0]
    df_spiller = df_all[df_all['VISNINGSNAVN'] == valgt_spiller].copy()

    t_pitch, t_phys, t_stats, t_compare = st.tabs(["Spillerprofil", "Fysisk Data", "Statistik & Grafer", "Sammenligning"])

    # --- TAB: SPILLERPROFIL ---
    with t_pitch:
        descriptions = {"Heatmap": "Bevægelsesmønster.", "Berøringer": "Touch punkter.", "Afslutninger": "Skud.", "Mål": "Scoringer.", "Skudassists": "Chancer.", "Indlæg": "Crosses.", "Erobringer": "Defensive."}
        df_filtreret = df_spiller[~df_spiller['Action_Label'].isin(['Pasning', 'Indkast'])]
        akt_stats = pd.DataFrame()
        if not df_filtreret.empty:
            akt_stats = df_filtreret.groupby('Action_Label').agg(Total=('OUTCOME', 'count'), Succes=('OUTCOME', 'sum')).sort_values('Total', ascending=False)

        c_stats_side, c_buffer, c_pitch_side = st.columns([1, 0.05, 2.2])
        with c_stats_side:
            st.markdown(f'<div class="player-header">{valgt_spiller}</div>', unsafe_allow_html=True)
            st.metric("Total aktioner", len(df_spiller))
            if not akt_stats.empty:
                st.write("**Top 10: Aktioner**")
                for akt, row in akt_stats.head(10).iterrows():
                    st.markdown(f'<div style="display:flex; justify-content:space-between; font-size:11px; border-bottom:0.5px solid #eee; padding:2px 0;"><span>{akt}</span><b>{int(row["Total"])}</b></div>', unsafe_allow_html=True)

        with c_pitch_side:
            visning = st.selectbox("Visning", list(descriptions.keys()), key="pitch_view_sel", label_visibility="collapsed")
            pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
            fig, ax = pitch.draw(figsize=(10, 7))
            draw_player_info_box(ax, hold_logo, valgt_spiller, "2025/2026", visning)
            if visning == "Heatmap":
                pitch.kdeplot(df_spiller.EVENT_X, df_spiller.EVENT_Y, ax=ax, cmap='Blues', fill=True, alpha=0.6, levels=50)
            st.pyplot(fig, use_container_width=True)

    # --- TAB: FYSISK DATA (NY ROBUST SØGNING) ---
    with t_phys:
        navne_dele = valgt_spiller.split(' ')
        f_navn = navne_dele[0]
        e_navn = navne_dele[-1] if len(navne_dele) > 1 else ""
        
        st.markdown(f"""<div class="debug-box"><b>SQL Søgning:</b> PLAYER_NAME LIKE '%{f_navn}%' AND '%{e_navn}%'</div>""", unsafe_allow_html=True)
        
        df_phys = get_physical_data(valgt_spiller, valgt_player_uuid, conn)
        
        if df_phys is not None and not df_phys.empty:
            latest = df_phys.iloc[0]
            m = st.columns(4)
            m[0].metric("Dist (km)", round(latest['DISTANCE']/1000, 2))
            m[1].metric("HSR (m)", int(latest['HSR']))
            m[2].metric("Sprint (m)", int(latest['SPRINTING']))
            m[3].metric("Top (km/t)", round(latest['TOP_SPEED'], 1))
            st.dataframe(df_phys, use_container_width=True, hide_index=True)
        else:
            st.error(f"Ingen fysiske data fundet for {valgt_spiller}. Prøv eventuelt at tjekke navnestavning i Second Spectrum.")

    # --- TAB: UDVIKLING ---
    with t_stats:
        if not df_spiller.empty:
            df_spiller['DATO'] = df_spiller['EVENT_TIMESTAMP'].dt.date
            st.line_chart(df_spiller.groupby('DATO').size())

if __name__ == "__main__":
    vis_side()
