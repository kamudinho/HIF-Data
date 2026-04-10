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
    ax.text(0.10, 0.92, player_name.upper(), transform=ax.transAxes, 
            fontsize=10, fontweight='bold', color='black', va='center')
    ax.text(0.10, 0.89, f"{season_str} | {category_str} (P90)", transform=ax.transAxes, 
            fontsize=8, color='#666666', va='center')

def vis_side(dp=None):
    st.markdown("""
        <style>
        [data-testid="stMetric"] { text-align: center; display: flex; flex-direction: column; align-items: center; }
        [data-testid="stMetricValue"] { font-size: 18px !important; justify-content: center; }
        [data-testid="stMetricLabel"] { font-size: 12px !important; justify-content: center; }
        [data-testid="stMetricLabel"] > div { justify-content: center; }
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

    # 2. Hent Sæson-data (Filtreret til aktive spillere)
    with st.spinner("Indlæser aktive spillere..."):
        # SQL der kun tager spillere som har været involveret i de seneste 5 kampe for at sikre de stadig er i klubben
        sql_all_season = f"""
            WITH RecentMatches AS (
                SELECT DISTINCT MATCH_OPTAUUID FROM {DB}.OPTA_EVENTS 
                WHERE EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' 
                ORDER BY EVENT_TIMESTAMP DESC LIMIT 5
            ),
            ActivePlayers AS (
                SELECT DISTINCT PLAYER_NAME FROM {DB}.OPTA_EVENTS 
                WHERE MATCH_OPTAUUID IN (SELECT MATCH_OPTAUUID FROM RecentMatches)
            )
            SELECT 
                e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, e.PLAYER_NAME, e.MATCH_OPTAUUID, 
                TO_CHAR(e.EVENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS') as EVENT_TIMESTAMP_STR, 
                e.EVENT_OUTCOME as OUTCOME,
                LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
            FROM {DB}.OPTA_EVENTS e
            JOIN ActivePlayers ap ON e.PLAYER_NAME = ap.PLAYER_NAME
            LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}'
            GROUP BY 1, 2, 3, 4, 5, 6, 7
        """
        df_all_h = conn.query(sql_all_season)
        
        if df_all_h is not None and not df_all_h.empty:
            df_all_h['EVENT_TIMESTAMP'] = pd.to_datetime(df_all_h['EVENT_TIMESTAMP_STR'])
            df_all_h['qual_list'] = df_all_h['QUALIFIERS'].fillna('').str.split(',')
            df_all_h['Action_Label'] = df_all_h.apply(get_action_label, axis=1)
            df_all_h = df_all_h.dropna(subset=['Action_Label'])
        else:
            st.warning("Ingen aktive spillere fundet.")
            return

    t_pitch, t_phys, t_stats, t_compare = st.tabs(["Spillerprofil", "Fysisk Data", "Statistik & Grafer", "Sammenligning"])

    with t_pitch:
        spiller_liste = sorted([n for n in df_all_h['PLAYER_NAME'].unique() if n is not None])
        descriptions = {
            "Heatmap": "Viser bevægelsesmønster (P90 intensitet).",
            "Berøringer": "Alle aktioner med bolden.",
            "Afslutninger": "Skudforsøg (Mål = stjerne).",
            "Mål": "Kun scoringer.",
            "Skudassists": "Afleveringer til afslutning.",
            "Indlæg": "Indlæg i feltet.",
            "Erobringer": "Tacklinger og opspappede bolde."
        }

        t_col1, t_col2, t_col3 = st.columns([0.9, 0.9, 1.2])
        valgt_spiller = t_col1.selectbox("Vælg spiller", spiller_liste, key="p_sel")
        visning = t_col2.selectbox("Visning", list(descriptions.keys()), key="v_sel")
        t_col3.caption(f"{descriptions.get(visning)}")
        
        df_spiller = df_all_h[df_all_h['PLAYER_NAME'] == valgt_spiller].copy()
        
        # --- P90 LOGIK ---
        antal_kampe = df_spiller['MATCH_OPTAUUID'].nunique()
        # Vi estimerer 90 minutter pr. unik kamp-id spilleren findes i
        spillede_90ere = antal_kampe if antal_kampe > 0 else 1 

        c_p1, c_buffer, c_p2 = st.columns([0.9, 0.1, 2.2])
        
        with c_p1:
            # Funktion til P90 konvertering
            def p90(val): return round(val / spillede_90ere, 1)

            st.markdown(f"#### {valgt_spiller}")
            
            m_row1 = st.columns(4)
            m_row1[0].metric("Aktion", p90(len(df_spiller)))
            
            touch_ids = [1, 3, 7, 10, 11, 12, 13, 14, 15, 16, 42, 44, 49, 50, 51, 54, 61, 73]
            t_count = len(df_spiller[df_spiller['EVENT_TYPEID'].isin(touch_ids)])
            m_row1[1].metric("Berør.", p90(t_count))
            
            pas_df = df_spiller[df_spiller['EVENT_TYPEID'] == 1]
            m_row1[2].metric("Pasn.", p90(len(pas_df)))
            
            acc = (pas_df['OUTCOME'].sum() / len(pas_df) * 100) if not pas_df.empty else 0
            m_row1[3].metric("Pasn. %", f"{int(acc)}%")
            
            m_row2 = st.columns(4)
            shots = len(df_spiller[df_spiller['EVENT_TYPEID'].isin([13,14,15,16])])
            m_row2[0].metric("Skud", p90(shots))
            
            chancer = len(df_spiller[df_spiller['Action_Label'].str.contains("assist|Key Pass|Stor chance", case=False, na=False)])
            m_row2[1].metric("Chancer", p90(chancer))
            
            indlæg = len(df_spiller[df_spiller['qual_list'].apply(lambda x: "2" in x)])
            m_row2[2].metric("Indlæg", p90(indlæg))
            
            erob = len(df_spiller[df_spiller['EVENT_TYPEID'].isin([7, 8, 12, 49])])
            m_row2[3].metric("Erob.", p90(erob))
            
            st.markdown("<hr style='margin: 8px 0; opacity: 0.7;'>", unsafe_allow_html=True)                
            st.write("**Top 10: Aktioner (Total)**")
            
            # Top 10 fastholdes som total jvf. ønske
            df_filtreret = df_spiller[~df_spiller['Action_Label'].isin(['Pasning', 'Indkast'])]
            if not df_filtreret.empty:
                akt_stats = df_filtreret.groupby('Action_Label').agg(Total=('OUTCOME', 'count'), Succes=('OUTCOME', 'sum')).sort_values('Total', ascending=False).head(10)
                bare_antal = ['Erobring', 'Clearing', 'Boldtab', 'Frispark vundet', 'Blokeret skud']
            
                for akt, row in akt_stats.iterrows():
                    total, succes = int(row['Total']), int(row['Succes'])
                    if akt in bare_antal: stats_html = f"<b>{total}</b>"
                    else:
                        pct = int((succes / total * 100)) if total > 0 else 0
                        stats_html = f"{succes} / {total} <span style='display: inline-block; width: 45px; margin-left: 5px;'><b>({pct}%)</b></span>"
                    
                    st.markdown(f'<div style="display: flex; justify-content: space-between; font-size: 11px; border-bottom: 0.5px solid #eee; padding: 5px 0;"><span>{akt}</span><span style="font-family: monospace;">{stats_html}</span></div>', unsafe_allow_html=True)

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
                    goals = df_plot[df_plot['EVENT_TYPEID'] == 16]
                    misses = df_plot[df_plot['EVENT_TYPEID'].isin([13, 14, 15])]
                    ax.scatter(misses.EVENT_X, misses.EVENT_Y, color='red', s=80, edgecolors='black', alpha=0.6, label='Afslutning')
                    ax.scatter(goals.EVENT_X, goals.EVENT_Y, color='gold', s=150, marker='*', edgecolors='black', zorder=5, label='Mål')
                    ax.legend(loc='upper right', ncol=2, fontsize=8)
                elif visning == "Skudassists":
                    d = df_plot[df_plot['qual_list'].apply(lambda x: "210" in x)]
                    ax.scatter(d.EVENT_X, d.EVENT_Y, color='#00ffcc', s=100, edgecolors='black')
                elif visning == "Erobringer":
                    d = df_plot[df_plot['EVENT_TYPEID'].isin([7, 8, 12, 49])]
                    ax.scatter(d.EVENT_X, d.EVENT_Y, color='orange', s=100, edgecolors='white')
            st.pyplot(f, use_container_width=True)

if __name__ == "__main__":
    vis_side()
