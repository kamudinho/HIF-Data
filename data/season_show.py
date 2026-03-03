from data.utils.team_mapping import COMPETITIONS

# --- 1. VALG AF LIGA ---
VALGT_LIGA = "1. Division" 
SEASONNAME = "2025/2026" 
TEAM_WYID = 7490
TOURNAMENTCALENDAR_NAME = "2025/2026" 

# --- 2. HENT INFO FRA CENTRAL MAPPING ---
# Nu bruger vi de nye kolonnenavne du lige har lavet
liga_info = COMPETITIONS.get(VALGT_LIGA, {})
COMPETITION_WYID = (liga_info.get("wyid"),)
OPTA_COMP_UUID = liga_info.get("COMPETITION_OPTAUUID")

# --- 3. AUTOMATISK COMP_MAP GENERERING ---
COMP_MAP = {info["wyid"]: navn for navn, info in COMPETITIONS.items() if info.get("wyid")}
# Tilføj Opta UUIDs til map hvis de findes
for navn, info in COMPETITIONS.items():
    if info.get("COMPETITION_OPTAUUID"):
        COMP_MAP[info["COMPETITION_OPTAUUID"]] = navn

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
