# --- 1. VALG AF LIGA (DETTE ER DET ENESTE STED DU RETTER) ---
VALGT_LIGA = "1. Division"  # Skift til "3F Superliga" når de rykker op!
SEASONNAME = "2025/2026" 
TEAM_WYID = 7490
TEAM_OPTA_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"
TOURNAMENTCALENDAR_NAME = "2025/2026" 

# --- 2. AVANCERET TURNERING MAPPING ---
COMPETITIONS = {
    "1. Division": {
        "wyid": 328, 
        "opta_uuid": "6ifaeunfdelecgticvxanikzu"
    },
    "Superliga": {
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

# --- 3. AUTOMATISK OPSÆTNING AF ID'ER (Baseret på VALGT_LIGA) ---
# Disse linjer henter selv de rigtige ID'er fra din mapping ovenfor
COMPETITION_WYID = (COMPETITIONS[VALGT_LIGA]["wyid"],)
OPTA_COMP_UUID = COMPETITIONS[VALGT_LIGA]["opta_uuid"]

# --- 4. HJÆLPEFUNKTIONER & BAGUDKOMPATIBEL COMP_MAP ---
def get_league_ids(league_name=VALGT_LIGA):
    conf = COMPETITIONS.get(league_name, {})
    ids = []
    if conf.get("wyid"): ids.append(str(conf["wyid"]))
    if conf.get("opta_uuid"): ids.append(conf["opta_uuid"])
    return ids

def get_competition_name(id_val):
    id_str = str(id_val)
    for name, ids in COMPETITIONS.items():
        if id_str == str(ids["wyid"]) or id_str == ids["opta_uuid"]:
            return name
    return "Ukendt Turnering"

# Genererer COMP_MAP automatisk
COMP_MAP = {}
for name, ids in COMPETITIONS.items():
    if ids["wyid"]: COMP_MAP[ids["wyid"]] = name
    if ids["opta_uuid"]: COMP_MAP[ids["opta_uuid"]] = name
