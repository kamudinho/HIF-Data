import base64
import io
import pandas as pd
import streamlit as st

from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS, SEASONS
from utils.helpers import get_logo_img, get_team_color
from data.sql.liga_spillere import (
    hent_samlet_spiller_statistik,
    hent_match_og_haendelsesdata,
)


def vis_side(dp=None):
    try:
        from data.players import player_mapping
    except ImportError:
        st.error(
            "Kunne ikke finde eller indlæse 'player_mapping.py'. Sørg for filen ligger i mappen."
        )
        st.stop()

    navne_map = hent_navne_map(player_mapping)

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

    DB = "KLUB_HVIDOVREIF.AXIS"
    SEASONNAME = getattr(player_mapping, "SEASONNAME", "2025/2026")
    active_leagues = SEASONS.get(SEASONNAME, {})
    optauuid_liste = list(active_leagues.values())

    if optauuid_liste:
        rensede_uuids = [str(uuid).strip() for uuid in optauuid_liste if uuid]
        LIGA_IDS = "('" + "', '".join(rensede_uuids) + "')"
    else:
        LIGA_IDS = "('2mb332vncy4450vu14paj8844')"

    team_map = hent_holdliste(conn, DB, LIGA_IDS, TEAMS)

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

    with st.spinner("Henter spillerstatistik..."):
        df_all_stats = hent_samlet_spiller_statistik(
            conn, DB, LIGA_IDS, navne_map
        )

    if df_all_stats is None or df_all_stats.empty:
        st.warning("Ingen spillerstatistik fundet.")
        st.stop()

    valgt_uuid_clean = str(valgt_uuid_hold).lower().lstrip("t")
    if "hold_optauuid" in df_all_stats.columns:
        df_hold_stats = df_all_stats[
            df_all_stats["hold_optauuid"]
            .astype(str)
            .str.lower()
            .str.lstrip("t")
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

        st.markdown(
            "<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True
        )

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

            beregnet_hoejde_saeson = min(
                int(len(df_visning_saeson) * 38 + 45), 600
            )
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
                er_hjemme = str(r["contestanthome_optauuid"]) == str(
                    valgt_uuid_hold
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

        st.markdown(
            "<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True
        )

        if not df_matches.empty and valgt_kamp_uuid:
            df_events_kamp, _, _ = hent_match_og_haendelsesdata(
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
                        .str.lstrip("t")
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
                                "Tacklinger": (
                                    x["event_typeid"] == 7
                                ).sum(),
                                "Erobringer": x["event_typeid"]
                                .isin([7, 8, 12, 49])
                                .sum(),
                                "Clearinger": (
                                    x["event_typeid"] == 12
                                ).sum(),
                                "Blokeringer": (
                                    x["event_typeid"] == 55
                                ).sum(),
                                "Chancer_skabt": x.apply(
                                    lambda r: 1
                                    if "210"
                                    in str(r.get("qualifiers", ""))
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

                truppen_stats_kamp_kamp = event_stats_kamp.copy()
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
                opb_kolonner = [
                    "visningsnavn",
                    "Pasninger",
                    "Pasningsprocent",
                ]
                off_kolonner = [
                    "visningsnavn",
                    "Afslutninger",
                    "Chancer_skabt",
                ]
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

                beregnet_hoejde_kamp = min(
                    int(len(df_visning_kamp) * 38 + 45), 600
                )
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
