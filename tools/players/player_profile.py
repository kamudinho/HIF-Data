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
    ax.text(0.10, 0.92, player_name.upper(), transform=ax.transAxes, 
            fontsize=10, fontweight='bold', color='black', va='center')
    ax.text(0.10, 0.89, f"{season_str} | {category_str} (P90)", transform=ax.transAxes, 
            fontsize=8, color='#666666', va='center')

def vis_side(dp=None):
    # CSS til centrering og metrics
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

    # 1. Team & Interval Selection
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
    ids = df_teams_raw['CONTESTANTHOME_OPTAUUID'].unique()
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    team_map = {mapping_lookup.get(str(u).lower().replace('t','')): u for u in ids if mapping_lookup.get(str(u).lower().replace('t','')) is not None}

    col_hold, col_interval = st.columns([1, 1])
    valgt_hold = col_hold.selectbox("Hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    interval = col_interval.radio("Periode", ["Forår 2026", "Efterår 2025"], horizontal=True, label_visibility="collapsed")
    
    date_filter = ">= '2026-01-01'" if interval == "Forår 2026" else "< '2026-01-01'"
    valgt_uuid = team_map[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid)

    # 2. Hent Sæson-data (Rettet SQL-fejl ved at fjerne tidsstempel fra ORDER BY i LISTAGG)
    with st.spinner(f"Henter data for {interval}..."):
        sql_all_season = f"""
            SELECT 
                e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, e.PLAYER_NAME, e.MATCH_OPTAUUID, 
                TO_CHAR(e.EVENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS') as EVENT_TIMESTAMP_STR, 
                e.EVENT_OUTCOME as OUTCOME,
                LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
            FROM {DB}.OPTA_EVENTS e
            LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' 
            AND e.EVENT_TIMESTAMP {date_filter}
            AND e.PLAYER_NAME IS NOT NULL
            GROUP BY 1, 2, 3, 4, 5, 6, 7
        """
        df_all_h = conn.query(sql_all_season)
        
        if df_all_h is not None and not df_all_h.empty:
            df_all_h['qual_list'] = df_all_h['QUALIFIERS'].fillna('').str.split(',')
            df_all_h['Action_Label'] = df_all_h.apply(get_action_label, axis=1)
            df_all_h = df_all_h.dropna(subset=['Action_Label'])
        else:
            st.warning(f"Ingen data fundet for {valgt_hold} i den valgte periode.")
            return

    t_pitch, t_stats = st.tabs(["Spillerprofil", "Statistik & Grafer"])

    with t_pitch:
        spiller_liste = sorted(df_all_h['PLAYER_NAME'].unique())
        
        t_col1, t_col2, t_col3 = st.columns([0.9, 0.9, 1.2])
        valgt_spiller = t_col1.selectbox("Vælg spiller", spiller_liste, key="p_sel_v6")
        
        visninger = ["Heatmap", "Berøringer", "Afslutninger", "Mål", "Skudassists", "Indlæg", "Erobringer"]
        visning = t_col2.selectbox("Visning", visninger, key="v_sel_v6")
        
        df_spiller = df_all_h[df_all_h['PLAYER_NAME'] == valgt_spiller].copy()
        
        # --- P90 BEREGNING ---
        kampe = df_spiller['MATCH_OPTAUUID'].nunique()
        minutter_est = kampe * 90 if kampe > 0 else 90
        p90_factor = 90 / minutter_est if minutter_est > 0 else 1

        c_p1, c_buffer, c_p2 = st.columns([0.9, 0.1, 2.2])
        
        with c_p1:
            st.markdown(f"#### {valgt_spiller}")
            def m_p90(val): return round(val * p90_factor, 1)

            r1 = st.columns(4)
            r1[0].metric("Aktion", m_p90(len(df_spiller)))
            t_ids = [1, 3, 7, 10, 11, 12, 13, 14, 15, 16, 42, 44, 49, 50, 51, 54, 61, 73]
            r1[1].metric("Berør.", m_p90(len(df_spiller[df_spiller['EVENT_TYPEID'].isin(t_ids)])))
            pas_df = df_spiller[df_spiller['EVENT_TYPEID'] == 1]
            r1[2].metric("Pasn.", m_p90(len(pas_df)))
            r1[3].metric("Pasn. %", f"{int(pas_df['OUTCOME'].sum()/len(pas_df)*100)}%" if not pas_df.empty else "0%")

            r2 = st.columns(4)
            r2[0].metric("Skud", m_p90(len(df_spiller[df_spiller['EVENT_TYPEID'].isin([13,14,15,16])])))
            r2[1].metric("Chancer", m_p90(len(df_spiller[df_spiller['Action_Label'].str.contains("assist|Key Pass|Stor chance", case=False, na=False)])))
            r2[2].metric("Indlæg", m_p90(len(df_spiller[df_spiller['qual_list'].apply(lambda x: "2" in x)])))
            r2[3].metric("Erob.", m_p90(len(df_spiller[df_spiller['EVENT_TYPEID'].isin([7, 8, 12, 49])])))

            st.markdown("<hr style='margin: 8px 0; opacity: 0.7;'>", unsafe_allow_html=True)
            st.write("**Top 10: Aktioner (Total)**")
            
            df_akt = df_spiller[~df_spiller['Action_Label'].isin(['Pasning', 'Indkast'])]
            if not df_akt.empty:
                akt_stats = df_akt.groupby('Action_Label').agg(T=('OUTCOME','count'), S=('OUTCOME','sum')).sort_values('T', ascending=False).head(10)
                for akt, row in akt_stats.iterrows():
                    pct_str = f"({int(row['S']/row['T']*100)}%)" if row['T'] > 0 else ""
                    res = f"{int(row['S'])} / {int(row['T'])} <b>{pct_str}</b>" if akt not in ['Erobring', 'Clearing', 'Boldtab'] else f"<b>{int(row['T'])}</b>"
                    st.markdown(f'<div style="display: flex; justify-content: space-between; font-size: 11px; border-bottom: 0.5px solid #eee; padding: 4px 0;"><span>{akt}</span><span>{res}</span></div>', unsafe_allow_html=True)

        with c_p2:
            p = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
            f, ax = p.draw(figsize=(10, 7))
            draw_player_info_box(ax, hold_logo, valgt_spiller, interval, visning)
            
            d_pl = df_spiller.dropna(subset=['EVENT_X', 'EVENT_Y'])
            if not d_pl.empty:
                if visning == "Heatmap":
                    p.kdeplot(d_pl.EVENT_X, d_pl.EVENT_Y, ax=ax, cmap='Blues', fill=True, alpha=0.6, levels=50)
                elif visning == "Berøringer":
                    ax.scatter(d_pl.EVENT_X, d_pl.EVENT_Y, color='#084594', s=40, edgecolors='white', alpha=0.5)
                elif visning == "Afslutninger":
                    ax.scatter(d_pl[d_pl['EVENT_TYPEID']==16].EVENT_X, d_pl[d_pl['EVENT_TYPEID']==16].EVENT_Y, color='gold', s=150, marker='*', edgecolors='black', label='Mål', zorder=5)
                    ax.scatter(d_pl[d_pl['EVENT_TYPEID'].isin([13,14,15])].EVENT_X, d_pl[d_pl['EVENT_TYPEID'].isin([13,14,15])].EVENT_Y, color='red', s=80, alpha=0.6, label='Skud')
                    ax.legend(loc='upper right', fontsize=8)
                elif visning == "Erobringer":
                    d_erob = d_pl[d_pl['EVENT_TYPEID'].isin([7, 8, 12, 49])]
                    ax.scatter(d_erob.EVENT_X, d_erob.EVENT_Y, color='orange', s=100, edgecolors='white')
            
            st.pyplot(f, use_container_width=True)

if __name__ == "__main__":
    vis_side()
