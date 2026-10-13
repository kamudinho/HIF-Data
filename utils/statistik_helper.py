# utils/statistik_helper.py
"""
Fælles filter- og layout-opsætning til alle statistik-sider, så de altid vises ens.

Filterrække (altid samme antal kolonner, så dropdowns ikke skifter størrelse):

    [ Kampoversigt | Holdoversigt ]                       <- st.segmented_control

    Sæson | Hold | (Kategori) | Kamp

    - Hold vælges altid efter sæson.
    - Kategori vises kun, hvis siden sender `kategorier` med.
    - Kamp kan kun vælges i Kampoversigt (kampene er filtreret til det valgte hold).
      I Holdoversigt står pladsen tom, så de andre dropdowns bliver samme størrelse.

Layout under filtrene: graf til venstre (øverst), data til højre i en smallere kolonne:

    graf_col, data_col = graf_og_data_kolonner()

Brug:
    from utils.statistik_helper import render_statistik_filtre, graf_og_data_kolonner

    valg = render_statistik_filtre(
        key="tids",
        kategorier=["Alle", "Fremadrettede"],                   # valgfri
        hent_kampe=lambda uuid: hent_hoved_stats(conn, uuid),   # kræves til kampoversigt
    )
    graf_col, data_col = graf_og_data_kolonner()
"""
from dataclasses import dataclass
from typing import Callable, Optional, Sequence

import pandas as pd
import streamlit as st

from data.utils.team_mapping import (
    SEASONS, SEASON_LEAGUE_MAPPER, TEAMS, COMPETITION_NAME,
)

KAMP = "Kampoversigt"
HOLD = "Holdoversigt"
OVERSIGTER = [KAMP, HOLD]

# Graf fylder det meste af siden, data en smallere kolonne til højre
GRAF_DATA_BREDDER = [2.6, 1]


@dataclass
class StatistikValg:
    oversigt: str
    saeson: str
    turnering: str
    calendar_uuid: str
    hold: str
    kategori: Optional[str] = None
    kamp: Optional[pd.Series] = None

    @property
    def er_kamp(self) -> bool:
        return self.oversigt == KAMP

    @property
    def er_hold(self) -> bool:
        return self.oversigt == HOLD


def graf_og_data_kolonner():
    """Returnerer (graf_col, data_col): graf til venstre, data til højre."""
    return st.columns(GRAF_DATA_BREDDER)


def _standard_turnering(saeson: str) -> str:
    """Vælger turneringen automatisk: COMPETITION_NAME hvis den findes, ellers den første."""
    turneringer = list(SEASONS[saeson].keys())
    return COMPETITION_NAME if COMPETITION_NAME in turneringer else turneringer[0]


def _filtrer_kampe_til_hold(df: pd.DataFrame, hold: str) -> pd.DataFrame:
    """Beholder kun kampe, hvor det valgte hold spiller (på uuid, ellers på navn)."""
    uuid = TEAMS.get(hold, {}).get("opta_uuid")
    if uuid and {"CONTESTANTHOME_OPTAUUID", "CONTESTANTAWAY_OPTAUUID"}.issubset(df.columns):
        mask = (df["CONTESTANTHOME_OPTAUUID"] == uuid) | (df["CONTESTANTAWAY_OPTAUUID"] == uuid)
    else:
        mask = (df["CONTESTANTHOME_NAME"] == hold) | (df["CONTESTANTAWAY_NAME"] == hold)
    return df[mask]


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
    kategorier   Valgfri liste. Hvis sat, vises en kategori-kolonne.
    hent_kampe   Funktion(calendar_uuid) -> DataFrame med MATCH_DATE_FULL,
                 CONTESTANTHOME_NAME/AWAY_NAME (og gerne *_OPTAUUID).
                 Kræves, hvis kampoversigt er blandt oversigterne.
    """
    oversigter = list(oversigter)
    har_kamp = KAMP in oversigter
    if har_kamp and hent_kampe is None:
        raise ValueError("render_statistik_filtre: hent_kampe skal angives til kampoversigt.")

    oversigt = st.segmented_control(
        "Oversigt",
        oversigter,
        selection_mode="single",
        default=oversigter[0],
        key=f"{key}_oversigt",
        label_visibility="collapsed",
    ) or oversigter[0]

    # Fast kolonneopsætning, uafhængig af valgt oversigt
    bredder = [1] + ([1] if vis_turnering else []) + [1] + ([1] if kategorier else []) + ([1.6] if har_kamp else [])
    cols = st.columns(bredder)
    i = 0

    # --- Sæson ---
    saesoner = list(SEASONS.keys())
    valgt_saeson = cols[i].selectbox("Sæson", saesoner, key=f"{key}_saeson"); i += 1

    # --- Turnering (valgfri kolonne) ---
    if vis_turnering:
        turnering = cols[i].selectbox(
            "Turnering", list(SEASONS[valgt_saeson].keys()), key=f"{key}_turnering"
        ); i += 1
    else:
        turnering = _standard_turnering(valgt_saeson)
    calendar_uuid = SEASONS[valgt_saeson][turnering]

    # --- Hold (vælges altid efter sæson) ---
    hold_liste = SEASON_LEAGUE_MAPPER.get(valgt_saeson, {}).get(turnering, ["Hvidovre"])
    hold_index = hold_liste.index("Hvidovre") if "Hvidovre" in hold_liste else 0
    valgt_hold = cols[i].selectbox("Hold", hold_liste, index=hold_index, key=f"{key}_hold"); i += 1

    # --- Kategori (valgfri kolonne) ---
    valgt_kategori = None
    if kategorier:
        valgt_kategori = cols[i].selectbox(kategori_label, list(kategorier), key=f"{key}_kategori"); i += 1

    valg = StatistikValg(
        oversigt=oversigt,
        saeson=valgt_saeson,
        turnering=turnering,
        calendar_uuid=calendar_uuid,
        hold=valgt_hold,
        kategori=valgt_kategori,
    )

    # --- Kamp: kun aktiv i kampoversigt, ellers står pladsen tom ---
    if har_kamp and oversigt == KAMP:
        df_kampe = hent_kampe(calendar_uuid)
        if df_kampe is not None and not df_kampe.empty:
            df_kampe = _filtrer_kampe_til_hold(df_kampe, valgt_hold).copy()

        if df_kampe is None or df_kampe.empty:
            cols[i].selectbox("Kamp", [], key=f"{key}_kamp", disabled=True)
            st.warning(f"Ingen spillede kampe fundet for {valgt_hold}.")
            return valg

        df_kampe["MATCH_LABEL"] = _kamp_label(df_kampe)
        valgt_label = cols[i].selectbox(
            "Kamp", df_kampe["MATCH_LABEL"].tolist(), key=f"{key}_kamp"
        )
        valg.kamp = df_kampe[df_kampe["MATCH_LABEL"] == valgt_label].iloc[0]

    return valg
