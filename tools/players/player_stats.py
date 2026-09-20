#tools/players/player_stats.py
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

# --- SPILLER-KATEGORIER ---
from data.utils.spiller_qualifiers import ACTION_CATEGORIES, POSITION_ACTIONS

# --- GENERELLE UI-HJÆLPERE ---
from utils.helpers import get_logo_img, get_team_color, get_ordinal, draw_player_info_box

# --- IMPORT AF SPILLERE OG SQL ---
from data.sql.liga_spillere import hent_spiller_event_stats

try:
    from data.players import player_mapping
    valgt_player_uuid = st.session_state.get('valgt_player_uuid', getattr(player_mapping, 'valgt_player_uuid', None))
    valgt_spiller = st.session_state.get('valgt_spiller', getattr(player_mapping, 'valgt_spiller', None))
    df_spiller = getattr(player_mapping, 'df_spiller', None)
    hold_logo = getattr(player_mapping, 'hold_logo', None)
    primær_farve = getattr(player_mapping, 'primær_farve', "#df003b")
    valgt_hold = getattr(player_mapping, 'valgt_hold', "Hvidovre")
    conn = getattr(player_mapping, 'conn', None)
    SEASONNAME = getattr(player_mapping, 'SEASONNAME', "2025/2026")
except ImportError:
    st.error("Kunne ikke finde eller indlæse 'player_mapping.py'. Sørg for filen ligger i mappen.")
    st.stop()

# --- POSITIONSDATA ---
_STATIC_PLAYERS = getattr(player_mapping, 'PLAYER_MAPPING', [])
POSITION_MAP = {
    str(p.get('player_optauuid')).strip(): p.get('position', 'Ukendt')
    for p in _STATIC_PLAYERS if p.get('player_optauuid')
}
POSITION_DA = {
    "Goalkeeper": "Målmand",
    "Defender": "Forsvar",
    "Midfielder": "Midtbane",
    "Attacker": "Angriber",
}

DB = "KLUB_HVIDOVREIF.AXIS"
TEAM_WYID = 7490
COMPETITION_WYID = (328,)
LIGA_IDS = "('2mb332vncy4450vu14paj8844', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '335', '328', '329', '43319', '331')"


@st.cache_data(ttl=600, show_spinner="Indlæser spillerliste...")
def hent_navne_map() -> dict:
    navne_map = {}
    try:
        for p in _STATIC_PLAYERS:
            uuid = str(p.get('player_optauuid', '')).strip()
            navn = p.get('navn') or p.get('visningsnavn') or p.get('name')
            if uuid and navn:
                navne_map[uuid] = navn
    except Exception:
        pass

    try:
        csv_path = os.path.join(os.getcwd(), 'data', 'players', '1div_overskrivning.csv')
        if os.path.exists(csv_path):
            df_csv = pd.read_csv(csv_path)
            for _, r in df_csv.iterrows():
                navne_map[str(r['PLAYER_OPTAUUID']).strip()] = r['NAVN']
    except Exception:
        pass
    return navne_map


@st.cache_data(ttl=1800, show_spinner=False)
def hent_holdliste(_conn) -> dict:
    df_teams_raw = _conn.query(
        f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID "
        f"FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}"
    )
    if df_teams_raw is not None:
        df_teams_raw.columns = df_teams_raw.columns.str.lower()
    else:
        df_teams_raw = pd.DataFrame()

    mapping_lookup = {
        str(info['opta_uuid']).lower().replace('t', ''): name
        for name, info in TEAMS.items() if 'opta_uuid' in info
    }

    team_map = {}
    if not df_teams_raw.empty:
        for _, r in df_teams_raw.iterrows():
            uuid_clean = str(r['contestanthome_optauuid']).lower().replace('t', '')
            if uuid_clean in mapping_lookup:
                team_map[mapping_lookup[uuid_clean]] = r['contestanthome_optauuid']
    return team_map


@st.cache_data(ttl=300, show_spinner="Henter data fra Snowflake...")
def hent_trup_data_fra_sql(_conn, valgt_uuid_hold: str, navne_map: dict):
    df_stats = hent_spiller_event_stats(
        _conn, DB, LIGA_IDS, hold_optauuid=valgt_uuid_hold, navne_map=navne_map
    )
    if df_stats is not None and not df_stats.empty:
        if 'player_optauuid' not in df_stats.columns:
            df_stats = df_stats.reset_index()
        df_stats.columns = df_stats.columns.str.lower()
    else:
        df_stats = pd.DataFrame()
    return df_stats


