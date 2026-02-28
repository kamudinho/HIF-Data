# --- Sæson og eget hold ---
SEASONNAME = "2025/2026"
TEAM_WYID = 7490
# Vi holder denne som en tuple for at matche din SQL 'IN' logik
COMPETITION_WYID = (328,) 

# --- Avanceret Turnering Mapping (COMP_MAP) ---
# Denne struktur gør det muligt at slå op i begge retninger
COMPETITIONS = {
    "3F Superliga": {
        "comp_wyid": 335, 
        "opta_uuid": "29actv1ohj8r10kd9hu0jnb0n"
    },
    "Betinia Ligaen": {
        "comp_wyid": 328, 
        "opta_uuid": "6ifaeunfdelecgticvxanikzu"
    },
    "2. division": {
        "comp_wyid": 329, 
        "opta_uuid": None
    },
    "3. division": {
        "comp_wyid": 43319, 
        "opta_uuid": None
    },
    "Oddset Pokalen": {
        "comp_wyid": 331, 
        "opta_uuid": None
    },
    "U19 Ligaen": {
        "comp_wyid": 1305, 
        "opta_uuid": None
    }
}

# --- Bagudkompatibel COMP_MAP (til dine nuværende dashboards) ---
# Denne funktion genererer automatisk din gamle COMP_MAP struktur
# så du ikke behøver rette i alle dine eksisterende filer.
COMP_MAP = {}
for name, ids in COMPETITIONS.items():
    COMP_MAP[ids["comp_wyid"]] = name
    if ids["opta_uuid"]:
        COMP_MAP[ids["opta_uuid"]] = name
