import base64
from io import BytesIO
import io
import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from mplsoccer import Pitch

# --- DATA OG MAPPING ---
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.utils.mapping import OPTA_EVENT_TYPES, OPTA_QUALIFIERS, get_action_label, is_assist, har_qualifier
from data.utils.spiller_qualifiers import ACTION_CATEGORIES, POSITION_ACTIONS
from utils.helpers import get_logo_img, get_team_color, get_ordinal, draw_player_info_box
from data.sql.liga_spillere import hent_match_og_haendelsesdata

try:
    from data.players import player_mapping
    valgt_player_uuid = st.session_state.get('valgt_player_uuid', getattr(player_mapping, 'valgt_player_uuid', None))
    valgt_spiller = st.session_state.get('valgt_spiller', getattr(player_mapping, 'valgt_spiller', None))
    hold_logo = getattr(player_mapping, 'hold_logo', None)
    primær_farve = getattr(player_mapping, 'primær_farve', "#df003b")
    valgt_hold = getattr(player_mapping, 'valgt_hold', "Hvidovre")
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

HIDDEN_VIEWS_PER_POSITION = {
    "Goalkeeper": ["Afslutninger", "Offensive pasninger"],
}

AKTIONS_FARVER = [
    ("Aflevering", lambda d: d['event_typeid'] == 1, '#1f77b4', 22, 'o'),
    ("Dribling", lambda d: d['event_typeid'] == 3, '#d62728', 45, 'o'),
    ("Afslutning", lambda d: d['event_typeid'].isin([13, 14, 15]), '#ff7f0e', 70, 'o'),
    ("Mål", lambda d: d['event_typeid'] == 16, '#2ca02c', 130, 's'),
    ("Defensiv aktion", lambda d: d['event_typeid'].isin([5, 7, 8, 12, 49, 55]), '#9467bd', 55, 'o'),
]

DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_IDS = "('2mb332vncy4450vu14paj8844', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '335', '328', '329', '43319', '331')"

