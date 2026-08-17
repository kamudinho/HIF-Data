import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import os
import io
import base64
from mplsoccer import Pitch

# --- DATA OG MAPPING ---
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS, SEASONS
from data.utils.mapping import get_action_label

# --- GENERELLE UI-HJÆLPERE ---
from utils.helpers import get_logo_img, get_team_color, draw_player_info_box

# --- IMPORT AF SPILLERE OG SQL ---
from data.sql.liga_spillere import hent_samlet_spiller_statistik, hent_match_og_haendelsesdata

try:
    from data.players import player_mapping
    SEASONNAME = getattr(player_mapping, 'SEASONNAME', "2026/2027")
except ImportError:
    SEASONNAME = "2026/2027"

DB = "KLUB_HVIDOVREIF.AXIS"

# --- DYNAMISK LIGA_IDS BYGGES SIKKERT ---
active_leagues = SEASONS.get(SEASONNAME, {})
optauuid_liste = list(active_leagues.values())

if optauuid_liste:
    rensede_uuids = [str(uuid).strip() for uuid in optauuid_liste if uuid]
    LIGA_IDS = "('" + "', '".join(rensede_uuids) + "')"
else:
    LIGA_IDS = "('2mb332vncy4450vu14paj8844')"

# --- KONSTANTER OG KONFIGURATION ---
TOUCH_IDS = [1, 3, 7, 10, 11, 12, 13, 14, 15, 16, 42, 44, 49, 50, 51, 54, 61, 73]

AKTIONS_FARVER = [
    ("Pasning", lambda df: df['event_typeid'] == 1, '#1f77b4', 30, 'o'),
    ("Dribling", lambda df: df['event_typeid'] == 3, '#d62728', 40, 'o'),
    ("Afslutning", lambda df: df['event_typeid'].isin([13, 14, 15]), '#ff7f0e', 60, 'o'),
    ("Mål", lambda df: df['event_typeid'] == 16, '#2ca02c', 100, 's'),
    ("Defensiv", lambda df: df['event_typeid'].isin([5, 7, 8, 12, 49, 55]), '#9467bd', 50, 'D'),
]

HIDDEN_VIEWS_PER_POSITION = {
    "GK": ["Offensive pasninger", "Afslutninger"],
    "Målmand": ["Offensive pasninger", "Afslutninger"]
}

FALLBACK_LABELS = {
    1: "Pasning",
    3: "Dribling",
    7: "Tackling",
    8: "Interception",
    13: "Skud forbi",
    14: "Skud blokeret",
    15: "Skud på stolpe",
    16: "Mål",
    42: "Clearing",
    44: "Frispark vundet",
    49: "Erobring",
    50: "Boldtab",
    51: "Fejl / Boldtab",
    55: "Fejl",
    73: "Duel"
}

@st.cache_data(ttl=600, show_spinner=False)
def hent_navne_map() -> dict:
    try:
        csv_path = os.path.join(os.getcwd(), 'data', 'players', '1div_overskrivning.csv')
        df_csv = pd.read_csv(csv_path)
        return dict(zip(df_csv['PLAYER_OPTAUUID'].astype(str), df_csv['NAVN']))
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


