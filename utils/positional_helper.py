"""
utils/positional_helper.py

To ansvarsområder:

1. Udledning af en spillers PRIMÆRE position ud fra kamphistorik, vægtet efter
   minutter spillet i den position (funktion: beregn_primaere_positioner).
   Kræver to rå Wyscout-tabeller på kamp-niveau:
     - WYSCOUT_PLAYERADVANCEDSTATS_BASE (POSITION1-4CODE / POSITION1-4PERCENT)
     - WYSCOUT_MATCHADVANCEDPLAYERSTATS_TOTAL (MINUTESONFIELD)
   Disse skal joines på MATCH_WYID + PLAYER_WYID.

2. Definition af hvilke metrics der er relevante for hver positionsgruppe, og
   udregning af dem ud fra det eksisterende sæson-aggregerede advanced_stats_df
   (samme datakilde som beregn_p90_stats i comparison.py bruger).

BEMÆRK: POSITION_GROUP_MAP er baseret på standard Wyscout-positionskoder.
Hvis der dukker ukendte koder op i jeres data, mappes de til "Ukendt" - tjek
periodisk om der mangler koder (se find_ukendte_koder nederst).
"""

import pandas as pd

# --------------------------------------------------------------------------
# 1. POSITIONSGRUPPER
# --------------------------------------------------------------------------

POSITION_GROUP_MAP = {
    "gk": "Målmand",

    "rb": "Back", "lb": "Back", "rb5": "Back", "lb5": "Back",
    "rwb": "Back", "lwb": "Back", "lb3": "Back", "rb3": "Back",

    "rcb": "Stopper", "lcb": "Stopper", "cb": "Stopper",
    "rcb3": "Stopper", "lcb3": "Stopper", "cb3": "Stopper",

    "dmf": "Def. Midtbane", "rdmf": "Def. Midtbane", "ldmf": "Def. Midtbane",

    "rcmf": "Central Midtbane", "lcmf": "Central Midtbane",
    "rcmf3": "Central Midtbane", "lcmf3": "Central Midtbane", "cmf": "Central Midtbane",

    "amf": "Off. Midtbane", "ramf": "Off. Midtbane", "lamf": "Off. Midtbane",

    "rw": "Kant", "lw": "Kant", "rwf": "Kant", "lwf": "Kant",

    "ss": "Angriber", "cf": "Angriber", "st": "Angriber",
}

POSITION_10_GROUP_MAP = {
    "gk": "Målmand",
    
    # Backs
    "lb": "Back", "rb": "Back", "lwb": "Back", "rwb": "Back", 
    "lb3": "Back", "rb3": "Back", "lb5": "Back", "rb5": "Back",

    # Midtstoppere
    "cb": "Stopper", "lcb": "Stopper", "rcb": "Stopper", 
    "lcb3": "Stopper", "rcb3": "Stopper", "cb3": "Stopper",

    # Central Midtbane (inkl. DMF og AMF som i din Top 10 SQL)
    "dmf": "Midtbane", "rdmf": "Midtbane", "ldmf": "Midtbane",
    "cmf": "Midtbane", "lcmf": "Midtbane", "rcmf": "Midtbane",
    "lcmf3": "Midtbane", "rcmf3": "Midtbane", 
    "amf": "Midtbane", "lamf": "Midtbane", "ramf": "Midtbane",

    # Kanter
    "lw": "Kant", "rw": "Kant", "lwf": "Kant", "rwf": "Kant",

    # Angribere
    "cf": "Angriber", "st": "Angriber", "ss": "Angriber",
}

# Rækkefølge til visning/dropdowns
POSITIONSGRUPPE_ORDEN = [
    "Målmand", "Back", "Midtstopper", "Def. Midtbane",
    "Central Midtbane", "Off. Midtbane", "Kant", "Angriber", "Ukendt"
]


def find_ukendte_koder(position_stats_df, kode_kolonner=("POSITION1CODE", "POSITION2CODE", "POSITION3CODE", "POSITION4CODE")):
    """
    Hjælpefunktion til vedligehold: kør denne på jeres fulde datasæt en gang
    imellem for at se om der findes positionskoder, som ikke er i POSITION_GROUP_MAP.
    Returnerer en liste af ukendte koder (små bogstaver).
    """
    df = position_stats_df.copy()
    df.columns = [c.upper() for c in df.columns]
    fundne = set()
    for col in kode_kolonner:
        if col in df.columns:
            fundne |= set(df[col].dropna().astype(str).str.lower().str.strip().unique())
    fundne.discard("")
    ukendte = sorted(k for k in fundne if k not in POSITION_GROUP_MAP)
    return ukendte