def _forbered_events(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.dropna(subset=['visningsnavn']).copy()
    df['event_timestamp'] = pd.to_datetime(df['event_timestamp_str'])
    df['qual_list'] = df['qualifiers'].fillna('').str.split(',')
    df['Pasninger_Total'] = (df['event_typeid'] == 1).astype(int)
    df['Pasninger_Succes'] = ((df['event_typeid'] == 1) & (df['outcome'] == 1)).astype(int)
    df_temp = df.rename(columns={
        'event_x': 'EVENT_X', 'event_y': 'EVENT_Y', 'event_typeid': 'EVENT_TYPEID',
        'visningsnavn': 'VISNINGSNAVN', 'player_optauuid': 'PLAYER_OPTAUUID',
        'outcome': 'OUTCOME', 'qualifiers': 'QUALIFIERS'
    })
    df['Action_Label'] = df_temp.apply(get_action_label, axis=1)
    return df

@st.cache_data(ttl=300, show_spinner="Henter spillerdata...")
def hent_spiller_data(_conn, spiller_uuid: str):
    # Optimeret: Hent kun data for den specifikke spiller i stedet for hele holdet/ligaen hvis muligt, 
    # eller filtrer direkte i SQL / her.
    df_all_raw, _, _ = hent_match_og_haendelsesdata(_conn, DB, "t7490", LIGA_IDS, {})
    if df_all_raw is None or df_all_raw.empty:
        return pd.DataFrame()
    
    df_prepared = _forbered_events(df_all_raw)
    if spiller_uuid:
        df_prepared = df_prepared[df_prepared['player_optauuid'] == spiller_uuid]
    return df_prepared

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

    if not valgt_player_uuid:
        st.warning("Ingen spiller valgt.")
        return

    with st.spinner("Indlæser aktioner..."):
        df_spiller = hent_spiller_data(conn, valgt_player_uuid)

    if df_spiller.empty:
        st.warning("Ingen hændelsesdata fundet for denne spiller.")
        return

    spiller_position = POSITION_MAP.get(str(valgt_player_uuid).strip(), 'Ukendt')

    # --- SPILLERAKTIONER (Uden tabs og uden spiller-dropdown) ---
    descriptions = {
        "Heatmap": "Viser spillerens generelle bevægelsesmønster og intensitet på banen.",
        "Berøringer": "Alle aktioner hvor spilleren har været i kontakt med bolden.",
        "Afslutninger": "Oversigt over alle skudforsøg (Mål = firkant, skud = cirkel).",
        "Defensive aktioner": "Tacklinger, bolderobringer og opsnappede afleveringer.",
        "Offensive pasninger": "Fremadrettede pasninger til sidste tredjedel (grøn = succes, grå = % succes).",
        "Alle aktioner": "Alle aktionstyper (blå = aflevering, rød = dribling, orange = afslutning, grøn = mål, lilla = defensiv aktion)."
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
        erob_count = len(df_spiller[df_spiller['event_typeid'].isin([49])])
        touch_count = len(df_spiller[df_spiller['event_typeid'].isin(touch_ids)])
        drib_count = len(df_spiller[df_spiller['event_typeid'].isin([3])])
        regains_count = len(df_spiller[df_spiller['event_typeid'].isin([7, 8, 12, 49])])
        boldtab_count = len(df_spiller[df_spiller['event_typeid'].isin([50, 51])])
        def_count = len(df_spiller[df_spiller['event_typeid'].isin([7, 8])])
        
        fremad_count = len(df_spiller[
            (df_spiller['event_typeid'] == 1)
            & df_spiller['end_x'].notna()
            & (df_spiller['end_x'] > df_spiller['event_x'])
        ]) if 'end_x' in df_spiller.columns else 0

        m_r1 = st.columns(4)
        m_r1[0].metric("Aktioner", total_akt)
        m_r1[1].metric("Berøringer", touch_count)
        m_r1[2].metric("Pasninger", pas_count)
        m_r1[3].metric("Pasning %", f"{int(pas_acc)}%")

        m_r2 = st.columns(4)
        m_r2[0].metric("Driblinger", drib_count)
        m_r2[1].metric("Skud", shots_count)
        m_r2[2].metric("Chancer", int(chancer_skabt))
        m_r2[3].metric("Indlæg", cross_count)

        m_r3 = st.columns(4)
        m_r3[0].metric("Def. 1v1", def_count)
        m_r3[1].metric("Regains", regains_count)
        m_r3[2].metric("Erobringer", erob_count)
        m_r3[3].metric("Boldtab", boldtab_count)

        m_r4 = st.columns(4)
        m_r4[0].metric("Fremad. pasn.", fremad_count)

        st.markdown("<hr style='margin: 15px 0; opacity: 0.5;'>", unsafe_allow_html=True)
        st.caption("**Top 10: Aktioner**")
        if not akt_stats.empty:
            bare_antal = ['Erobring', 'Clearing', 'Boldtab', 'Frispark vundet', 'Blokeret skud', 'Interception']
            for akt, row in akt_stats.head(10).iterrows():
                total, succes = int(row['Total']), int(row['Succes'])
                stats_html = f"<b>{total}</b>" if akt in bare_antal else f"{succes}/{total} <b>({int(succes/total*100)}%)</b>"
                st.markdown(f'<div style="display:flex; justify-content:space-between; font-size:11px; border-bottom:0.5px solid #eee; padding:5px 0;"><span>{akt}</span><span style="font-family:monospace;">{stats_html}</span></div>', unsafe_allow_html=True)

    with c_pitch_side:
        c_side_spacer, c_desc_col, c_menu_col = st.columns([0.2, 2.0, 1.0])

        skjulte_visninger = HIDDEN_VIEWS_PER_POSITION.get(spiller_position, [])
        descriptions_visning = {k: v for k, v in descriptions.items() if k not in skjulte_visninger}

        with c_menu_col:
            visning = st.selectbox(
                "Visning",
                list(descriptions_visning.keys()),
                key=f"pitch_view_sel_{valgt_player_uuid}",
                label_visibility="collapsed"
            )
        with c_desc_col:
            st.markdown(f'<div style="text-align: right; margin-top: 8px; line-height: 1.2;"><span style="color: #666; font-size: 0.85rem;">{descriptions_visning.get(visning)}</span></div>', unsafe_allow_html=True)

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
            elif visning == "Defensive aktioner":
                d = df_plot[df_plot['event_typeid'].isin([5, 7, 8, 12, 49, 55])]
                ax.scatter(d.event_x, d.event_y, color='orange', s=100, edgecolors='white')
            elif visning == "Alle aktioner":
                noget_vist = False
                for label, mask_fn, color, size, marker in AKTIONS_FARVER:
                    d = df_plot[mask_fn(df_plot)]
                    if not d.empty:
                        noget_vist = True
                        ax.scatter(
                            d.event_x, d.event_y, color=color, s=size,
                            edgecolors='white', alpha=0.75, label=label,
                            marker=marker, zorder=3
                        )
                if noget_vist:
                    ax.legend(
                        loc='upper center', bbox_to_anchor=(0.5, -0.03),
                        ncol=len(AKTIONS_FARVER), fontsize=7, frameon=False
                    )
            elif visning == "Offensive pasninger":
                if 'end_x' not in df_plot.columns or 'end_y' not in df_plot.columns:
                    st.info("Denne visning kræver pasningens slutkoordinater.")
                else:
                    d = df_plot[
                        (df_plot['event_typeid'] == 1) &
                        (df_plot['end_x'] > 66.7) &
                        (df_plot['end_x'] > df_plot['event_x'])
                    ].dropna(subset=['end_x', 'end_y'])

                    succes = d[d['outcome'] == 1]
                    fejl = d[d['outcome'] != 1]

                    if not fejl.empty:
                        pitch.arrows(
                            fejl.event_x, fejl.event_y, fejl.end_x, fejl.end_y,
                            ax=ax, color='#bdbdbd', width=0.7, headwidth=2, headlength=3, alpha=0.6, zorder=2
                        )
                    if not succes.empty:
                        pitch.arrows(
                            succes.event_x, succes.event_y, succes.end_x, succes.end_y,
                            ax=ax, color='green', width=1.3, headwidth=3, headlength=4, alpha=0.85, zorder=3
                        )
                    ax.scatter(d.event_x, d.event_y, color='green', s=20, edgecolors='white', alpha=0.6, zorder=4)

        st.pyplot(fig, use_container_width=True)

if __name__ == "__main__":
    vis_side()
