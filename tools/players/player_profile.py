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
    info_text = f"{season_str} | {category_str}"
    ax.text(0.10, 0.89, info_text, transform=ax.transAxes, 
            fontsize=8, color='#666666', va='center')

def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn: return

    # 1. Team Mapping & Selection
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
    ids = df_teams_raw['CONTESTANTHOME_OPTAUUID'].unique()
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    
    team_map = {
        mapping_lookup.get(str(u).lower().replace('t','')): u 
        for u in ids 
        if mapping_lookup.get(str(u).lower().replace('t','')) is not None
    }

    col_spacer, col_hold = st.columns([3.5, 1])
    valgt_hold = col_hold.selectbox("Vælg hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid)

    # 2. Hent Sæson-data (Ingen LIMIT 10)
    with st.spinner("Indlæser sæsonens aktioner..."):
        sql_all_season = f"""
            SELECT 
                e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, e.PLAYER_NAME, e.MATCH_OPTAUUID, 
                e.EVENT_TIMESTAMP, e.EVENT_OUTCOME as OUTCOME,
                LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
            FROM {DB}.OPTA_EVENTS e
            LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' 
            AND e.PLAYER_NAME IS NOT NULL
            GROUP BY 1, 2, 3, 4, 5, 6, 7
        """
        df_all_h = conn.query(sql_all_season)
        
        if df_all_h is not None and not df_all_h.empty:
            df_all_h['qual_list'] = df_all_h['QUALIFIERS'].fillna('').str.split(',')
            df_all_h['Action_Label'] = df_all_h.apply(get_action_label, axis=1)
            df_all_h = df_all_h.dropna(subset=['Action_Label'])
        else:
            st.warning("Ingen data fundet for det valgte hold.")
            return

    # 3. Definer Hoved-tabs (t6 struktur)
    t_pitch, t_phys, t_stats, t_compare = st.tabs([
        "👤 Spillerprofil", 
        "⚡ Fysisk Data", 
        "📈 Statistik & Grafer", 
        "📊 Sammenligning"
    ])

    # --- TAB: SPILLERPROFIL (HJERTET) ---
    with t_pitch:
        spiller_liste = sorted(df_all_h['PLAYER_NAME'].unique())
        
        descriptions = {
            "Heatmap": "Bevægelsesmønster og intensitet på banen.",
            "Berøringer": "Alle aktioner med boldkontakt.",
            "Afslutninger": "Skudforsøg (Mål markeres med stjerne).",
            "Mål": "Kun scoringer.",
            "Skudassists": "Afleveringer der førte til afslutning.",
            "Indlæg": "Indlæg til feltet.",
            "Erobringer": "Tacklinger og opsnappede bolde."
        }

        c1, c2, c3 = st.columns([1, 1, 1.5])
        valgt_spiller = c1.selectbox("Vælg spiller", spiller_liste, key="psel")
        visning = c2.selectbox("Visning", list(descriptions.keys()), key="vsel")
        c3.caption(f"{descriptions.get(visning)}")

        df_spiller = df_all_h[df_all_h['PLAYER_NAME'] == valgt_spiller].copy()
        
        # Layout: Tal til venstre, Bane til højre
        col_metrics, col_pitch = st.columns([1, 2.2])

        with col_metrics:
            st.subheader(valgt_spiller)
            
            # Metrics uden ikoner
            m1, m2 = st.columns(2)
            m1.metric("Aktioner", len(df_spiller))
            
            pas_df = df_spiller[df_spiller['EVENT_TYPEID'] == 1]
            acc = int(pas_df['OUTCOME'].sum() / len(pas_df) * 100) if not pas_df.empty else 0
            m2.metric("Pasning %", f"{acc}%")

            m3, m4 = st.columns(2)
            m3.metric("Skud", len(df_spiller[df_spiller['EVENT_TYPEID'].isin([13,14,15,16])]))
            m4.metric("Erobringer", len(df_spiller[df_spiller['EVENT_TYPEID'].isin([7,8,12,49])]))

            st.markdown("<hr style='margin:10px 0; opacity:0.2;'>", unsafe_allow_html=True)
            st.write("**Top Aktioner (Sæson)**")
            
            # Aktionstabel
            akt_stats = df_spiller[~df_spiller['Action_Label'].isin(['Pasning', 'Indkast'])]\
                        .groupby('Action_Label').agg(Total=('OUTCOME', 'count'), Succes=('OUTCOME', 'sum'))\
                        .sort_values('Total', ascending=False).head(10)

            for akt, row in akt_stats.iterrows():
                p = int((row['Succes'] / row['Total'] * 100)) if row['Total'] > 0 else 0
                st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; font-size:11px; border-bottom:0.5px solid #eee; padding:5px 0;">
                        <span>{akt}</span>
                        <span><b>{int(row['Total'])}</b> ({p}%)</span>
                    </div>""", unsafe_allow_html=True)

        with col_pitch:
            p = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
            f, ax = p.draw(figsize=(10, 7))
            draw_player_info_box(ax, hold_logo, valgt_spiller, "2025/2026", visning)
            
            df_plot = df_spiller.dropna(subset=['EVENT_X', 'EVENT_Y'])
            if not df_plot.empty:
                if visning == "Heatmap":
                    p.kdeplot(df_plot.EVENT_X, df_plot.EVENT_Y, ax=ax, cmap='Blues', fill=True, alpha=0.6, levels=50)
                
                elif visning == "Afslutninger":
                    goals = df_plot[df_plot['EVENT_TYPEID'] == 16]
                    misses = df_plot[df_plot['EVENT_TYPEID'].isin([13, 14, 15])]
                    ax.scatter(misses.EVENT_X, misses.EVENT_Y, color='red', s=80, edgecolors='black', alpha=0.6, label='Afslutning')
                    ax.scatter(goals.EVENT_X, goals.EVENT_Y, color='gold', s=150, marker='*', edgecolors='black', zorder=5, label='Mål')
                    ax.legend(loc='upper right', bbox_to_anchor=(1, 1), ncol=2, fontsize=8, frameon=True)

                elif visning == "Berøringer":
                    touch_ids = [1, 3, 7, 10, 11, 12, 13, 14, 15, 16, 42, 44, 49, 50, 51, 54, 61, 73]
                    d = df_plot[df_plot['EVENT_TYPEID'].isin(touch_ids)]
                    ax.scatter(d.EVENT_X, d.EVENT_Y, color='#084594', s=40, edgecolors='white', alpha=0.5)

                elif visning == "Erobringer":
                    d = df_plot[df_plot['EVENT_TYPEID'].isin([7, 8, 12, 49])]
                    ax.scatter(d.EVENT_X, d.EVENT_Y, color='orange', s=100, edgecolors='white')

                elif visning == "Indlæg":
                    d = df_plot[df_plot['qual_list'].apply(lambda x: "2" in x)]
                    ax.scatter(d.EVENT_X, d.EVENT_Y, color='#cc00ff', s=80, edgecolors='white')

                elif visning == "Skudassists":
                    d = df_plot[df_plot['qual_list'].apply(lambda x: "210" in x)]
                    ax.scatter(d.EVENT_X, d.EVENT_Y, color='#00ffcc', s=100, edgecolors='black')

            st.pyplot(f, use_container_width=True)

    # --- TAB: FYSISK DATA (RESTRICTION POINT) ---
    with t_phys:
        st.subheader("Fysisk Performance (Catapult)")
        st.info("Her indlæses data for sprint-distancer, HSR og topfart fra Snowflake.")
        # Eksempel på fremtidig kode:
        # if st.session_state.user_role == 'admin':
        #     draw_physical_metrics(valgt_spiller)

    # --- TAB: STATISTIK & GRAFER ---
    with t_stats:
        st.subheader("Sæsonudvikling")
        if not df_spiller.empty:
            df_spiller['DATO'] = pd.to_datetime(df_spiller['EVENT_TIMESTAMP']).dt.date
            match_stats = df_spiller.groupby('DATO').size()
            st.line_chart(match_stats)

    # --- TAB: SAMMENLIGNING ---
    with t_compare:
        st.subheader("Benchmark")
        st.write("Sammenlign spilleren mod ligagennemsnittet på valgte parametre.")

if __name__ == "__main__":
    vis_side()
