# data/utils/team_mapping.py

# --- Sæsoner og Turneringer (Opta UUIDs) ---
SEASONS = {
    "2026/2027": {
        "1. Division": "2mb332vncy4450vu14paj8844",  # Den nye 26/27 UUID
        "3F Superliga": "29actv1ohj8r10kd9hu0jnb0n",
    },
    "2025/2026": {
        "1. Division": "dyjr458hcmrcy87fsabfsy87o",  # UUID fra din forrige side-kode
        "3F Superliga": "dummy_old_superliga_uuid",
    }
}

# --- GLOBAL KONTROL ---
COMPETITION_NAME = "1. Division"
TOURNAMENTCALENDAR_NAME = "2026/2027"

# --- Turneringer ---
COMPETITIONS = {
    "1. Division": {"wyid": 328, "COMPETITION_OPTAUUID": "2mb332vncy4450vu14paj8844", "COMPETITION_NAME": "1. Division"},
    "3F Superliga": {"wyid": 335, "COMPETITION_OPTAUUID": "29actv1ohj8r10kd9hu0jnb0n", "COMPETITION_NAME": "Superliga"},
    "2. division": {"wyid": 329, "opta_uuid": None},
    "3. division": {"wyid": 43319, "opta_uuid": None},
    "Oddset Pokalen": {"wyid": 331, "opta_uuid": None},
    "U19 Ligaen": {"wyid": 1305, "opta_uuid": None}
}

# --- Sæsonbetinget hold-placering (Styrer hvem der vises i dropdown pr. sæson) ---
SEASON_LEAGUE_MAPPER = {
    "2026/2027": {
        "1. Division": [
            "Hvidovre", "Fredericia", "Vejle", "Esbjerg", "Kolding", "Hobro", 
            "HB Køge", "Hillerød", "Aarhus Fremad", "AB", "AaB", "Vendsyssel"
        ],
        "3F Superliga": [
            "FC København", "FC Midtjylland", "Brøndby IF", "AGF", 
            "FC Nordsjælland", "Viborg FF", "SønderjyskE", "Randers FC", 
            "Silkeborg IF", "OB",
            "Lyngby", "Horsens"
        ]
    },
    "2025/2026": {
        "1. Division": [
            "Hvidovre", "AaB", "Horsens", "Esbjerg", "Kolding", 
            "Hobro", "HB Køge", "Hillerød", "Aarhus Fremad", "B 93", "Middelfart"
        ],
        "3F Superliga": [
            "FC København", "FC Midtjylland", "Brøndby IF", "AGF", 
            "FC Nordsjælland", "Viborg FF", "SønderjyskE", "Randers FC", 
            "Silkeborg IF", "Vejle Boldklub", "OB", "FC Fredericia", "Lyngby"
        ]
    }
}