# --------------------------------------------------------------------------
# 2. PRIMÆR POSITION (vægtet efter minutter)
# --------------------------------------------------------------------------

def beregn_primaere_positioner(position_stats_df):
    """
    Udleder hver spillers primære position ud fra WYSCOUT_PLAYERADVANCEDSTATS_BASE.

    VIGTIGT: Denne tabel er sæson-aggregeret (nøglet på SEASON_WYID + PLAYER_WYID +
    COMPETITION_WYID), IKKE kamp-niveau - der findes ingen MATCH_WYID. Wyscout har
    allerede beregnet hvor stor en andel af sæsonen spilleren har spillet i hver
    position (POSITIONS1PERCENT osv. - bemærk "S" i navnet).

    Hvis en spiller har flere rækker (flere sæsoner/konkurrencer i det hentede
    datasæt), lægges procenterne sammen på tværs, så vi stadig får ét samlet bud
    på den mest spillede position.

    Parametre:
        position_stats_df: rådata fra WYSCOUT_PLAYERADVANCEDSTATS_BASE.
            Forventede kolonner: PLAYER_WYID,
            POSITION1CODE..POSITION4CODE, POSITIONS1PERCENT..POSITIONS4PERCENT

    Returnerer:
        DataFrame med én række pr. spiller:
        PLAYER_WYID, PRIMAER_POSITION_KODE, PRIMAER_POSITIONSGRUPPE,
        SAMLET_PROCENT_I_POSITION (til debugging/gennemsigtighed)
    """
    pos_df = position_stats_df.copy()
    pos_df.columns = [c.upper() for c in pos_df.columns]

    if "PLAYER_WYID" not in pos_df.columns:
        raise ValueError("position_stats_df skal indeholde PLAYER_WYID")

    pos_df["PLAYER_WYID"] = pos_df["PLAYER_WYID"].astype(str).str.split(".").str[0].str.strip()

    # Fold de 4 position-slots ud til lange rækker: én række pr. (spiller, position-slot)
    slots = []
    for i in range(1, 5):
        kode_kol = f"POSITION{i}CODE"
        pct_kol = f"POSITIONS{i}PERCENT"  # bemærk "S" - sådan hedder kolonnen faktisk
        if kode_kol not in pos_df.columns or pct_kol not in pos_df.columns:
            continue
        slot = pos_df[["PLAYER_WYID", kode_kol, pct_kol]].copy()
        slot = slot.rename(columns={kode_kol: "POSITIONKODE", pct_kol: "POSITIONPCT"})
        slots.append(slot)

    if not slots:
        return pd.DataFrame(columns=[
            "PLAYER_WYID", "PRIMAER_POSITION_KODE", "PRIMAER_POSITIONSGRUPPE",
            "SAMLET_PROCENT_I_POSITION"
        ])

    lang = pd.concat(slots, ignore_index=True)
    lang["POSITIONKODE"] = lang["POSITIONKODE"].astype(str).str.lower().str.strip()
    lang = lang[lang["POSITIONKODE"].notna() & (lang["POSITIONKODE"] != "") & (lang["POSITIONKODE"] != "nan")]
    lang["POSITIONPCT"] = pd.to_numeric(lang["POSITIONPCT"], errors="coerce").fillna(0)

    agg = (
        lang.groupby(["PLAYER_WYID", "POSITIONKODE"])["POSITIONPCT"]
        .sum()
        .reset_index()
    )

    # Vælg positionen med højest samlet procent pr. spiller
    idx = agg.groupby("PLAYER_WYID")["POSITIONPCT"].idxmax()
    primaer = agg.loc[idx].reset_index(drop=True)
    primaer = primaer.rename(columns={
        "POSITIONKODE": "PRIMAER_POSITION_KODE",
        "POSITIONPCT": "SAMLET_PROCENT_I_POSITION"
    })
    primaer["PRIMAER_POSITIONSGRUPPE"] = primaer["PRIMAER_POSITION_KODE"].map(POSITION_GROUP_MAP).fillna("Ukendt")

    return primaer[[
        "PLAYER_WYID", "PRIMAER_POSITION_KODE", "PRIMAER_POSITIONSGRUPPE", "SAMLET_PROCENT_I_POSITION"
    ]]


