import base64
from io import BytesIO
import io
import os
import requests
from PIL import Image
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from mplsoccer import Pitch
import streamlit as st

# --- DATA OG MAPPING ---
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS, TEAM_COLORS, SEASONS
from data.utils.mapping import (
    OPTA_EVENT_TYPES,
    OPTA_QUALIFIERS,
    get_action_label,
    is_assist,
    har_qualifier,
)

# --- SPILLER-KATEGORIER (position -> aktionskategorier, offensiv/defensiv) ---
from data.utils.spiller_qualifiers import ACTION_CATEGORIES, POSITION_ACTIONS

# --- GENERELLE UI-HJÆLPERE ---
from utils.helpers import (
    get_logo_img,
    get_team_color,
    get_ordinal,
    draw_player_info_box,
)

# --- IMPORT AF SPILLERE OG SQL ---
from data.sql.liga_spillere import (
    hent_samlet_spiller_statistik,
    hent_match_og_haendelsesdata,
)

try:
    from data.players import player_mapping

    df_spiller = getattr(player_mapping, "df_spiller", None)
    hold_logo = getattr(player_mapping, "hold_logo", None)
    primær_farve = getattr(player_mapping, "primær_farve", "#df003b")
    valgt_hold = getattr(player_mapping, "valgt_hold", "Hvidovre")
    conn = getattr(player_mapping, "conn", None)
    SEASONNAME = getattr(player_mapping, "SEASONNAME", "2025/2026")
except ImportError:
    st.error(
        "Kunne ikke finde eller indlæse 'player_mapping.py'. Sørg for filen ligger i mappen."
    )
    st.stop()

# --- POSITIONSDATA ---
_STATIC_PLAYERS = getattr(player_mapping, "PLAYER_MAPPING", [])
POSITION_MAP = {
    str(p.get("player_optauuid")).strip(): p.get("position", "Ukendt")
    for p in _STATIC_PLAYERS
    if p.get("player_optauuid")
}
POSITION_DA = {
    "Goalkeeper": "Målmand",
    "Defender": "Forsvar",
    "Midfielder": "Midtbane",
    "Attacker": "Angriber",
}

POSITION_TO_SPQ = {
    "Goalkeeper": "GK",
    "Defender": "DEF",
    "Midfielder": "MID",
    "Attacker": "FWD",
}

DB = "KLUB_HVIDOVREIF.AXIS"

# --- DYNAMISK LIGA_IDS BYGGES SIKKERT ---
active_leagues = SEASONS.get(SEASONNAME, {})
optauuid_liste = list(active_leagues.values())

if optauuid_liste:
    rensede_uuids = [str(uuid).strip() for uuid in optauuid_liste if uuid]
    LIGA_IDS = "('" + "', '".join(rensede_uuids) + "')"
else:
    LIGA_IDS = "('2mb332vncy4450vu14paj8844')"


@st.cache_data(ttl=600, show_spinner=False)
def hent_navne_map() -> dict:
    try:
        if hasattr(player_mapping, "PLAYER_MAPPING"):
            mapping_data = player_mapping.PLAYER_MAPPING

            if isinstance(mapping_data, list):
                return {
                    str(r.get("player_optauuid") or r.get("PLAYER_OPTAUUID"))
                    .strip()
                    .lower()
                    .replace("t", ""): str(r.get("navn") or r.get("NAVN"))
                    for r in mapping_data
                    if (r.get("player_optauuid") or r.get("PLAYER_OPTAUUID"))
                    and (r.get("navn") or r.get("NAVN"))
                }
            elif isinstance(mapping_data, dict):
                return {
                    str(k).strip().lower().replace("t", ""): str(v)
                    for k, v in mapping_data.items()
                }

        return {}
    except Exception:
        return {}


@st.cache_data(ttl=1800, show_spinner=False)
def hent_holdliste(_conn) -> dict:
    sql_query = (
        "SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID "
        "FROM {db}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {liga_ids}"
    ).format(db=DB, liga_ids=LIGA_IDS)

    df_teams_raw = _conn.query(sql_query)
    if df_teams_raw is not None:
        df_teams_raw.columns = df_teams_raw.columns.str.lower()
    else:
        df_teams_raw = pd.DataFrame()

    mapping_lookup = {
        str(info["opta_uuid"]).lower().replace("t", ""): name
        for name, info in TEAMS.items()
        if "opta_uuid" in info
    }

    team_map = {}
    if not df_teams_raw.empty:
        for _, r in df_teams_raw.iterrows():
            uuid_clean = str(r["contestanthome_optauuid"]).lower().replace("t", "")
            if uuid_clean in mapping_lookup:
                team_map[mapping_lookup[uuid_clean]] = r[
                    "contestanthome_optauuid"
                ]
    return team_map


