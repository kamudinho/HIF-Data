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
        [data-testid="stMetricValue"] { font-size: 16px !important; text-align: center; font-weight: bold !important; width: 100%; }
        [data-testid="stMetricLabel"] { font-size: 10px !important; text-align: center; width: 100%; }
        [data-testid="stMetric"] { display: flex; flex-direction: column; align-items: center; }
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

    # --- TOPBAR: KUN HOLD OG SPILLER HER ---
    col_spacer_top, col_h_hold, col_h_spiller = st.columns([2, 1.2, 1.2])
    valgt_hold = col_h_hold.selectbox("Hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid)

    # 2. HENT DATA (Baseline for alle faner)
    with st.spinner("Henter data..."):
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

    # --- TAB: SPILLERPROFIL (t_pitch) ---
    with t_pitch:
        if not df_all_h.empty:
            descriptions = {
                "Heatmap": "Viser spillerens generelle bevægelsesmønster og intensitet på banen.",
                "Berøringer": "Alle aktioner hvor spilleren har været i kontakt med bolden.",
                "Afslutninger": "Oversigt over alle skudforsøg (Mål markeres med stjerne).",
                "Mål": "Kun de aktioner der resulterede i scoring.",
                "Skudassists": "Afleveringer der direkte førte til en afslutning.",
                "Indlæg": "Indlæg ind i feltet.",
                "Erobringer": "Tacklinger, bolderobringer og opsnappede afleveringer."
            }

            # Pre-calculation for at sikre synkroniserede tal
            df_spiller = df_all_h[df_all_h['VISNINGSNAVN'] == valgt_spiller].copy()
            df_filtreret = df_spiller[~df_spiller['Action_Label'].isin(['Pasning', 'Indkast'])]
            akt_stats = pd.DataFrame()
            if not df_filtreret.empty:
                akt_stats = df_filtreret.groupby('Action_Label').agg(
                    Total=('OUTCOME', 'count'), Succes=('OUTCOME', 'sum')
                ).sort_values('Total', ascending=False)

            # --- HOVEDLAYOUT ---
            # Vi definerer de to hovedkolonner med det samme
            c_stats_side, c_buffer, c_pitch_side = st.columns([1, 0.05, 2.2])
            
            # VENSTRE SIDE (Stats)
            with c_stats_side:
                # Navnet starter helt i top
                st.markdown(f'<div class="player-header" style="margin: 0; line-height: 1;">{valgt_spiller}</div>', unsafe_allow_html=True)
                
                # Beregninger
                total_akt = len(df_spiller)
                pas_df = df_spiller[df_spiller['EVENT_TYPEID'] == 1]
                pas_count = len(pas_df)
                pas_acc = (pas_df['OUTCOME'].sum() / pas_count * 100) if pas_count > 0 else 0
                chancer_skabt = akt_stats[akt_stats.index.str.contains("Key Pass|assist|Stor chance", case=False, na=False)]['Total'].sum() if not akt_stats.empty else 0
                shots_count = len(df_spiller[df_spiller['EVENT_TYPEID'].isin([13, 14, 15, 16])])
                cross_count = len(df_spiller[df_spiller['qual_list'].apply(lambda x: "2" in x)])
                erob_count = len(df_spiller[df_spiller['EVENT_TYPEID'].isin([7, 8, 12, 49])])
                touch_ids = [1, 3, 7, 10, 11, 12, 13, 14, 15, 16, 42, 44, 49, 50, 51, 54, 61, 73]
                touch_count = len(df_spiller[df_spiller['EVENT_TYPEID'].isin(touch_ids)])

                # Metrics i 4 per række
                st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
                m_r1 = st.columns(4)
                m_r1[0].metric("Aktion", total_akt)
                m_r1[1].metric("Touch", touch_count)
                m_r1[2].metric("Pasn.", pas_count)
                m_r1[3].metric("Acc %", f"{int(pas_acc)}%")
                
                m_r2 = st.columns(4)
                m_r2[0].metric("Skud", shots_count)
                m_r2[1].metric("Chancer", int(chancer_skabt))
                m_r2[2].metric("Indlæg", cross_count)
                m_r2[3].metric("Erob.", erob_count)
                
                st.markdown("<hr style='margin: 15px 0; opacity: 0.5;'>", unsafe_allow_html=True)                
                st.write("**Top 10: Aktioner**")
                
                if not akt_stats.empty:
                    bare_antal = ['Erobring', 'Clearing', 'Boldtab', 'Frispark vundet', 'Blokeret skud', 'Interception']
                    for akt, row in akt_stats.head(10).iterrows():
                        total, succes = int(row['Total']), int(row['Succes'])
                        stats_html = f"<b>{total}</b>" if akt in bare_antal else f"{succes}/{total} <b>({int(succes/total*100)}%)</b>"
                        st.markdown(f'<div style="display:flex; justify-content:space-between; font-size:11px; border-bottom:0.5px solid #eee; padding:5px 0;"><span>{akt}</span><span style="font-family:monospace;">{stats_html}</span></div>', unsafe_allow_html=True)

            # HØJRE SIDE (Bane og kontrol)
            with c_pitch_side:
                # Vi laver en indre række her for at få tekst og dropdown på samme linje som navnet til venstre
                c_desc_text, c_vis_dropdown = st.columns([2.5, 1])
                
                with c_desc_text:
                    # Denne tekst vil nu flugte med navnet til venstre
                    st.caption(f"<div style='margin-top: 5px;'> <span style='color: #666;'>{descriptions.get(visning if 'visning' in locals() else 'Heatmap')}</span></div>", unsafe_allow_html=True)
                
                with c_vis_dropdown:
                    visning = st.selectbox("Visning", list(descriptions.keys()), key="pitch_view_sel", label_visibility="collapsed")
                
                # Banen tegnes direkte under kontrol-rækken
                pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
                fig, ax = pitch.draw(figsize=(10, 7))
                draw_player_info_box(ax, hold_logo, valgt_spiller, "2025/2026", visning)
                
                df_plot = df_spiller.dropna(subset=['EVENT_X', 'EVENT_Y'])
                if not df_plot.empty:
                    if visning == "Heatmap":
                        pitch.kdeplot(df_plot.EVENT_X, df_plot.EVENT_Y, ax=ax, cmap='Blues', fill=True, alpha=0.6, levels=50)
                    elif visning == "Berøringer":
                        d = df_plot[df_plot['EVENT_TYPEID'].isin(touch_ids)]
                        ax.scatter(d.EVENT_X, d.EVENT_Y, color='#084594', s=40, edgecolors='white', alpha=0.5)
                    elif visning == "Afslutninger":
                        d = df_plot[df_plot['EVENT_TYPEID'].isin([13, 14, 15, 16])]
                        goals = d[d['EVENT_TYPEID'] == 16]
                        misses = d[d['EVENT_TYPEID'].isin([13, 14, 15])]
                        ax.scatter(misses.EVENT_X, misses.EVENT_Y, color='red', s=80, edgecolors='black', alpha=0.6, label='Afslutning')
                        ax.scatter(goals.EVENT_X, goals.EVENT_Y, color='gold', s=150, marker='*', edgecolors='black', zorder=5, label='Mål')
                        ax.legend(loc='upper right', ncol=2, fontsize=8, frameon=True)
                    elif visning == "Erobringer":
                        d = df_plot[df_plot['EVENT_TYPEID'].isin([7, 8, 12, 49])]
                        ax.scatter(d.EVENT_X, d.EVENT_Y, color='orange', s=100, edgecolors='white')
                
                st.pyplot(fig, use_container_width=True)

    # --- TAB: STATISTIK & GRAFER ---
    with t_stats:
        st.subheader(f"Sæsonudvikling: {valgt_spiller}")
        if not df_spiller.empty:
            df_spiller['DATO'] = df_spiller['EVENT_TIMESTAMP'].dt.date
            trend = df_spiller.groupby('DATO').size()
            st.line_chart(trend)
            st.bar_chart(df_spiller['Action_Label'].value_counts())

if __name__ == "__main__":
    vis_side()
