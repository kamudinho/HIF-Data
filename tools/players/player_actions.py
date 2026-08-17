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

# --- MAPPINGS & HJÆLPERE ---
POSITION_MAP = {} # Definer eller importer efter behov
POSITION_DA = {}  # Danske betegnelser for positioner
POSITION_DA_FLERTAL = {}
KATEGORI_PER_POSITION = {}
DEFAULT_KAT_LISTE = {"offensiv": [], "defensiv": []}

@st.cache_data(ttl=600, show_spinner=False)
def hent_navne_map() -> dict:
    try:
        from data.players import player_mapping
        if hasattr(player_mapping, "PLAYER_MAPPING"):
            mapping_data = player_mapping.PLAYER_MAPPING
            return mapping_data
    except Exception:
        return {}
    return {}

@st.cache_data(ttl=1800, show_spinner=False)
def hent_holdliste(_conn) -> dict:
    sql_query = (
        "SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID "
        "FROM {db}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {liga_ids}"
    ).format(db=DB, liga_ids=LIGA_IDS)
    try:
        df_teams_raw = _conn.query(sql_query)
        return df_teams_raw
    except Exception:
        return {}

def map_event_to_category(row) -> str:
    return "Ukendt aktion"

def create_relative_donut(player_val, max_val, label, rank_str, color="#1f77b4"):
    import plotly.graph_objects as go
    fig = go.Figure(go.Pie(
        values=[player_val, max(0, max_val - player_val)],
        hole=0.7,
        marker_colors=[color, "#e9ecef"],
        textinfo='none',
        hoverinfo='none'
    ))
    fig.update_layout(
        showlegend=False,
        margin=dict(t=10, b=10, l=10, r=10),
        annotations=[dict(text=f"{rank_str}", x=0.5, y=0.5, font_size=14, showarrow=False)]
    )
    return fig

def vis_side():
    st.subheader("Spiller Aktioner & Profil")
    
    # Eksempelvariabler til test/integration (tilpasses efter din app-state)
    conn = _get_snowflake_conn()
    holdliste = hent_holdliste(conn)
    
    # Tabs eller containere defineres her
    _, t_profile = st.tabs("Oversigt", "Profil") # Eksempel
    
    # Hvis t_profile bruges direkte som container / kolonne / tab:
    # (Her indsættes din logik direkte)
    
    truppen_stats = pd.DataFrame()
    truppen_stats_liga = pd.DataFrame()
    valgt_player_uuid = ""
    valgt_spiller = ""
    spiller_position = "Ukendt"
    hold_logo = None
    primær_farve = "#1f77b4"

    with t_profile:
        if not truppen_stats.empty and valgt_player_uuid in truppen_stats.index:
            if 'Position' not in truppen_stats.columns:
                truppen_stats['Position'] = truppen_stats.index.to_series().apply(
                    lambda u: POSITION_MAP.get(str(u).strip(), 'Ukendt')
                )

            if spiller_position != 'Ukendt':
                sammenligningsgruppe = truppen_stats_liga[truppen_stats_liga['Position'] == spiller_position]
                if sammenligningsgruppe.empty:
                    sammenligningsgruppe = truppen_stats_liga
            else:
                sammenligningsgruppe = truppen_stats_liga

            numeric_cols = sammenligningsgruppe.drop(columns=['visningsnavn', 'Pasningsprocent_Str', 'Position'], errors='ignore')
            ranks = (-numeric_cols).rank(ascending=True, method='min').astype(int)

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

                position_label = POSITION_DA.get(spiller_position, spiller_position)
                st.markdown(f'''<div style="display: flex; align-items: center; margin-bottom: 10px;">{logo_html}<div>
                        <div style="font-size: 18px; font-weight: bold; line-height: 1.2;">{valgt_spiller}</div>
                        <div style="font-size: 12px; color: #888;">{position_label}</div>
                    </div></div>''', unsafe_allow_html=True)
                st.markdown("<hr style='margin: 10px 0; opacity: 0.5;'>", unsafe_allow_html=True)

                st.markdown(f"""
                    <div style="background-color: #f8f9fa; padding: 12px; border-radius: 8px; border: 1px solid #e9ecef;">
                        <h4 style="margin: 0 0 10px 0; font-size: 14px; text-transform: uppercase; font-weight: bold;">Kampdata</h4>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Kampe:</b></span><span>{int(s_data.get('Kampe', 0))}</span></div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Minutter:</b></span><span>{int(s_data.get('Minutter', 0))}'</span></div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Mål (xG):</b></span><span>{int(s_data.get('Mål', 0))} ({round(s_data.get('xG', 0.0), 2)})</span></div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Assists (xA):</b></span><span>{int(s_data.get('Assists', 0))} ({round(s_data.get('xA', 0.0), 2)})</span></div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Gule kort:</b></span><span>{int(s_data.get('Gule_kort', 0))}</span></div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Røde kort:</b></span><span>{int(s_data.get('Roede_kort', 0))}</span></div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Indskiftet:</b></span><span>{int(s_data.get('Indskiftet', 0))}</span></div>
                        <div style="display: flex; justify-content: space-between; font-size: 13px;"><span><b>Udskiftet:</b></span><span>{int(s_data.get('Udskiftet', 0))}</span></div>
                    </div>
                """, unsafe_allow_html=True)

                st.markdown("<hr style='margin: 15px 0; opacity: 0.5;'>", unsafe_allow_html=True)
                gruppe_navn = POSITION_DA_FLERTAL.get(spiller_position, "spillere")
                st.caption(f"Sammenlignet med alle {gruppe_navn} i ligaen.")

            with main_col_right:
                kat_dict = KATEGORI_PER_POSITION.get(spiller_position, DEFAULT_KAT_LISTE)

                for side_label, side_key in (("Offensivt", "offensiv"), ("Defensivt", "defensiv")):
                    if side_key not in kat_dict:
                        continue
                    kat_liste = [(label, k_id) for label, k_id in kat_dict[side_key] if k_id in truppen_stats.columns]
                    if not kat_liste:
                        continue

                    st.markdown(
                        f"<p style='font-weight:bold; font-size:12px; color:#888; "
                        f"text-transform:uppercase; letter-spacing:0.5px; margin:12px 0 6px 0;'>{side_label}</p>",
                        unsafe_allow_html=True
                    )

                    for i in range(0, len(kat_liste), 4):
                        cols = st.columns(4)
                        for j, (label, k_id) in enumerate(kat_liste[i:i + 4]):
                            with cols[j]:
                                st.markdown(f"<p style='text-align:center; font-weight:bold; font-size:12px; margin-bottom:0px;'>{label}</p>", unsafe_allow_html=True)
                                player_val = truppen_stats.loc[valgt_player_uuid, k_id]
                                if isinstance(player_val, pd.Series):
                                    player_val = player_val.iloc[0]
                                max_val = sammenligningsgruppe[k_id].max() if k_id in sammenligningsgruppe.columns else 1
                                rank_val = spiller_ranks[k_id] if k_id in spiller_ranks.index else 1
                                fig = create_relative_donut(player_val, max_val, label, get_ordinal(rank_val), color=primær_farve)
                                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"p_{side_key}_{k_id}_{i}_{j}")
        else:
            st.info("Ingen spillerdata tilgængelig.")

if __name__ == "__main__":
    vis_side()
