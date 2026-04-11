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
        [data-testid="stMetricValue"] { font-size: 18px !important; }
        [data-testid="stMetricLabel"] { font-size: 10px !important; }
        </style>
        """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn: return

    # 1. Team Mapping
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    team_map = {}
    for _, row in df_teams_raw.iterrows():
        uuid_clean = str(row['CONTESTANTHOME_OPTAUUID']).lower().replace('t', '')
        if uuid_clean in mapping_lookup:
            team_map[mapping_lookup[uuid_clean]] = row['CONTESTANTHOME_OPTAUUID']

    # Holdvælger i toppen
    col_spacer, col_hold = st.columns([3.5, 1])
    valgt_hold = col_hold.selectbox("Vælg hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid)

    # 2. Hent Sæson-data
    with st.spinner(f"Henter data for {valgt_hold}..."):
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
            AND e.EVENT_X BETWEEN 0 AND 100 AND e.EVENT_Y BETWEEN 0 AND 100
            AND p.FIRST_NAME IS NOT NULL
            GROUP BY 1, 2, 3, 4, 5, 6, 7
        """
        df_all_h = conn.query(sql)
        
        if df_all_h is not None and not df_all_h.empty:
            df_all_h['EVENT_TIMESTAMP'] = pd.to_datetime(df_all_h['EVENT_TIMESTAMP_STR'])
            df_all_h['qual_list'] = df_all_h['QUALIFIERS'].fillna('').str.split(',')
            df_all_h['Action_Label'] = df_all_h.apply(get_action_label, axis=1)
            df_all_h = df_all_h.dropna(subset=['Action_Label'])
        else:
            st.warning("Ingen data fundet.")
            return

    # --- GLOBAL SPILLERVÆLGER OG METRICS ---
    spiller_liste = sorted(df_all_h['VISNINGSNAVN'].unique())
    
    c_sel, c_met = st.columns([1, 3])
    with c_sel:
        valgt_spiller = st.selectbox("Vælg spiller", spiller_liste, key="global_player_select")
    
    df_spiller = df_all_h[df_all_h['VISNINGSNAVN'] == valgt_spiller].copy()
    
    with c_met:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Kampe", df_spiller['MATCH_OPTAUUID'].nunique())
        m2.metric("Aktioner", len(df_spiller))
        m3.metric("Mål", len(df_spiller[df_spiller['EVENT_TYPEID']==16]))
        m4.metric("Chancer skabt", len(df_spiller[df_spiller['qual_list'].apply(lambda x: '210' in x)]))

    st.markdown("---")

    # 3. Tabs opdeling
    t_pitch, t_phys, t_stats, t_compare = st.tabs([
        "Spillerprofil", "Fysisk Data", "Statistik & Grafer", "Sammenligning"
    ])

    # --- TAB: SPILLERPROFIL ---
    with t_pitch:
        descriptions = {
            "Heatmap": "Bevægelsesmønster og intensitet.",
            "Berøringer": "Tekniske aktioner med bolden.",
            "Afslutninger": "Skudforsøg (Mål = Stjerne).",
            "Mål": "Kun scoringer.",
            "Skudassists": "Afleveringer til afslutning.",
            "Indlæg": "Bolde i feltet.",
            "Erobringer": "Tacklinger og opspillede bolde."
        }

        t_col1, t_col2 = st.columns([1, 2])
        visning = t_col1.selectbox("Visning", list(descriptions.keys()), key="prof_vis", label_visibility="collapsed")
        t_col2.caption(descriptions.get(visning))
        
        c_left, c_right = st.columns([1, 2.2])
        
        with c_left:
            st.write("**Top 10: Aktioner**")
            df_filtreret = df_spiller[~df_spiller['Action_Label'].isin(['Pasning', 'Indkast'])]
            if not df_filtreret.empty:
                akt_stats = df_filtreret.groupby('Action_Label').agg(
                    Total=('OUTCOME', 'count'), Succes=('OUTCOME', 'sum')
                ).sort_values('Total', ascending=False).head(10)
                
                bare_antal = ['Erobring', 'Clearing', 'Boldtab', 'Frispark vundet', 'Blokeret skud']
                for akt, row in akt_stats.iterrows():
                    total, succes = int(row['Total']), int(row['Succes'])
                    val = f"<b>{total}</b>" if akt in bare_antal else f"{succes}/{total} <b>({int(succes/total*100)}%)</b>"
                    st.markdown(f"<div style='display:flex; justify-content:space-between; font-size:11px; padding:3px 0; border-bottom:0.5px solid #eee;'><span>{akt}</span><span>{val}</span></div>", unsafe_allow_html=True)

        with c_right:
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
        # Beskrivelse følger under koden
        if not df_spiller.empty:
            df_spiller['DATO'] = df_spiller['EVENT_TIMESTAMP'].dt.date
            trend_data = df_spiller.groupby('DATO').size()
            st.line_chart(trend_data)
            
            st.markdown("---")
            st.write("**Aktionsfordeling i sæsonen**")
            st.bar_chart(df_spiller['Action_Label'].value_counts())

    with t_phys:
        st.subheader("Fysisk Data")
        st.info("Sektion til GPS-data.")

    with t_compare:
        st.subheader("Sammenligning")
        st.write("Benchmark mod ligaen.")

if __name__ == "__main__":
    vis_side()