def vis_side():
    navne_map = hent_navne_map()

    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 15px !important; text-align: center; font-weight: bold !important; width: 100%; }
        [data-testid="stMetricLabel"] { font-size: 10px !important; text-align: center; width: 100%; }
        [data-testid="stMetric"] { display: flex; flex-direction: column; align-items: center; background-color: transparent !important; padding: 2px !important; }
        .player-header { font-size: 18px; font-weight: bold; margin-bottom: 10px; color: #1E1E1E; }
        </style>
        """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn:
        st.error("Ingen databaseforbindelse.")
        return

    team_map = hent_holdliste(conn)

    # --- TOPBAR: SELECT HOLD & SPILLER ---
    col_spacer, col_hold, col_spiller = st.columns([2.0, 1.2, 1.3])

    default_team_idx = 0
    team_names = sorted(list(team_map.keys()))
    for idx, name in enumerate(team_names):
        if "hvidovre" in name.lower():
            default_team_idx = idx
            break

    valgt_hold = col_hold.selectbox("Vælg hold", team_names if team_names else ["Hvidovre"], index=default_team_idx if team_names else 0, label_visibility="collapsed")
    valgt_uuid_hold = team_map.get(valgt_hold, "t7490")
    valgt_uuid_clean = str(valgt_uuid_hold).lower().replace('t', '')
    
    hold_logo = get_logo_img(valgt_uuid_hold)
    primær_farve = get_team_color(valgt_hold, "primary", "#df003b")

    # Hent holdets spillere
    with st.spinner("Henter spillere..."):
        df_all_stats = hent_samlet_spiller_statistik(conn, DB, LIGA_IDS, navne_map)

    if df_all_stats is None or df_all_stats.empty:
        st.warning("Ingen spillerdata fundet.")
        return

    # Filtrer spillere på det valgte hold
    if 'hold_optauuid' in df_all_stats.columns:
        df_hold_spillere = df_all_stats[
            df_all_stats['hold_optauuid'].astype(str).str.lower().str.replace('t', '') == valgt_uuid_clean
        ].copy()
    else:
        df_hold_spillere = df_all_stats.copy()

    if df_hold_spillere.empty:
        st.warning("Ingen spillere fundet for det valgte hold.")
        return

    spiller_options = {
        r['visningsnavn']: r['player_optauuid']
        for _, r in df_hold_spillere[['visningsnavn', 'player_optauuid']].drop_duplicates().iterrows()
    }
    
    valgt_spiller_navn = col_spiller.selectbox("Vælg spiller", sorted(list(spiller_options.keys())), label_visibility="collapsed")
    valgt_player_uuid = spiller_options.get(valgt_spiller_navn)

    # Vandret linje mellem top-filtrering og indholdet
    st.markdown("<hr style='margin: 10px 0 20px 0; opacity: 0.3;'>", unsafe_allow_html=True)

    # Hent kamp/hændelsesdata for holdet
    with st.spinner("Henter spillerens aktioner..."):
        df_events, _, _ = hent_match_og_haendelsesdata(conn, DB, valgt_uuid_hold, LIGA_IDS, navne_map)

    if df_events is None or df_events.empty:
        st.info("Ingen hændelsesdata fundet.")
        return

    df_events.columns = df_events.columns.str.lower()
    
    # Filtrér data på den valgte spiller
    df_spiller = df_events[df_events['player_optauuid'].astype(str) == str(valgt_player_uuid)].copy()

    if df_spiller.empty:
        st.info(f"Ingen registrerede aktioner for {valgt_spiller_navn} i de hentede kampe.")
        return

    # Sikr nødvendige kolonner og felter
    if 'action_label' not in df_spiller.columns:
        df_spiller['Action_Label'] = df_spiller.apply(lambda r: get_action_label(r), axis=1)
    else:
        df_spiller['Action_Label'] = df_spiller['action_label']

    # Robust rettelse af 'Ukendt aktion' ved at tjekke event_typeid mod fallback-mapping
    if 'event_typeid' in df_spiller.columns:
        df_spiller['event_typeid'] = pd.to_numeric(df_spiller['event_typeid'], errors='coerce')
        mask_ukendt = df_spiller['Action_Label'].isin(['Ukendt', 'Ukendt aktion', 'nan', 'None', '']) | df_spiller['Action_Label'].isna()
        if mask_ukendt.any():
            df_spiller.loc[mask_ukendt, 'Action_Label'] = df_spiller.loc[mask_ukendt, 'event_typeid'].map(FALLBACK_LABELS).fillna('Ukendt aktion')

    if 'qual_list' not in df_spiller.columns:
        if 'qualifiers' in df_spiller.columns:
            df_spiller['qual_list'] = df_spiller['qualifiers'].astype(str).str.split(',')
        else:
            df_spiller['qual_list'] = [[] for _ in range(len(df_spiller))]

    spiller_position = df_spiller['position'].iloc[0] if 'position' in df_spiller.columns and not df_spiller['position'].empty else "Ukendt"

    # --- HOVEDLAYOUT (VENSTRE: STATS, HØJRE: BANE) ---
    descriptions = {
        "Heatmap": "Viser spillerens generelle bevægelsesmønster og intensitet på banen.",
        "Berøringer": "Alle aktioner hvor spilleren har været i kontakt med bolden.",
        "Afslutninger": "Oversigt over alle skudforsøg (Mål = firkant, skud = cirkel).",
        "Defensive aktioner": "Tacklinger, bolderobringer og opsnappede afleveringer.",
        "Offensive pasninger": "Fremadrettede pasninger til sidste tredjedel (grøn = succes, grå = % succes).",
        "Alle aktioner": "Alle aktionstyper (blå = aflevering, rød = dribling, orange = afslutning, grøn = mål, lilla = defensiv aktion)."
    }

    # Sikr at outcome kolonnen findes og er numerisk for aggregering
    if 'outcome' not in df_spiller.columns:
        df_spiller['outcome'] = 0
    else:
        df_spiller['outcome'] = pd.to_numeric(df_spiller['outcome'], errors='coerce').fillna(0)

    df_filtreret = df_spiller[~df_spiller['Action_Label'].isin(['Pasning', 'Indkast'])].copy()

    akt_stats = pd.DataFrame()
    if not df_filtreret.empty:
        akt_stats = df_filtreret.groupby('Action_Label').agg(
            Total=('outcome', 'count'), 
            Succes=('outcome', lambda x: (x == 1).sum())
        ).sort_values('Total', ascending=False)

    c_stats_side, c_buffer, c_pitch_side = st.columns([1, 0.05, 2.2])

    # --- VENSTRE KOLONNE: METRIKKER & TOP 10 AKTIONER ---
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
                    {valgt_spiller_navn}
                </div>
            </div>
        """, unsafe_allow_html=True)
        st.markdown("<hr style='margin: 10px 0; opacity: 0.5;'>", unsafe_allow_html=True)

        total_akt = len(df_spiller)
        pas_df = df_spiller[df_spiller['event_typeid'] == 1]
        pas_count = len(pas_df)
        pas_acc = (pas_df['outcome'].eq(1).sum() / pas_count * 100) if pas_count > 0 else 0

        chancer_skabt = akt_stats[akt_stats.index.str.contains("Key Pass|assist|Stor chance", case=False, na=False)]['Total'].sum() if not akt_stats.empty else 0
        shots_count = len(df_spiller[df_spiller['event_typeid'].isin([13, 14, 15, 16])])
        cross_count = len(df_spiller[df_spiller['qual_list'].apply(lambda x: "2" in x if isinstance(x, (list, np.ndarray)) else False)])
        erob_count = len(df_spiller[df_spiller['event_typeid'].isin([49])])
        touch_count = len(df_spiller[df_spiller['event_typeid'].isin(TOUCH_IDS)])
        drib_count = len(df_spiller[df_spiller['event_typeid'].isin([3])])
        regains_count = len(df_spiller[df_spiller['event_typeid'].isin([7, 8, 12, 49])])
        boldtab_count = len(df_spiller[df_spiller['event_typeid'].isin([50, 51])])
        def_count = len(df_spiller[df_spiller['event_typeid'].isin([7, 8])])

        if 'end_x' in df_spiller.columns and 'event_x' in df_spiller.columns:
            fremad_count = len(df_spiller[
                (df_spiller['event_typeid'] == 1) &
                df_spiller['end_x'].notna() &
                (df_spiller['end_x'] > df_spiller['event_x'])
            ])
        else:
            fremad_count = 0

        # Sat op i 4 kolonner pr. række
        m_r1 = st.columns(4)
        m_r1[0].metric("Aktioner", total_akt)
        m_r1[1].metric("Berøringer", touch_count)
        m_r1[2].metric("Pasninger", pas_count)
        m_r1[3].metric("Pasning %", f"{int(pas_acc)}%")

        st.markdown("<div style='margin-bottom: 2px;'></div>", unsafe_allow_html=True)

        m_r2 = st.columns(4)
        m_r2[0].metric("Driblinger", drib_count)
        m_r2[1].metric("Skud", shots_count)
        m_r2[2].metric("Chancer", int(chancer_skabt))
        m_r2[3].metric("Indlæg", cross_count)

        st.markdown("<div style='margin-bottom: 2px;'></div>", unsafe_allow_html=True)

        m_r3 = st.columns(4)
        m_r3[0].metric("Def. 1v1", def_count)
        m_r3[1].metric("Regains", regains_count)
        m_r3[2].metric("Erobringer", erob_count)
        m_r3[3].metric("Boldtab", boldtab_count)

        st.markdown("<div style='margin-bottom: 2px;'></div>", unsafe_allow_html=True)

        m_r4 = st.columns(4)
        m_r4[0].metric("Fremad. pasn.", fremad_count)

        st.markdown("<hr style='margin: 15px 0; opacity: 0.5;'>", unsafe_allow_html=True)
        st.caption("**Top 10: Aktioner**")
        
        if not akt_stats.empty:
            bare_antal = ['Erobring', 'Clearing', 'Boldtab', 'Frispark vundet', 'Blokeret skud', 'Interception']
            for akt, row in akt_stats.head(10).iterrows():
                total, succes = int(row['Total']), int(row['Succes'])
                stats_html = f"<b>{total}</b>" if akt in bare_antal else f"{succes}/{total} <b>({int(succes/total*100) if total > 0 else 0}%)</b>"
                st.markdown(
                    f'<div style="display:flex; justify-content:space-between; font-size:11px; border-bottom:0.5px solid #eee; padding:4px 0;">'
                    f'<span>{akt}</span><span style="font-family:monospace;">{stats_html}</span></div>', 
                    unsafe_allow_html=True
                )
        else:
            st.caption("Ingen aktionsdata tilgængelig.")

    # --- HØJRE KOLONNE: BANE & DROPDOWN ---
    with c_pitch_side:
        c_side_spacer, c_desc_col, c_menu_col = st.columns([0.2, 2.0, 1.2])

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
            st.markdown(f'<div style="text-align: right; margin-top: 6px; line-height: 1.2;"><span style="color: #666; font-size: 0.82rem;">{descriptions_visning.get(visning)}</span></div>', unsafe_allow_html=True)

        pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
        fig, ax = pitch.draw(figsize=(10, 7))
        draw_player_info_box(ax, hold_logo, valgt_spiller_navn, SEASONNAME, visning)

        df_plot = df_spiller.dropna(subset=['event_x', 'event_y'])
        
        if not df_plot.empty:
            if visning == "Heatmap":
                pitch.kdeplot(df_plot.event_x, df_plot.event_y, ax=ax, cmap='Blues', fill=True, alpha=0.6, levels=50)
                
            elif visning == "Berøringer":
                d = df_plot[df_plot['event_typeid'].isin(TOUCH_IDS)]
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
                        ncol=len(AKTIONS_FARVER), fontsize=8, frameon=False
                    )
                    
            elif visning == "Offensive pasninger":
                if 'end_x' not in df_plot.columns or 'end_y' not in df_plot.columns:
                    st.info("Denne visning kræver pasningens slutkoordinater (end_x/end_y).")
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
