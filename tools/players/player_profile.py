import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from mplsoccer import Pitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS
import requests
from PIL import Image
import io
import base64
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
CURRENT_SEASON = "2025/2026"

# --- HJÆLPEFUNKTIONER ---
@st.cache_data(ttl=3600)
def get_logo_img(opta_uuid):
    if not opta_uuid: 
        return None
    uuid_clean = str(opta_uuid).lower().replace('t', '')
    url = next((info['logo'] for name, info in TEAMS.items() if str(info.get('opta_uuid', '')).lower().replace('t','') == uuid_clean), None)
    if not url: 
        return None
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except: 
        return None

def har_qualifier(row_events, row_quals, event_id, qual_ids):
    try:
        if str(row_events) != str(event_id):
            return False
        
        # Håndter både liste og streng for rækkens qualifiers (Opta format)
        ql = row_quals if isinstance(row_quals, list) else str(row_quals).split(',')
        row_quals_set = {str(q).strip() for q in ql}
        
        # Hvis qual_ids er en liste (f.eks. [2, 155]), tjekker vi om der er overlap
        if isinstance(qual_ids, list):
            target_quals = {str(q).strip() for q in qual_ids}
            return len(row_quals_set.intersection(target_quals)) > 0
        else:
            return str(qual_ids).strip() in row_quals_set
    except:
        return False

def get_ordinal(n):
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

def create_relative_donut(player_val, max_val, label, rank_text, color="#df003b"):
    base_max = max(max_val, player_val, 1)
    reminder = base_max - player_val
    
    fig = go.Figure(go.Pie(
        values=[player_val, reminder],
        hole=0.7,
        marker_colors=[color, "#eeeeee"],
        textinfo='none',
        hoverinfo='none',
        rotation=0,
        direction='clockwise',
        sort=False
    ))
    
    fig.update_layout(
        showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=110, width=130,
        annotations=[dict(
            # Her viser vi nu rank_text i stedet for procent
            text=f"<b>{player_val}</b><br><span style='font-size:12px; color:#df003b; font-weight:bold;'>{rank_text}</span>", 
            x=0.5, y=0.5, font_size=16, showarrow=False, font_family="Arial"
        )]
    )
    return fig
    
def draw_player_info_box(ax, team_logo, player_name, season_str, category_str):
    if team_logo:
        ax_l = ax.inset_axes([0.02, 0.88, 0.07, 0.07], transform=ax.transAxes)
        ax_l.imshow(team_logo)
        ax_l.axis('off')
    ax.text(0.10, 0.92, str(player_name).upper(), transform=ax.transAxes, 
            fontsize=10, fontweight='bold', color='black', va='center')
    ax.text(0.10, 0.89, f"{season_str} | {category_str}", transform=ax.transAxes, 
            fontsize=8, color='#666666', va='center')

def get_physical_data(player_name, player_opta_uuid, valgt_hold_navn, db_conn):
    target_ssiid = TEAMS.get(valgt_hold_navn, {}).get('ssid')
    if not target_ssiid:
        target_ssiid = '56fa29c7-3a48-4186-9d14-dbf45fbc78d9'

    clean_id = str(player_opta_uuid).lower().replace('p', '').strip()
    navne_dele = [n.strip() for n in player_name.split(' ') if len(n.strip()) > 2]
    name_conditions = " OR ".join([f"PLAYER_NAME ILIKE '%{n}%'" for n in navne_dele])

    sql = f"""
        SELECT 
            p.MATCH_DATE,
            ANY_VALUE(p.MATCH_TEAMS) as MATCH_TEAMS,
            MAX(p.MINUTES) as MINUTES,
            SUM(p.DISTANCE) as DISTANCE,
            SUM(p."HIGH SPEED RUNNING") as HSR,
            SUM(p.SPRINTING) as SPRINTING,
            MAX(p.TOP_SPEED) as TOP_SPEED,
            SUM(p.NO_OF_HIGH_INTENSITY_RUNS) as HI_RUNS
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS p
        WHERE (({name_conditions}) OR ("optaId" LIKE '%{clean_id}%'))
          AND p.MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'
          AND p.MATCH_SSIID IN (
              SELECT MATCH_SSIID 
              FROM {DB}.SECONDSPECTRUM_GAME_METADATA
              WHERE HOME_SSIID = '{target_ssiid}' 
                 OR AWAY_SSIID = '{target_ssiid}'
          )
        GROUP BY p.MATCH_DATE, p.PLAYER_NAME
        ORDER BY p.MATCH_DATE DESC
    """
    return db_conn.query(sql)

