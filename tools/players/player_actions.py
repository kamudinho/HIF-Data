import base64
from io import BytesIO
import io
import os
import pandas as pd
import streamlit as st
from mplsoccer import Pitch

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
from data.utils.spiller_qualifiers import (
    ACTION_CATEGORIES,
    POSITION_ACTIONS,
    EVENT_TYPES,
)
from utils.helpers import (
    get_logo_img,
    get_team_color,
    get_ordinal,
    draw_player_info_box,
)
from data.sql.liga_spillere import (
    hent_samlet_spiller_statistik,
    hent_match_og_haendelsesdata,
)

# --- KONFIGURATION FRA KONTEKST ---
SEASONNAME = "2025/2026"
DB = "KLUB_HVIDOVREIF.AXIS"
active_leagues = SEASONS.get(SEASONNAME, {})
optauuid_liste = list(active_leagues.values())

if optauuid_liste:
    rensede_uuids = [str(uuid).strip() for uuid in optauuid_liste if uuid]
    LIGA_IDS = "('" + "', '".join(rensede_uuids) + "')"
else:
    LIGA_IDS = "('2mb332vncy4450vu14paj8844')"

# --- KONSTANTER ---
TOUCH_IDS = [1, 3, 7, 10, 11, 12, 13, 14, 15, 16, 42, 44, 49, 50, 51, 54, 61, 73]

AKTIONS_FARVER = [
    ("Pasning", lambda df: df["event_typeid"] == 1, "#1f77b4", 30, "o"),
    ("Dribling", lambda df: df["event_typeid"] == 3, "#d62728", 40, "o"),
    ("Afslutning", lambda df: df["event_typeid"].isin([13, 14, 15]), "#ff7f0e", 60, "o"),
    ("Mål", lambda df: df["event_typeid"] == 16, "#2ca02c", 100, "s"),
    ("Defensiv", lambda df: df["event_typeid"].isin([5, 7, 8, 12, 49, 55]), "#9467bd", 50, "D"),
]

HIDDEN_VIEWS_PER_POSITION = {
    "GK": ["Offensive pasninger", "Afslutninger"],
    "Målmand": ["Offensive pasninger", "Afslutninger"],
}

# --- FUNKTIONER ---
@st.cache_data(ttl=600, show_spinner=False)
def hent_navne_map() -> dict:
    try:
        from data.players import player_mapping
        if hasattr(player_mapping, "PLAYER_MAPPING"):
            mapping_data = player_mapping.PLAYER_MAPPING
            # ... (Logik som i det originale script)
    except Exception:
        return {}
    return {}

@st.cache_data(ttl=1800, show_spinner=False)
def hent_holdliste(_conn) -> dict:
    sql_query = (
        "SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID "
        "FROM {db}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {liga_ids}"
    ).format(db=DB, liga_ids=LIGA_IDS)
    df_teams_raw = _conn.query(sql_query)
    # ... (Logik som i det originale script)
    return {}

def map_event_to_category(row) -> str:
    # ... (Logik som i det originale script)
    return "Ukendt aktion"

def vis_side():
    # ... (Samlet visningslogik)
    st.write("Viser spiller aktioner...")

if __name__ == "__main__":
    vis_side()
