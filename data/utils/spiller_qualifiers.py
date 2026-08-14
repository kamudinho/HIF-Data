"""
#data/utils/spiller_qualifiers.py
==========

Overskuelig mapping af Opta "Match Events" (MA3) data.

Formål:
  Opta's rå feed består af to lag:
    1) EVENT TYPES (typeId)   -> selve aktionen, fx "Pass", "Tackle", "Goal"
    2) QUALIFIERS (qualifierId) -> ekstra detaljer om aktionen, fx
       "Cross", "Long ball", "Head", "Blocked" osv.

  Denne fil samler begge lag og grupperer dem i overordnede
  AKTIONSKATEGORIER (fx "Pasninger", "Afslutninger", "Tacklinger"),
  som derefter kobles til:
    - POSITIONER: GK, DEF, MID, FWD
    - HOLD-NIVEAU: offensiv / defensiv

  Kategorierne går bevidst igen på tværs af positioner, da fx en
  "duel" eller en "pasning" er relevant for alle positioner - blot
  med forskellig vægtning/hyppighed.

  Kilde for typeId og qualifierId: Opta Match Events (MA3) dokumentation.
  NB: Dokumentationen, filen bygger på, lister primært qualifiers og deres
  tilknyttede typeId-værdier (ikke selve typeId-navnene). typeId-navnene
  nedenfor følger Opta's offentligt kendte standardnavngivning og er
  nødvendige for at kunne "oversætte" tallene til noget læsbart.
"""

from __future__ import annotations
from typing import Dict, List, TypedDict


# ---------------------------------------------------------------------------
# 1. EVENT TYPES (typeId -> navn på aktionen)
# ---------------------------------------------------------------------------
EVENT_TYPES: Dict[int, str] = {
    1: "Pasning",
    2: "Pasning (offside)",
    3: "Driblinger (Take On)",
    4: "Frispark tildelt / Forseelse",
    5: "Bolden ude af spil",
    6: "Corner tildelt",
    7: "Tackling",
    8: "Interception",
    9: "Boldtab (Turnover)",
    10: "Redning (målmand)",
    11: "Grib (målmand, høj bold)",
    12: "Clearance",
    13: "Afslutning forbi mål (Miss)",
    14: "Afslutning i stolpe/overligger (Post)",
    15: "Afslutning reddet (Attempt Saved)",
    16: "Mål",
    17: "Kort (advarsel/udvisning)",
    18: "Spiller ud (udskiftning)",
    19: "Spiller ind (udskiftning)",
    20: "Spiller stopper karriere",
    21: "Spiller vender tilbage",
    22: "Markspiller bliver målmand",
    23: "Målmand bliver markspiller",
    24: "Kampbetingelser (vejr, underlag mm.)",
    25: "Dommerskift",
    27: "Kampafbrydelse (start)",
    28: "Kampafbrydelse (slut)",
    30: "Periode/Kamp slut",
    32: "Periode/Kamp start",
    34: "Holdopstilling",
    37: "Post-kamp kontrol/godkendelse",
    40: "Formationsændring",
    41: "Bokseredning (Punch)",
    43: "Slettet hændelse",
    44: "Luftduel (Aerial)",
    45: "Dueltackling (Challenge)",
    49: "Boldgenerobring (Ball Recovery)",
    50: "Boldtab efter pres (Dispossessed)",
    51: "Individuel fejl (Error)",
    52: "Målmand griber bolden (Keeper Pick-up)",
    54: "Ikke grebet indlæg (Cross Not Claimed)",
    58: "Straffespark reageret på (Penalty Faced)",
    60: "Målmand ude af mål (Keeper Sweeper)",
    61: "Stor chance forspildt (Chance Missed / Ball Touch)",
    65: "Omstridt dommerafgørelse / VAR",
    67: "50/50-duel",
    68: "Oplæg fra dommer (Drop Ball)",
    69: "Mislykket blokering",
    70: "Tillægstid annonceret",
    71: "Trænerteam opsætning",
    74: "Blokeret pasning",
    75: "Forsinkelse",
    76: "Midlertidig redning",
    77: "Spiller uden for banen",
    79: "Afbrydelse i videodækning",
    81: "Bolden rammer forhindring (dommer, hjørneflag mv.)",
    84: "Slettet efter VAR-gennemgang",
}

DEFENSIVE_TYPE_IDS = {
    4, 7, 8, 9, 10, 11, 12, 17, 41, 44, 45, 50, 51, 52, 54, 60, 67, 69, 74,
}
OFFENSIVE_TYPE_IDS = {
    1, 2, 3, 6, 13, 14, 15, 16, 49, 61,
}