def vis_side(dp=None):
    navne_map = hent_navne_map()

    st.markdown(
        """
        <style>
        [data-testid="stMetricValue"] { font-size: 16px !important; text-align: center; font-weight: bold !important; width: 100%; }
        [data-testid="stMetricLabel"] { font-size: 10px !important; text-align: center; width: 100%; }
        [data-testid="stMetric"] { display: flex; flex-direction: column; align-items: center; }
        .player-header { font-size: 18px; font-weight: bold; margin-bottom: 10px; color: #1E1E1E; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    conn = _get_snowflake_conn()
    if not conn:
        return

    team_map = hent_holdliste(conn)

    col_spacer_top, col_h_hold = st.columns([3.5, 1.3])

    default_team_idx = 0
    team_names = sorted(list(team_map.keys()))
    for idx, name in enumerate(team_names):
        if "hvidovre" in name.lower():
            default_team_idx = idx
            break

    valgt_hold = col_h_hold.selectbox(
        "Hold",
        team_names if team_names else ["Hvidovre"],
        index=default_team_idx if team_names else 0,
        label_visibility="collapsed",
    )
    valgt_uuid_hold = team_map.get(valgt_hold, "t7490")
    hold_logo = get_logo_img(valgt_uuid_hold)
    primær_farve = get_team_color(valgt_hold, "primary", "#df003b")

    with st.spinner("Henter spillerstatistik..."):
        df_all_stats = hent_samlet_spiller_statistik(
            conn, DB, LIGA_IDS, navne_map
        )

    if df_all_stats is None or df_all_stats.empty:
        st.warning("Ingen spillerstatistik fundet.")
        st.stop()

    valgt_uuid_clean = str(valgt_uuid_hold).lower().replace("t", "")
    if "hold_optauuid" in df_all_stats.columns:
        df_hold_stats = df_all_stats[
            df_all_stats["hold_optauuid"]
            .astype(str)
            .str.lower()
            .str.replace("t", "")
            == valgt_uuid_clean
        ].copy()
    else:
        df_hold_stats = df_all_stats.copy()

    t_team, t_matches = st.tabs(["Holdoversigt", "Kampoversigt"])

    with t_team:
        col_t1_title, col_t1_btn = st.columns(
            [2.0, 2.0], vertical_alignment="center"
        )
        with col_t1_title:
            logo_html = ""
            if hold_logo is not None:
                buffered = io.BytesIO()
                hold_logo.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                logo_html = f'<img src="data:image/png;base64,{img_str}" style="height: 26px; margin-right: 10px; object-fit: contain;">'
            st.markdown(
                f'<div style="display: flex; align-items: center;">{logo_html}<span style="font-size: 16px; font-weight: bold; line-height: 1;">HOLDOVERSIGT - {valgt_hold.upper()}</span></div>',
                unsafe_allow_html=True,
            )

        with col_t1_btn:
            st.markdown(
                '<div style="display: flex; justify-content: flex-end;">',
                unsafe_allow_html=True,
            )
            kategori_valg_saeson = st.segmented_control(
                "Visningskategori Sæson",
                options=["Generelt", "Opbygning", "Offensiv", "Defensiv"],
                default="Generelt",
                key="saeson_kategori_control",
                label_visibility="collapsed",
            )
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

        if not df_hold_stats.empty:
            df_vis_saeson = df_hold_stats.copy()

            gen_kolonner = [
                "visningsnavn",
                "kampe",
                "minutter",
                "aktioner",
                "maal",
                "xg",
                "xa",
            ]
            opb_kolonner = [
                "visningsnavn",
                "pasninger",
                "pasningsprocent",
                "fremadrettede_pasninger",
            ]
            off_kolonner = ["visningsnavn", "afslutninger", "maal", "xg", "xa"]
            def_kolonner = [
                "visningsnavn",
                "tacklinger",
                "erobringer",
                "clearinger",
                "blokeringer",
            ]

            if kategori_valg_saeson == "Generelt":
                eksisterende_kolonner = [
                    k for k in gen_kolonner if k in df_vis_saeson.columns
                ]
            elif kategori_valg_saeson == "Opbygning":
                eksisterende_kolonner = [
                    k for k in opb_kolonner if k in df_vis_saeson.columns
                ]
            elif kategori_valg_saeson == "Offensiv":
                eksisterende_kolonner = [
                    k for k in off_kolonner if k in df_vis_saeson.columns
                ]
            elif kategori_valg_saeson == "Defensiv":
                eksisterende_kolonner = [
                    k for k in def_kolonner if k in df_vis_saeson.columns
                ]
            else:
                eksisterende_kolonner = [
                    k
                    for k in df_vis_saeson.columns
                    if k not in ["player_optauuid", "hold_optauuid"]
                ]

            df_visning_saeson = df_vis_saeson[eksisterende_kolonner].copy()
            if "aktioner" in df_visning_saeson.columns:
                df_visning_saeson = df_visning_saeson.sort_values(
                    by="aktioner", ascending=False
                )

            df_visning_saeson = df_visning_saeson.rename(
                columns={
                    "visningsnavn": "Spiller",
                    "kampe": "Kampe",
                    "minutter": "Minutter",
                    "aktioner": "Aktioner",
                    "pasninger": "Pasninger",
                    "pasningsprocent": "Pasning (%)",
                    "fremadrettede_pasninger": "Fremadrettede pasninger",
                    "afslutninger": "Afslutninger",
                    "maal": "Mål",
                    "xg": "xG",
                    "xa": "xA",
                    "tacklinger": "Tacklinger",
                    "erobringer": "Erobringer",
                    "clearinger": "Clearinger",
                    "blokeringer": "Blokeringer",
                }
            )

            beregnet_hoejde_saeson = int(len(df_visning_saeson) * 38 + 45)
            st.dataframe(
                df_visning_saeson,
                use_container_width=True,
                hide_index=True,
                height=beregnet_hoejde_saeson,
                column_config={
                    "Pasning (%)": st.column_config.NumberColumn(
                        "Pasning (%)", format="%.1f%%"
                    ),
                    "xG": st.column_config.NumberColumn("xG", format="%.2f"),
                    "xA": st.column_config.NumberColumn("xA", format="%.2f"),
                },
            )
        else:
            st.info("Ingen spillerstatistik fundet for det valgte hold.")

    with t_matches:
        col_t_title, col_t_matches, col_t_btn = st.columns(
            [1.3, 2.0, 1.7], vertical_alignment="center"
        )
        with col_t_title:
            logo_html = ""
            if hold_logo is not None:
                buffered = io.BytesIO()
                hold_logo.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                logo_html = f'<img src="data:image/png;base64,{img_str}" style="height: 26px; margin-right: 10px; object-fit: contain;">'
            st.markdown(
                f'<div style="display: flex; align-items: center;">{logo_html}<span style="font-size: 16px; font-weight: bold; line-height: 1;">KAMPOVERSIGT - {valgt_hold.upper()}</span></div>',
                unsafe_allow_html=True,
            )

        sql_matches = (
            "SELECT MATCH_OPTAUUID, MATCH_DATE_FULL, WEEK, MATCH_STATUS, "
            "CONTESTANTHOME_OPTAUUID, CONTESTANTHOME_NAME, CONTESTANTAWAY_OPTAUUID, "
            "CONTESTANTAWAY_NAME, TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE "
            "FROM {db}.OPTA_MATCHINFO "
            "WHERE TOURNAMENTCALENDAR_NAME = '{season}' "
            "AND MATCH_STATUS = 'Played' "
            "AND (CONTESTANTHOME_OPTAUUID = '{uuid}' OR CONTESTANTAWAY_OPTAUUID = '{uuid}') "
            "ORDER BY MATCH_DATE_FULL DESC"
        ).format(db=DB, season=SEASONNAME, uuid=valgt_uuid_hold)

        df_matches = conn.query(sql_matches)
        if df_matches is None:
            df_matches = pd.DataFrame()

        valgt_kamp_uuid = None
        if not df_matches.empty:
            df_matches.columns = df_matches.columns.str.lower()
            df_matches["match_date_full"] = pd.to_datetime(
                df_matches["match_date_full"], errors="coerce"
            )

            kamp_options = {}
            for _, r in df_matches.iterrows():
                er_hjemme = (
                    str(r["contestanthome_optauuid"]) == str(valgt_uuid_hold)
                )
                modstander = (
                    r["contestantaway_name"]
                    if er_hjemme
                    else r["contestanthome_name"]
                )
                hjemme_maal = (
                    int(r["total_home_score"])
                    if pd.notna(r["total_home_score"])
                    else 0
                )
                ude_maal = (
                    int(r["total_away_score"])
                    if pd.notna(r["total_away_score"])
                    else 0
                )
                hold_maal = hjemme_maal if er_hjemme else ude_maal
                mod_maal = ude_maal if er_hjemme else hjemme_maal
                label = (
                    f"Kamp {r['week']}: vs. {modstander} ({hold_maal}-{mod_maal})"
                )
                kamp_options[label] = str(r["match_optauuid"])

            with col_t_matches:
                valgt_kamp_label = st.selectbox(
                    "Vælg kamp",
                    list(kamp_options.keys()),
                    key="valgt_kamp_dropdown",
                    label_visibility="collapsed",
                )
                valgt_kamp_uuid = kamp_options[valgt_kamp_label]

        with col_t_btn:
            st.markdown(
                '<div style="display: flex; justify-content: flex-end;">',
                unsafe_allow_html=True,
            )
            kategori_valg_kamp = st.segmented_control(
                "Visningskategori Kamp",
                options=["Generelt", "Opbygning", "Offensiv", "Defensiv"],
                default="Generelt",
                key="match_kategori_control",
                label_visibility="collapsed",
            )
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

        if not df_matches.empty and valgt_kamp_uuid:
            df_events_kamp, df_expected_kamp, _ = hent_match_og_haendelsesdata(
                conn, DB, valgt_uuid_hold, LIGA_IDS, navne_map
            )

            if df_events_kamp is not None and not df_events_kamp.empty:
                match_col_in_all = next(
                    (
                        col
                        for col in ["match_optauuid", "match_id"]
                        if col in df_events_kamp.columns
                    ),
                    None,
                )
                df_kamp_events = (
                    df_events_kamp[
                        df_events_kamp[match_col_in_all].astype(str)
                        == valgt_kamp_uuid
                    ].copy()
                    if match_col_in_all
                    else pd.DataFrame()
                )

                if "hold_optauuid" in df_kamp_events.columns:
                    df_kamp_events = df_kamp_events[
                        df_kamp_events["hold_optauuid"]
                        .astype(str)
                        .str.lower()
                        .str.replace("t", "")
                        == valgt_uuid_clean
                    ]
            else:
                df_kamp_events = pd.DataFrame()

            if not df_kamp_events.empty:
                event_stats_kamp = (
                    df_kamp_events.groupby(
                        ["player_optauuid", "visningsnavn"]
                    )
                    .apply(
                        lambda x: pd.Series(
                            {
                                "Kampe": 1,
                                "Aktioner": len(x),
                                "Pasninger": (x["event_typeid"] == 1).sum(),
                                "Pasninger_Succes": (
                                    (x["event_typeid"] == 1)
                                    & (x["outcome"] == 1)
                                ).sum(),
                                "Mål": (x["event_typeid"] == 16).sum(),
                                "Assists": 0,
                                "Afslutninger": x["event_typeid"]
                                .isin([13, 14, 15, 16])
                                .sum(),
                                "Tacklinger": (x["event_typeid"] == 7).sum(),
                                "Erobringer": x["event_typeid"]
                                .isin([7, 8, 12, 49])
                                .sum(),
                                "Clearinger": (x["event_typeid"] == 12).sum(),
                                "Blokeringer": (x["event_typeid"] == 55).sum(),
                                "Chancer_skabt": x.apply(
                                    lambda r: 1
                                    if "210" in str(r.get("qualifiers", ""))
                                    else 0,
                                    axis=1,
                                ).sum(),
                            }
                        )
                    )
                    .reset_index()
                    .drop_duplicates(subset=["player_optauuid"])
                    .set_index("player_optauuid")
                )

                truppen_stats_kamp_raw = event_stats_kamp.copy()
                truppen_stats_kamp_kamp = truppen_stats_kamp_raw.copy()
                truppen_stats_kamp_kamp["Pasningsprocent"] = (
                    (
                        truppen_stats_kamp_kamp["Pasninger_Succes"]
                        / truppen_stats_kamp_kamp["Pasninger"]
                    )
                    * 100
                ).where(
                    truppen_stats_kamp_kamp["Pasninger"] > 0, 0
                ).round(
                    1
                )

                df_vis_kamp = truppen_stats_kamp_kamp.reset_index()

                gen_kolonner = [
                    "visningsnavn",
                    "Kampe",
                    "Aktioner",
                    "Mål",
                    "Assists",
                ]
                opb_kolonner = ["visningsnavn", "Pasninger", "Pasningsprocent"]
                off_kolonner = ["visningsnavn", "Afslutninger", "Chancer_skabt"]
                def_kolonner = [
                    "visningsnavn",
                    "Tacklinger",
                    "Erobringer",
                    "Clearinger",
                    "Blokeringer",
                ]

                if kategori_valg_kamp == "Generelt":
                    eksisterende_kolonner_kamp = [
                        k for k in gen_kolonner if k in df_vis_kamp.columns
                    ]
                elif kategori_valg_kamp == "Opbygning":
                    eksisterende_kolonner_kamp = [
                        k for k in opb_kolonner if k in df_vis_kamp.columns
                    ]
                elif kategori_valg_kamp == "Offensiv":
                    eksisterende_kolonner_kamp = [
                        k for k in off_kolonner if k in df_vis_kamp.columns
                    ]
                elif kategori_valg_kamp == "Defensiv":
                    eksisterende_kolonner_kamp = [
                        k for k in def_kolonner if k in df_vis_kamp.columns
                    ]
                else:
                    eksisterende_kolonner_kamp = [
                        k for k in df_vis_kamp.columns if k != "player_optauuid"
                    ]

                df_visning_kamp = df_vis_kamp[
                    eksisterende_kolonner_kamp
                ].copy()
                if "Aktioner" in df_visning_kamp.columns:
                    df_visning_kamp = df_visning_kamp.sort_values(
                        by="Aktioner", ascending=False
                    )

                df_visning_kamp = df_visning_kamp.rename(
                    columns={
                        "visningsnavn": "Spiller",
                        "Pasningsprocent": "Pasning (%)",
                        "Chancer_skabt": "Chancer skabt",
                    }
                )

                beregnet_hoejde_kamp = int(len(df_visning_kamp) * 38 + 45)
                st.dataframe(
                    df_visning_kamp,
                    use_container_width=True,
                    hide_index=True,
                    height=beregnet_hoejde_kamp,
                    column_config={
                        "Pasning (%)": st.column_config.NumberColumn(
                            "Pasning (%)", format="%.1f%%"
                        )
                    },
                )
            else:
                st.info("Ingen hændelsesdata for denne kamp.")
        else:
            st.warning("Ingen spillede kampe fundet i denne sæson.")


def _forbered_liga_ids(liga_ids):
    """Sikrer at liga_ids altid konverteres til et sikkert SQL IN-format, uanset datatype."""
    if liga_ids is None:
        return "('__DUMMY__')"

    if isinstance(liga_ids, pd.Series):
        liga_ids = liga_ids.dropna().tolist()
    elif isinstance(liga_ids, np.ndarray):
        liga_ids = liga_ids.tolist()
    elif isinstance(liga_ids, (str, int, float)):
        s = str(liga_ids).strip()
        if "," in s and not (
            s.startswith("'") or s.startswith('"') or s.startswith("(")
        ):
            liga_ids = [item.strip() for item in s.split(",")]
        else:
            liga_ids = [s]
    elif isinstance(liga_ids, (list, tuple, set)):
        liga_ids = list(liga_ids)
    else:
        try:
            liga_ids = list(liga_ids)
        except Exception:
            liga_ids = [str(liga_ids)]

    clean_ids = []
    for x in liga_ids:
        if x is not None:
            val = str(x).strip().strip("'\"()[]")
            if val:
                clean_ids.append(f"'{val}'")

    if not clean_ids:
        return "('__DUMMY__')"

    return f"({', '.join(clean_ids)})"


def hent_match_og_haendelsesdata(
    conn, db_navn, valgt_uuid_hold, liga_ids, navne_map
):
    """Henter events, forventede mål og database-stats for hele ligaen fra Snowflake."""
    liga_ids_sql = _forbered_liga_ids(liga_ids)

    sql_events = (
        """
        SELECT 
            e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, e.MATCH_OPTAUUID, 
            p.MATCH_NAME, p.FIRST_NAME, p.SHORT_LAST_NAME, m.MATCHLENGTHMIN,
            e.PLAYER_OPTAUUID, e.EVENT_OUTCOME as OUTCOME,
            e.EVENT_CONTESTANT_OPTAUUID as HOLD_OPTAUUID,
            TO_CHAR(e.EVENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS') as EVENT_TIMESTAMP_STR,
            LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS,
            MAX(CASE WHEN q.QUALIFIER_QID = 140 THEN q.QUALIFIER_VALUE END) AS END_X,
            MAX(CASE WHEN q.QUALIFIER_QID = 141 THEN q.QUALIFIER_VALUE END) AS END_Y
        FROM {db_navn}.OPTA_EVENTS e
        JOIN {db_navn}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
        JOIN (SELECT DISTINCT PLAYER_OPTAUUID, FIRST_NAME, LAST_NAME, SHORT_LAST_NAME, MATCH_NAME FROM {db_navn}.OPTA_MATCH_LINEUPS WHERE FIRST_NAME IS NOT NULL) p 
            ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
        LEFT JOIN {db_navn}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
        WHERE m.TOURNAMENTCALENDAR_OPTAUUID IN {liga_ids_sql}
          AND e.EVENT_TIMESTAMP >= '2026-07-01'
        GROUP BY 
            e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, e.MATCH_OPTAUUID, 
            p.MATCH_NAME, p.FIRST_NAME, p.SHORT_LAST_NAME, m.MATCHLENGTHMIN,
            e.PLAYER_OPTAUUID, e.EVENT_OUTCOME, e.EVENT_CONTESTANT_OPTAUUID, 
            e.EVENT_TIMESTAMP
    """
        .replace("{db_navn}", str(db_navn))
        .replace("{liga_ids_sql}", str(liga_ids_sql))
    )

    df_all = conn.query(sql_events)

    if df_all is not None and not df_all.empty:
        df_all.columns = df_all.columns.str.lower()
        for col in ["end_x", "end_y", "matchlenghtmin"]:
            if col in df_all.columns:
                df_all[col] = pd.to_numeric(df_all[col], errors="coerce")

    def fix_name(row):
        f_name = row.get("first_name")
        m_name = row.get("match_name")
        f_str = (
            str(f_name).strip()
            if f_name is not None and str(f_name).lower() not in ["nan", "none"]
            else ""
        )
        m_str = (
            str(m_name).strip()
            if m_name is not None and str(m_name).lower() not in ["nan", "none"]
            else ""
        )
        if m_str and "." in m_str:
            parts = m_str.split(".", 1)
            if len(parts) > 1 and f_str:
                return f"{f_str} {parts[1].strip()}"
        return m_str if m_str else (f_str if f_str else "Ukendt spiller")

    if df_all is not None and not df_all.empty:
        df_all["visningsnavn"] = df_all.apply(fix_name, axis=1)
        df_all["visningsnavn"] = df_all.apply(
            lambda r: navne_map.get(str(r["player_optauuid"]), r["visningsnavn"]),
            axis=1,
        )
    else:
        df_all = pd.DataFrame()

    sql_expected = (
        """
        SELECT 
            MATCH_OPTAUUID,
            PLAYER_OPTAUUID,
            CONTESTANT_OPTAUUID as HOLD_OPTAUUID,
            MAX(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_VALUE ELSE 0 END) AS xg,
            MAX(CASE WHEN STAT_TYPE = 'expectedAssists' THEN STAT_VALUE ELSE 0 END) AS xa,
            MAX(CASE WHEN STAT_TYPE = 'minsPlayed' THEN STAT_VALUE ELSE 0 END) AS minutes
        FROM {db_navn}.OPTA_MATCHEXPECTEDGOALS
        WHERE TOURNAMENTCALENDAR_OPTAUUID IN {liga_ids_sql}
          AND MATCH_STATUS = 'Played'
        GROUP BY MATCH_OPTAUUID, PLAYER_OPTAUUID, CONTESTANT_OPTAUUID
    """
        .replace("{db_navn}", str(db_navn))
        .replace("{liga_ids_sql}", str(liga_ids_sql))
    )

    df_expected = conn.query(sql_expected)
    if df_expected is not None and not df_expected.empty:
        df_expected.columns = df_expected.columns.str.lower()
    else:
        df_expected = pd.DataFrame()

    sql_db_stats = (
        """
        WITH EventQualifiers AS (
            SELECT 
                e.EVENT_OPTAUUID, e.PLAYER_OPTAUUID, e.EVENT_TYPEID, e.EVENT_TIMESTAMP, e.MATCH_OPTAUUID,
                e.EVENT_CONTESTANT_OPTAUUID as HOLD_OPTAUUID,
                p.MATCH_NAME, p.FIRST_NAME, p.SHORT_LAST_NAME,
                LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
            FROM {db_navn}.OPTA_EVENTS e
            JOIN {db_navn}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
            JOIN (SELECT DISTINCT PLAYER_OPTAUUID, FIRST_NAME, LAST_NAME, SHORT_LAST_NAME, MATCH_NAME FROM {db_navn}.OPTA_MATCH_LINEUPS WHERE FIRST_NAME IS NOT NULL) p 
                ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
            LEFT JOIN {db_navn}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE m.TOURNAMENTCALENDAR_OPTAUUID IN {liga_ids_sql}
              AND e.EVENT_TIMESTAMP >= '2026-07-01'
            GROUP BY e.EVENT_OPTAUUID, e.PLAYER_OPTAUUID, e.EVENT_TYPEID, e.EVENT_TIMESTAMP, e.MATCH_OPTAUUID, e.EVENT_CONTESTANT_OPTAUUID, p.FIRST_NAME, p.SHORT_LAST_NAME, p.MATCH_NAME
        ),
        SortedEvents AS (
            SELECT 
                PLAYER_OPTAUUID, HOLD_OPTAUUID, MATCH_NAME, FIRST_NAME, SHORT_LAST_NAME, EVENT_TYPEID, MATCH_OPTAUUID, QUALIFIERS,
                LAG(PLAYER_OPTAUUID) OVER (PARTITION BY MATCH_OPTAUUID ORDER BY EVENT_TIMESTAMP) AS ASSIST_PLAYER_UUID,
                LAG(EVENT_TYPEID) OVER (PARTITION BY MATCH_OPTAUUID ORDER BY EVENT_TIMESTAMP) AS PREV_EVENT_TYPEID,
                LAG(QUALIFIERS) OVER (PARTITION BY MATCH_OPTAUUID ORDER BY EVENT_TIMESTAMP) AS PREV_QUALIFIERS
            FROM EventQualifiers
        ),
        PlayerGoals AS (
            SELECT PLAYER_OPTAUUID, 
                MAX(HOLD_OPTAUUID) AS HOLD_OPTAUUID,
                MAX(MATCH_NAME) AS MATCH_NAME, MAX(FIRST_NAME) AS FIRST_NAME, MAX(SHORT_LAST_NAME) AS SHORT_LAST_NAME,
                SUM(CASE WHEN EVENT_TYPEID = 16 THEN 1 ELSE 0 END) AS GOALS
            FROM SortedEvents
            GROUP BY PLAYER_OPTAUUID
        ),
        PlayerAssists AS (
            SELECT ASSIST_PLAYER_UUID AS PLAYER_OPTAUUID, COUNT(*) AS ASSISTS
            FROM SortedEvents
            WHERE EVENT_TYPEID = 16 
              AND ASSIST_PLAYER_UUID IS NOT NULL
              AND ASSIST_PLAYER_UUID != PLAYER_OPTAUUID
              AND (QUALIFIERS LIKE '%29%' OR PREV_QUALIFIERS LIKE '%210%')
            GROUP BY ASSIST_PLAYER_UUID
        )
        SELECT 
            g.PLAYER_OPTAUUID as player_optauuid, g.HOLD_OPTAUUID as hold_optauuid, g.MATCH_NAME as match_name,
            g.FIRST_NAME as first_name, g.SHORT_LAST_NAME as short_last_name,
            g.GOALS as goals, COALESCE(a.ASSISTS, 0) as assists
        FROM PlayerGoals g
        LEFT JOIN PlayerAssists a ON g.PLAYER_OPTAUUID = a.PLAYER_OPTAUUID
    """
        .replace("{db_navn}", str(db_navn))
        .replace("{liga_ids_sql}", str(liga_ids_sql))
    )

    df_db_stats = conn.query(sql_db_stats)
    if df_db_stats is not None and not df_db_stats.empty:
        df_db_stats.columns = df_db_stats.columns.str.lower()
        df_db_stats = df_db_stats.drop_duplicates(
            subset=["player_optauuid"]
        ).copy()
        df_db_stats["visningsnavn"] = df_db_stats.apply(fix_name, axis=1)
        df_db_stats["visningsnavn"] = df_db_stats.apply(
            lambda r: navne_map.get(str(r["player_optauuid"]), r["visningsnavn"]),
            axis=1,
        )
    else:
        df_db_stats = pd.DataFrame()

    return df_all, df_expected, df_db_stats


def hent_samlet_spiller_statistik(conn, db_navn, liga_ids, navne_map=None):
    """Henter fuldt aggregerede spillerstatistikker direkte via optimeret SQL-forespørgsel."""
    if navne_map is None:
        navne_map = {}

    liga_ids_sql = _forbered_liga_ids(liga_ids)

    sql_query = (
        """
    WITH EventAggregates AS (
        SELECT 
            e.PLAYER_OPTAUUID,
            e.EVENT_CONTESTANT_OPTAUUID AS HOLD_OPTAUUID,
            COUNT(DISTINCT e.MATCH_OPTAUUID) AS Kampe,
            COUNT(e.EVENT_OPTAUUID) AS Aktioner,
            SUM(CASE WHEN e.EVENT_TYPEID = 1 THEN 1 ELSE 0 END) AS Pasninger,
            SUM(CASE WHEN e.EVENT_TYPEID = 1 AND e.EVENT_OUTCOME = 1 THEN 1 ELSE 0 END) AS Pasninger_Succes,
            SUM(CASE WHEN e.EVENT_TYPEID = 1 AND TRY_CAST(q_endx.QUALIFIER_VALUE AS FLOAT) > e.EVENT_X THEN 1 ELSE 0 END) AS Fremadrettede_Pasninger,
            SUM(CASE WHEN e.EVENT_TYPEID IN (13, 14, 15, 16) THEN 1 ELSE 0 END) AS Afslutninger,
            SUM(CASE WHEN e.EVENT_TYPEID = 16 THEN 1 ELSE 0 END) AS Maal,
            SUM(CASE WHEN e.EVENT_TYPEID = 7 THEN 1 ELSE 0 END) AS Tacklinger,
            SUM(CASE WHEN e.EVENT_TYPEID IN (7, 8, 12, 49) THEN 1 ELSE 0 END) AS Erobringer,
            SUM(CASE WHEN e.EVENT_TYPEID = 12 THEN 1 ELSE 0 END) AS Clearinger,
            SUM(CASE WHEN e.EVENT_TYPEID = 55 THEN 1 ELSE 0 END) AS Blokeringer
        FROM {db_navn}.OPTA_EVENTS e
        JOIN {db_navn}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
        LEFT JOIN {db_navn}.OPTA_QUALIFIERS q_endx ON e.EVENT_OPTAUUID = q_endx.EVENT_OPTAUUID AND q_endx.QUALIFIER_QID = 140
        WHERE m.TOURNAMENTCALENDAR_OPTAUUID IN {liga_ids_sql}
        GROUP BY e.PLAYER_OPTAUUID, e.EVENT_CONTESTANT_OPTAUUID
    ),
    ExpectedAggregates AS (
        SELECT 
            PLAYER_OPTAUUID,
            CONTESTANT_OPTAUUID AS HOLD_OPTAUUID,
            SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN TRY_CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS xG,
            SUM(CASE WHEN STAT_TYPE = 'expectedAssists' THEN TRY_CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS xA,
            SUM(CASE WHEN STAT_TYPE = 'minsPlayed' THEN TRY_CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS Minutter
        FROM {db_navn}.OPTA_MATCHEXPECTEDGOALS
        WHERE TOURNAMENTCALENDAR_OPTAUUID IN {liga_ids_sql}
          AND MATCH_STATUS = 'Played'
        GROUP BY PLAYER_OPTAUUID, CONTESTANT_OPTAUUID
    ),
    PlayerNames AS (
        SELECT DISTINCT PLAYER_OPTAUUID, FIRST_NAME, SHORT_LAST_NAME, MATCH_NAME
        FROM {db_navn}.OPTA_MATCH_LINEUPS
        WHERE FIRST_NAME IS NOT NULL
    )
    SELECT 
        pn.FIRST_NAME,
        pn.SHORT_LAST_NAME,
        pn.MATCH_NAME,
        ea.PLAYER_OPTAUUID AS player_optauuid,
        ea.HOLD_OPTAUUID,
        ea.Kampe,
        COALESCE(xa.Minutter, 0) AS Minutter,
        ea.Aktioner,
        ea.Pasninger,
        ROUND((ea.Pasninger_Succes / NULLIF(ea.Pasninger, 0)) * 100, 1) AS Pasningsprocent,
        ea.Fremadrettede_Pasninger,
        ea.Afslutninger,
        ea.Maal,
        COALESCE(xa.xG, 0) AS xG,
        COALESCE(xa.xA, 0) AS xA,
        ea.Tacklinger,
        ea.Erobringer,
        ea.Clearinger,
        ea.Blokeringer
    FROM EventAggregates ea
    LEFT JOIN ExpectedAggregates xa ON ea.PLAYER_OPTAUUID = xa.PLAYER_OPTAUUID AND ea.HOLD_OPTAUUID = xa.HOLD_OPTAUUID
    LEFT JOIN PlayerNames pn ON ea.PLAYER_OPTAUUID = pn.PLAYER_OPTAUUID
    ORDER BY ea.Aktioner DESC;
    """
        .replace("{db_navn}", str(db_navn))
        .replace("{liga_ids_sql}", str(liga_ids_sql))
    )

    df = conn.query(sql_query)
    if df is not None and not df.empty:
        df.columns = df.columns.str.lower()

        def fix_name(row):
            f_name = row.get("first_name")
            m_name = row.get("match_name")
            f_str = (
                str(f_name).strip()
                if f_name is not None and str(f_name).lower() not in ["nan", "none"]
                else ""
            )
            m_str = (
                str(m_name).strip()
                if m_name is not None and str(m_name).lower() not in ["nan", "none"]
                else ""
            )
            if m_str and "." in m_str:
                parts = m_str.split(".", 1)
                if len(parts) > 1 and f_str:
                    return f"{f_str} {parts[1].strip()}"
            return m_str if m_str else (f_str if f_str else "Ukendt spiller")

        df["visningsnavn"] = df.apply(fix_name, axis=1)
        if navne_map:
            df["visningsnavn"] = df.apply(
                lambda r: navne_map.get(
                    str(r["player_optauuid"]), r["visningsnavn"]
                ),
                axis=1,
            )
    else:
        df = pd.DataFrame()

    return df


def _byg_event_stats(df_events):
    if df_events.empty:
        return pd.DataFrame()
    return df_events.groupby("player_optauuid").agg(
        Aktioner=("event_typeid", "count"),
        Pasninger=("event_typeid", lambda x: (x == 1).sum()),
        Pasninger_Succes=(
            "outcome",
            lambda x: ((x == 1) & (df_events.loc[x.index, "outcome"] == 1)).sum(),
        ),
    )
