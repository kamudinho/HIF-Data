import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from mplsoccer import Pitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS, TEAM_COLORS
import requests
from PIL import Image
import io
import base64
from io import BytesIO
import os

# --- IMPORT FRA MAPPING ---
from data.utils.mapping import (
    OPTA_EVENT_TYPES, 
    OPTA_QUALIFIERS,
    get_action_label
)

# --- KONFIGURATION (HVIDOVRE-APP / 2026/2027) ---
DB = "KLUB_HVIDOVREIF.AXIS"
SEASONNAME = "2026/2027"
LIGA_IDS = "('2mb332vncy4450vu14paj8844')"

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

def get_team_color(team_name, color_type="primary", default="#df003b"):
    found_colors = None
    for key, colors in TEAM_COLORS.items():
        if key.lower() in team_name.lower() or team_name.lower() in key.lower():
            found_colors = colors
            break
            
    if not found_colors:
        return default
        
    primary = found_colors.get("primary", default)
    secondary = found_colors.get("secondary", "#000000")
    
    if color_type == "primary" and primary.lower() in ["#ffffff", "white", "#fff"]:
        return secondary
        
    return found_colors.get(color_type, default)

def har_qualifier(row_events, row_quals, event_id, qual_ids):
    try:
        if str(row_events) != str(event_id):
            return False
        ql = row_quals if isinstance(row_quals, list) else str(row_quals).split(',')
        row_quals_set = {str(q).strip() for q in ql}
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
            text=f"<b>{player_val}</b><br><span style='font-size:12px; color:{color}; font-weight:bold;'>{rank_text}</span>", 
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
    efternavn = player_name.split()[-1]
    sql = f"""
        SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE UPPER(PLAYER_NAME) LIKE UPPER('%{efternavn}%')
        AND MATCH_DATE >= '2026-07-01'
    """
    df = db_conn.query(sql)
    if df is not None and not df.empty:
        df.columns = df.columns.str.lower()
        rename_map = {
            'high speed running': 'hsr',
            'sprinting': 'sprinting',
            'top_speed': 'top_speed',
            'no_of_high_intensity_runs': 'hi_runs',
            'distance': 'distance'
        }
        df = df.rename(columns=rename_map, errors='ignore')
        return df
    return None

