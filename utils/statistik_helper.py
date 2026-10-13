# utils/statistik_helper.py
"""
Fælles filter-opsætning til alle statistik-sider, så de altid vises ens.

Layout:
    [ Kampoversigt | Holdoversigt ]                  <- st.segmented_control

    Holdoversigt:  col1 = sæson | col2 = hold | col3 = kategori
    Kampoversigt:  col1 = sæson | col2 = kamp (bredere kolonne kun til kampe)

Kategori-kolonnen vises kun, hvis siden sender `kategorier` med.
Turnering vælges automatisk (COMPETITION_NAME). Sæt vis_turnering=True, hvis
siden skal have en ekstra turnerings-kolonne lige efter sæson.

Brug:
    from utils.statistik_helper import render_statistik_filtre

    valg = render_statistik_filtre(
        key="tids",
        kategorier=["Alle", "Fremadrettede"],            # valgfri
        hent_kampe=lambda uuid: hent_hoved_stats(conn, uuid),  # kræves til kampoversigt
    )

    if valg.er_kamp:
        if valg.kamp is None: return
        ...  # valg.kamp er en række (pd.Series) fra kamp-tabellen
    else:
        ...  # valg.hold, valg.kategori
"""
from dataclasses import dataclass
from typing import Callable, Optional, Sequence

import pandas as pd
import streamlit as st

from data.utils.team_mapping import SEASONS, SEASON_LEAGUE_MAPPER, COMPETITION_NAME

KAMP = "Kampoversigt"
HOLD = "Holdoversigt"
OVERSIGTER = [KAMP, HOLD]


@dataclass
class StatistikValg:
    oversigt: str
    saeson: str
    turnering: str
    calendar_uuid: str
    hold: Optional[str] = None
    kategori: Optional[str] = None
    kamp: Optional[pd.Series] = None

    @property
    def er_kamp(self) -> bool:
        return self.oversigt == KAMP

    @property
    def er_hold(self) -> bool:
        return self.oversigt == HOLD


def _standard_turnering(saeson: str) -> str:
    """Vælger turneringen automatisk: COMPETITION_NAME hvis den findes, ellers den første."""
    turneringer = list(SEASONS[saeson].keys())
    return COMPETITION_NAME if COMPETITION_NAME in turneringer else turneringer[0]


def _kamp_label(df: pd.DataFrame) -> pd.Series:
    return (
        df["MATCH_DATE_FULL"].astype(str)
        + ": "
        + df["CONTESTANTHOME_NAME"]
        + " vs "
        + df["CONTESTANTAWAY_NAME"]
    )


def render_statistik_filtre(
    key: str,
    kategorier: Optional[Sequence[str]] = None,
    kategori_label: str = "Kategori",
    hent_kampe: Optional[Callable[[str], pd.DataFrame]] = None,
    oversigter: Sequence[str] = OVERSIGTER,
    vis_turnering: bool = False,
) -> StatistikValg:
    """
    Tegner segmented control + filterrækken og returnerer brugerens valg.

    key          Unik prefix pr. side, så widgets ikke støder sammen.
    kategorier   Valgfri liste. Hvis sat, vises en kategori-kolonne i holdoversigten.
    hent_kampe   Funktion(calendar_uuid) -> DataFrame med MATCH_DATE_FULL,
                 CONTESTANTHOME_NAME og CONTESTANTAWAY_NAME. Kræves til kampoversigt.
    """
    oversigter = list(oversigter)
    oversigt = st.segmented_control(
        "Oversigt",
        oversigter,
        selection_mode="single",
        default=oversigter[0],
        key=f"{key}_oversigt",
        label_visibility="collapsed",
    ) or oversigter[0]

    saesoner = list(SEASONS.keys())

    # --- KAMPOVERSIGT: sæson | (turnering) | kamp ---
    if oversigt == KAMP:
        if hent_kampe is None:
            raise ValueError("render_statistik_filtre: hent_kampe skal angives til kampoversigt.")

        bredder = [1] + ([1] if vis_turnering else []) + [2]
        cols = st.columns(bredder)

        valgt_saeson = cols[0].selectbox("Sæson", saesoner, key=f"{key}_saeson")
        if vis_turnering:
            turnering = cols[1].selectbox(
                "Turnering", list(SEASONS[valgt_saeson].keys()), key=f"{key}_turnering"
            )
        else:
            turnering = _standard_turnering(valgt_saeson)
        calendar_uuid = SEASONS[valgt_saeson][turnering]

        valg = StatistikValg(oversigt, valgt_saeson, turnering, calendar_uuid)

        df_kampe = hent_kampe(calendar_uuid)
        if df_kampe is None or df_kampe.empty:
            cols[-1].selectbox("Kamp", [], key=f"{key}_kamp", disabled=True)
            st.warning("Ingen spillede kampe fundet for denne turnering.")
            return valg

        df_kampe = df_kampe.copy()
        df_kampe["MATCH_LABEL"] = _kamp_label(df_kampe)
        valgt_label = cols[-1].selectbox(
            "Kamp", df_kampe["MATCH_LABEL"].tolist(), key=f"{key}_kamp"
        )
        valg.kamp = df_kampe[df_kampe["MATCH_LABEL"] == valgt_label].iloc[0]
        return valg

    # --- HOLDOVERSIGT: sæson | (turnering) | hold | (kategori) ---
    antal_cols = 2 + (1 if vis_turnering else 0) + (1 if kategorier else 0)
    cols = st.columns(antal_cols)
    i = 0

    valgt_saeson = cols[i].selectbox("Sæson", saesoner, key=f"{key}_saeson"); i += 1
    if vis_turnering:
        turnering = cols[i].selectbox(
            "Turnering", list(SEASONS[valgt_saeson].keys()), key=f"{key}_turnering"
        ); i += 1
    else:
        turnering = _standard_turnering(valgt_saeson)
    calendar_uuid = SEASONS[valgt_saeson][turnering]

    hold_liste = SEASON_LEAGUE_MAPPER.get(valgt_saeson, {}).get(turnering, ["Hvidovre"])
    hold_index = hold_liste.index("Hvidovre") if "Hvidovre" in hold_liste else 0
    valgt_hold = cols[i].selectbox("Hold", hold_liste, index=hold_index, key=f"{key}_hold"); i += 1

    valgt_kategori = None
    if kategorier:
        valgt_kategori = cols[i].selectbox(kategori_label, list(kategorier), key=f"{key}_kategori")

    return StatistikValg(
        oversigt=oversigt,
        saeson=valgt_saeson,
        turnering=turnering,
        calendar_uuid=calendar_uuid,
        hold=valgt_hold,
        kategori=valgt_kategori,
    )