def vis_side(dp=None):
    navne_map = hent_navne_map()

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

    team_map = hent_holdliste(conn)

    col_spacer_top, col_h_hold, col_h_spiller = st.columns([2, 1.2, 1.2])

    default_team_idx = 0
    team_names = sorted(list(team_map.keys()))
    for idx, name in enumerate(team_names):
        if "hvidovre" in name.lower():
            default_team_idx = idx
            break

    valgt_hold = col_h_hold.selectbox("Hold", team_names if team_names else ["Hvidovre"], index=default_team_idx if team_names else 0, label_visibility="collapsed")
    valgt_uuid_hold = team_map.get(valgt_hold, "t7490")
    hold_logo = get_logo_img(valgt_uuid_hold)
    primær_farve = get_team_color(valgt_hold, "primary", "#df003b")

    with st.spinner("Henter spillere og statistik..."):
        truppen_stats = hent_trup_data_fra_sql(conn, valgt_uuid_hold, navne_map)

    if truppen_stats is None or truppen_stats.empty:
        st.warning("Ingen hændelsesdata fundet for dette hold.")
        st.stop()

    # --- RENGØRING OG FJERNELSE AF DUBLEREDE RÆKKER ---
    truppen_stats.columns = truppen_stats.columns.str.lower()

    if 'player_optauuid' in truppen_stats.columns:
        truppen_stats = truppen_stats[
            truppen_stats['player_optauuid'].notna() & 
            (truppen_stats['player_optauuid'].astype(str).str.strip() != "") & 
            (truppen_stats['player_optauuid'].astype(str).str.lower() != "none") &
            (truppen_stats['player_optauuid'].astype(str).str.lower() != "nan")
        ]
        truppen_stats = truppen_stats.drop_duplicates(subset=['player_optauuid'], keep='first')

    # Sikr at visningsnavn er sat korrekt ud fra match_name, hvis det mangler
    if 'match_name' in truppen_stats.columns:
        if 'visningsnavn' not in truppen_stats.columns:
            truppen_stats['visningsnavn'] = truppen_stats['match_name']
        else:
            mask_fejl = (
                truppen_stats['visningsnavn'].isna() | 
                truppen_stats['visningsnavn'].astype(str).str.lower().isin(['fejlspiller', 'nan', 'none', ''])
            )
            truppen_stats.loc[mask_fejl, 'visningsnavn'] = truppen_stats.loc[mask_fejl, 'match_name']

    # FJERN RÆKKER HVOR NAVNET STADIG ER "NONE", "NAN" ELLER TOMT
    if 'visningsnavn' in truppen_stats.columns:
        truppen_stats = truppen_stats[
            truppen_stats['visningsnavn'].notna() &
            ~truppen_stats['visningsnavn'].astype(str).str.lower().isin(['none', 'nan', 'fejlspiller', ''])
        ]
    
    df_spillere_unikke = truppen_stats.copy()

    spiller_options = {}
    for _, r in df_spillere_unikke.iterrows():
        uuid = r.get('player_optauuid')
        if not uuid:
            continue
            
        uuid_str = str(uuid).strip()

        navn = (
            navne_map.get(uuid_str)
            or r.get('match_name')
            or r.get('visningsnavn')
            or f"{r.get('first_name', '')} {r.get('short_last_name', '')}".strip()
        )
        
        if not navn or str(navn).lower() in ["nan", "none", "", "fejlspiller"]:
            continue

        eng_pos = POSITION_MAP.get(uuid_str, 'Ukendt')
        da_pos = POSITION_DA.get(eng_pos, eng_pos)
        
        visnings_label = f"{navn} ({da_pos})"
        spiller_options[visnings_label] = uuid_str

    spiller_liste = sorted(list(spiller_options.keys()))
    valgt_label = col_h_spiller.selectbox("Spiller", spiller_liste if spiller_liste else [""], label_visibility="collapsed")

    valgt_player_uuid = spiller_options.get(valgt_label, None)
    df_spiller = truppen_stats[truppen_stats['player_optauuid'].astype(str).str.strip() == str(valgt_player_uuid)].copy() if valgt_player_uuid else pd.DataFrame()
    
    t_team, t_matches = st.tabs(["Holdoversigt", "Kampoversigt"])

    # Fælleskolonner til visning (uden player_optauuid)
    gen_kolonner = ['visningsnavn', 'kampe', 'minutter', 'aktioner', 'pasninger', 'pasningsprocent', 'mål', 'assists', 'udskiftet', 'indskiftet', 'gule_kort', 'roede_kort']
    opb_kolonner = ['visningsnavn', 'aktioner', 'pasninger', 'pasningsprocent', 'key_passes', 'fremadrettede_pasninger', 'stikninger', 'driblinger', 'driblinger_succes', 'rum_driblinger_space']
    off_kolonner = ['visningsnavn', 'aktioner', 'afslutninger', 'xg', 'chancer_skabt', 'indlæg', 'xa', 'offensive_dueller', 'gennembrud_overtake', 'driblinger_succes']
    def_kolonner = ['visningsnavn', 'aktioner', 'erobringer', 'tacklinger', 'clearinger', 'blokeringer', 'interceptioner', 'defensive_dueller', 'defensive_1v1_stoppet', 'frispark_imod']

    renaming_dict = {
        'visningsnavn': 'Spiller',
        'pasningsprocent': 'Pasning (%)',
        'gule_kort': 'Gule kort',
        'roede_kort': 'Røde kort',
        'chancer_skabt': 'Chancer skabt',
        'key_passes': 'Key Passes',
        'frispark_imod': 'Frispark',
        'fremadrettede_pasninger': 'Fremad. pasninger',
        'driblinger_ialt': 'Driblinger, ialt', 
        'driblinger_succes': 'Driblinger (Succes)', 
        'gennembrud_overtake': 'Gennembrud, 1v1', 
        'rum_driblinger_space': 'Driblinger, 1v1', 
        'offensive_dueller': 'Off. dueller',
        'defensive_dueller': 'Def. dueller', 
        'defensive_1v1_stoppet': 'Def. 1v1'
    }

    # --- HOLDOVERSIGT ---
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
            if kategori_valg == "Generelt":
                eksisterende_kolonner = [k for k in gen_kolonner if k in truppen_stats.columns]
            elif kategori_valg == "Opbygning":
                eksisterende_kolonner = [k for k in opb_kolonner if k in truppen_stats.columns]
            elif kategori_valg == "Offensiv":
                eksisterende_kolonner = [k for k in off_kolonner if k in truppen_stats.columns]
            elif kategori_valg == "Defensiv":
                eksisterende_kolonner = [k for k in def_kolonner if k in truppen_stats.columns]
            else:  
                eksisterende_kolonner = [k for k in truppen_stats.columns if k != 'player_optauuid']

            df_visning = truppen_stats[eksisterende_kolonner].copy()
            if 'aktioner' in df_visning.columns:
                df_visning = df_visning.sort_values(by='aktioner', ascending=False)

            df_visning = df_visning.rename(columns=renaming_dict)

            beregnet_hoejde = int(len(df_visning) * 38 + 45)
            st.dataframe(
                df_visning, 
                use_container_width=True, 
                hide_index=True,
                height=beregnet_hoejde,
                column_config={"Pasning (%)": st.column_config.NumberColumn("Pasning (%)", format="%.1f%%")}
            )
        else:
            st.info("Ingen trup-data tilgængelig endnu.")

    # --- KAMPOVERSIGT ---
    with t_matches:
        col_t_title, col_t_matches, col_t_btn = st.columns([1.3, 2.0, 1.7], vertical_alignment="center")
        with col_t_title:
            logo_html = ""
            if hold_logo is not None:
                buffered = io.BytesIO()
                hold_logo.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                logo_html = f'<img src="data:image/png;base64,{img_str}" style="height: 26px; margin-right: 10px; object-fit: contain;">'
            st.markdown(f'<div style="display: flex; align-items: center;">{logo_html}<span style="font-size: 16px; font-weight: bold; line-height: 1;">KAMPOVERSIGT</span></div>', unsafe_allow_html=True)
            
        sql_matches = f"""
            SELECT MATCH_OPTAUUID, MATCH_DATE_FULL, WEEK, MATCH_STATUS, CONTESTANTHOME_OPTAUUID, CONTESTANTHOME_NAME, CONTESTANTAWAY_OPTAUUID, CONTESTANTAWAY_NAME, TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE
            FROM {DB}.OPTA_MATCHINFO
            WHERE TOURNAMENTCALENDAR_NAME = '{SEASONNAME}'
              AND MATCH_STATUS = 'Played'
              AND (CONTESTANTHOME_OPTAUUID = '{valgt_uuid_hold}' OR CONTESTANTAWAY_OPTAUUID = '{valgt_uuid_hold}')
            ORDER BY MATCH_DATE_FULL DESC
        """
        df_matches = conn.query(sql_matches)
        if df_matches is None:
            df_matches = pd.DataFrame()
            
        valgt_kamp_uuid = None
        if not df_matches.empty:
            df_matches.columns = df_matches.columns.str.lower()
            df_matches['match_date_full'] = pd.to_datetime(df_matches['match_date_full'], errors='coerce')
            
            kamp_options = {}
            for _, r in df_matches.iterrows():
                er_hjemme = str(r['contestanthome_optauuid']) == str(valgt_uuid_hold)
                modstander = r['contestantaway_name'] if er_hjemme else r['contestanthome_name']
                hjemme_maal = int(r['total_home_score']) if pd.notna(r['total_home_score']) else 0
                ude_maal = int(r['total_away_score']) if pd.notna(r['total_away_score']) else 0
                hold_maal = hjemme_maal if er_hjemme else ude_maal
                mod_maal = ude_maal if er_hjemme else hjemme_maal
                label = f"Kamp {r['week']}: vs. {modstander} ({hold_maal}-{mod_maal})"
                kamp_options[label] = str(r['match_optauuid'])
                
            with col_t_matches:
                valgt_kamp_label = st.selectbox("Vælg kamp", list(kamp_options.keys()), key="valgt_kamp_dropdown", label_visibility="collapsed")
                valgt_kamp_uuid = kamp_options[valgt_kamp_label]
            
        with col_t_btn:
            st.markdown('<div style="display: flex; justify-content: flex-end;">', unsafe_allow_html=True)
            kategori_valg_kamp = st.segmented_control(
                "Visningskategori Kamp", 
                options=["Generelt", "Opbygning", "Offensiv", "Defensiv"], 
                default="Generelt",
                key="match_kategori_control",
                label_visibility="collapsed"
            )
            st.markdown('</div>', unsafe_allow_html=True)
     
        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
            
        if not df_matches.empty and valgt_kamp_uuid:
            df_kamp_stats = hent_spiller_event_stats(
                conn, DB, LIGA_IDS, hold_optauuid=valgt_uuid_hold, match_optauuid=valgt_kamp_uuid, navne_map=navne_map
            )
            if df_kamp_stats is not None and not df_kamp_stats.empty:
                if 'player_optauuid' not in df_kamp_stats.columns:
                    df_kamp_stats = df_kamp_stats.reset_index()
                df_kamp_stats.columns = df_kamp_stats.columns.str.lower()
                
                if 'player_optauuid' in df_kamp_stats.columns:
                    df_kamp_stats = df_kamp_stats.drop_duplicates(subset=['player_optauuid'], keep='first')

                if 'match_name' in df_kamp_stats.columns:
                    if 'visningsnavn' not in df_kamp_stats.columns:
                        df_kamp_stats['visningsnavn'] = df_kamp_stats['match_name']
                    else:
                        mask_kamp_fejl = (
                            df_kamp_stats['visningsnavn'].isna() | 
                            df_kamp_stats['visningsnavn'].astype(str).str.lower().isin(['fejlspiller', 'nan', 'none', ''])
                        )
                        df_kamp_stats.loc[mask_kamp_fejl, 'visningsnavn'] = df_kamp_stats.loc[mask_kamp_fejl, 'match_name']

                # FJERN RÆKKER HVOR NAVNET ER "NONE", "NAN" ELLER TOMT FOR DENNE KAMP
                if 'visningsnavn' in df_kamp_stats.columns:
                    df_kamp_stats = df_kamp_stats[
                        df_kamp_stats['visningsnavn'].notna() &
                        ~df_kamp_stats['visningsnavn'].astype(str).str.lower().isin(['none', 'nan', 'fejlspiller', ''])
                    ]

                if kategori_valg_kamp == "Generelt":
                    eks_kol_kamp = [k for k in gen_kolonner if k in df_kamp_stats.columns]
                elif kategori_valg_kamp == "Opbygning":
                    eks_kol_kamp = [k for k in opb_kolonner if k in df_kamp_stats.columns]
                elif kategori_valg_kamp == "Offensiv":
                    eks_kol_kamp = [k for k in off_kolonner if k in df_kamp_stats.columns]
                elif kategori_valg_kamp == "Defensiv":
                    eks_kol_kamp = [k for k in def_kolonner if k in df_kamp_stats.columns]
                else:
                    eks_kol_kamp = [k for k in df_kamp_stats.columns if k != 'player_optauuid']

                df_visning_kamp = df_kamp_stats[eks_kol_kamp].copy()
                if 'aktioner' in df_visning_kamp.columns:
                    df_visning_kamp = df_visning_kamp.sort_values(by='aktioner', ascending=False)
                df_visning_kamp = df_visning_kamp.rename(columns=renaming_dict)

                beregnet_hoejde_kamp = int(len(df_visning_kamp) * 38 + 45)
                st.dataframe(
                    df_visning_kamp, 
                    use_container_width=True, 
                    hide_index=True,
                    height=beregnet_hoejde_kamp,
                    column_config={"Pasning (%)": st.column_config.NumberColumn("Pasning (%)", format="%.1f%%")}
                )
            else:
                st.warning("Ingen hændelsesdata for denne kamp.")
        else:
            st.warning("Ingen spillede kampe fundet i denne sæson.")