# --- CACHET LIGASAMMENLIGNING & STATISTIK FUNKTION ---
@st.cache_data(ttl=3600)
def hent_ligasammenligning_data(_conn, db_name, navn_mapping):
    try:
        sql_liga_events = f"""
            SELECT 
                e.EVENT_OPTAUUID,
                e.PLAYER_OPTAUUID,
                e.EVENT_TYPEID,
                e.EVENT_TIMESTAMP,
                e.MATCH_OPTAUUID,
                e.EVENT_X, e.EVENT_Y, 
                e.EVENT_OUTCOME as OUTCOME,
                TO_CHAR(e.EVENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS') as EVENT_TIMESTAMP_STR,
                e.EVENT_CONTESTANT_OPTAUUID as TEAM_UUID,
                TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as VISNINGSNAVN,
                LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
            FROM {db_name}.OPTA_EVENTS e
            JOIN {db_name}.OPTA_MATCH_LINEUPS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
            LEFT JOIN {db_name}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE e.EVENT_TIMESTAMP >= '2026-07-01'
              AND p.FIRST_NAME IS NOT NULL
            GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
        """
        df_l_events = _conn.query(sql_liga_events)
        if df_l_events is None or df_l_events.empty:
            return pd.DataFrame(), pd.DataFrame()
        
        df_l_events.columns = df_l_events.columns.str.lower()
        df_l_events['visningsnavn'] = df_l_events.apply(lambda r: navn_mapping.get(str(r['player_optauuid']), r['visningsnavn']), axis=1)
        df_l_events['event_timestamp'] = pd.to_datetime(df_l_events['event_timestamp_str'])
        df_l_events['qual_list'] = df_l_events['qualifiers'].fillna('').str.split(',')
        
        # Tilføj Action_Label baseret på event_typeid og qualifiers
        df_l_events['action_label'] = df_l_events['event_typeid'].apply(get_action_label)

        sql_liga_expected = f"""
            SELECT 
                MATCH_ID,
                PLAYER_OPTAUUID,
                MAX(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_VALUE ELSE 0 END) AS xg,
                MAX(CASE WHEN STAT_TYPE = 'expectedAssists' THEN STAT_VALUE ELSE 0 END) AS xa,
                MAX(CASE WHEN STAT_TYPE = 'minsPlayed' THEN STAT_VALUE ELSE 0 END) AS minutes
            FROM {db_name}.OPTA_MATCHEXPECTEDGOALS
            WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}
              AND MATCH_STATUS = 'Played'
            GROUP BY MATCH_ID, PLAYER_OPTAUUID
        """
        df_liga_expected = _conn.query(sql_liga_expected)
        if df_liga_expected is not None and not df_liga_expected.empty:
            df_liga_expected.columns = df_liga_expected.columns.str.lower()

        df_sorted = df_l_events.sort_values(['match_optauuid', 'event_timestamp'])
        df_sorted['assist_player_uuid'] = df_sorted['player_optauuid'].shift(1)
        df_sorted['prev_match'] = df_sorted['match_optauuid'].shift(1)
        df_sorted['prev_event_typeid'] = df_sorted['event_typeid'].shift(1)
        df_sorted['prev_qualifiers'] = df_sorted['qualifiers'].shift(1)

        player_goals = df_sorted[df_sorted['event_typeid'] == 16].groupby(['player_optauuid', 'visningsnavn']).size().reset_index(name='goals')

        assist_mask = (
            (df_sorted['event_typeid'] == 16) &
            (df_sorted['match_optauuid'] == df_sorted['prev_match']) &
            (df_sorted['assist_player_uuid'].notnull()) &
            (df_sorted['assist_player_uuid'] != df_sorted['player_optauuid']) &
            (df_sorted['qualifiers'].fillna('').str.contains('29') | df_sorted['prev_qualifiers'].fillna('').str.contains('210'))
        )
        player_assists = df_sorted[assist_mask].groupby('assist_player_uuid').size().reset_index(name='assists')
        df_db_stats = pd.merge(player_goals, player_assists, left_on='player_optauuid', right_on='assist_player_uuid', how='left').fillna({'assists': 0})

        def count_event_with_qual_l(df_group, eid, qids):
            return df_group.apply(lambda r: har_qualifier(r['event_typeid'], r.get('qual_list', []), eid, qids), axis=1).sum()

        event_stats_liga = df_l_events.groupby(['player_optauuid', 'visningsnavn', 'team_uuid']).apply(lambda x: pd.Series({
            'Aktioner': len(x),
            'Gule_kort': count_event_with_qual_l(x, 17, 31),
            'Roede_kort': count_event_with_qual_l(x, 17, 33),
            'Indskiftet': (x['event_typeid'] == 19).sum(),
            'Udskiftet': (x['event_typeid'] == 18).sum(),
            'Pasninger': (x['event_typeid'] == 1).sum(),
            'Stikninger': count_event_with_qual_l(x, 1, 4),
            'Indlæg': count_event_with_qual_l(x, 1, [2, 155]),
            'Afslutninger': x['event_typeid'].isin([13, 14, 15, 16]).sum(),
            'Erobringer': x['event_typeid'].isin([7, 8, 12, 49]).sum(),
            'Driblinger': (x['event_typeid'] == 3).sum(),
            'Chancer_skabt': x.apply(lambda r: '210' in r.get('qual_list', []), axis=1).sum(),
            'Key_Passes': x.apply(lambda r: '210' in r.get('qual_list', []), axis=1).sum(),
            'Tacklinger': (x['event_typeid'] == 7).sum(),
            'Clearinger': (x['event_typeid'] == 12).sum(),
            'Blokeringer': (x['event_typeid'] == 55).sum(),
            'Interceptioner': (x['event_typeid'] == 5).sum(),
            'Frispark_imod': (x['event_typeid'] == 4).sum()
        })).reset_index()

        event_stats_liga = event_stats_liga.drop_duplicates(subset=['player_optauuid']).set_index('player_optauuid')

        if df_liga_expected is not None and not df_liga_expected.empty:
            match_stats_liga = df_liga_expected.groupby('player_optauuid').agg({
                'match_id': 'nunique',
                'minutes': 'sum',
                'xg': 'sum',
                'xa': 'sum'
            }).rename(columns={'match_id': 'Kampe', 'minutes': 'Minutter', 'xg': 'xG', 'xa': 'xA'})
            liga_stats_raw = event_stats_liga.join(match_stats_liga, how='left').fillna(0)
        else:
            liga_stats_raw = event_stats_liga.copy()
            liga_stats_raw['Kampe'] = 0
            liga_stats_raw['Minutter'] = 0
            liga_stats_raw['xG'] = 0.0
            liga_stats_raw['xA'] = 0.0

        if df_db_stats is not None and not df_db_stats.empty:
            db_stats_clean = df_db_stats.drop_duplicates(subset=['player_optauuid']).set_index('player_optauuid')
            liga_stats_raw['Mål'] = db_stats_clean['goals']
            liga_stats_raw['Assists'] = db_stats_clean['assists']
        else:
            liga_stats_raw['Mål'] = 0
            liga_stats_raw['Assists'] = 0

        liga_stats_raw['Mål'] = liga_stats_raw['Mål'].fillna(0).astype(int)
        liga_stats_raw['Assists'] = liga_stats_raw['Assists'].fillna(0).astype(int)

        team_lookup = {str(info['opta_uuid']).lower().replace('t', ''): name for name, info in TEAMS.items() if 'opta_uuid' in info}
        def get_team_name(uuid_val):
            if not uuid_val:
                return "Ukendt hold"
            return team_lookup.get(str(uuid_val).lower().replace('t', ''), str(uuid_val))

        liga_stats_raw['hold'] = liga_stats_raw['team_uuid'].apply(get_team_name)
        
        return liga_stats_raw.reset_index(), df_l_events

    except Exception as e:
        st.error(f"Fejl ved hentning af ligadata: {e}")
        return pd.DataFrame(), pd.DataFrame()