# ---------------------------------------------------------------------------
# 2. QUALIFIERS (qualifierId -> navn, kort beskrivelse, relaterede typeId'er)
#    Udvalgt til de qualifiers, der reelt bruges til at kategorisere
#    aktioner. Listen kan udvides 1:1 efter samme mønster med resten af
#    Opta's ~490 qualifiers.
# ---------------------------------------------------------------------------
class Qualifier(TypedDict):
    navn: str
    beskrivelse: str
    type_ids: List[int]


QUALIFIERS: Dict[int, Qualifier] = {
    1:  {"navn": "Langaflevering", "beskrivelse": "Pasning over 32 meter", "type_ids": [1, 2]},
    2:  {"navn": "Indlæg", "beskrivelse": "Bold spillet ind fra kanten", "type_ids": [1, 2]},
    3:  {"navn": "Hovedaflevering", "beskrivelse": "Pasning med hovedet", "type_ids": [1, 2]},
    4:  {"navn": "Gennembrudspasning", "beskrivelse": "Through ball", "type_ids": [1, 2]},
    5:  {"navn": "Frispark afleveret", "beskrivelse": "Frispark eksekveret", "type_ids": [1, 2]},
    6:  {"navn": "Corner afleveret", "beskrivelse": "Hjørnespark eksekveret", "type_ids": [1, 2]},
    9:  {"navn": "Straffespark", "beskrivelse": "Straffesparks-relateret", "type_ids": [4, 10, 13, 14, 15, 16, 58, 65]},
    10: {"navn": "Håndbold", "beskrivelse": "Frispark/kort for hånd på bold", "type_ids": [4, 17]},
    13: {"navn": "Forseelse", "beskrivelse": "Alle fejl der udløser frispark/kort", "type_ids": [4, 17]},
    14: {"navn": "Sidste mand", "beskrivelse": "Defensiv aktion som sidste spiller", "type_ids": [7, 8, 10]},
    20: {"navn": "Højrefod", "beskrivelse": "Udført med højre fod", "type_ids": [13, 14, 15, 16]},
    22: {"navn": "Åbent spil", "beskrivelse": "Ikke fra dødbold", "type_ids": [1, 13, 14, 15, 16]},
    23: {"navn": "Kontraangreb", "beskrivelse": "Del af fastbreak", "type_ids": [1, 2, 3, 4, 13, 14, 15, 16]},
    24: {"navn": "Dødbold", "beskrivelse": "Efter frispark", "type_ids": [1, 13, 14, 15, 16]},
    25: {"navn": "Efter corner", "beskrivelse": "Opstod efter hjørnespark", "type_ids": [1, 13, 14, 15, 16]},
    26: {"navn": "Direkte fra frispark", "beskrivelse": "Skud direkte fra dødbold", "type_ids": [13, 14, 15, 16, 65]},
    29: {"navn": "Assisteret", "beskrivelse": "Forudgået af oplæg", "type_ids": [13, 14, 15, 16, 60]},
    31: {"navn": "Gult kort", "beskrivelse": "Advarsel", "type_ids": [17]},
    32: {"navn": "Andet gult kort", "beskrivelse": "Udvisning efter 2 gule", "type_ids": [17]},
    33: {"navn": "Rødt kort", "beskrivelse": "Direkte udvisning", "type_ids": [17, 65]},
    41: {"navn": "Skade", "beskrivelse": "Udskiftning/afbrydelse pga. skade", "type_ids": [18, 19, 27]},
    42: {"navn": "Taktisk udskiftning", "beskrivelse": "Udskiftning af taktiske årsager", "type_ids": [18, 19]},
    56: {"navn": "Zone", "beskrivelse": "Bane-zone hvor aktionen sker", "type_ids": [1, 2, 13, 14, 15, 16]},
    72: {"navn": "Venstrefod", "beskrivelse": "Udført med venstre fod", "type_ids": [13, 14, 15, 16]},
    82: {"navn": "Blokeret", "beskrivelse": "Afslutning blokeret", "type_ids": [15]},
    89: {"navn": "1-mod-1", "beskrivelse": "Alene med målmanden", "type_ids": [13, 14, 15, 16, 60]},
    94: {"navn": "Feltblokering", "beskrivelse": "Blokeret af markspiller", "type_ids": [10]},
    100: {"navn": "Blokeret i lille felt", "beskrivelse": "Blokeret afslutning i 6-meter feltet", "type_ids": [15]},
    108: {"navn": "Volley", "beskrivelse": "Direkte afslutning uden førsteberøring", "type_ids": [13, 14, 15, 16]},
    123: {"navn": "Målmandskast", "beskrivelse": "Udkast fra målmand", "type_ids": [1, 2]},
    124: {"navn": "Målspark", "beskrivelse": "Afspark efter udmål", "type_ids": [1]},
    128: {"navn": "Boksredning", "beskrivelse": "Målmand bokser bolden væk", "type_ids": [10, 11, 41]},
    133: {"navn": "Afbøjning", "beskrivelse": "Afsluttet skud afbøjet", "type_ids": [13, 14, 15, 16]},
    136: {"navn": "Målmand rørte bolden", "beskrivelse": "Mål scoret trods målmandsberøring", "type_ids": [16]},
    137: {"navn": "Reddet trods forbi mål", "beskrivelse": "Målmand redder skud der var forbi mål", "type_ids": [10, 13]},
    154: {"navn": "Oplæg til stor chance", "beskrivelse": "Pasning der skaber klar chance", "type_ids": [1, 13, 14, 15, 16, 60]},
    173: {"navn": "Parering til sikkerhed", "beskrivelse": "Målmand parerer i sikkerhed", "type_ids": [10]},
    174: {"navn": "Parering i fare", "beskrivelse": "Målmand parerer ud i farezone", "type_ids": [10]},
    176: {"navn": "Grebet", "beskrivelse": "Målmand griber bolden", "type_ids": [10]},
    177: {"navn": "Opsamlet", "beskrivelse": "Målmand samler rullende bold op", "type_ids": [10]},
    182: {"navn": "Med hænder", "beskrivelse": "Redning med hænderne", "type_ids": [10]},
    183: {"navn": "Med fødder", "beskrivelse": "Redning med fødderne", "type_ids": [10]},
    210: {"navn": "Assist", "beskrivelse": "Pasningen der forudgik skud/mål", "type_ids": [1]},
    214: {"navn": "Stor chance", "beskrivelse": "Klar oplagt scoringschance", "type_ids": [13, 14, 15, 16]},
    223: {"navn": "Indsvingende corner", "beskrivelse": "Corner der svinger mod mål", "type_ids": [1]},
    224: {"navn": "Udsvingende corner", "beskrivelse": "Corner der svinger væk fra mål", "type_ids": [1]},
    236: {"navn": "Blokeret pasning", "beskrivelse": "Pasning blokeret tæt på afgiver", "type_ids": [1]},
    285: {"navn": "Defensiv duel", "beskrivelse": "Duel vundet defensivt", "type_ids": [3, 4, 7, 10, 12, 44, 45, 50, 67, 69, 74]},
    286: {"navn": "Offensiv duel", "beskrivelse": "Duel vundet offensivt", "type_ids": [1, 3, 4, 7, 13, 14, 15, 16, 44, 45, 50, 67]},
    328: {"navn": "Førsteberøring", "beskrivelse": "Afslutning på første berøring", "type_ids": [13, 14, 15, 16]},
}


