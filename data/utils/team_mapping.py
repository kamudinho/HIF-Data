#data/utils/team_mapping.py

# --- GLOBAL KONTROL (RET KUN HER) ---
COMPETITION_NAME = "1. Division"
TOURNAMENTCALENDAR_NAME = "2025/2026"

# --- Turneringer ---
COMPETITIONS = {
    "1. Division": {
        "wyid": 328, 
        "COMPETITION_OPTAUUID": "6ifaeunfdelecgticvxanikzu",
        "COMPETITION_NAME": "1. Division"
    },
    "3F Superliga": {
        "wyid": 335, 
        "COMPETITION_OPTAUUID": "29actv1ohj8r10kd9hu0jnb0n",
        "COMPETITION_NAME": "Superliga"
    },
    "2. division": {"wyid": 329, "opta_uuid": None},
    "3. division": {"wyid": 43319, "opta_uuid": None},
    "Oddset Pokalen": {"wyid": 331, "opta_uuid": None},
    "U19 Ligaen": {"wyid": 1305, "opta_uuid": None}
}

# --- Hold ---
TEAMS = {
    "Hvidovre": {"team_wyid": 7490, "opta_uuid": "8gxd9ry2580pu1b1dd5ny9ymy", "opta_id": 2397, "league": "1. division", "logo": "https://cdn5.wyscout.com/photos/team/public/2659_120x120.png"},
    "AaB": {"team_wyid": 7454, "opta_uuid": "36g6ifzjliec1jqnbtf7yesme", "opta_id": 401, "league": "1. division", "logo": "https://cdn5.wyscout.com/photos/team/public/283_120x120.png"},
    "Horsens": {"team_wyid": 7465, "opta_uuid": "a9vw7ikerpr4cuweeeka5aneg", "opta_id": 2289, "league": "1. division", "logo": "https://cdn5.wyscout.com/photos/team/public/285_120x120.png"},
    "Lyngby": {"team_wyid": 7484, "opta_uuid": "anga7587r1zv4ey71ge9zxol3", "opta_id": 272, "league": "1. division", "logo": "https://cdn5.wyscout.com/photos/team/public/2527_120x120.png"},
    "Esbjerg": {"team_wyid": 7451, "opta_uuid": "f1h34qp5zbfl489q8vnkhiq9s", "opta_id": 1409, "league": "1. division", "logo": "https://cdn5.wyscout.com/photos/team/public/290_120x120.png"},
    "Kolding": {"team_wyid": 7622, "opta_uuid": "b8oqgvx1ijeyn6y1cn6929ix4", "opta_id": 13253, "league": "1. division", "logo": "https://cdn5.wyscout.com/photos/team/public/g13383_120x120.png"},
    "Hobro": {"team_wyid": 7510, "opta_uuid": "b2vft81kyjurzbmekvgrqwr64", "opta_id": 4802, "league": "1. division", "logo": "https://cdn5.wyscout.com/photos/team/public/2662_120x120.png"},
    "HB Køge": {"team_wyid": 7615, "opta_uuid": "8cfkisxf1fkxdqtt6tx1tup48", "opta_id": 4042, "league": "1. division", "logo": "https://cdn5.wyscout.com/photos/team/public/1941_120x120.png"},
    "Hillerød": {"team_wyid": 7699, "opta_uuid": "aqtkb4mgrz8c6iqfufj6qjbv9", "opta_id": 6463, "league": "1. division", "logo": "https://cdn5.wyscout.com/photos/team/public/g19126_120x120.png"},
    "Aarhus Fremad": {"team_wyid": 7502, "opta_uuid": "bfwi3pjyg3whbn0tpsz19e8hq", "opta_id": 2290, "league": "1. division", "logo": "https://cdn5.wyscout.com/photos/team/public/g3686_120x120.png"},
    "B 93": {"team_wyid": 7470, "opta_uuid": "ajtb177oqwawkdwbqhldmq6mx", "opta_id": 2935, "league": "1. division", "logo": "https://cdn5.wyscout.com/photos/team/public/g620_120x120.png"},
    "Middelfart": {"team_wyid": 7578, "opta_uuid": "eq2jaitwsokibzx3wy7kb5gqp", "opta_id": 3050, "league": "1. division", "logo": "https://cdn5.wyscout.com/photos/team/public/g11034_120x120.png"},    
    # --- 3F Superliga ---
    "FC København": {"team_wyid": 7452, "opta_uuid": "569_uuid_dummy", "opta_id": 569, "league": "3F Superliga", "logo": "https://cdn5.wyscout.com/photos/team/public/284_120x120.png"},
    "FC Midtjylland": {"team_wyid": 7455, "opta_uuid": "1000_uuid_dummy", "opta_id": 1000, "league": "3F Superliga", "logo": "https://cdn5.wyscout.com/photos/team/public/286_120x120.png"},
    "Brøndby IF": {"team_wyid": 7453, "opta_uuid": "239_uuid_dummy", "opta_id": 239, "league": "3F Superliga", "logo": "https://cdn5.wyscout.com/photos/team/public/291_120x120.png"},
    "AGF": {"team_wyid": 7457, "opta_uuid": "420_uuid_dummy", "opta_id": 420, "league": "3F Superliga", "logo": "https://cdn5.wyscout.com/photos/team/public/292_120x120.png"},
    "FC Nordsjælland": {"team_wyid": 7458, "opta_uuid": "2592_uuid_dummy", "opta_id": 2592, "league": "3F Superliga", "logo": "https://cdn5.wyscout.com/photos/team/public/289_120x120.png"},
    "Viborg FF": {"team_wyid": 7456, "opta_uuid": "547_uuid_dummy", "opta_id": 547, "league": "3F Superliga", "logo": "https://cdn5.wyscout.com/photos/team/public/2504_120x120.png"},
    "SønderjyskE": {"team_wyid": 7499, "opta_uuid": "2827_uuid_dummy", "opta_id": 2827, "league": "3F Superliga", "logo": "https://cdn5.wyscout.com/photos/team/public/796_120x120.png"},
    "Randers FC": {"team_wyid": 7462, "opta_uuid": "1943_uuid_dummy", "opta_id": 1943, "league": "3F Superliga", "logo": "https://cdn5.wyscout.com/photos/team/public/288_120x120.png"},
    "Silkeborg IF": {"team_wyid": 7461, "opta_uuid": "418_uuid_dummy", "opta_id": 418, "league": "3F Superliga", "logo": "https://cdn5.wyscout.com/photos/team/public/1948_120x120.png"},
    "Vejle Boldklub": {"team_wyid": 7473, "opta_uuid": "2450_uuid_dummy", "opta_id": 2450, "league": "3F Superliga", "logo": "https://cdn5.wyscout.com/photos/team/public/g623_120x120.png"},
    "OB": {"team_wyid": 7460, "opta_uuid": "5rz9enoyknpg8ji78za5b82p8", "opta_id": 545, "league": "3F Superliga", "logo": "https://cdn5.wyscout.com/photos/team/public/287_120x120.png"},
    "FC Fredericia": {"team_wyid": 7469, "opta_uuid": "3051_uuid_dummy", "opta_id": 3051, "league": "3F Superliga", "logo": "https://cdn5.wyscout.com/photos/team/public/2469_120x120.png"},

    # --- 2. division ---
    "AB": {"team_wyid": 7464, "league": "2. division", "logo": "https://cdn5.wyscout.com/photos/team/public/2470_120x120.png"},
    "Næstved": {"team_wyid": 7475, "league": "2. division", "logo": "https://cdn5.wyscout.com/photos/team/public/2501_120x120.png"},
    "Roskilde": {"team_wyid": 7497, "league": "2. division", "logo": "https://cdn5.wyscout.com/photos/team/public/2656_120x120.png"},
    "Thisted": {"team_wyid": 7513, "league": "2. division", "logo": "https://cdn5.wyscout.com/photos/team/public/g4526_120x120.png"},
    "HIK": {"team_wyid": 7476, "league": "2. division", "logo": "https://cdn5.wyscout.com/photos/team/public/g626_120x120.png"},
    "Vendsyssel": {"team_wyid": 7488, "league": "2. division", "logo": "https://cdn5.wyscout.com/photos/team/public/2661_120x120.png"},
    "VSK Aarhus": {"team_wyid": 38132, "league": "2. division", "logo": "https://cdn5.wyscout.com/photos/team/public/g36661_120x120.png"},
    "Fremad Amager": {"team_wyid": 7471, "league": "2. division", "logo": "https://cdn5.wyscout.com/photos/team/public/g621_120x120.png"},
    "Brabrand": {"team_wyid": 7482, "league": "2. division", "logo": "https://cdn5.wyscout.com/photos/team/public/g633_120x120.png"},
    "Ishøj": {"team_wyid": 70771, "league": "2. division", "logo": "-"},
    "Skive": {"team_wyid": 7491, "league": "2. division", "logo": "https://cdn5.wyscout.com/photos/team/public/2660_120x120.png"},
    "Helsingør": {"team_wyid": 7566, "league": "2. division", "logo": "https://cdn5.wyscout.com/photos/team/public/g11023_120x120.png"},

    # --- 3. division ---
    "Nykøbing": {"team_wyid": 7526, "league": "3. division", "logo": "https://cdn5.wyscout.com/photos/team/public/g6717_120x120.png"},
    "FA 2000": {"team_wyid": 7644, "league": "3. division", "logo": "https://cdn5.wyscout.com/photos/team/public/g15693_120x120.png"},
    "Holbæk B&I": {"team_wyid": 30574, "league": "3. division", "logo": "https://cdn5.wyscout.com/photos/team/public/g29003_120x120.png"},
    "Brønshøj": {"team_wyid": 7472, "league": "3. division", "logo": "https://cdn5.wyscout.com/photos/team/public/2663_120x120.png"},
    "Hørsholm-Usserød": {"team_wyid": 71244, "league": "3. division", "logo": "-"},
    "Frem": {"team_wyid": 7463, "league": "3. division", "logo": "https://cdn5.wyscout.com/photos/team/public/2575_120x120.png"},
    "Vanløse": {"team_wyid": 7551, "league": "3. division", "logo": "https://cdn5.wyscout.com/photos/team/public/g8650_120x120.png"},
    "Næsby": {"team_wyid": 7503, "league": "3. division", "logo": "https://cdn5.wyscout.com/photos/team/public/g3687_120x120.png"},
    "Vejgaard B": {"team_wyid": 25748, "league": "3. division", "logo": "https://cdn5.wyscout.com/photos/team/public/g24721_120x120.png"},
    "Lyseng": {"team_wyid": 7649, "league": "3. division", "logo": "https://cdn5.wyscout.com/photos/team/public/g15698_120x120.png"},
    "Sundby": {"team_wyid": 34555, "league": "3. division", "logo": "-"},
    "Odder": {"team_wyid": 7588, "league": "3. division", "logo": "https://cdn5.wyscout.com/photos/team/public/g11044_120x120.png"}
}

TEAM_COLORS = {
    "Hvidovre": {"primary": "#cc0000", "secondary": "#0000ff"},
    "B.93": {"primary": "#0000ff", "secondary": "#ffffff"},
    "Hillerød": {"primary": "#ff6600", "secondary": "#000000"},
    "Esbjerg": {"primary": "#003399", "secondary": "#ffffff"},
    "Lyngby": {"primary": "#003366", "secondary": "#ffffff"},
    "Horsens": {"primary": "#ffff00", "secondary": "#000000"},
    "Middelfart": {"primary": "#0099ff", "secondary": "#ffffff"},
    "AaB": {"primary": "#cc0000", "secondary": "#ffffff"},
    "Kolding IF": {"primary": "#ffffff", "secondary": "#0000ff"},
    "Hobro": {"primary": "#ffff00", "secondary": "#0000ff"},
    "HB Køge": {"primary": "#000000", "secondary": "#0000ff"},
    "Aarhus Fremad": {"primary": "#000000", "secondary": "#ffff00"}
}