# --- Hold Stamdata (Statiske data fælles for alle sæsoner) ---
TEAMS = {
    # 1. Division stamdata
    "Hvidovre": {"abbr": "HIF", "team_wyid": 7490, "opta_uuid": "8gxd9ry2580pu1b1dd5ny9ymy", "opta_id": 2397, "ssid": "56fa29c7-3a48-4186-9d14-dbf45fbc78d9", "logo": "https://cdn5.wyscout.com/photos/team/public/2659_120x120.png"},
    "AaB": {"abbr": "AaB", "team_wyid": 7454, "opta_uuid": "36g6ifzjliec1jqnbtf7yesme", "opta_id": 401, "ssid": "40d5387b-ac2f-4e9b-bb97-34456aeb69c4", "logo": "https://cdn5.wyscout.com/photos/team/public/283_120x120.png"},
    "Horsens": {"abbr": "ACH", "team_wyid": 7465, "opta_uuid": "a9vw7ikerpr4cuweeeka5aneg", "opta_id": 2289, "ssid": "f2b45639-d8e6-4d9b-9371-6f9f1fe2a9d9", "logo": "https://cdn5.wyscout.com/photos/team/public/285_120x120.png"},
    "Lyngby": {"abbr": "LBK", "team_wyid": 7484, "opta_uuid": "anga7587r1zv4ey71ge9zxol3", "opta_id": 272, "ssid": "15af1cc2-5ce6-4552-8a5f-7e233a65cedc", "logo": "https://cdn5.wyscout.com/photos/team/public/2527_120x120.png"},
    "Esbjerg": {"abbr": "EfB", "team_wyid": 7451, "opta_uuid": "f1h34qp5zbfl489q8vnkhiq9s", "opta_id": 1409, "ssid": "bfc8edb9-96af-4152-a8b0-d096d4271f48", "logo": "https://cdn5.wyscout.com/photos/team/public/290_120x120.png"},
    "Kolding": {"abbr": "KIF", "team_wyid": 7622, "opta_uuid": "b8oqgvx1ijeyn6y1cn6929ix4", "opta_id": 13253, "ssid": "04aaceac-8a20-422b-8417-9199a519c1b3", "logo": "https://cdn5.wyscout.com/photos/team/public/g13383_120x120.png"},
    "Hobro": {"abbr": "HOB", "team_wyid": 7510, "opta_uuid": "b2vft81kyjurzbmekvgrqwr64", "opta_id": 4802, "ssid": "c4398d21-4dd5-456a-be5d-c8102a6cd3dd", "logo": "https://cdn5.wyscout.com/photos/team/public/2662_120x120.png"},
    "HB Køge": {"abbr": "HBK", "team_wyid": 7615, "opta_uuid": "8cfkisxf1fkxdqtt6tx1tup48", "opta_id": 4042, "ssid": "2dccb353-4598-4f35-845d-c6c55c9f5672", "logo": "https://cdn5.wyscout.com/photos/team/public/1941_120x120.png"},
    "Hillerød": {"abbr": "HIF", "team_wyid": 7699, "opta_uuid": "aqtkb4mgrz8c6iqfufj6qjbv9", "opta_id": 6463, "ssid": "e274c022-4cf1-4c4d-9555-4c6dd38b1224", "logo": "https://cdn5.wyscout.com/photos/team/public/g19126_120x120.png"},
    "Aarhus Fremad": {"abbr": "AAF", "team_wyid": 7502, "opta_uuid": "bfwi3pjyg3whbn0tpsz19e8hq", "opta_id": 2290, "ssid": "cd08baf0-84c3-490a-9879-da4a55b8e645", "logo": "https://cdn5.wyscout.com/photos/team/public/g3686_120x120.png"},
    "B 93": {"abbr": "B93", "team_wyid": 7470, "opta_uuid": "ajtb177oqwawkdwbqhldmq6mx", "opta_id": 2935, "ssid": "e0bb5b5f-2df2-4fc4-854a-e537bd65a280", "logo": "https://cdn5.wyscout.com/photos/team/public/g620_120x120.png"},
    "Middelfart": {"abbr": "MIF", "team_wyid": 7578, "opta_uuid": "eq2jaitwsokibzx3wy7kb5gqp", "opta_id": 3050, "ssid": "c90bbc9d-d21c-4be0-a045-d41a633c6005", "logo": "https://cdn5.wyscout.com/photos/team/public/g11034_120x120.png"},
    "AB": {"abbr": "AB", "team_wyid": 7464, "opta_uuid": "1uovb0izovmuzdhoq7eyk3ou3", "opta_id": 2397, "ssid": "56fa29c7-3a48-4186-9d14-dbf45fbc78d9", "logo": "https://cdn5.wyscout.com/photos/team/public/2470_120x120.png"},
    "Vendsyssel": {"abbr": "VEN", "team_wyid": 7488, "opta_uuid": "7gkglopz9cjsysn2u6sbhuvc5", "opta_id": 401, "ssid": "40d5387b-ac2f-4e9b-bb97-34456aeb69c4", "logo": "https://cdn5.wyscout.com/photos/team/public/2661_120x120.png"},

    # Superliga stamdata
    "FC København": {"abbr": "FCK", "team_wyid": 7452, "opta_uuid": "569_uuid_dummy", "opta_id": 569, "logo": "https://cdn5.wyscout.com/photos/team/public/284_120x120.png"},
    "FC Midtjylland": {"abbr": "FCM", "team_wyid": 7455, "opta_uuid": "1000_uuid_dummy", "opta_id": 1000, "logo": "https://cdn5.wyscout.com/photos/team/public/286_120x120.png"},
    "Brøndby IF": {"abbr": "BIF", "team_wyid": 7453, "opta_uuid": "239_uuid_dummy", "opta_id": 239, "logo": "https://cdn5.wyscout.com/photos/team/public/291_120x120.png"},
    "AGF": {"abbr": "AGF", "team_wyid": 7457, "opta_uuid": "420_uuid_dummy", "opta_id": 420, "logo": "https://cdn5.wyscout.com/photos/team/public/292_120x120.png"},
    "FC Nordsjælland": {"abbr": "FCN", "team_wyid": 7458, "opta_uuid": "2592_uuid_dummy", "opta_id": 2592, "logo": "https://cdn5.wyscout.com/photos/team/public/289_120x120.png"},
    "Viborg FF": {"abbr": "VFF", "team_wyid": 7456, "opta_uuid": "547_uuid_dummy", "opta_id": 547, "logo": "https://cdn5.wyscout.com/photos/team/public/2504_120x120.png"},
    "SønderjyskE": {"abbr": "SJE", "team_wyid": 7499, "opta_uuid": "2827_uuid_dummy", "opta_id": 2827, "logo": "https://cdn5.wyscout.com/photos/team/public/796_120x120.png"},
    "Randers FC": {"abbr": "RFC", "team_wyid": 7462, "opta_uuid": "1943_uuid_dummy", "opta_id": 1943, "logo": "https://cdn5.wyscout.com/photos/team/public/288_120x120.png"},
    "Silkeborg IF": {"abbr": "SIF", "team_wyid": 7461, "opta_uuid": "418_uuid_dummy", "opta_id": 418, "logo": "https://cdn5.wyscout.com/photos/team/public/1948_120x120.png"},
    "Vejle": {"abbr": "VB", "team_wyid": 7473, "opta_uuid": "2450_uuid_dummy", "opta_id": 2450, "logo": "https://cdn5.wyscout.com/photos/team/public/g623_120x120.png"},
    "OB": {"abbr": "OB", "team_wyid": 7460, "opta_uuid": "5rz9enoyknpg8ji78za5b82p8", "opta_id": 545, "logo": "https://cdn5.wyscout.com/photos/team/public/287_120x120.png"},
    "Fredericia": {"abbr": "FCF", "team_wyid": 7469, "opta_uuid": "3051_uuid_dummy", "opta_id": 3051, "logo": "https://cdn5.wyscout.com/photos/team/public/2469_120x120.png"},
}