# ---------------------------------------------------------------------------
# 3. AKTIONSKATEGORIER
#    Her samles typeId + relevante qualifierId i overordnede,
#    genkendelige kategorier - fx "pasninger", "afslutninger", "tacklinger".
#    "side" angiver om kategorien primært er offensiv, defensiv, eller
#    kan være begge dele afhængig af udfald (fx duel, aerial).
# ---------------------------------------------------------------------------
class ActionCategory(TypedDict):
    navn: str
    beskrivelse: str
    type_ids: List[int]
    qualifier_ids: List[int]
    side: str  # "offensiv" | "defensiv" | "begge"


ACTION_CATEGORIES: Dict[str, ActionCategory] = {
    "pasninger": {
        "navn": "Pasninger",
        "beskrivelse": "Almindelige afleveringer, korte som lange",
        "type_ids": [1, 2],
        "qualifier_ids": [1, 3, 4, 22, 23, 24, 25, 56, 72, 123, 124, 236],
        "side": "offensiv",
    },
    "indlaeg": {
        "navn": "Indlæg / crosses",
        "beskrivelse": "Bolde spillet ind fra kanten mod boksen",
        "type_ids": [1, 2],
        "qualifier_ids": [2, 223, 224],
        "side": "offensiv",
    },
    "afgoerende_pasninger": {
        "navn": "Nøglepasninger / assists",
        "beskrivelse": "Pasninger der direkte skaber eller fører til mål",
        "type_ids": [1],
        "qualifier_ids": [154, 210, 29],
        "side": "offensiv",
    },
    "driblinger": {
        "navn": "Driblinger (Take On)",
        "beskrivelse": "Forsøg på at spille sig forbi en modstander",
        "type_ids": [3],
        "qualifier_ids": [],
        "side": "offensiv",
    },
    "afslutninger": {
        "navn": "Afslutninger",
        "beskrivelse": "Alle former for skud på/ved mål (mål, redning, forbi, stolpe)",
        "type_ids": [13, 14, 15, 16],
        "qualifier_ids": [9, 20, 26, 29, 72, 89, 108, 133, 154, 214, 328],
        "side": "offensiv",
    },
    "maal": {
        "navn": "Scoringer",
        "beskrivelse": "Mål scoret",
        "type_ids": [16],
        "qualifier_ids": [28, 136, 210],
        "side": "offensiv",
    },
    "tacklinger": {
        "navn": "Tacklinger",
        "beskrivelse": "Forsøg på at vinde bolden i tackling",
        "type_ids": [7],
        "qualifier_ids": [14],
        "side": "defensiv",
    },
    "interceptions": {
        "navn": "Interceptions",
        "beskrivelse": "Afbrydelse af modstanders pasning",
        "type_ids": [8],
        "qualifier_ids": [14],
        "side": "defensiv",
    },
    "clearances": {
        "navn": "Clearances",
        "beskrivelse": "Nedslag/frigørelse af bolden fra farezone",
        "type_ids": [12],
        "qualifier_ids": [14],
        "side": "defensiv",
    },
    "blokeringer": {
        "navn": "Blokeringer",
        "beskrivelse": "Blokering af skud eller pasning",
        "type_ids": [15, 74],
        "qualifier_ids": [82, 94, 100, 133, 192],
        "side": "defensiv",
    },
    "duel_i_luften": {
        "navn": "Luftduel (Aerial)",
        "beskrivelse": "Dueller om høj bold",
        "type_ids": [44],
        "qualifier_ids": [285, 286],
        "side": "begge",
    },
    "duel_paa_jorden": {
        "navn": "Jordduel / 50-50",
        "beskrivelse": "Dueller om bold langs jorden",
        "type_ids": [45, 67],
        "qualifier_ids": [285, 286],
        "side": "begge",
    },
    "forseelser": {
        "navn": "Forseelser / frispark begået",
        "beskrivelse": "Frispark tildelt modstander",
        "type_ids": [4],
        "qualifier_ids": [10, 12, 13],
        "side": "defensiv",
    },
    "kort": {
        "navn": "Kort",
        "beskrivelse": "Gult og rødt kort",
        "type_ids": [17],
        "qualifier_ids": [31, 32, 33],
        "side": "defensiv",
    },
    "redninger": {
        "navn": "Redninger (målmand)",
        "beskrivelse": "Alle former for redning",
        "type_ids": [10, 11, 41],
        "qualifier_ids": [128, 173, 174, 176, 177, 182, 183],
        "side": "defensiv",
    },
    "keeper_distribution": {
        "navn": "Målmandsudspil",
        "beskrivelse": "Målmandens opstart af angreb (kast, målspark)",
        "type_ids": [1],
        "qualifier_ids": [123, 124],
        "side": "offensiv",
    },
    "boldgenerobring": {
        "navn": "Boldgenerobringer",
        "beskrivelse": "Generobring af bolden efter boldtab",
        "type_ids": [49],
        "qualifier_ids": [],
        "side": "defensiv",
    },
    "boldtab": {
        "navn": "Boldtab",
        "beskrivelse": "Mistet bold under pres/fejl",
        "type_ids": [9, 50, 51],
        "qualifier_ids": [],
        "side": "offensiv",
    },
    "corner_frispark": {
        "navn": "Standardsituationer (hjørne/frispark)",
        "beskrivelse": "Tildelte og udførte dødbolde",
        "type_ids": [1, 2, 6],
        "qualifier_ids": [5, 6, 24, 25, 26, 223, 224],
        "side": "offensiv",
    },
}


