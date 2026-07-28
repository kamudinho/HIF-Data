import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO
import requests
from PIL import Image
import os
from mplsoccer import Pitch
import io
import base64

# --- DATA OG MAPPING ---
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.utils.mapping import OPTA_EVENT_TYPES, OPTA_QUALIFIERS, get_action_label, is_assist, har_qualifier
from data.utils.match_data import classify_take_on

# --- GENERELLE UI-HJÆLPERE ---
from utils.helpers import get_logo_img, get_team_color, get_ordinal, draw_player_info_box

# --- IMPORT AF SPILLERE OG SQL ---
from data.sql.liga_spillere import hent_match_og_haendelsesdata

# --- KONFIGURATION (HVIDOVRE-APP / 2026/2027) ---
DB = "KLUB_HVIDOVREIF.AXIS"
SEASONNAME = "2026/2027"
TEAM_WYID = 7490
COMPETITION_WYID = (328,)
COMP_MAP = { 
    335: "Superliga", 
    328: "NordicBet Liga", 
    329: "2. division", 
    43319: "3. division", 
    331: "Oddset Pokalen", 
    1305: "U19 Ligaen" 
}
LIGA_IDS = "('2mb332vncy4450vu14paj8844', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '335', '328', '329', '43319', '331')"

# --- GRAFISKE HJÆLPEFUNKTIONER ---
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

