import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch, VerticalPitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS
import requests
from PIL import Image
from io import BytesIO

# --- IMPORT FRA DIN MAPPING.PY ---
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
    """Tegner spiller-info overlay på banen (fra din t6)"""
    if team_logo:
        ax_l = ax.inset_axes([0.02, 0.88, 0.07, 0.07], transform=ax.transAxes)
        ax_l.imshow(team_logo); ax_l.axis('off')
    ax.text(0.10, 0.92, player_name.upper(), transform=ax.transAxes, 
            fontsize=10, fontweight='bold', color='black', va='center')
    ax.text(0.10, 0.89, f"{season_str} | {category_str}", transform=ax.transAxes, 
            fontsize=8, color='#666666', va='center')

def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn: return

    # 1. Team Mapping
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
    ids = df_teams_raw['CONTESTANTHOME_OPTAUUID'].unique()
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    team_map = {mapping_lookup.get(str(u).lower().replace('t','')): u for u in ids if mapping_lookup.get(str(u).lower().replace('t','')) is not None}

    col_spacer_top, col_hold = st.columns([3.5, 1])
    valgt_hold = col_hold.selectbox("Vælg hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid)

    # 2. Hent Sæson-data (Med streng-cast for at undgå skema-fejl)
    with st.spinner("Henter sæson-data..."):
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
            st.error("Ingen data fundet.")
            return

    # 3. Tabs (Struktureret til let restriction)
    t_pitch, t_phys, t_stats, t_compare = st.tabs(["SPILLERPROFIL", "FYSISK DATA", "STATISTIK", "BENCHMARK"])

    # --- TAB: SPILLERPROFIL (DIN OPRINDELIGE T6 LOGIK) ---
    with t_pitch:
        spiller_liste = sorted([n for n in df_all_h['PLAYER_NAME'].unique() if n is not None])
        
        descriptions = {
            "Heatmap": "Bevægelsesmønster og intensitet på banen.",
            "Berøringer": "Alle aktioner med boldkontakt.",
            "Afslutninger": "Skudforsøg (Mål markeres med stjerne).",
            "Mål": "Kun de aktioner der resulterede i scoring.",
            "Skudassists": "Afleveringer der direkte førte til en afslutning.",
            "Indlæg": "Indlæg fra kanten til feltet.",
            "Erobringer": "Tacklinger, bolderobringer og opsnappede bolde."
        }

        t_col1, t_col2, t_col3 = st.columns([0.9, 0.9, 1.2])
        valgt_spiller = t_col1.selectbox("Vælg spiller", spiller_liste, key="prof_select")
        visning = t_col2.selectbox("Visning", list(descriptions.keys()), key="prof_pitch_view")
        t_col3.caption(descriptions.get(visning))
        
        df_spiller = df_all_h[df_all_h['PLAYER_NAME'] == valgt_spiller].copy()

        # Layout: Metrics (Venstre), Bane (Højre)
        c_p1, c_buffer, c_p2 = st.columns([1.0, 0.1, 2.0])
        
        with c_p1:
            st.markdown(f"#### {valgt_spiller}")
            
            # Metrics (Ingen ikoner)
            m1, m2 = st.columns(2)
            m1.metric("Aktioner", len(df_spiller))
            
            pas_df = df_spiller[df_spiller['EVENT_TYPEID'] == 1]
            acc = int(pas_df['OUTCOME'].sum() / len(pas_df) * 100) if not pas_df.empty else 0
            m2.metric("Pasning %", f"{acc}%")
            
            m3, m4 = st.columns(2)
            m3.metric("Skud", len(df_spiller[df_spiller['EVENT_TYPEID'].isin([13,14,15,16])]))
            m4.metric("Erobringer", len(df_spiller[df_spiller['EVENT_TYPEID'].isin([7,8,12,49])]))

            st.markdown("<hr style='margin:10px 0; opacity:0.3;'>", unsafe_allow_html=True)
            st.write("**Top Aktioner (Sæson)**")
            
            akt_stats = df_spiller[~df_spiller['Action_Label'].isin(['Pasning', 'Indkast'])]\
                        .groupby('Action_Label').agg(Total=('OUTCOME', 'count'), Succes=('OUTCOME', 'sum'))\
                        .sort_values('Total', ascending=False).head(10)

            for akt, row in akt_stats.iterrows():
                p = int((row['Succes'] / row['Total'] * 100)) if row['Total'] > 0 else 0
                st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; font-size:11px; border-bottom:1px solid #eee; padding:4px 0;">
                        <span>{akt}</span>
                        <span><b>{int(row['Total'])}</b> ({p}%)</span>
                    </div>""", unsafe_allow_html=True)

        with c_p2:
            # Pitch Visualisering (VerticalPitch som i din oprindelige visning)
            pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
            fig, ax = pitch.draw(figsize=(10, 7))
            draw_player_info_box(ax, hold_logo, valgt_spiller, "2025/2026", visning)
            
            df_plot = df_spiller.dropna(subset=['EVENT_X', 'EVENT_Y'])
            if not df_plot.empty:
                if visning == "Heatmap":
                    pitch.kdeplot(df_plot.EVENT_X, df_plot.EVENT_Y, ax=ax, cmap='Blues', fill=True, alpha=0.6, levels=50)
                elif visning == "Afslutninger":
                    goals = df_plot[df_plot['EVENT_TYPEID'] == 16]
                    misses = df_plot[df_plot['EVENT_TYPEID'].isin([13,14,15])]
                    ax.scatter(misses.EVENT_X, misses.EVENT_Y, color='red', s=80, edgecolors='black', alpha=0.6)
                    ax.scatter(goals.EVENT_X, goals.EVENT_Y, color='gold', s=150, marker='*', edgecolors='black', zorder=5)
                elif visning == "Berøringer":
                    ids = [1, 3, 7, 10, 11, 12, 13, 14, 15, 16, 42, 44, 49, 50, 51, 54, 61, 73]
                    d = df_plot[df_plot['EVENT_TYPEID'].isin(ids)]
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

            st.pyplot(fig, use_container_width=True)

    # --- RESTEN AF TABS (KLAR TIL INDHOLD) ---
    with t_phys:
        st.subheader("Fysisk Data (Catapult)")
        st.info("Her kan GPS-data integreres for den valgte spiller.")

    with t_stats:
        st.subheader("Sæsonudvikling")
        if not df_spiller.empty:
            df_spiller['DATO'] = pd.to_datetime(df_spiller['EVENT_TIMESTAMP']).dt.date
            match_stats = df_spiller.groupby('DATO').size()
            st.line_chart(match_stats)

    with t_compare:
        st.subheader("Benchmark")
        st.write("Sammenligning mod resten af ligaen.")

if __name__ == "__main__":
    vis_side()