def vis_side(dp=None):
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 16px !important; text-align: center; font-weight: bold !important; width: 100%; }
        [data-testid="stMetricLabel"] { font-size: 10px !important; text-align: center; width: 100%; }
        [data-testid="stMetric"] { display: flex; flex-direction: column; align-items: center; }
        .player-header { font-size: 18px; font-weight: bold; margin-bottom: 10px; color: #1E1E1E; }
        </style>
        """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn: 
        return

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

    t_profile, t_pitch, t_phys, t_stats, t_compare = st.tabs(["Spillerprofil", "Spilleraktioner", "Fysisk data", "Statistik", "Sammenligning"])

    with t_profile:
        # Vores interne hjælper til at tælle (kigger på både EVENT_TYPEID og qual_list)
        # Vi konverterer nu internt til strenge under sammenligningen for at sikre, at '17' matcher 17.
        def count_event_with_qual(df_group, eid, qids):
            return df_group.apply(lambda r: har_qualifier(r['EVENT_TYPEID'], r.get('qual_list', []), eid, qids), axis=1).sum()

        # 1. Beregn stats for ALLE spillere (Fejlsikker Opta-logik)
        truppen_stats = df_all.groupby('VISNINGSNAVN').apply(lambda x: pd.Series({
            # --- GRUNDLÆGGENDE KAMPDATA ---
            'Kampe': x['GAME_ID'].nunique() if 'GAME_ID' in x.columns else (x['game_id'].nunique() if 'game_id' in x.columns else x['match_id'].nunique() if 'match_id' in x.columns else 0),
            
            # Da vi ikke kan summe EVENT_TIMEMIN direkte, tæller vi minutter, hvis du har en dedikeret kolonne til det
            'Minutter': x['MINUTTER'].sum() if 'MINUTTER' in x.columns else (x['minutter'].sum() if 'minutter' in x.columns else x['minutes'].sum() if 'minutes' in x.columns else 0),
            
            # Gule kort: Event 17 + Qualifier 31
            'Gule_kort': count_event_with_qual(x, 17, 31),
            
            # Røde kort: Event 17 + Qualifier 33
            'Roede_kort': count_event_with_qual(x, 17, 33),
            
            # Indskiftet (Event 19) og Udskiftet (Event 18) som rene tal (uden ' ')
            'Indskiftet': (x['EVENT_TYPEID'] == 19).sum(),
            'Udskiftet': (x['EVENT_TYPEID'] == 18).sum(),
            
            # --- AKTIONER / DONUTS ---
            'Pasninger': (x['EVENT_TYPEID'] == 1).sum(),
            'Stikninger': count_event_with_qual(x, 1, 4),    # Event 1 + Qual 4
            'Indlæg': count_event_with_qual(x, 1, [2, 155]), # Event 1 + Qual 2 (eller 155: Chip)
            'Afslutninger': x['EVENT_TYPEID'].isin([13, 14, 15, 16]).sum(),
            'Mål': (x['EVENT_TYPEID'] == 16).sum(),
            
            # Assists i Opta: Pasning (Event 1) der har Qualifier 210 (Key Pass) OG som førte til et mål (Event 16)
            'Assists': x.apply(lambda r: '210' in str(r.get('qual_list', '')) and r['EVENT_TYPEID'] == 16, axis=1).sum(),
            
            'Erobringer': x['EVENT_TYPEID'].isin([7, 8, 12, 49]).sum(),
            'Driblinger': (x['EVENT_TYPEID'] == 3).sum(),
            'Chancer_skabt': x.apply(lambda r: '210' in str(r.get('qual_list', '')), axis=1).sum(),
            'Key_Passes': x.apply(lambda r: '210' in str(r.get('qual_list', '')), axis=1).sum()
        })).fillna(0)

        # 2. Beregn rank (Højeste tal giver 1st plads)
        ranks = truppen_stats.rank(ascending=False, method='min').astype(int)
        spiller_ranks = ranks.loc[valgt_spiller]
        s_data = truppen_stats.loc[valgt_spiller]

        # 3. Layout: Vi skaber hovedstrukturen
        main_col_left, main_col_right = st.columns([1.3, 4])

        # VENSTRE SIDE: Spillerinfo og Kampdata
        with main_col_left:
            logo_html = ""
            if hold_logo is not None:
                buffered = io.BytesIO()
                hold_logo.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                logo_html = f'<img src="data:image/png;base64,{img_str}" style="height: 35px; margin-right: 12px;">'

            st.markdown(f'<div style="display: flex; align-items: center; margin-bottom: 10px;">{logo_html}<div style="font-size: 18px; font-weight: bold;">{valgt_spiller}</div></div>', unsafe_allow_html=True)
            st.markdown("<hr style='margin: 10px 0; opacity: 0.5;'>", unsafe_allow_html=True)

            # Kampdata boks (Helt renset for ikoner og emojis)
            st.markdown(f"""
                <div style="background-color: #f8f9fa; padding: 12px; border-radius: 8px; border: 1px solid #e9ecef;">
                    <h4 style="margin: 0 0 10px 0; font-size: 14px; text-transform: uppercase; font-weight: bold;">Kampdata</h4>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Kampe:</b></span><span>{int(s_data['Kampe'])}</span></div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Minutter:</b></span><span>{int(s_data['Minutter'])}'</span></div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Mål:</b></span><span>{int(s_data['Mål'])}</span></div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Assists:</b></span><span>{int(s_data['Assists'])}</span></div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Gule kort:</b></span><span>{int(s_data['Gule_kort'])}</span></div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Røde kort:</b></span><span>{int(s_data['Roede_kort'])}</span></div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Indskiftet:</b></span><span>{int(s_data['Indskiftet'])}</span></div>
                    <div style="display: flex; justify-content: space-between; font-size: 13px;"><span><b>Udskiftet:</b></span><span>{int(s_data['Udskiftet'])}</span></div>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<hr style='margin: 15px 0; opacity: 0.5;'>", unsafe_allow_html=True)
            st.caption("Sammenlignet med holdets bedste.")

        # HØJRE SIDE: Alle Donuts (uafhængig af venstre sides højde)
        with main_col_right:
            kat_liste = [
                ("PASNINGER", "Pasninger"), ("STIKNINGER", "Stikninger"), 
                ("AFSLUTNINGER", "Afslutninger"), ("MÅL", "Mål"),
                ("EROBRINGER", "Erobringer"), ("DRIBLINGER", "Driblinger"),
                ("INDLÆG", "Indlæg"), ("CHANCER SKABT", "Chancer_skabt"),
                ("KEY PASSES", "Key_Passes")
            ]
            
            # Loop igennem alle kategorier i rækker af 4
            for i in range(0, len(kat_liste), 4):
                cols = st.columns(4)
                for j, (label, k_id) in enumerate(kat_liste[i:i+4]):
                    with cols[j]:
                        st.markdown(f"<p style='text-align:center; font-weight:bold; font-size:12px; margin-bottom:0px;'>{label}</p>", unsafe_allow_html=True)
                        fig = create_relative_donut(truppen_stats.loc[valgt_spiller, k_id], truppen_stats[k_id].max(), label, get_ordinal(spiller_ranks[k_id]))
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"p_{k_id}_{i}_{j}")
                        
    with t_pitch:
        descriptions = {
            "Heatmap": "Viser spillerens generelle bevægelsesmønster og intensitet på banen.",
            "Berøringer": "Alle aktioner hvor spilleren har været i kontakt med bolden.",
            "Afslutninger": "Oversigt over alle skudforsøg (Mål = firkant, skud = cirkel).",
            "Erobringer": "Tacklinger, bolderobringer og opsnappede afleveringer."
        }
        touch_ids = [1, 3, 7, 10, 11, 12, 13, 14, 15, 16, 42, 44, 49, 50, 51, 54, 61, 73]
        df_filtreret = df_spiller[~df_spiller['Action_Label'].isin(['Pasning', 'Indkast'])]
        
        akt_stats = pd.DataFrame()
        if not df_filtreret.empty:
            akt_stats = df_filtreret.groupby('Action_Label').agg(Total=('OUTCOME', 'count'), Succes=('OUTCOME', 'sum')).sort_values('Total', ascending=False)

        c_stats_side, c_buffer, c_pitch_side = st.columns([1, 0.05, 2.2])

        with c_stats_side:
            logo_html = ""
            if hold_logo is not None:
                # Omdan PIL-billedet til base64
                buffered = io.BytesIO()
                hold_logo.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                logo_html = f'<img src="data:image/png;base64,{img_str}" style="height: 35px; margin-right: 12px; object-fit: contain;">'

            # HTML Flexbox sørger for, at de står på samme linje og er centreret lodret
            st.markdown(f"""
                <div style="display: flex; align-items: center; margin-bottom: 10px;">
                    {logo_html}
                    <div class="player-header" style="margin: 0; line-height: 1.2; font-size: 18px; font-weight: bold;">
                        {valgt_spiller}
                    </div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown("<hr style='margin: 15px 0; opacity: 0.5;'>", unsafe_allow_html=True)
            total_akt = len(df_spiller)
            pas_df = df_spiller[df_spiller['EVENT_TYPEID'] == 1]
            pas_count = len(pas_df)
            pas_acc = (pas_df['OUTCOME'].sum() / pas_count * 100) if pas_count > 0 else 0
            
            chancer_skabt = akt_stats[akt_stats.index.str.contains("Key Pass|assist|Stor chance", case=False, na=False)]['Total'].sum() if not akt_stats.empty else 0
            shots_count = len(df_spiller[df_spiller['EVENT_TYPEID'].isin([13, 14, 15, 16])])
            cross_count = len(df_spiller[df_spiller['qual_list'].apply(lambda x: "2" in x if isinstance(x, list) else False)])
            erob_count = len(df_spiller[df_spiller['EVENT_TYPEID'].isin([7, 8, 12, 49])])
            touch_count = len(df_spiller[df_spiller['EVENT_TYPEID'].isin(touch_ids)])

            m_r1 = st.columns(4)
            m_r1[0].metric("Aktioner", total_akt)
            m_r1[1].metric("Berøringer", touch_count)
            m_r1[2].metric("Pasninger", pas_count)
            m_r1[3].metric("Pasning %", f"{int(pas_acc)}%")
            
            m_r2 = st.columns(4)
            m_r2[0].metric("Skud", shots_count)
            m_r2[1].metric("Chancer", int(chancer_skabt))
            m_r2[2].metric("Indlæg", cross_count)
            m_r2[3].metric("Erobringer", erob_count)

            st.markdown("<hr style='margin: 15px 0; opacity: 0.5;'>", unsafe_allow_html=True)
            st.write("**Top 10: Aktioner**")
            if not akt_stats.empty:
                bare_antal = ['Erobring', 'Clearing', 'Boldtab', 'Frispark vundet', 'Blokeret skud', 'Interception']
                for akt, row in akt_stats.head(10).iterrows():
                    total, succes = int(row['Total']), int(row['Succes'])
                    stats_html = f"<b>{total}</b>" if akt in bare_antal else f"{succes}/{total} <b>({int(succes/total*100)}%)</b>"
                    st.markdown(f'<div style="display:flex; justify-content:space-between; font-size:11px; border-bottom:0.5px solid #eee; padding:5px 0;"><span>{akt}</span><span style="font-family:monospace;">{stats_html}</span></div>', unsafe_allow_html=True)

        with c_pitch_side:
            c_side_spacer, c_desc_col, c_menu_col = st.columns([0.2, 2.0, 1.0])
            with c_menu_col:
                visning = st.selectbox("Visning", list(descriptions.keys()), key="pitch_view_sel", label_visibility="collapsed")
            with c_desc_col:
                st.markdown(f'<div style="text-align: right; margin-top: 8px; line-height: 1.2;"><span style="color: #666; font-size: 0.85rem;">{descriptions.get(visning)}</span></div>', unsafe_allow_html=True)

            pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
            fig, ax = pitch.draw(figsize=(10, 7))
            draw_player_info_box(ax, hold_logo, valgt_spiller, CURRENT_SEASON, visning)

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
                    ax.scatter(misses.EVENT_X, misses.EVENT_Y, color='grey', s=60, edgecolors='black', alpha=0.6)
                    ax.scatter(goals.EVENT_X, goals.EVENT_Y, color='red', s=120, marker='s', edgecolors='black', zorder=5)
                elif visning == "Erobringer":
                    d = df_plot[df_plot['EVENT_TYPEID'].isin([7, 8, 12, 49])]
                    ax.scatter(d.EVENT_X, d.EVENT_Y, color='orange', s=100, edgecolors='white')
            
            st.pyplot(fig, use_container_width=True)

    with t_phys:
        df_phys = get_physical_data(valgt_spiller, valgt_player_uuid, valgt_hold, conn)
        if df_phys is not None and not df_phys.empty:
            df_phys['MATCH_DATE'] = pd.to_datetime(df_phys['MATCH_DATE'])
            df_phys = df_phys.sort_values('MATCH_DATE', ascending=False)
            avg_dist = df_phys['DISTANCE'].mean()
            avg_hsr = df_phys['HSR'].mean()
            latest = df_phys.iloc[0]

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Seneste Distance", f"{round(latest['DISTANCE']/1000, 2)} km", delta=f"{round((latest['DISTANCE'] - avg_dist)/1000, 2)} km")
            m2.metric("HSR Meter", f"{int(latest['HSR'])} m", delta=f"{int(latest['HSR'] - avg_hsr)} m")
            m3.metric("Topfart", f"{round(latest['TOP_SPEED'], 1)} km/t")
            m4.metric("Højintense Akt.", int(latest['HI_RUNS']))

            t_sub_log, t_sub_charts = st.tabs(["Kampoversigt", "Grafer"])

            with t_sub_charts:
                cat_choice = st.segmented_control("Vælg metrik", options=["HSR (m)", "Sprint (m)", "Distance (km)", "Topfart (km/t)"], default="HSR (m)", key="phys_graph_control")
                mapping = {"HSR (m)": ("HSR", 1, "m"), "Sprint (m)": ("SPRINTING", 1, "m"), "Distance (km)": ("DISTANCE", 1000, "km"), "Topfart (km/t)": ("TOP_SPEED", 1, "km/t")}
                col, div, suffix = mapping[cat_choice]

                df_chart = df_phys[df_phys['MATCH_DATE'] >= '2025-07-01'].copy()
                df_chart = df_chart.drop_duplicates(subset=['MATCH_DATE', 'MATCH_TEAMS'])
                df_chart = df_chart.sort_values('MATCH_DATE', ascending=True)

                if not df_chart.empty:
                    def get_opponent(teams_str, my_team):
                        if not teams_str: return "?"
                        parts = [p.strip() for p in teams_str.split('-')]
                        if len(parts) < 2: return teams_str
                        return parts[1] if parts[0].lower() in my_team.lower() else parts[0]

                    df_chart['Opponent'] = df_chart['MATCH_TEAMS'].apply(lambda x: get_opponent(x, valgt_hold))
                    df_chart['Label'] = df_chart['Opponent'] + "<br>" + df_chart['MATCH_DATE'].dt.strftime('%d/%m')
                    y_vals = df_chart[col] / div
                    season_avg = y_vals.mean()

                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=df_chart['Label'], 
                        y=y_vals,
                        text=y_vals.apply(lambda x: f"{x:.0f}" if x > 100 else f"{x:.1f}"),
                        textposition='outside', 
                        marker_color='#cc0000', 
                        textfont=dict(size=9, color="black"),
                        cliponaxis=False
                    ))

                    fig.add_shape(type="line", x0=-0.5, x1=len(df_chart)-0.5, y0=season_avg, y1=season_avg, 
                                  line=dict(color="#D3D3D3", width=2, dash="dash"))

                    fig.update_layout(
                        plot_bgcolor="white", 
                        height=400, 
                        margin=dict(t=50, b=80, l=10, r=10),
                        xaxis=dict(showgrid=False, tickangle=-45, tickfont=dict(size=10), type='category'),
                        yaxis=dict(showgrid=True, gridcolor='#f0f0f0', showticklabels=False, zeroline=False, range=[0, y_vals.max() * 1.3]),
                        showlegend=False
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.info("Ingen fysiske data fundet for denne sæson.")

            with t_sub_log:
                st.data_editor(df_phys, hide_index=True, use_container_width=True, disabled=True)

if __name__ == "__main__":
    vis_side()