# --- Klubfarver ---
TEAM_COLORS = {
    "Hvidovre": {"primary": "#cc0000", "secondary": "#0000ff"},
    "B 93": {"primary": "#0000ff", "secondary": "#ffffff"},
    "Hillerød": {"primary": "#ff6600", "secondary": "#000000"},
    "Esbjerg": {"primary": "#003399", "secondary": "#ffffff"},
    "Lyngby": {"primary": "#003366", "secondary": "#ffffff"},
    "Horsens": {"primary": "#E3C91A", "secondary": "#000000"},
    "Middelfart": {"primary": "#0099ff", "secondary": "#ffffff"},
    "AaB": {"primary": "#cc0000", "secondary": "#ffffff"},
    "Kolding": {"primary": "#0000ff", "secondary": "#0000ff"},
    "Hobro": {"primary": "#ffff00", "secondary": "#0000ff"},
    "HB Køge": {"primary": "#000000", "secondary": "#0000ff"},
    "Aarhus Fremad": {"primary": "#000000", "secondary": "#ffff00"},
    "Vejle": {"primary": "#003399", "secondary": "#ffffff"},
    "Fredericia": {"primary": "#E2000F", "secondary": "#000000"},
    "Vendsyssel": {"primary": "#003399", "secondary": "#ffffff"},
    "AB": {"primary": "#000000", "secondary": "#ffffff"},

}
