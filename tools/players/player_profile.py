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
    url = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), None)
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
    ax.text(0.10, 0.92, player_name.upper(), transform=ax.transAxes, 
            fontsize=10, fontweight='bold', color='black', va='center')
    ax.text(0.10, 0.89, f"{season_str} | {category_str}", transform=ax.transAxes, 
            fontsize=8, color='#666666', va='center')

def vis_side(dp=None):
    st.markdown("""
        <style>
        /* Centrerer hele metric-containeren */
        [data-testid="stMetric"] {
            text-align: center;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        
        /* Justerer størrelse på værdien (tallet) */
        [data-testid="stMetricValue"] {
            font-size: 18px !important;
            justify-content: center;
        }
        
        /* Justerer størrelse på label (teksten) */
        [data-testid="stMetricLabel"] {
            font-size: 12px !important;
            justify-content: center;
        }
        
        /* Fjerner default padding for at gøre det mere kompakt */
        [data-testid="stMetricLabel"] > div {
            justify-content: center;
        }
        </style>
        """, unsafe_allow_html=True)
    
    conn = _get_snowflake_conn()
    if not conn: return

    # 1. Team Mapping
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
    ids = df_teams_raw['CONTESTANTHOME_OPTAUUID'].unique()
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    team_map = {mapping_lookup.get(str(u).lower().replace('t','')): u for u in ids if mapping_lookup.get(str(u).lower().replace('t','')) is not None}

    col_spacer, col_hold = st.columns([3.5, 1])
    valgt_hold = col_hold.selectbox("Vælg hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid)

    # 2. Hent Sæson-data (Med TO_CHAR for at undgå skema-fejl)
    with st.spinner("Indlæser sæsonens data..."):
        sql_all_season = f"""
            SELECT 
                e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, e.PLAYER_NAME, e.MATCH_OPTAUUID, 
                TO_CHAR(e.EVENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS') as EVENT_TIMESTAMP_STR, 
                e.EVENT_OUTCOME as OUTCOME,
                LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
            FROM {DB}.OPTA_EVENTS e
            LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' 
            AND e.PLAYER_NAME IS NOT NULL
            GROUP BY 1, 2, 3, 4, 5, 6, 7
        """
        df_all_h = conn.query(sql_all_season)
        
        if df_all_h is not None and not df_all_h.empty:
            df_all_h['EVENT_TIMESTAMP'] = pd.to_datetime(df_all_h['EVENT_TIMESTAMP_STR'])
            df_all_h['qual_list'] = df_all_h['QUALIFIERS'].fillna('').str.split(',')
            df_all_h['Action_Label'] = df_all_h.apply(get_action_label, axis=1)
            df_all_h = df_all_h.dropna(subset=['Action_Label'])
        else:
            st.warning("Ingen data fundet.")
            return

    # 3. Tabs opdeling
    t_pitch, t_phys, t_stats, t_compare = st.tabs([
        "Spillerprofil", "Fysisk Data", "Statistik & Grafer", "Sammenligning"
    ])

    # --- TAB: SPILLERPROFIL (DIN t6 LOGIK) ---
    with t_pitch:
        if not df_all_h.empty:
            # --- 1. Top-kontrolbar ---
            spiller_liste = sorted([n for n in df_all_h['PLAYER_NAME'].unique() if n is not None])
            
            descriptions = {
                "Heatmap": "Viser spillerens generelle bevægelsesmønster og intensitet på banen.",
                "Berøringer": "Alle aktioner hvor spilleren har været i kontakt med bolden.",
                "Afslutninger": "Oversigt over alle skudforsøg (Mål markeres med stjerne).",
                "Mål": "Kun de aktioner der resulterede i scoring.",
                "Skudassists": "Afleveringer der direkte førte til en afslutning og mål.",
                "Indlæg": "Indlæg der fører til afslutning eller duel i feltet.",
                "Erobringer": "Tacklinger, bolderobringer og opsnappede afleveringer."
            }

            t_col1, t_col2, t_col3 = st.columns([0.9, 0.9, 1.2])
            with t_col1:
                valgt_spiller = st.selectbox("Vælg spiller", spiller_liste, key="player_profile_select_final_v5", label_visibility="collapsed")
            with t_col2:
                visning = st.selectbox("Visning", list(descriptions.keys()), key="pitch_view_final_v5", label_visibility="collapsed")
            with t_col3:
                st.caption(f"{descriptions.get(visning)}")
            
            # --- 2. Dataforberedelse ---
            df_spiller = df_all_h[df_all_h['PLAYER_NAME'] == valgt_spiller].copy()
            
            # --- 3. Hovedlayout ---
            c_p1, c_buffer, c_p2 = st.columns([0.9, 0.1, 2.2])
            
            with c_p1:
                total_akt = len(df_spiller)
                pas_df = df_spiller[df_spiller['EVENT_TYPEID'] == 1]
                pas_count = len(pas_df)
                pas_acc = (pas_df['OUTCOME'].sum() / pas_count * 100) if pas_count > 0 else 0
                
                chancer_skabt = len(df_spiller[df_spiller['Action_Label'].str.contains("assist|Key Pass|Stor chance", case=False, na=False)])
                shots_count = len(df_spiller[df_spiller['EVENT_TYPEID'].isin([13, 14, 15, 16])])
                cross_count = len(df_spiller[df_spiller['qual_list'].apply(lambda x: "2" in x)])
                erob_count = len(df_spiller[df_spiller['EVENT_TYPEID'].isin([7, 8, 12, 49])])
                
                touch_ids = [1, 3, 7, 10, 11, 12, 13, 14, 15, 16, 42, 44, 49, 50, 51, 54, 61, 73]
                touch_count = len(df_spiller[df_spiller['EVENT_TYPEID'].isin(touch_ids)])

                st.markdown(f"#### {valgt_spiller}")
                
                m_row1 = st.columns(4)
                m_row1[0].metric("Aktion", total_akt)
                m_row1[1].metric("Berøringer", touch_count)
                m_row1[2].metric("Pasninger", pas_count)
                m_row1[3].metric("Pasning %", f"{int(pas_acc)}%")
                
                m_row2 = st.columns(4)
                m_row2[0].metric("Afslutninger", shots_count)
                m_row2[1].metric("Chancer", chancer_skabt)
                m_row2[2].metric("Indlæg", cross_count)
                m_row2[3].metric("Erobringer", erob_count)
                
                st.markdown("<hr style='margin: 8px 0; opacity: 0.7;'>", unsafe_allow_html=True)                
                st.write("**Top 10: Aktioner**")
                
                ekskluder = ['Pasning', 'Indkast']
                df_filtreret = df_spiller[~df_spiller['Action_Label'].isin(ekskluder)]
                
                if not df_filtreret.empty:
                    akt_stats = df_filtreret.groupby('Action_Label').agg(
                        Total=('OUTCOME', 'count'),
                        Succes=('OUTCOME', 'sum')
                    ).sort_values('Total', ascending=False).head(10)
                
                    bare_antal = ['Erobring', 'Clearing', 'Boldtab', 'Frispark vundet', 'Blokeret skud']
                
                    for akt, row in akt_stats.iterrows():
                        total = int(row['Total'])
                        succes = int(row['Succes'])
                        
                        if akt in bare_antal:
                            stats_html = f"<b>{total}</b>"
                        else:
                            pct = int((succes / total * 100)) if total > 0 else 0
                            stats_html = f"{succes} / {total} <span style='display: inline-block; width: 45px; margin-left: 5px;'><b>({pct}%)</b></span>"
                        
                        st.markdown(f'''
                            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11px; border-bottom: 0.5px solid #eee; padding: 5px 0;">
                                <span style="flex-grow: 1; color: #31333F;">{akt}</span>
                                <span style="min-width: 110px; text-align: right; font-family: 'Courier New', monospace;">
                                    {stats_html}
                                </span>
                            </div>''', unsafe_allow_html=True)
                else:
                    st.caption("Ingen øvrige aktioner fundet.")

            with c_p2:
                p = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
                f, ax = p.draw(figsize=(10, 7))
                draw_player_info_box(ax, hold_logo, valgt_spiller, "2025/2026", visning)
                
                df_plot = df_spiller.dropna(subset=['EVENT_X', 'EVENT_Y'])
                if not df_plot.empty:
                    if visning == "Heatmap":
                        p.kdeplot(df_plot.EVENT_X, df_plot.EVENT_Y, ax=ax, cmap='Blues', fill=True, alpha=0.6, levels=50)
                    elif visning == "Berøringer":
                        d = df_plot[df_plot['EVENT_TYPEID'].isin(touch_ids)]
                        ax.scatter(d.EVENT_X, d.EVENT_Y, color='#084594', s=40, edgecolors='white', alpha=0.5)
                    elif visning == "Afslutninger":
                        d = df_plot[df_plot['EVENT_TYPEID'].isin([13, 14, 15, 16])]
                        goals = d[d['EVENT_TYPEID'] == 16]
                        misses = d[d['EVENT_TYPEID'].isin([13, 14, 15])]
                        ax.scatter(misses.EVENT_X, misses.EVENT_Y, color='red', s=80, edgecolors='black', alpha=0.6, label='Afslutning')
                        ax.scatter(goals.EVENT_X, goals.EVENT_Y, color='gold', s=150, marker='*', edgecolors='black', zorder=5, label='Mål')
                        if not d.empty:
                            ax.legend(loc='upper right', bbox_to_anchor=(1, 1), ncol=2, fontsize=8, frameon=True, facecolor='white', edgecolor='#BDBDBD', handletextpad=0.5)
                    elif visning == "Mål":
                        d = df_plot[df_plot['EVENT_TYPEID'] == 16]
                        ax.scatter(d.EVENT_X, d.EVENT_Y, color='gold', s=180, marker='*', edgecolors='black', zorder=5)
                    elif visning == "Skudassists":
                        d = df_plot[df_plot['qual_list'].apply(lambda x: "210" in x)]
                        ax.scatter(d.EVENT_X, d.EVENT_Y, color='#00ffcc', s=100, edgecolors='black')
                    elif visning == "Indlæg":
                        d = df_plot[df_plot['qual_list'].apply(lambda x: "2" in x)]
                        ax.scatter(d.EVENT_X, d.EVENT_Y, color='#cc00ff', s=80, edgecolors='white')
                    elif visning == "Erobringer":
                        d = df_plot[df_plot['EVENT_TYPEID'].isin([7, 8, 12, 49])]
                        ax.scatter(d.EVENT_X, d.EVENT_Y, color='orange', s=100, edgecolors='white')
                
                st.pyplot(f, use_container_width=True)

    # --- ANDRE TABS (KLAR TIL RESTRICTION) ---
    with t_phys:
        st.subheader("Fysisk Data")
        st.info("Sektion til GPS og fysisk data.")

    with t_stats:
        st.subheader("Sæsonudvikling")
        if not df_spiller.empty:
            df_spiller['DATO'] = pd.to_datetime(df_spiller['EVENT_TIMESTAMP']).dt.date
            st.line_chart(df_spiller.groupby('DATO').size())

    with t_compare:
        st.subheader("Sammenligning")
        st.write("Benchmark mod ligaen.")

if __name__ == "__main__":
    vis_side()