# --- DATAFUNKTIONER ---
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

    # 1. HOLDVALG
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

    # 2. HENT DATA VIA FILEN I data/sql/liga_spillere.py
    with st.spinner("Henter spillere..."):
        df_all, df_expected, df_db_stats = hent_match_og_haendelsesdata(
            conn, DB, valgt_uuid_hold, LIGA_IDS, navne_map
        )
    
    if df_all is None or df_all.empty:
        st.warning("Ingen hændelsesdata fundet.")
        st.stop()
    
    df_all = df_all.dropna(subset=['visningsnavn'])
    df_all['event_timestamp'] = pd.to_datetime(df_all['event_timestamp_str'])
    df_all['qual_list'] = df_all['qualifiers'].fillna('').str.split(',')
    
    # Forbered pasningskolonner tidligt
    df_all['Pasninger_Total'] = (df_all['event_typeid'] == 1).astype(int)
    df_all['Pasninger_Succes'] = ((df_all['event_typeid'] == 1) & (df_all['outcome'] == 1)).astype(int)
    
    df_all_temp = df_all.rename(columns={
        'event_x': 'EVENT_X', 'event_y': 'EVENT_Y', 'event_typeid': 'EVENT_TYPEID',
        'visningsnavn': 'VISNINGSNAVN', 'player_optauuid': 'PLAYER_OPTAUUID',
        'outcome': 'OUTCOME', 'qualifiers': 'QUALIFIERS'
    })
    df_all['Action_Label'] = df_all_temp.apply(get_action_label, axis=1)
    
    df_spillere_unikke = df_all[['visningsnavn', 'player_optauuid']].drop_duplicates()
    
    spiller_options = {}
    for _, r in df_spillere_unikke.iterrows():
        navn = r['visningsnavn']
        uuid = r['player_optauuid']
        if list(spiller_options.keys()).count(navn) > 0:
            visnings_label = f"{navn} ({uuid[-4:]})"
        else:
            visnings_label = navn
        spiller_options[visnings_label] = uuid
    
    spiller_liste = sorted(list(spiller_options.keys()))
    valgt_label = col_h_spiller.selectbox("Spiller", spiller_liste, label_visibility="collapsed")
    
    valgt_player_uuid = spiller_options[valgt_label]
    valgt_spiller = valgt_label.split(" (")[0]
    
    df_spiller = df_all[df_all['player_optauuid'] == valgt_player_uuid].copy()
    
    # --- BEREGN TRUP-STATS INKL. DRIBLINGER OG DUELLER ---
    def count_event_with_qual(df_group, eid, qids):
        return df_group.apply(lambda r: har_qualifier(r['event_typeid'], r.get('qual_list', []), eid, qids), axis=1).sum()
    
    event_stats = df_all.groupby(['player_optauuid', 'visningsnavn']).apply(lambda x: pd.Series({
        'Aktioner': len(x),
        'Gule_kort': count_event_with_qual(x, 17, 31),
        'Roede_kort': count_event_with_qual(x, 17, 33),
        'Indskiftet': (x['event_typeid'] == 19).sum(),
        'Udskiftet': (x['event_typeid'] == 18).sum(),
        'Pasninger': x['Pasninger_Total'].sum(),
        'Pasninger_Succes': x['Pasninger_Succes'].sum(),
        'Stikninger': count_event_with_qual(x, 1, 4),
        'Indlæg': count_event_with_qual(x, 1, [2, 155]),
        'Afslutninger': x['event_typeid'].isin([13, 14, 15, 16]).sum(),
        'Erobringer': x['event_typeid'].isin([7, 8, 12, 49]).sum(),
        
        # --- NYE DRIBLING OG DUEL STATS ---
        'Driblinger': (x['event_typeid'] == 3).sum(),
        'Driblinger_Succes': x.apply(lambda r: 1 if str(r['event_typeid']) == "3" and "211" not in [str(q).strip() for q in (r.get('qual_list', []) if isinstance(r.get('qual_list', []), list) else str(r.get('qual_list', '')).split(','))] else 0, axis=1).sum(),
        'Gennembrud_Overtake': x.apply(lambda r: 1 if str(r['event_typeid']) == "3" and "465" in [str(q).strip() for q in (r.get('qual_list', []) if isinstance(r.get('qual_list', []), list) else str(r.get('qual_list', '')).split(','))] else 0, axis=1).sum(),
        'Rum_Driblinger_Space': x.apply(lambda r: 1 if str(r['event_typeid']) == "3" and "464" in [str(q).strip() for q in (r.get('qual_list', []) if isinstance(r.get('qual_list', []), list) else str(r.get('qual_list', '')).split(','))] else 0, axis=1).sum(),
        'Offensive_Dueller': x.apply(lambda r: 1 if "286" in [str(q).strip() for q in (r.get('qual_list', []) if isinstance(r.get('qual_list', []), list) else str(r.get('qual_list', '')).split(','))] else 0, axis=1).sum(),
        'Defensive_Dueller': x.apply(lambda r: 1 if "285" in [str(q).strip() for q in (r.get('qual_list', []) if isinstance(r.get('qual_list', []), list) else str(r.get('qual_list', '')).split(','))] else 0, axis=1).sum(),
        'Defensive_1v1_Stoppet': x.apply(lambda r: 1 if "467" in [str(q).strip() for q in (r.get('qual_list', []) if isinstance(r.get('qual_list', []), list) else str(r.get('qual_list', '')).split(','))] else 0, axis=1).sum(),
        
        'Chancer_skabt': x.apply(lambda r: '210' in r.get('qual_list', []), axis=1).sum(),
        'Key_Passes': x.apply(lambda r: '210' in r.get('qual_list', []), axis=1).sum(),
        'Tacklinger': (x['event_typeid'] == 7).sum(),
        'Clearinger': (x['event_typeid'] == 12).sum(),
        'Blokeringer': (x['event_typeid'] == 55).sum(),
        'Interceptioner': (x['event_typeid'] == 5).sum(),
        'Frispark_imod': (x['event_typeid'] == 4).sum()
    })).reset_index()
    
    event_stats = event_stats.drop_duplicates(subset=['player_optauuid']).set_index('player_optauuid')
    
    if df_expected is not None and not df_expected.empty:
        match_stats = df_expected.groupby('player_optauuid').agg({
            'match_id': 'nunique',
            'minutes': 'sum',
            'xg': 'sum',
            'xa': 'sum'
        }).rename(columns={'match_id': 'Kampe', 'minutes': 'Minutter', 'xg': 'xG', 'xa': 'xA'})
        truppen_stats_raw = event_stats.join(match_stats, how='left').fillna(0)
    else:
        truppen_stats_raw = event_stats.copy()
        truppen_stats_raw['Kampe'] = 0
        truppen_stats_raw['Minutter'] = 0
        truppen_stats_raw['xG'] = 0.0
        truppen_stats_raw['xA'] = 0.0
    
    if df_db_stats is not None and not df_db_stats.empty:
        db_stats_clean = df_db_stats.drop_duplicates(subset=['player_optauuid']).set_index('player_optauuid')
        truppen_stats_raw['Mål'] = db_stats_clean['goals']
        truppen_stats_raw['Assists'] = db_stats_clean['assists']
    else:
        truppen_stats_raw['Mål'] = 0
        truppen_stats_raw['Assists'] = 0
    
    truppen_stats_raw['Mål'] = truppen_stats_raw['Mål'].fillna(0).astype(int)
    truppen_stats_raw['Assists'] = truppen_stats_raw['Assists'].fillna(0).astype(int)
    truppen_stats = truppen_stats_raw.copy()
    
    # --- BEREGN PASNINGSPROCENT DIREKTE PÅ TRUPPEN_STATS ---
    truppen_stats['Pasningsprocent'] = (
        (truppen_stats['Pasninger_Succes'] / truppen_stats['Pasninger']) * 100
    ).where(truppen_stats['Pasninger'] > 0, 0).round(1)
    
    # --- OPSETNING AF FANER ---
    t_team, t_profile, t_pitch, t_phys = st.tabs(["Holdoversigt", "Spillerprofil", "Spilleraktioner", "Fysisk data"])
    
    # --- UI & VISNING ---
    with t_team:
        col_t_title, col_t_btn = st.columns([2.7, 1.3])
        
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
                options=["Generelt", "Opbygning", "Offensiv", "Defensiv"], 
                default="Generelt",
                key="team_kategori_control",
                label_visibility="collapsed"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        if not truppen_stats.empty:
            df_vis_truppen = truppen_stats.reset_index()
            
            # --- KOLONNE-OPSÆTNING ---
            gen_kolonner = [
                'visningsnavn', 'Kampe', 'Minutter', 'Aktioner', 'Pasninger', 'Pasningsprocent', 
                'Mål', 'Assists', 'Udskiftet', 'Indskiftet', 'Gule_kort', 'Roede_kort'
            ]
            
            # --- FOKUS PÅ OPBYGNING OG SPILFORDELING ---
            opb_kolonner = [
                'visningsnavn', 'Aktioner', 'Pasninger', 'Pasningsprocent', 'Key_Passes', 'Stikninger', 
                'Driblinger', 'Driblinger_Succes', 'Rum_Driblinger_Space'
            ]
            
            # --- FOKUS PÅ DEN SIDSTE TREDJEDEL & AFSLUTNINGER ---
            off_kolonner = [
                'visningsnavn', 'Aktioner', 'Afslutninger', 'xG', 'Chancer_skabt', 
                'Indlæg', 'xA', 'Offensive_Dueller', 'Gennembrud_Overtake', 'Driblinger_Succes'
            ]
            
            def_kolonner = [
                'visningsnavn', 'Aktioner', 'Erobringer', 'Tacklinger', 'Clearinger', 
                'Blokeringer', 'Interceptioner', 'Defensive_Dueller', 'Defensive_1v1_Stoppet', 'Frispark_imod'
            ]
            
            if kategori_valg == "Generelt":
                eksisterende_kolonner = [k for k in gen_kolonner if k in df_vis_truppen.columns]
            elif kategori_valg == "Opbygning":
                eksisterende_kolonner = [k for k in opb_kolonner if k in df_vis_truppen.columns]
            elif kategori_valg == "Offensiv":
                eksisterende_kolonner = [k for k in off_kolonner if k in df_vis_truppen.columns]
            elif kategori_valg == "Defensiv":
                eksisterende_kolonner = [k for k in def_kolonner if k in df_vis_truppen.columns]
            else:  
                eksisterende_kolonner = [k for k in df_vis_truppen.columns if k != 'player_optauuid']
            
            df_visning = df_vis_truppen[eksisterende_kolonner].copy()
            
            df_visning = df_visning.rename(columns={
                'visningsnavn': 'Spiller',
                'Pasningsprocent': 'Pasningsprocent (%)',
                'Gule_kort': 'Gule kort',
                'Roede_kort': 'Røde kort',
                'Chancer_skabt': 'Chancer skabt',
                'Key_Passes': 'Key Passes',
                'Frispark_imod': 'Frispark',
                'Driblinger_Ialt': 'Driblinger, ialt', 
                'Driblinger_Succes': 'Driblinger (Succes)', 
                'Gennembrud_Overtake': 'Gennembrud, 1v1', 
                'Rum_Driblinger_Space': 'Driblinger, 1v1', 
                'Offensive_Dueller': 'Off. dueller',
                'Defensive_Dueller': 'Def. dueller', 
                'Defensive_1v1_Stoppet': 'Def. 1v1',
                'Pasninger_Succes': 'Pasnings%'
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
            st.stop()
    
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
        df_filtreret = df_spiller[~df_spiller['Action_Label'].isin(['Pasning', 'Indkast'])]
        
        akt_stats = pd.DataFrame()
        if not df_filtreret.empty:
            akt_stats = df_filtreret.groupby('Action_Label').agg(Total=('outcome', 'count'), Succes=('outcome', 'sum')).sort_values('Total', ascending=False)
    
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
            st.warning("Data findes endnu ikke hos Second Spectrum")
        else:
            df_phys.columns = df_phys.columns.str.lower()
            df_phys['match_date'] = pd.to_datetime(df_phys['match_date'])
            df_phys = df_phys.sort_values('match_date', ascending=False)
            
            hsr_val = df_phys.get('hsr', df_phys.get('high speed running', pd.Series(0, index=df_phys.index)))
            spr_val = df_phys.get('sprinting', df_phys.get('sprint', pd.Series(0, index=df_phys.index)))
            
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
                col_key, div, suffix = mapping[cat_choice]
    
                df_chart = df_phys[df_phys['match_date'] >= '2026-07-01'].copy()
                df_chart = df_chart.drop_duplicates(subset=['match_date', 'match_teams'])
                df_chart = df_chart.sort_values('match_date', ascending=True)
    
                if not df_chart.empty:
                    def get_opponent(teams_str, my_team):
                        if not teams_str: return "?"
                        parts = [p.strip() for p in teams_str.split('-')]
                        if len(parts) < 2: return teams_str
                        return parts[1] if parts[0].lower() in my_team.lower() else parts[0]
    
                    df_chart['opponent'] = df_chart['match_teams'].apply(lambda x: get_opponent(str(x), valgt_hold))
                    df_chart['dato_str'] = df_chart['match_date'].dt.strftime('%d/%m')
                    df_chart['hover_label'] = df_chart['dato_str'] + " vs " + df_chart['opponent']
                    df_chart['y_val'] = df_chart[col_key] / div
    
                    fig_phys = go.Figure(go.Bar(
                        x=df_chart['hover_label'],
                        y=df_chart['y_val'],
                        marker_color=primær_farve,
                        text=df_chart['y_val'].round(1),
                        textposition='auto',
                    ))
                    fig_phys.update_layout(
                        margin=dict(t=20, b=20, l=20, r=20),
                        height=300,
                        xaxis=dict(tickangle=-30),
                        yaxis=dict(title=suffix)
                    )
                    st.plotly_chart(fig_phys, use_container_width=True)

            with t_sub_log:
                df_log = df_phys[['match_date', 'match_teams', 'distance', 'hsr_total', 'top_speed', 'hi_runs']].copy()
                df_log['match_date'] = df_log['match_date'].dt.strftime('%Y-%m-%d')
                df_log['distance'] = (df_log['distance'] / 1000).round(2)
                df_log['top_speed'] = df_log['top_speed'].round(1)
                
                df_log = df_log.rename(columns={
                    'match_date': 'Dato',
                    'match_teams': 'Kamp',
                    'distance': 'Distance (km)',
                    'hsr_total': 'HSR (m)',
                    'top_speed': 'Topfart (km/t)',
                    'hi_runs': 'Højintense løb'
                })
                st.dataframe(df_log, use_container_width=True, hide_index=True)