# ---------------------------------------------------------------------------
# 4. POSITIONS-MAPPING
#    Kobler de ovenstående aktionskategorier til positionsgrupper.
#    Hver position har en liste af kategorier, der typisk er relevante
#    OFFENSIVT og en liste der er relevante DEFENSIVT.
#    Kategorier kan sagtens gå igen på tværs af positioner - det er
#    tilsigtet (fx "pasninger" og "duel_paa_jorden" er relevant for alle).
# ---------------------------------------------------------------------------
class PositionActions(TypedDict):
    offensiv: List[str]
    defensiv: List[str]


POSITION_ACTIONS: Dict[str, PositionActions] = {
    "GK": {
        "offensiv": [
            "pasninger",
            "keeper_distribution",
            "afgoerende_pasninger",
        ],
        "defensiv": [
            "redninger",
            "clearances",
            "blokeringer",
            "duel_i_luften",
            "boldgenerobring",
        ],
    },
    "DEF": {
        "offensiv": [
            "pasninger",
            "indlaeg",
            "afgoerende_pasninger",
            "corner_frispark",
            "boldtab",
        ],
        "defensiv": [
            "tacklinger",
            "interceptions",
            "clearances",
            "blokeringer",
            "duel_i_luften",
            "duel_paa_jorden",
            "forseelser",
            "kort",
            "boldgenerobring",
        ],
    },
    "MID": {
        "offensiv": [
            "pasninger",
            "indlaeg",
            "afgoerende_pasninger",
            "driblinger",
            "afslutninger",
            "corner_frispark",
            "boldtab",
        ],
        "defensiv": [
            "tacklinger",
            "interceptions",
            "duel_i_luften",
            "duel_paa_jorden",
            "forseelser",
            "kort",
            "boldgenerobring",
        ],
    },
    "FWD": {
        "offensiv": [
            "afslutninger",
            "maal",
            "driblinger",
            "pasninger",
            "afgoerende_pasninger",
            "duel_paa_jorden",
            "boldtab",
        ],
        "defensiv": [
            "duel_i_luften",
            "forseelser",
            "kort",
            "boldgenerobring",
        ],
    },
}


