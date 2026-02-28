# data/utils/team_mapping.py

# --- Turneringer / Ligaer ---
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

# --- Hold ---
TEAMS = {
    # --- Betinia Ligaen (1. division) ---
    "Hvidovre IF": {"team_wyid": 7490, "opta_uuid": "8gxd9ry2580pu1b1dd5ny9ymy", "league": "Betinia Ligaen"},
    "AaB": {"team_wyid": 7454, "opta_uuid": "36g6ifzjliec1jqnbtf7yesme", "league": "Betinia Ligaen"},
    "Horsens": {"team_wyid": 7465, "opta_uuid": "5rz9enoyknpg8ji78za5b82p0", "league": "Betinia Ligaen"},
    "Lyngby": {"team_wyid": 7484, "opta_uuid": "anga7587r1zv4ey71ge9zxol3", "league": "Betinia Ligaen"},
    "Esbjerg": {"team_wyid": 7451, "opta_uuid": "2v69668s6p2c68wz2hpg018h2", "league": "Betinia Ligaen"},
    "Kolding IF": {"team_wyid": 7622, "opta_uuid": "d1zdf956i09p4v02r76h9h0be", "league": "Betinia Ligaen"},
    "Hobro": {"team_wyid": 7510, "opta_uuid": "4t96h936f01p4v02r76h9h0be", "league": "Betinia Ligaen"},
    "HB Køge": {"team_wyid": 7615, "opta_uuid": "8cfkisxf1fkxdqtt6tx1tup48", "league": "Betinia Ligaen"},
    "Hillerød": {"team_wyid": 7699, "opta_uuid": "9v69668s6p2c68wz2hpg018h2", "league": "Betinia Ligaen"},
    "Aarhus Fremad": {"team_wyid": 7502, "opta_uuid": "6v69668s6p2c68wz2hpg018h2", "league": "Betinia Ligaen"},
    "B.93": {"team_wyid": 7470, "opta_uuid": "7v69668s6p2c68wz2hpg018h2", "league": "Betinia Ligaen"},
    "Middelfart": {"team_wyid": 7578, "opta_uuid": "3v69668s6p2c68wz2hpg018h2", "league": "Betinia Ligaen"},

    # --- 3F Superliga ---
    "Copenhagen": {"team_wyid": 7452, "opta_uuid": "5rz9enoyknpg8ji78za5b82p1", "league": "3F Superliga"},
    "Midtjylland": {"team_wyid": 7455, "opta_uuid": "5rz9enoyknpg8ji78za5b82p2", "league": "3F Superliga"},
    "Brøndby": {"team_wyid": 7453, "opta_uuid": "5rz9enoyknpg8ji78za5b82p3", "league": "3F Superliga"},
    "AGF": {"team_wyid": 7457, "opta_uuid": "5rz9enoyknpg8ji78za5b82p4", "league": "3F Superliga"},
    "Nordsjælland": {"team_wyid": 7458, "opta_uuid": "5rz9enoyknpg8ji78za5b82p5", "league": "3F Superliga"},
    "Viborg": {"team_wyid": 7456, "opta_uuid": "5rz9enoyknpg8ji78za5b82p6", "league": "3F Superliga"},
    "SønderjyskE": {"team_wyid": 7499, "opta_uuid": "5rz9enoyknpg8ji78za5b82p7", "league": "3F Superliga"},
    "OB": {"team_wyid": 7460, "opta_uuid": "5rz9enoyknpg8ji78za5b82p8", "league": "3F Superliga"},
    "Randers": {"team_wyid": 7462, "opta_uuid": "5rz9enoyknpg8ji78za5b82p9", "league": "3F Superliga"},
    "Fredericia": {"team_wyid": 7469, "opta_uuid": "5rz9enoyknpg8ji78za5b82p0", "league": "3F Superliga"},
    "Silkeborg": {"team_wyid": 7461, "opta_uuid": "5rz9enoyknpg8ji78za5b82p1", "league": "3F Superliga"},
    "Vejle": {"team_wyid": 7473, "opta_uuid": "5rz9enoyknpg8ji78za5b82p2", "league": "3F Superliga"},

    # --- 2. division ---
    "AB": {"team_wyid": 7464, "league": "2. division"},
    "Næstved": {"team_wyid": 7475, "league": "2. division"},
    "Roskilde": {"team_wyid": 7497, "league": "2. division"},
    "Thisted": {"team_wyid": 7513, "league": "2. division"},
    "HIK": {"team_wyid": 7476, "league": "2. division"},
    "Vendsyssel": {"team_wyid": 7488, "league": "2. division"},
    "VSK Aarhus": {"team_wyid": 38132, "league": "2. division"},
    "Fremad Amager": {"team_wyid": 7471, "league": "2. division"},
    "Brabrand": {"team_wyid": 7482, "league": "2. division"},
    "Ishøj": {"team_wyid": 70771, "league": "2. division"},
    "Skive": {"team_wyid": 7491, "league": "2. division"},
    "Helsingør": {"team_wyid": 7566, "league": "2. division"},

    # --- 3. division ---
    "Nykøbing": {"team_wyid": 7526, "league": "3. division"},
    "FA 2000": {"team_wyid": 7644, "league": "3. division"},
    "Holbæk B&I": {"team_wyid": 30574, "league": "3. division"},
    "Brønshøj": {"team_wyid": 7472, "league": "3. division"},
    "Hørsholm-Usserød": {"team_wyid": 71244, "league": "3. division"},
    "Frem": {"team_wyid": 7463, "league": "3. division"},
    "Vanløse": {"team_wyid": 7551, "league": "3. division"},
    "Næsby": {"team_wyid": 7503, "league": "3. division"},
    "Vejgaard B": {"team_wyid": 25748, "league": "3. division"},
    "Lyseng": {"team_wyid": 7649, "league": "3. division"},
    "Sundby": {"team_wyid": 34555, "league": "3. division"},
    "Odder": {"team_wyid": 7588, "league": "3. division"}
}

# --- Hjælpefunktioner ---

def get_team_name(team_id):
    """Slår navnet op baseret på team_wyid (int) eller opta_uuid (str)"""
    for name, info in TEAMS.items():
        if info.get("team_wyid") == team_id or info.get("opta_uuid") == team_id:
            return name
    return str(team_id)

def get_league_name(league_id):
    """Slår liganavnet op baseret på comp_wyid (int) eller opta_uuid (str)"""
    for name, info in COMPETITIONS.items():
        if info.get("comp_wyid") == league_id or info.get("opta_uuid") == league_id:
            return name
    return str(league_id)

def get_teams_by_league(league_input):
    """
    Henter holdnavne. league_input kan være navn (f.eks. 'Betinia Ligaen') 
    eller comp_wyid (f.eks. 328).
    """
    league_name = league_input
    if isinstance(league_input, int):
        league_name = get_league_name(league_input)
    
    return [name for name, info in TEAMS.items() if info["league"] == league_name]

def get_hvi_ids():
    """Henter ID'erne for Hvidovre IF"""
    hvi = TEAMS["Hvidovre IF"]
    return hvi["team_wyid"], hvi["opta_uuid"]