def berig_med_spillernavne(primaere_positioner_df, players_df):
    """
    Beriger resultatet fra beregn_primaere_positioner() med spillernavne fra
    WYSCOUT_PLAYERS.

    Parametre:
        primaere_positioner_df: output fra beregn_primaere_positioner()
        players_df: rådata fra WYSCOUT_PLAYERS. Forventede kolonner (mindst):
            PLAYER_WYID, SHORTNAME, FIRSTNAME, LASTNAME

    Returnerer:
        primaere_positioner_df beriget med kolonnerne:
        NAVN (= SHORTNAME hvis udfyldt, ellers FIRSTNAME + LASTNAME), FIRSTNAME, LASTNAME
    """
    if primaere_positioner_df.empty:
        return primaere_positioner_df

    spillere = players_df.copy()
    spillere.columns = [c.upper() for c in spillere.columns]
    spillere["PLAYER_WYID"] = spillere["PLAYER_WYID"].astype(str).str.split(".").str[0].str.strip()

    def afled_navn(row):
        # Understøtter både SHORTNAME (fra WYSCOUT_PLAYERS direkte) og
        # PLAYER_NAME (fra queries["players"]/["wyscout_players"], som omdøber SHORTNAME)
        for kol in ("SHORTNAME", "PLAYER_NAME"):
            kort = str(row.get(kol, "") or "").strip()
            if kort and kort.lower() != "nan":
                return kort
        fornavn = str(row.get("FIRSTNAME", "") or "").strip()
        efternavn = str(row.get("LASTNAME", "") or "").strip()
        navn = f"{fornavn} {efternavn}".strip()
        return navn if navn else "Ukendt spiller"

    spillere["NAVN"] = spillere.apply(afled_navn, axis=1)

    behold_kolonner = ["PLAYER_WYID", "NAVN"] + [c for c in ("FIRSTNAME", "LASTNAME") if c in spillere.columns]
    resultat = primaere_positioner_df.merge(
        spillere[behold_kolonner],
        on="PLAYER_WYID",
        how="left"
    )
    resultat["NAVN"] = resultat["NAVN"].fillna("Ukendt spiller")

    return resultat


def hent_position_for_spiller(pid, primaere_positioner_df):
    """
    Slår en enkelt spillers primære position op i resultatet fra
    beregn_primaere_positioner(). Bruges som erstatning for map_position(ROLECODE3).

    Returnerer ("Ukendt", "Ukendt") hvis spilleren ikke findes.
    """
    clean_pid = str(pid).split(".")[0].strip()
    m = primaere_positioner_df[primaere_positioner_df["PLAYER_WYID"] == clean_pid]
    if m.empty:
        return "Ukendt", "Ukendt"
    r = m.iloc[0]
    return r["PRIMAER_POSITION_KODE"], r["PRIMAER_POSITIONSGRUPPE"]


# --------------------------------------------------------------------------
# 3. METRICS PR. POSITIONSGRUPPE
# --------------------------------------------------------------------------
# Hver metric er defineret som enten:
#   ("p90", label, rå_kolonne)                -> værdi pr. 90 minutter
#   ("pct", label, succes_kolonne, total_kolonne) -> succesrate i %
#
# Baseret på kolonnerne i WYSCOUT_MATCHADVANCEDPLAYERSTATS_TOTAL /
# jeres sæson-aggregerede advanced_stats_df (samme kolonnenavne, blot summeret).