# ---------------------------------------------------------------------------
# 5. HOLD-NIVEAU (samlet offensivt / defensivt aktionssæt, uafhængigt af
#    position - nyttigt til holdstatistik/aggregering)
# ---------------------------------------------------------------------------
TEAM_LEVEL_ACTIONS: Dict[str, List[str]] = {
    "offensiv": [
        "pasninger",
        "indlaeg",
        "afgoerende_pasninger",
        "driblinger",
        "afslutninger",
        "maal",
        "keeper_distribution",
        "corner_frispark",
    ],
    "defensiv": [
        "tacklinger",
        "interceptions",
        "clearances",
        "blokeringer",
        "forseelser",
        "kort",
        "redninger",
        "boldgenerobring",
        "duel_i_luften",
        "duel_paa_jorden",
    ],
}


# ---------------------------------------------------------------------------
# 6. HJÆLPEFUNKTIONER
# ---------------------------------------------------------------------------
def get_categories_for_position(position: str, side: str | None = None) -> List[str]:
    """
    Returnerer aktionskategori-nøgler for en given position ("GK","DEF","MID","FWD").
    side: "offensiv", "defensiv" eller None (= begge, uden dubletter).
    """
    position = position.upper()
    if position not in POSITION_ACTIONS:
        raise ValueError(f"Ukendt position: {position}")

    if side is None:
        combined = POSITION_ACTIONS[position]["offensiv"] + POSITION_ACTIONS[position]["defensiv"]
        # bevar rækkefølge, fjern dubletter
        seen = set()
        result = []
        for cat in combined:
            if cat not in seen:
                seen.add(cat)
                result.append(cat)
        return result

    if side not in ("offensiv", "defensiv"):
        raise ValueError('side skal være "offensiv", "defensiv" eller None')

    return POSITION_ACTIONS[position][side]


def get_qualifiers_for_event(type_id: int) -> Dict[int, Qualifier]:
    """Returnerer alle qualifiers, der er relevante for en given typeId."""
    return {
        qid: q for qid, q in QUALIFIERS.items() if type_id in q["type_ids"]
    }


def describe_category(category_key: str) -> str:
    """Returnerer en læsbar beskrivelse af en aktionskategori inkl. typeId/qualifierId."""
    cat = ACTION_CATEGORIES[category_key]
    type_names = ", ".join(EVENT_TYPES.get(t, str(t)) for t in cat["type_ids"])
    qual_names = ", ".join(QUALIFIERS[q]["navn"] for q in cat["qualifier_ids"] if q in QUALIFIERS)
    return (
        f"{cat['navn']} ({cat['side']})\n"
        f"  Event-typer: {type_names}\n"
        f"  Qualifiers:  {qual_names or '—'}"
    )


if __name__ == "__main__":
    # Lille demo af mappingen
    for pos in ("GK", "DEF", "MID", "FWD"):
        print(f"\n=== {pos} ===")
        print("Offensivt: ", ", ".join(POSITION_ACTIONS[pos]["offensiv"]))
        print("Defensivt: ", ", ".join(POSITION_ACTIONS[pos]["defensiv"]))

    print("\n--- Eksempel: kategori-beskrivelse ---")
    print(describe_category("afslutninger"))
