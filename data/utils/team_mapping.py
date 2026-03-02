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
    # --- Betinia Ligaen (NordicBet Liga) ---
    "Hvidovre IF": {"team_wyid": 7490, "opta_uuid": "8gxd9ry2580pu1b1dd5ny9ymy", "opta_id": 2397, "league": "Betinia Ligaen"},
    "AaB": {"team_wyid": 7454, "opta_uuid": "36g6ifzjliec1jqnbtf7yesme", "opta_id": 401, "league": "Betinia Ligaen"},
    "Horsens": {"team_wyid": 7465, "opta_uuid": "60msc9045s5v96pghp5px88v", "opta_id": 2289, "league": "Betinia Ligaen"},
    "Lyngby Boldklub": {"team_wyid": 7484, "opta_uuid": "272_uuid_dummy", "opta_id": 272, "league": "Betinia Ligaen"},
    "Esbjerg": {"team_wyid": 7451, "opta_uuid": "2v69668s6p2c68wz2hpg018h2", "opta_id": 1409, "league": "Betinia Ligaen"},
    "Kolding IF": {"team_wyid": 7622, "opta_uuid": "9935j8s3d9m257n9v6p9v6p9v", "opta_id": 13253, "league": "Betinia Ligaen"},
    "Hobro": {"team_wyid": 7510, "opta_uuid": "4t96h936f01p4v02r76h9h0be", "opta_id": 4802, "league": "Betinia Ligaen"},
    "HB Køge": {"team_wyid": 7615, "opta_uuid": "8cfkisxf1fkxdqtt6tx1tup48", "opta_id": 4042, "league": "Betinia Ligaen"},
    "Hillerød": {"team_wyid": 7699, "opta_uuid": "6v99668s6p2c68wz2hpg018h3", "opta_id": 6463, "league": "Betinia Ligaen"},
    "Aarhus Fremad": {"team_wyid": 7502, "opta_uuid": "6v69668s6p2c68wz2hpg018h2", "opta_id": 2290, "league": "Betinia Ligaen"},
    "B.93": {"team_wyid": 7470, "opta_uuid": "7v69668s6p2c68wz2hpg018h2", "opta_id": 2935, "league": "Betinia Ligaen"},
    "FC Roskilde": {"team_wyid": 7497, "opta_uuid": "3050_uuid_dummy", "opta_id": 3050, "league": "Betinia Ligaen"},

    # --- 3F Superliga ---
    "FC København": {"team_wyid": 7452, "opta_uuid": "569_uuid_dummy", "opta_id": 569, "league": "3F Superliga"},
    "FC Midtjylland": {"team_wyid": 7455, "opta_uuid": "1000_uuid_dummy", "opta_id": 1000, "league": "3F Superliga"},
    "Brøndby IF": {"team_wyid": 7453, "opta_uuid": "239_uuid_dummy", "opta_id": 239, "league": "3F Superliga"},
    "AGF": {"team_wyid": 7457, "opta_uuid": "420_uuid_dummy", "opta_id": 420, "league": "3F Superliga"},
    "FC Nordsjælland": {"team_wyid": 7458, "opta_uuid": "2592_uuid_dummy", "opta_id": 2592, "league": "3F Superliga"},
    "Viborg FF": {"team_wyid": 7456, "opta_uuid": "547_uuid_dummy", "opta_id": 547, "league": "3F Superliga"},
    "SønderjyskE": {"team_wyid": 7499, "opta_uuid": "2827_uuid_dummy", "opta_id": 2827, "league": "3F Superliga"},
    "Randers FC": {"team_wyid": 7462, "opta_uuid": "1943_uuid_dummy", "opta_id": 1943, "league": "3F Superliga"},
    "Silkeborg IF": {"team_wyid": 7461, "opta_uuid": "418_uuid_dummy", "opta_id": 418, "league": "3F Superliga"},
    "Vejle Boldklub": {"team_wyid": 7473, "opta_uuid": "2450_uuid_dummy", "opta_id": 2450, "league": "3F Superliga"},
    "OB": {"team_wyid": 7460, "opta_uuid": "5rz9enoyknpg8ji78za5b82p8", "opta_id": 545, "league": "3F Superliga"},
    "FC Fredericia": {"team_wyid": 7469, "opta_uuid": "3051_uuid_dummy", "opta_id": 3051, "league": "3F Superliga"},

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