METRICS_BY_GROUP = {
    "Målmand": [
        ("p90", "Redninger P90", "GKSAVES"),
        ("pct", "Exits succesrate %", "GKSUCCESSFULEXITS", "GKEXITS"),
        ("pct", "Luftdueller vundet %", "GKAERIALDUELSWON", "GKAERIALDUELS"),
    ],
    "Back": [
        ("pct", "Dueller vundet %", "DUELSWON", "DUELS"),
        ("pct", "Defensive dueller vundet %", "DEFENSIVEDUELSWON", "DEFENSIVEDUELS"),
        ("p90", "Interceptions P90", "INTERCEPTIONS"),
        ("p90", "Driblinger P90", "SUCCESSFULDRIBBLES"),
        ("pct", "Pasning %", "SUCCESSFULPASSES", "PASSES"),
        ("p90", "Indlæg P90", "SUCCESSFULCROSSES"),
    ],
    "Midtstopper": [
        ("pct", "Dueller vundet %", "DUELSWON", "DUELS"),
        ("pct", "Defensive dueller vundet %", "DEFENSIVEDUELSWON", "DEFENSIVEDUELS"),
        ("pct", "Luftdueller vundet %", "AERIALDUELSWON", "AERIALDUELS"),
        ("p90", "Interceptions P90", "INTERCEPTIONS"),
        ("p90", "Clearances P90", "CLEARANCES"),
        ("pct", "Pasning %", "SUCCESSFULPASSES", "PASSES"),
    ],
    "Def. Midtbane": [
        ("pct", "Dueller vundet %", "DUELSWON", "DUELS"),
        ("p90", "Interceptions P90", "INTERCEPTIONS"),
        ("p90", "Recoveries P90", "RECOVERIES"),
        ("pct", "Pasning %", "SUCCESSFULPASSES", "PASSES"),
        ("p90", "Progressive pasninger P90", "SUCCESSFULPROGRESSIVEPASSES"),
    ],
    "Central Midtbane": [
        ("pct", "Pasning %", "SUCCESSFULPASSES", "PASSES"),
        ("p90", "Progressive pasninger P90", "SUCCESSFULPROGRESSIVEPASSES"),
        ("p90", "Key Passes P90", "KEYPASSES"),
        ("p90", "Interceptions P90", "INTERCEPTIONS"),
        ("pct", "Dueller vundet %", "DUELSWON", "DUELS"),
    ],
    "Off. Midtbane": [
        ("p90", "Key Passes P90", "KEYPASSES"),
        ("p90", "XA P90", "XGASSIST"),
        ("p90", "XG P90", "XGSHOT"),
        ("p90", "Driblinger P90", "SUCCESSFULDRIBBLES"),
        ("p90", "Touches i feltet P90", "TOUCHINBOX"),
    ],
    "Kant": [
        ("p90", "Driblinger P90", "SUCCESSFULDRIBBLES"),
        ("p90", "XA P90", "XGASSIST"),
        ("p90", "XG P90", "XGSHOT"),
        ("p90", "Indlæg P90", "SUCCESSFULCROSSES"),
        ("p90", "Touches i feltet P90", "TOUCHINBOX"),
    ],
    "Angriber": [
        ("p90", "XG P90", "XGSHOT"),
        ("p90", "XA P90", "XGASSIST"),
        ("p90", "Skud P90", "SHOTS"),
        ("p90", "Touches i feltet P90", "TOUCHINBOX"),
        ("p90", "Driblinger P90", "SUCCESSFULDRIBBLES"),
    ],
    "Ukendt": [
        ("pct", "Dueller vundet %", "DUELSWON", "DUELS"),
        ("p90", "Driblinger P90", "SUCCESSFULDRIBBLES"),
        ("pct", "Pasning %", "SUCCESSFULPASSES", "PASSES"),
        ("p90", "XG P90", "XGSHOT"),
    ],
}


def beregn_metrics_for_gruppe(pid, positionsgruppe, advanced_stats_df, min_minutter=45):
    """
    Udregner de relevante metrics for en given positionsgruppe, ud fra det
    sæson-aggregerede advanced_stats_df (samme datakilde/struktur som
    beregn_p90_stats i comparison.py forventer).

    Returnerer en dict {label: værdi}, eller {label: "-"} hvis spilleren har
    for få minutter eller ikke findes.
    """
    definitioner = METRICS_BY_GROUP.get(positionsgruppe, METRICS_BY_GROUP["Ukendt"])

    if advanced_stats_df is None or advanced_stats_df.empty:
        return {d[1]: "-" for d in definitioner}

    df = advanced_stats_df.copy()
    df.columns = [c.upper() for c in df.columns]

    clean_pid = str(pid).split(".")[0].strip()
    df["PLAYER_WYID"] = df["PLAYER_WYID"].astype(str).str.split(".").str[0].str.strip()
    p_row = df[df["PLAYER_WYID"] == clean_pid]

    if p_row.empty:
        return {d[1]: "-" for d in definitioner}

    r = p_row.iloc[0]
    mins = float(r.get("MINUTESONFIELD", 0) or 0)

    if mins < min_minutter:
        return {d[1]: "-" for d in definitioner}

    resultat = {}
    for definition in definitioner:
        if definition[0] == "p90":
            _, label, kolonne = definition
            vaerdi = float(r.get(kolonne, 0) or 0)
            resultat[label] = round((vaerdi / mins) * 90, 2)
        elif definition[0] == "pct":
            _, label, succes_kol, total_kol = definition
            total = float(r.get(total_kol, 0) or 0)
            succes = float(r.get(succes_kol, 0) or 0)
            resultat[label] = round((succes / total) * 100, 1) if total > 0 else 0.0

    return resultat
