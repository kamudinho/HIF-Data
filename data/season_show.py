# season_show.py - CENTRAL STYRING FOR HVIDOVRE-APP 2025/2026

# season_show.py
SEASONNAME = "2025/2026"
OPTA_SEASON_NAME = "2025/2026" 
TEAM_WYID = 7490

# Tjek at dette UUID matcher NordicBet Ligaen 25/26 i din Opta data
COMPETITION_WYID = (328,) 
OPTA_COMP_UUID = "6ifaeunfdelecgticvxanikzu"

# --- 2. AVANCERET TURNERING MAPPING ---
# Denne struktur sikrer, at appen virker uanset om data kommer fra WYSCOUT eller OPTA
COMPETITIONS = {
    "Betinia Ligaen": {
        "wyid": 328, 
        "opta_uuid": "6ifaeunfdelecgticvxanikzu"
    },
    "3F Superliga": {
        "wyid": 335, 
        "opta_uuid": "29actv1ohj8r10kd9hu0jnb0n"
    },
    "2. division": {
        "wyid": 329, 
        "opta_uuid": None
    },
    "3. division": {
        "wyid": 43319, 
        "opta_uuid": None
    },
    "Oddset Pokalen": {
        "wyid": 331, 
        "opta_uuid": None
    },
    "U19 Ligaen": {
        "wyid": 1305, 
        "opta_uuid": None
    }
}

# --- 3. HJÆLPEFUNKTIONER TIL FILTRERING ---

def get_league_ids(league_name="Betinia Ligaen"):
    """
    Returnerer en liste med både Wyscout ID og Opta UUID 
    for at sikre korrekt filtrering i dine dataframes.
    """
    conf = COMPETITIONS.get(league_name, {})
    ids = []
    if conf.get("wyid"):
        ids.append(str(conf["wyid"]))
    if conf.get("opta_uuid"):
        ids.append(conf["opta_uuid"])
    return ids

def get_competition_name(id_val):
    """
    Slår et ID (Wyscout eller Opta) op og returnerer det læselige navn.
    Svarer til din gamle COMP_MAP logik.
    """
    id_str = str(id_val)
    for name, ids in COMPETITIONS.items():
        if id_str == str(ids["wyid"]) or id_str == ids["opta_uuid"]:
            return name
    return "Ukendt Turnering"

# --- 4. BAGUDKOMPATIBEL COMP_MAP ---
# Genererer den COMP_MAP du plejer at bruge, så dine gamle scripts ikke fejler
COMP_MAP = {}
for name, ids in COMPETITIONS.items():
    if ids["wyid"]:
        COMP_MAP[ids["wyid"]] = name
    if ids["opta_uuid"]:
        COMP_MAP[ids["opta_uuid"]] = name
