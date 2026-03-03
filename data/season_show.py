from data.utils.team_mapping import COMPETITIONS

# --- 1. DETTE ER DET ENESTE STED DU RETTER FREMOVER ---
TOURNAMENTCALENDAR_NAME = "2025/2026" 
TEAM_WYID = 7490
TEAM_OPTA_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"

# --- 2. AUTOMATISK OPSÆTNING (Læser fra TEAM_MAPPING) ---
liga_info = COMPETITIONS.get(VALGT_LIGA, {})
COMPETITION_WYID = (liga_info.get("wyid"),)
OPTA_COMP_UUID = liga_info.get("COMPETITION_OPTAUUID")

# --- 3. HJÆLPEFUNKTIONER ---
def get_league_ids(league_name=VALGT_LIGA):
    conf = COMPETITIONS.get(league_name, {})
    ids = []
    if conf.get("wyid"): ids.append(str(conf["wyid"]))
    if conf.get("COMPETITION_OPTAUUID"): ids.append(conf["COMPETITION_OPTAUUID"])
    return ids

def get_competition_name(id_val):
    id_str = str(id_val)
    for name, info in COMPETITIONS.items():
        if id_str == str(info.get("wyid")) or id_str == info.get("COMPETITION_OPTAUUID"):
            return name
    return "Ukendt Turnering"

# Genererer COMP_MAP automatisk til brug i andre visninger
COMP_MAP = {}
for name, info in COMPETITIONS.items():
    if info.get("wyid"): COMP_MAP[info["wyid"]] = name
    if info.get("COMPETITION_OPTAUUID"): COMP_MAP[info["COMPETITION_OPTAUUID"]] = name