def vis_side(dp=None):
    try:
        csv_path = os.path.join(os.getcwd(), 'data', 'players', '1div_overskrivning.csv')
        df_csv = pd.read_csv(csv_path)
        navne_map = dict(zip(df_csv['PLAYER_OPTAUUID'].astype(str), df_csv['NAVN']))
    except:
        navne_map = {}

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

    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
    if df_teams_raw is not None:
        df_teams_raw.columns = df_teams_raw.columns.str.lower()
        
    mapping_lookup = {str(info['opta_uuid']).lower().replace('t', ''): name for name, info in TEAMS.items() if 'opta_uuid' in info}

    team_map = {}
    if df_teams_raw is not None:
        for _, r in df_teams_raw.iterrows():
            uuid_clean = str(r['contestanthome_optauuid']).lower().replace('t','')
            if uuid_clean in mapping_lookup:
                team_map[mapping_lookup[uuid_clean]] = r['contestanthome_optauuid']

    col_spacer_top, col_h_hold, col_h_spiller = st.columns([2, 1.2, 1.2])
    
    default_team_idx = 0
    team_names = sorted(list(team_map.keys()))
    for idx, name in enumerate(team_names):
        if "hvidovre" in name.lower():
            default_team_idx = idx
            break

    valgt_hold = col_h_hold.selectbox("Hold", team_names, index=default_team_idx, label_visibility="collapsed")
    valgt_uuid_hold = team_map[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid_hold)
    
    primær_farve = get_team_color(valgt_hold, "primary", "#df003b")

    with st.spinner("Henter spillerdata for ligaen..."):
        df_alle_spillere_liga, df_all_events = hent_ligasammenligning_data(conn, DB, navne_map)

    if df_alle_spillere_liga is None or df_alle_spillere_liga.empty:
        st.warning("Ingen hændelsesdata fundet.")
        return

    valgt_uuid_clean = str(valgt_uuid_hold).lower().replace('t', '')
    truppen_stats = df_alle_spillere_liga[
        df_alle_spillere_liga['team_uuid'].astype(str).str.lower().str.replace('t', '') == valgt_uuid_clean
    ].copy()

    df_spiller_events = df_all_events[
        df_all_events['team_uuid'].astype(str).str.lower().str.replace('t', '') == valgt_uuid_clean
    ].copy()

    if truppen_stats.empty:
        st.warning("Ingen data fundet for det valgte hold.")
        return

    spiller_options = dict(zip(truppen_stats['visningsnavn'], truppen_stats['player_optauuid']))
    spiller_liste = sorted(list(spiller_options.keys()))
    
    if not spiller_liste:
        st.warning("Ingen spillere fundet på holdet.")
        return

    valgt_label = col_h_spiller.selectbox("Spiller", spiller_liste, label_visibility="collapsed")
    valgt_player_uuid = spiller_options[valgt_label]
    valgt_spiller = valgt_label

    df_spiller = df_spiller_events[df_spiller_events['player_optauuid'] == valgt_player_uuid].copy()
    truppen_stats = truppen_stats.set_index('player_optauuid')

    # --- OPSETNING AF FANER ---
    t_team, t_profile, t_pitch, t_phys = st.tabs([
        "Holdoversigt", "Spillerprofil", "Spilleraktioner", "Fysisk data"
    ])
    with t_team:
        col_t_title, col_t_btn = st.columns([3, 1])
        
        with col_t_title:
            logo_html = ""
            if hold_logo is not None:
                buffered = io.BytesIO()
                hold_logo.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                logo_html = f'<img src="data:image/png;base64,{img_str}" style="height: 26px; margin-right: 10px; object-fit: contain;">'
    
            st.markdown(f'<div style="display: flex; align-items: center; padding-top: 20px;">{logo_html}<span style="font-size: 16px; font-weight: bold; line-height: 1;">{valgt_hold.upper()}</span></div>', unsafe_allow_html=True)
            
        with col_t_btn:
            st.markdown('<div style="display: flex; justify-content: flex-end;">', unsafe_allow_html=True)
            kategori_valg = st.segmented_control(
                "Visningskategori", 
                options=["Generelt", "Offensiv", "Defensiv"], 
                default="Generelt",
                key="team_kategori_control",
                label_visibility="collapsed"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        if not truppen_stats.empty:
            df_vis_truppen = truppen_stats.reset_index()
            
            gen_kolonner = ['visningsnavn', 'Kampe', 'Minutter', 'Aktioner', 'Pasninger', 'Mål', 'Assists', 'Udskiftet', 'Indskiftet', 'Gule_kort', 'Roede_kort']
            off_kolonner = ['visningsnavn', 'Aktioner', 'Afslutninger', 'xG', 'Chancer_skabt', 'Key_Passes', 'Stikninger', 'Indlæg', 'xA', 'Driblinger']
            def_kolonner = ['visningsnavn', 'Aktioner', 'Erobringer', 'Tacklinger', 'Clearinger', 'Blokeringer', 'Interceptioner', 'Frispark_imod']
            
            if kategori_valg == "Generelt":
                eksisterende_kolonner = [k for k in gen_kolonner if k in df_vis_truppen.columns]
            elif kategori_valg == "Offensiv":
                eksisterende_kolonner = [k for k in off_kolonner if k in df_vis_truppen.columns]
            elif kategori_valg == "Defensiv":
                eksisterende_kolonner = [k for k in def_kolonner if k in df_vis_truppen.columns]
            else:  
                eksisterende_kolonner = [k for k in df_vis_truppen.columns if k != 'player_optauuid']
            
            df_visning = df_vis_truppen[eksisterende_kolonner].copy()
            
            df_visning = df_visning.rename(columns={
                'visningsnavn': 'Spiller',
                'Gule_kort': 'Gule kort',
                'Roede_kort': 'Røde kort',
                'Chancer_skabt': 'Chancer skabt',
                'Key_Passes': 'Key Passes'
            })
            
            beregnet_hoejde = int(len(df_visning) * 38 + 45)
            
            st.dataframe(
                df_visning, 
                use_container_width=True, 
                hide_index=True,
                height=beregnet_hoejde
            )
        else:
            st.info("Ingen trup-data tilgængelig endnu.")

    with t_profile:
        numeric_cols = truppen_stats.drop(columns=['visningsnavn'], errors='ignore')
        ranks = numeric_cols.rank(ascending=False, method='min').astype(int)
        
        try:
            spiller_ranks = ranks.loc[valgt_player_uuid]
            if isinstance(spiller_ranks, pd.DataFrame):
                spiller_ranks = spiller_ranks.iloc[0]
            s_data = truppen_stats.loc[valgt_player_uuid]
            if isinstance(s_data, pd.DataFrame):
                s_data = s_data.iloc[0]
        except KeyError:
            st.error(f"Kunne ikke finde stats for spiller: {valgt_spiller}")
            return
    
        main_col_left, main_col_right = st.columns([1.3, 4])
    
        with main_col_left:
            logo_html = ""
            if hold_logo is not None:
                buffered = io.BytesIO()
                hold_logo.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                logo_html = f'<img src="data:image/png;base64,{img_str}" style="height: 35px; margin-right: 12px;">'
    
            st.markdown(f'<div style="display: flex; align-items: center; margin-bottom: 10px;">{logo_html}<div style="font-size: 18px; font-weight: bold;">{valgt_spiller}</div></div>', unsafe_allow_html=True)
            st.markdown("<hr style='margin: 10px 0; opacity: 0.5;'>", unsafe_allow_html=True)
    
            st.markdown(f"""
                <div style="background-color: #f8f9fa; padding: 12px; border-radius: 8px; border: 1px solid #e9ecef;">
                    <h4 style="margin: 0 0 10px 0; font-size: 14px; text-transform: uppercase; font-weight: bold;">Kampdata</h4>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Kampe:</b></span><span>{int(s_data['Kampe'])}</span></div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Minutter:</b></span><span>{int(s_data['Minutter'])}'</span></div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Mål (xG):</b></span><span>{int(s_data['Mål'])} ({round(s_data['xG'], 2)})</span></div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Assists (xA):</b></span><span>{int(s_data['Assists'])} ({round(s_data['xA'], 2)})</span></div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Gule kort:</b></span><span>{int(s_data['Gule_kort'])}</span></div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Røde kort:</b></span><span>{int(s_data['Roede_kort'])}</span></div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Indskiftet:</b></span><span>{int(s_data['Indskiftet'])}</span></div>
                    <div style="display: flex; justify-content: space-between; font-size: 13px;"><span><b>Udskiftet:</b></span><span>{int(s_data['Udskiftet'])}</span></div>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<hr style='margin: 15px 0; opacity: 0.5;'>", unsafe_allow_html=True)
            st.caption("Sammenlignet med holdets bedste.")
    
        with main_col_right:
            kat_liste = [
                ("PASNINGER", "Pasninger"), ("STIKNINGER", "Stikninger"), 
                ("AFSLUTNINGER", "Afslutninger"), ("MÅL", "Mål"),
                ("EROBRINGER", "Erobringer"), ("DRIBLINGER", "Driblinger"),
                ("INDLÆG", "Indlæg"), ("CHANCER SKABT", "Chancer_skabt"),
                ("KEY PASSES", "Key_Passes")
            ]
            
            for i in range(0, len(kat_liste), 4):
                cols = st.columns(4)
                for j, (label, k_id) in enumerate(kat_liste[i:i+4]):
                    with cols[j]:
                        st.markdown(f"<p style='text-align:center; font-weight:bold; font-size:12px; margin-bottom:0px;'>{label}</p>", unsafe_allow_html=True)
                        player_val = truppen_stats.loc[valgt_player_uuid, k_id]
                        if isinstance(player_val, pd.Series):
                            player_val = player_val.iloc[0]
                        fig = create_relative_donut(player_val, truppen_stats[k_id].max(), label, get_ordinal(spiller_ranks[k_id]), color=primær_farve)
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"p_{k_id}_{i}_{j}")
    
    with t_pitch:
        descriptions = {
            "Heatmap": "Viser spillerens generelle bevægelsesmønster og intensitet på banen.",
            "Berøringer": "Alle aktioner hvor spilleren har været i kontakt med bolden.",
            "Afslutninger": "Oversigt over alle skudforsøg (Mål = firkant, skud = cirkel).",
            "Erobringer": "Tacklinger, bolderobringer og opsnappede afleveringer."
        }
        touch_ids = [1, 3, 7, 10, 11, 12, 13, 14, 15, 16, 42, 44, 49, 50, 51, 54, 61, 73]
        
        df_filtreret = df_spiller[~df_spiller['action_label'].isin(['Pasning', 'Indkast'])]
        
        akt_stats = pd.DataFrame()
        if not df_filtreret.empty:
            akt_stats = df_filtreret.groupby('action_label').agg(Total=('outcome', 'count'), Succes=('outcome', 'sum')).sort_values('Total', ascending=False)
    
        c_stats_side, c_buffer, c_pitch_side = st.columns([1, 0.05, 2.2])
    
        with c_stats_side:
            logo_html = ""
            if hold_logo is not None:
                buffered = io.BytesIO()
                hold_logo.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                logo_html = f'<img src="data:image/png;base64,{img_str}" style="height: 35px; margin-right: 12px; object-fit: contain;">'
    
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
            pas_df = df_spiller[df_spiller['event_typeid'] == 1]
            pas_count = len(pas_df)
            pas_acc = (pas_df['outcome'].sum() / pas_count * 100) if pas_count > 0 else 0
            
            chancer_skabt = akt_stats[akt_stats.index.str.contains("Key Pass|assist|Stor chance", case=False, na=False)]['Total'].sum() if not akt_stats.empty else 0
            shots_count = len(df_spiller[df_spiller['event_typeid'].isin([13, 14, 15, 16])])
            cross_count = len(df_spiller[df_spiller['qual_list'].apply(lambda x: "2" in x if isinstance(x, list) else False)])
            erob_count = len(df_spiller[df_spiller['event_typeid'].isin([7, 8, 12, 49])])
            touch_count = len(df_spiller[df_spiller['event_typeid'].isin(touch_ids)])
    
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
            draw_player_info_box(ax, hold_logo, valgt_spiller, SEASONNAME, visning)
    
            df_plot = df_spiller.dropna(subset=['event_x', 'event_y'])
            if not df_plot.empty:
                if visning == "Heatmap":
                    pitch.kdeplot(df_plot.event_x, df_plot.event_y, ax=ax, cmap='Blues', fill=True, alpha=0.6, levels=50)
                elif visning == "Berøringer":
                    d = df_plot[df_plot['event_typeid'].isin(touch_ids)]
                    ax.scatter(d.event_x, d.event_y, color=primær_farve, s=40, edgecolors='white', alpha=0.5)
                elif visning == "Afslutninger":
                    d = df_plot[df_plot['event_typeid'].isin([13, 14, 15, 16])]
                    goals = d[d['event_typeid'] == 16]
                    misses = d[d['event_typeid'].isin([13, 14, 15])]
                    ax.scatter(misses.event_x, misses.event_y, color='grey', s=60, edgecolors='black', alpha=0.6)
                    ax.scatter(goals.event_x, goals.event_y, color=primær_farve, s=120, marker='s', edgecolors='black', zorder=5)
                elif visning == "Erobringer":
                    d = df_plot[df_plot['event_typeid'].isin([7, 8, 12, 49])]
                    ax.scatter(d.event_x, d.event_y, color='orange', s=100, edgecolors='white')
            
            st.pyplot(fig, use_container_width=True)
    
    with t_phys:
        df_phys = get_physical_data(valgt_spiller, valgt_player_uuid, valgt_hold, conn)
    
        if df_phys is None or df_phys.empty:
            st.warning("Ingen fysiske data fundet for denne spiller.")
        else:
            df_phys.columns = df_phys.columns.str.lower()
            df_phys['match_date'] = pd.to_datetime(df_phys['match_date'])
            df_phys = df_phys.sort_values('match_date', ascending=False)
            
            hsr_val = df_phys.get('hsr', pd.Series(0, index=df_phys.index))
            spr_val = df_phys.get('sprinting', pd.Series(0, index=df_phys.index))
            
            df_phys['hsr_total'] = hsr_val + spr_val
            latest = df_phys.iloc[0]
    
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Distance", f"{round(latest.get('distance', 0)/1000, 2)} km")
            m2.metric("HSR", f"{int(latest.get('hsr_total', 0))} m")
            m3.metric("Topfart", f"{round(float(latest.get('top_speed', 0)), 1)} km/t")
            m4.metric("Højintense", int(latest.get('hi_runs', 0)))
    
            t_sub_log, t_sub_charts = st.tabs(["Kampoversigt", "Grafer"])
                    
            with t_sub_charts:
                cat_choice = st.segmented_control("Vælg metrik", options=["HSR (m)", "Sprint (m)", "Distance (km)", "Topfart (km/t)"], default="HSR (m)", key="phys_graph_control")
                mapping = {"HSR (m)": ("hsr", 1, "m"), "Sprint (m)": ("sprinting", 1, "m"), "Distance (km)": ("distance", 1000, "km"), "Topfart (km/t)": ("top_speed", 1, "km/t")}
                col, div, suffix = mapping[cat_choice]
    
                df_chart = df_phys[df_phys['match_date'] >= '2025-07-01'].copy()
                df_chart = df_chart.drop_duplicates(subset=['match_date', 'match_teams'])
                df_chart = df_chart.sort_values('match_date', ascending=True)
    
                if not df_chart.empty:
                    def get_opponent(teams_str, my_team):
                        if not teams_str: return "?"
                        parts = [p.strip() for p in teams_str.split('-')]
                        if len(parts) < 2: return teams_str
                        return parts[1] if parts[0].lower() in my_team.lower() else parts[0]
    
                    df_chart['Opponent'] = df_chart['match_teams'].apply(lambda x: get_opponent(x, valgt_hold))
                    df_chart['Label'] = df_chart['Opponent'] + "<br>" + df_chart['match_date'].dt.strftime('%d/%m')
                    y_vals = df_chart[col] / div
                    season_avg = y_vals.mean()
    
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=df_chart['Label'], 
                        y=y_vals,
                        text=y_vals.apply(lambda x: f"{x:.0f}" if x > 100 else f"{x:.1f}"),
                        textposition='outside', 
                        marker_color=primær_farve, 
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
