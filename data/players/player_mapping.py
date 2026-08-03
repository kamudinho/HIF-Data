# data/players/player_mapping.py

class PlayerMapping:
    def __init__(self, player_list=None):
        self.wy_to_optauuid = {}
        self.optauuid_to_wy = {}
        self.optauuid_to_name = {}
        self.players_by_name = {}
        
        if player_list:
            self._load_data(player_list)

    def _load_data(self, player_list):
        for p in player_list:
            klub = p.get("klub")
            navn = str(p.get("navn", "")).strip()
            position = str(p.get("position", "")).strip()
            wy_id = p.get("player_wyid")
            opta_uuid = p.get("player_optauuid")

            wy_id_int = int(wy_id) if str(wy_id).isdigit() and str(wy_id) != "0" else None
            opta_uuid_val = str(opta_uuid).strip() if opta_uuid and str(opta_uuid) != "None" else None

            player_info = {
                "klub": klub,
                "navn": navn,
                "position": position,
                "player_wyid": wy_id_int,
                "player_optauuid": opta_uuid_val
            }

            if wy_id_int:
                self.wy_to_optauuid[wy_id_int] = opta_uuid_val
            
            if opta_uuid_val:
                self.optauuid_to_wy[opta_uuid_val] = wy_id_int
                if navn:
                    self.optauuid_to_name[opta_uuid_val] = navn
            
            if navn:
                self.players_by_name.setdefault(navn.lower(), []).append(player_info)

    def get_opta_uuid(self, player_wyid):
        return self.wy_to_optauuid.get(int(player_wyid))

    def get_wy_id(self, player_optauuid):
        return self.optauuid_to_wy.get(str(player_optauuid))

    def get_name_by_opta_uuid(self, player_optauuid):
        """Henter det korrekte navn ud fra Opta UUID"""
        return self.optauuid_to_name.get(str(player_optauuid))

    def get_player_by_name(self, navn):
        return self.players_by_name.get(str(navn).lower(), [])


# --- OVERSIGT OVER SPILLERE ---
SEASONNAME = "2025/2026"
TEAM_WYID = 7490
COMPETITION_WYID = (328,)
COMPETITION_OPTAUUID = "6ifaeunfdelecgticvxanikzu"

COMP_MAP = {
    335: "Superliga",
    328: "NordicBet Liga",
    329: "2. division",
    43319: "3. division",
    331: "Oddset Pokalen",
    1305: "U19 Ligaen"
}
# Samlet oversigt over spillere fordelt på klubber i NordicBet Ligaen
PLAYER_MAPPING = [
    # Aalborg BK
    {"klub": "Aalborg BK", "navn": "William Hoffenzitz Thomsen", "position": "Attacker", "player_wyid": 845879, "player_optauuid": "14ur60ict5k3l9nv02o7psw0k"},
    {"klub": "Aalborg BK", "navn": "Uche Brian Seo Nwadike", "position": "Attacker", "player_wyid": 91, "player_optauuid": "cvtiaq4im9hiydjiualozdg"},
    {"klub": "Aalborg BK", "navn": "Frederik Lindbøg Børsting", "position": "Midfielder", "player_wyid": 331196, "player_optauuid": "egwhlgopjtjkop7ozy7ltk1cl"},
    {"klub": "Aalborg BK", "navn": "Valdemar Møller Damgaard", "position": "Midfielder", "player_wyid": 12129975, "player_optauuid": "521epytthhw9afm2r3jn3384"},
    {"klub": "Aalborg BK", "navn": "Kelvin Pius John", "position": "Attacker", "player_wyid": 5689235, "player_optauuid": "vrsflxiv2dgfa8199a2qxsve"},
    {"klub": "Aalborg BK", "navn": "Markus André Kaasa", "position": "Midfielder", "player_wyid": 472140, "player_optauuid": "e0j0uakuzduvis9wqsocngwrt"},
    {"klub": "Aalborg BK", "navn": "Nóel Atli Arnórsson", "position": "Defender", "player_wyid": 660853, "player_optauuid": "brinkgys7026490q3ixx6h9uc"},
    {"klub": "Aalborg BK", "navn": "Andres Jasson", "position": "Midfielder", "player_wyid": 5349828, "player_optauuid": "bi1tlz62rjwyak4pnnzgp562"},
    {"klub": "Aalborg BK", "navn": "Jubril Adedeji", "position": "Attacker", "player_wyid": 5687664, "player_optauuid": "sgxth7onhb5mu29bgyupby3u"},
    {"klub": "Aalborg BK", "navn": "Marcus Bonde", "position": "Midfielder", "player_wyid": 760812, "player_optauuid": "e7wytawxwiszq1aass5ujio7o"},
    {"klub": "Aalborg BK", "navn": "Alexander Lien Håpnes", "position": "Midfielder", "player_wyid": 7503635, "player_optauuid": "y2mfgruizah0ylcz7q1abw9g"},
    {"klub": "Aalborg BK", "navn": "Mathias Nordestgaard Kubel", "position": "Midfielder", "player_wyid": 450111, "player_optauuid": "az9olsp7tglzt73awei9a4cgk"},
    {"klub": "Aalborg BK", "navn": "Elison Makolli", "position": "Defender", "player_wyid": 77625869, "player_optauuid": "7f50qoetodmfe8ybcuey2ac"},
    {"klub": "Aalborg BK", "navn": "Cornelius Axel Olsson", "position": "Defender", "player_wyid": 6786635, "player_optauuid": "uo9saax5iqsctxq7w3si8w0k"},
    {"klub": "Aalborg BK", "navn": "Marc Langskov Nielsen", "position": "Defender", "player_wyid": 1222413, "player_optauuid": "bcdp9e3dezuaybm8ndrsanbx0"},
    {"klub": "Aalborg BK", "navn": "Vincent Carsten Maria Müller", "position": "Goalkeeper", "player_wyid": 520616, "player_optauuid": "a2l4ep71txn2edtjjcgewai5m"},
    {"klub": "Aalborg BK", "navn": "Kornelius Normann Hansen", "position": "Attacker", "player_wyid": 11031364, "player_optauuid": "8sqqhgtmfmpqb3602iirspd6"},

    # Aarhus Fremad
    {"klub": "Aarhus Fremad", "navn": "Frederik Grube Andersen", "position": "Midfielder", "player_wyid": 450283186, "player_optauuid": "mdd3akww1wyxdc9ouw6kno"},
    {"klub": "Aarhus Fremad", "navn": "Andreas Pisani Laugesen", "position": "Defender", "player_wyid": 9477822, "player_optauuid": "lvlyvfvdoz7kyqtib6jm9btg"},
    {"klub": "Aarhus Fremad", "navn": "Magnus Kirchheiner", "position": "Midfielder", "player_wyid": 4533195, "player_optauuid": "q7msbcrmtsr3b7tykgb6l05w"},
    {"klub": "Aarhus Fremad", "navn": "Jashar Beluli", "position": "Midfielder", "player_wyid": 62466329, "player_optauuid": "y19vqfjkvlc8s9gr5v5atqs"},
    {"klub": "Aarhus Fremad", "navn": "Magnus Kaastrup Refstrup Lauritsen", "position": "Attacker", "player_wyid": 4763559, "player_optauuid": "nafz0c0x2qvmo5ldm0djmcq1"},
    {"klub": "Aarhus Fremad", "navn": "Linus Rönnberg", "position": "Midfielder", "player_wyid": "cyidz45zw5umg1yd6ahot3ndg", "player_optauuid": "cyidz45zw5umg1yd6ahot3ndg"},
    {"klub": "Aarhus Fremad", "navn": "Carl Carøe Nygaard", "position": "Midfielder", "player_wyid": 11229002, "player_optauuid": "n8fvjqe4es6a04l4ki18uvbo"},
    {"klub": "Aarhus Fremad", "navn": "Jonas Østergaard", "position": "Attacker", "player_wyid": 12393314, "player_optauuid": "yfwo1ja5nchmj85dlml95o2c"},
    {"klub": "Aarhus Fremad", "navn": "Simon Bækgård", "position": "Midfielder", "player_wyid": 5188905, "player_optauuid": "o1k2hd9rdooxpjgbnabuh94a"},
    {"klub": "Aarhus Fremad", "navn": "Alexander Ludwig", "position": "Defender", "player_wyid": 19102461, "player_optauuid": "vr9xr91fr4g6ayzga5vn9w5"},
    {"klub": "Aarhus Fremad", "navn": "Ólafur Dan Hjaltason", "position": "Defender", "player_wyid": "a5alop4wg4qwwu812pfskfjtg", "player_optauuid": "a5alop4wg4qwwu812pfskfjtg"},
    {"klub": "Aarhus Fremad", "navn": "Marcus Løvenbalk Kirchheiner", "position": "Defender", "player_wyid": 5626837, "player_optauuid": "zb57r5m7lmvj3xlf9y1ldez8"},
    {"klub": "Aarhus Fremad", "navn": "Viktor Højbjerg", "position": "Goalkeeper", "player_wyid": 620139, "player_optauuid": "f2hab1q8nrvah7j2k5ci0edxw"},
    {"klub": "Aarhus Fremad", "navn": "Marcus Ryberg", "position": "Midfielder", "player_wyid": 682962, "player_optauuid": "df9m624q4gqk35f4y3ohxch04"},
    {"klub": "Aarhus Fremad", "navn": "Devon Bernasko-Appu", "position": "Attacker", "player_wyid": 2, "player_optauuid": "isfyjd6l2uktg58g3pbazaj8"},
    {"klub": "Aarhus Fremad", "navn": "Kasper Lunding Jakobsen", "position": "Midfielder", "player_wyid": 4839566, "player_optauuid": "zxcmzp7w6esj54g05tvk7ai1"},
    {"klub": "Aarhus Fremad", "navn": "Elias Caspersen Egerton", "position": "Midfielder", "player_wyid": 7005148, "player_optauuid": "rqctff92ui8fanzbk6skyyac"},

    # Akademisk Boldklub Gladsaxe
    {"klub": "Akademisk Boldklub Gladsaxe", "navn": "Marc Dal Hende", "position": "Defender", "player_wyid": 5644633, "player_optauuid": "sxiwcjeqcop3ukuok86ujmd"},
    {"klub": "Akademisk Boldklub Gladsaxe", "navn": "O’Vonte Mullings", "position": "Attacker", "player_wyid": 6868747, "player_optauuid": "pdl6jqfaq1x1trdi5k30wsus"},
    {"klub": "Akademisk Boldklub Gladsaxe", "navn": "Casper Grening", "position": "Attacker", "player_wyid": 8404386, "player_optauuid": "hms8o682fsh33l3hp4qo39ey"},
    {"klub": "Akademisk Boldklub Gladsaxe", "navn": "Frederik Lindgaard", "position": "Defender", "player_wyid": 681248, "player_optauuid": "clf3fgzelbfqh8sya98k5pdlg"},
    {"klub": "Akademisk Boldklub Gladsaxe", "navn": "Noah Engell Christensen", "position": "Attacker", "player_wyid": 6600155, "player_optauuid": "crdnyx54gw8u104sjprb7das"},
    {"klub": "Akademisk Boldklub Gladsaxe", "navn": "Travian Anthony LaMere Sousa", "position": "Defender", "player_wyid": 5381617, "player_optauuid": "zr3gif60ntltgt3s5yi6qjca"},
    {"klub": "Akademisk Boldklub Gladsaxe", "navn": "Mikkel Clement", "position": "Midfielder", "player_wyid": 1090929, "player_optauuid": "c6s8nbgk1z9xvasi3rh3a82s4"},
    {"klub": "Akademisk Boldklub Gladsaxe", "navn": "Jonathan Mathys", "position": "Attacker", "player_wyid": 622992, "player_optauuid": "zpl7lyln792rt0b2oedamvbo"},
    {"klub": "Akademisk Boldklub Gladsaxe", "navn": "Aidan Bardina Liu", "position": "Defender", "player_wyid": 5242234, "player_optauuid": "z0ebjgc0s506zay6ekwf5gmi"},
    {"klub": "Akademisk Boldklub Gladsaxe", "navn": "Gabriel Rodrigues Noga", "position": "Defender", "player_wyid": 1, "player_optauuid": "x74ueydb3hpmz8tkzblt68oa"},
    {"klub": "Akademisk Boldklub Gladsaxe", "navn": "Marcus Immersen", "position": "Attacker", "player_wyid": 1055842, "player_optauuid": "afr71rcay1uq4ngti10fvr9xw"},
    {"klub": "Akademisk Boldklub Gladsaxe", "navn": "Adam Ingi Benediktsson", "position": "Goalkeeper", "player_wyid": 599989, "player_optauuid": "cnfkqyunacrm7mli650a3l3ze"},
    {"klub": "Akademisk Boldklub Gladsaxe", "navn": "Noah Ibsen", "position": "Defender", "player_wyid": 12290942, "player_optauuid": "lvkvn7fds2seqd882lv90mc4"},
    {"klub": "Akademisk Boldklub Gladsaxe", "navn": "Marco Vesterholm", "position": "Midfielder", "player_wyid": 4490634, "player_optauuid": "m23g10w898skztiwfiedqcd0"},
    {"klub": "Akademisk Boldklub Gladsaxe", "navn": "Serigne Saliou Diop", "position": "Attacker", "player_wyid": 8, "player_optauuid": "gma3ufrjv0hj0k2nulcbodn8"},
    {"klub": "Akademisk Boldklub Gladsaxe", "navn": "Søren Ulrik Ilsøe", "position": "Midfielder", "player_wyid": 5356388, "player_optauuid": "ii8snymcafyrv1x9srwkrtka"},
    {"klub": "Akademisk Boldklub Gladsaxe", "navn": "Tobias Damtoft Andersen", "position": "Attacker", "player_wyid": 481121, "player_optauuid": "ernnq3ugpx34joskjyj373lgq"},
    {"klub": "Akademisk Boldklub Gladsaxe", "navn": "Milan Justin Silva Rasmussen", "position": "Attacker", "player_wyid": 10715704, "player_optauuid": "po6qfkmrc30lep6z6ka5db10"},

    # Esbjerg fB
    {"klub": "Esbjerg fB", "navn": "Julius Lucena", "position": "Attacker", "player_wyid": 7672305, "player_optauuid": "ha6xhovfmuzd7rolx1om39w3"},
    {"klub": "Esbjerg fB", "navn": "Lucas Skjoldberg From", "position": "Attacker", "player_wyid": 4841656, "player_optauuid": "hmsrr08cllpl4iumu92zskbt"},
    {"klub": "Esbjerg fB", "navn": "Peter Nicolai Kruse Bjur", "position": "Midfielder", "player_wyid": 4954216, "player_optauuid": "m4anciafmzc24s44xszymbc9"},
    {"klub": "Esbjerg fB", "navn": "Benjamin Steenfeldt Hvidt", "position": "Midfielder", "player_wyid": 4342944, "player_optauuid": "yyiv4t6irqpeayug5qgvmkmh"},
    {"klub": "Esbjerg fB", "navn": "Oskar Adam Rudkjøbing Boesen", "position": "Midfielder", "player_wyid": 776612, "player_optauuid": "lmrff8mviimc33yyrpjzr2tw"},
    {"klub": "Esbjerg fB", "navn": "Noah Oliver Strandby", "position": "Attacker", "player_wyid": 679271, "player_optauuid": "a3s2lypc1aceu363i78aczx1w"},
    {"klub": "Esbjerg fB", "navn": "Oluwatomiwa John Kolawole", "position": "Midfielder", "player_wyid": 860179, "player_optauuid": "djm3hebvv79jo679zzd2b71g4"},
    {"klub": "Esbjerg fB", "navn": "Anders Sønderskov", "position": "Defender", "player_wyid": 638043, "player_optauuid": "ajk0mbprro09pccglih9y740k"},
    {"klub": "Esbjerg fB", "navn": "Mikail Maden", "position": "Midfielder", "player_wyid": 64309515, "player_optauuid": "yli690oxmbr4dl1ksti2p9m"},
    {"klub": "Esbjerg fB", "navn": "Sander Eng Strand", "position": "Defender", "player_wyid": 544672, "player_optauuid": "f5gja2wqjlm60rideia16jpm2"},
    {"klub": "Esbjerg fB", "navn": "Patrick Lindholm Tjørnelund", "position": "Defender", "player_wyid": 5356223, "player_optauuid": "7mo55lynu3blqnb8k9ln8k16"},
    {"klub": "Esbjerg fB", "navn": "Andreas Kristiansen", "position": "Midfielder", "player_wyid": 1069758, "player_optauuid": "ddbrysgujd87xr0si82kha1as"},
    {"klub": "Esbjerg fB", "navn": "William Johannes Lykke", "position": "Goalkeeper", "player_wyid": 6277309, "player_optauuid": "h6c9ue598hllcri39erjitqs"},
    {"klub": "Esbjerg fB", "navn": "Jonathan Roland Foss", "position": "Defender", "player_wyid": 623256, "player_optauuid": "cy4iqzsaxd9c9v07s4m93caac"},
    {"klub": "Esbjerg fB", "navn": "Marcus Winther Hansen", "position": "Midfielder", "player_wyid": 1234283, "player_optauuid": "cod92jjb3qqrg6n1tu15ciwpg"},
    {"klub": "Esbjerg fB", "navn": "Muamer Brajanac", "position": "Attacker", "player_wyid": 5449404, "player_optauuid": "krwgfspxdgpq1pli11b04iga"},

    # FC Fredericia
    {"klub": "FC Fredericia", "navn": "Jeppe Kudsk Pedersen", "position": "Defender", "player_wyid": 577942, "player_optauuid": "b1kyjkhaaiw32cb4bubbpm7tg"},
    {"klub": "FC Fredericia", "navn": "Elias Hansborg-Sørensen", "position": "Attacker", "player_wyid": 624743, "player_optauuid": "ewh6t7yo6clfewu89uznll9uc"},
    {"klub": "FC Fredericia", "navn": "Anders Dahl", "position": "Defender", "player_wyid": 5786346, "player_optauuid": "5g5cfsdr10378yvmkpm19444"},
    {"klub": "FC Fredericia", "navn": "Valdemar Birksø Thorsen", "position": "Goalkeeper", "player_wyid": 449432, "player_optauuid": "eiy7fhqxdx3ypg4dq4454hpbe"},
    {"klub": "FC Fredericia", "navn": "Frederik Thykær Rieper", "position": "Defender", "player_wyid": 5707983, "player_optauuid": "od63zrf6cay4d6ync9i2iuqc"},
    {"klub": "FC Fredericia", "navn": "Patrick Hessellund Egelund", "position": "Attacker", "player_wyid": 5356426, "player_optauuid": "lb4k3g75nzgi8bp1y1mzxkru"},
    {"klub": "FC Fredericia", "navn": "Lauritz Dauerhøj", "position": "Defender", "player_wyid": 6789444, "player_optauuid": "2j3pc9y10qfcabdvjwu179qs"},
    {"klub": "FC Fredericia", "navn": "Emilio Stuberg Simonsen", "position": "Midfielder", "player_wyid": 10024994, "player_optauuid": "5ssaw51hm80y1tfalyesap9m"},
    {"klub": "FC Fredericia", "navn": "Felix Vrede Winther", "position": "Midfielder", "player_wyid": 4497637, "player_optauuid": "rt4wpc0qphwnvhn8jeazesfe"},
    {"klub": "FC Fredericia", "navn": "Frederik Bunten Kjeldal", "position": "Midfielder", "player_wyid": 7692202, "player_optauuid": "qo4th9tyx2t7mjws65klutjo"},
    {"klub": "FC Fredericia", "navn": "Daniel Bisgaard Haarbo", "position": "Midfielder", "player_wyid": 5793962, "player_optauuid": "zt1yrfv8m2mhpo720n0uydck"},
    {"klub": "FC Fredericia", "navn": "Svenn Crone", "position": "Defender", "player_wyid": 1351041, "player_optauuid": "ai0gvdx68lxclbj6m255w72t"},
    {"klub": "FC Fredericia", "navn": "William Madsen", "position": "Midfielder", "player_wyid": 9598467, "player_optauuid": "ztdirfvd9d0x2yw1v051xzbo"},
    {"klub": "FC Fredericia", "navn": "Malthe Riis Ladefoged", "position": "Defender", "player_wyid": 8467727, "player_optauuid": "uw675zanxb576wzfvf0lnpjo"},
    {"klub": "FC Fredericia", "navn": "Oliver Aare Vest", "position": "Defender", "player_wyid": 7016515, "player_optauuid": "ok6g9rtqb7bz8gnyjqwo2j9w"},
    {"klub": "FC Fredericia", "navn": "Eskild Munk Dall", "position": "Attacker", "player_wyid": 5615959, "player_optauuid": "1xtn2wlot8g8ue89zn4iiyqy"},
    {"klub": "FC Fredericia", "navn": "Nemo Thomsen", "position": "Attacker", "player_wyid": 766025, "player_optauuid": "dqp8e2et9fm9r6zo47u1njq50"},

    # HB Køge
    {"klub": "HB Køge", "navn": "Mads Schütt Rasmussen", "position": "Midfielder", "player_wyid": 1071570, "player_optauuid": "k43cten7yb6p59yo0firhb84"},
    {"klub": "HB Køge", "navn": "Mike Lindemann Jensen", "position": "Midfielder", "player_wyid": 12332266, "player_optauuid": "19s1phj5bkgkug3aszc1y9cl"},
    {"klub": "HB Køge", "navn": "Erkan Semovski", "position": "Attacker", "player_wyid": 7056048, "player_optauuid": "qzac8nxm8nxbckdaisnooutw"},
    {"klub": "HB Køge", "navn": "Ibrahim Figuigui", "position": "Midfielder", "player_wyid": 7666323, "player_optauuid": "wu2xz4b1gx81bvn53pktoges"},
    {"klub": "HB Køge", "navn": "Laurits Bust Sørensen", "position": "Defender", "player_wyid": 5163756, "player_optauuid": "gmm4awyvlf9p7jr9dvnmp0tm"},
    {"klub": "HB Køge", "navn": "Mattias Jakobsen", "position": "Defender", "player_wyid": 5622245, "player_optauuid": "nved2kta2hk8103hkyhq33hm"},
    {"klub": "HB Køge", "navn": "Gabriel M. Larsen", "position": "Midfielder", "player_wyid": 11325663, "player_optauuid": "mgrufy83uhzs9liw8pwxi784"},
    {"klub": "HB Køge", "navn": "Silas Hald", "position": "Defender", "player_wyid": 7383766, "player_optauuid": "7p0s4o54xcmiustgy8k5gljo"},
    {"klub": "HB Køge", "navn": "Marcel Ibsen Rømer", "position": "Midfielder", "player_wyid": 5636557, "player_optauuid": "33iw16239m83syv5dm8huj9"},
    {"klub": "HB Køge", "navn": "Noah Emil Sømmergaard", "position": "Goalkeeper", "player_wyid": 639591, "player_optauuid": "bwxxfcjd31gykfbpomwr1od90"},
    {"klub": "HB Køge", "navn": "Lukas Rostgaard Achton", "position": "Defender", "player_wyid": 765153, "player_optauuid": "czudq621hgfprwetp10ckv9jo"},
    {"klub": "HB Køge", "navn": "Magnus Warming", "position": "Attacker", "player_wyid": 506857, "player_optauuid": "diwrq7ulrey4juxk4dafct0q1"},
    {"klub": "HB Køge", "navn": "Mads Westergren", "position": "Defender", "player_wyid": 5210677, "player_optauuid": "al9w77ailhli8g487tkl32tw"},
    {"klub": "HB Køge", "navn": "Tobias Bendix Thomsen", "position": "Attacker", "player_wyid": 101279943, "player_optauuid": "m33adgmas68tl6m34gkuzth"},
    {"klub": "HB Køge", "navn": "Viktor Løvgren Sørensen", "position": "Midfielder", "player_wyid": 680621, "player_optauuid": "egxik3guom123v43rthy89c7o"},
    {"klub": "HB Køge", "navn": "Rasmus Brodersen", "position": "Defender", "player_wyid": 5683731, "player_optauuid": "4mwsmzsrmev2646t2gg22has"},
    {"klub": "HB Køge", "navn": "Noah Stolshøj", "position": "Attacker", "player_wyid": 765144, "player_optauuid": "ez43e5jd3aur00h75x99xu49g"},

    # Hillerød Fodbold
    {"klub": "Hillerød Fodbold", "navn": "Noah Kretzschmar Nielsen", "position": "Attacker", "player_wyid": 6796545, "player_optauuid": "x7mnku7nky0ojwfvmmqphl3o"},
    {"klub": "Hillerød Fodbold", "navn": "Nicklas Bjerre Schmidt", "position": "Midfielder", "player_wyid": 6792175, "player_optauuid": "dlh0fa9yo6z283w9p58xmnoq"},
    {"klub": "Hillerød Fodbold", "navn": "Jonathan Witt", "position": "Defender", "player_wyid": 5083295, "player_optauuid": "z7y55t2o577r8ki3i5855as"},
    {"klub": "Hillerød Fodbold", "navn": "Rasmus Thelander", "position": "Defender", "player_wyid": 56435, "player_optauuid": "cw6s5hf1tytvb98vjuosz9r6d"},
    {"klub": "Hillerød Fodbold", "navn": "Rezan Çorlu", "position": "Midfielder", "player_wyid": "bqcjd0macjc7hmtz7zx34ym6t", "player_optauuid": "bqcjd0macjc7hmtz7zx34ym6t"},
    {"klub": "Hillerød Fodbold", "navn": "Andreas Høyer", "position": "Defender", "player_wyid": 681326, "player_optauuid": "c119s9yebqgzdc4qrvvjw5bmc"},
    {"klub": "Hillerød Fodbold", "navn": "William Owen Glindtvad", "position": "Defender", "player_wyid": 559, "player_optauuid": "w0q3q2smb3aeotyi724s9g"},
    {"klub": "Hillerød Fodbold", "navn": "Saman Sebastean Jalaei", "position": "Attacker", "player_wyid": 680616, "player_optauuid": "e0u730to91qqtvvx16uhajz10"},
    {"klub": "Hillerød Fodbold", "navn": "Tobias Arndal", "position": "Midfielder", "player_wyid": 5119871, "player_optauuid": "n4eldqa7h9jvcx1693zqu06i"},
    {"klub": "Hillerød Fodbold", "navn": "Mikkel Mouritz Jensen", "position": "Midfielder", "player_wyid": 494823, "player_optauuid": "ezbixgm2km8iapnsl57bn4wkp"},
    {"klub": "Hillerød Fodbold", "navn": "Kasper Enghardt Pedersen", "position": "Defender", "player_wyid": 383090, "player_optauuid": "khqldwfq14b7giakss24l9t5"},
    {"klub": "Hillerød Fodbold", "navn": "Magnus Munck Bjørnholm", "position": "Midfielder", "player_wyid": 6277219, "player_optauuid": "gr9rdahnavv0irjauh5xim8k"},
    {"klub": "Hillerød Fodbold", "navn": "Berzan Kücükylidiz", "position": "Midfielder", "player_wyid": 815332, "player_optauuid": "bpldj4qdzfdm1n739atcadbmc"},
    {"klub": "Hillerød Fodbold", "navn": "Mads Høyer Julø", "position": "Defender", "player_wyid": 4502073, "player_optauuid": "bf4r3xgrs0ttlhgzb93as5t6"},
    {"klub": "Hillerød Fodbold", "navn": "Sebastian Larsen", "position": "Defender", "player_wyid": 7692004, "player_optauuid": "m7gr5z6b40dj02yrmlwgeluc"},
    {"klub": "Hillerød Fodbold", "navn": "Jakob Gunnar Sigurðsson", "position": "Attacker", "player_wyid": 1211997, "player_optauuid": "cqqkcrvqu2k0tmbtkvtcdk5jo"},
    {"klub": "Hillerød Fodbold", "navn": "Andreas Frederik Dithmer", "position": "Goalkeeper", "player_wyid": 624732, "player_optauuid": "ekbi29eljngvxgx9scbzwygwk"},

    # Hobro IK
    {"klub": "Hobro IK", "navn": "Oliver Klitten", "position": "Attacker", "player_wyid": 449367, "player_optauuid": "e19g5bz7s9wqcvj8mttztxi0a"},
    {"klub": "Hobro IK", "navn": "Mikkel Bach Løndal", "position": "Defender", "player_wyid": 684216, "player_optauuid": "ehjqrbqo7ewbztia7k2mrzx90"},
    {"klub": "Hobro IK", "navn": "Frederik Dietz Nielsen", "position": "Defender", "player_wyid": 621798, "player_optauuid": "ebd3uvtt54wkdsahc2127j02c"},
    {"klub": "Hobro IK", "navn": "Théo Puggaard Ekié Hansen", "position": "Midfielder", "player_wyid": 766318, "player_optauuid": "e0rgqk3gxzs005m9ok9hvp1ck"},
    {"klub": "Hobro IK", "navn": "Mikkel Mejlstrup Pedersen", "position": "Midfielder", "player_wyid": 12129939, "player_optauuid": "xub4z9b3bog8wqhn5yfihecp"},
    {"klub": "Hobro IK", "navn": "Søren Skals Andreasen", "position": "Attacker", "player_wyid": 3808324, "player_optauuid": "qyfoq5fjiochtj89w426lm21"},
    {"klub": "Hobro IK", "navn": "Mikkel Kannegaard Kristensen", "position": "Defender", "player_wyid": 13072683, "player_optauuid": "sog1gsk11bwwrf7l7wm2j7dg"},
    {"klub": "Hobro IK", "navn": "Anders Abdull-Gaffar Haidar Noshe", "position": "Attacker", "player_wyid": 6447943, "player_optauuid": "c7oy1stwyquawdfzzom13xn8"},
    {"klub": "Hobro IK", "navn": "Christian Enemark", "position": "Defender", "player_wyid": 3995562, "player_optauuid": "qedb8t85t1ieeed9613c9crt"},
    {"klub": "Hobro IK", "navn": "Lukas Sparre Klitten", "position": "Defender", "player_wyid": 449370, "player_optauuid": "ea2x4o6ufsqoz2zz7tqcnvo16"},
    {"klub": "Hobro IK", "navn": "Oliver Friis Dorph", "position": "Defender", "player_wyid": 449603, "player_optauuid": "ayhdul772mr22qoly04psb3f8"},
    {"klub": "Hobro IK", "navn": "Oscar Nørgaard Meedom", "position": "Attacker", "player_wyid": 6247064, "player_optauuid": "dmz3u7j1eoz4ofr1o8tbxedw"},
    {"klub": "Hobro IK", "navn": "Jonas Dakir", "position": "Goalkeeper", "player_wyid": 484061, "player_optauuid": "yxhg70gpwi3e9s84c8qwg0yx"},
    {"klub": "Hobro IK", "navn": "Marius Jacobsen", "position": "Defender", "player_wyid": 12246536, "player_optauuid": "bv0j0ezhh9u5u5hqz64p790q"},
    {"klub": "Hobro IK", "navn": "Martin Huldahl", "position": "Attacker", "player_wyid": 6393348, "player_optauuid": "76cmwkx9p9wsqgdddfzmipzo"},

    # Hvidovre IF
    {"klub": "Hvidovre IF", "navn": "Andreas Smed", "position": "Midfielder", "player_wyid": 562692, "player_optauuid": "dncrhma6gwcn6pxiu7hfc6qz8"},
    {"klub": "Hvidovre IF", "navn": "Alexander Johansen", "position": "Attacker", "player_wyid": 1023285, "player_optauuid": "7ymn0ytcqi6l43nqraxt9s1zo"},
    {"klub": "Hvidovre IF", "navn": "Marius Elvius", "position": "Defender", "player_wyid": 5053926, "player_optauuid": "c2isptqoy4cq5c8rlr9s1roq"},
    {"klub": "Hvidovre IF", "navn": "Nicolai Clausen", "position": "Defender", "player_wyid": 6232526, "player_optauuid": "dzg820946z4848whaa6ny2nd"},
    {"klub": "Hvidovre IF", "navn": "Nicolaj Jungvig", "position": "Defender", "player_wyid": 5793933, "player_optauuid": "pk6hii2s8tbv2zux8mvbapec"},
    {"klub": "Hvidovre IF", "navn": "Louka Prip Andreasen", "position": "Attacker", "player_wyid": 562503, "player_optauuid": "9dnceiwcpsatrdrj2m1uz6pnu"},
    {"klub": "Hvidovre IF", "navn": "Oliver Bjerrum Jensen", "position": "Midfielder", "player_wyid": 11298524, "player_optauuid": "e7sicg0km2z5jq80ptgaxo4q"},
    {"klub": "Hvidovre IF", "navn": "Filip Đukić", "position": "Goalkeeper", "player_wyid": 471964, "player_optauuid": "d9hh01mit4geyadol3gmzco9"},
    {"klub": "Hvidovre IF", "navn": "Oliver Juul", "position": "Defender", "player_wyid": 519715, "player_optauuid": "aejgqvdw1jftxaa538kaa15w4"},
    {"klub": "Hvidovre IF", "navn": "Oliver Kjærgaard", "position": "Midfielder", "player_wyid": 435879, "player_optauuid": "cl4xl80n4gew1ox03r3ooshrd"},
    {"klub": "Hvidovre IF", "navn": "Ahmed Iljazovski", "position": "Defender", "player_wyid": 879754, "player_optauuid": "bfvdr7ckiersz26ya2kq9f1g4"},
    {"klub": "Hvidovre IF", "navn": "Zamir Aliji", "position": "Midfielder", "player_wyid": 620821, "player_optauuid": "aajgld24isoem1ycoysyxxp1w"},
    {"klub": "Hvidovre IF", "navn": "Emmanuel Aby", "position": "Attacker", "player_wyid": 748624, "player_optauuid": "907vtkod58b7986k7u1619gr8"},
    {"klub": "Hvidovre IF", "navn": "Daniel Stenderup", "position": "Defender", "player_wyid": 56017, "player_optauuid": "a30gduuv9d1s4pkthgu2jhyol"},
    {"klub": "Hvidovre IF", "navn": "Malte Kiilerich", "position": "Defender", "player_wyid": 3702696, "player_optauuid": "30daj1ef34rczbhng0eoncvd"},
    {"klub": "Hvidovre IF", "navn": "Donavan Bagou", "position": "Attacker", "player_wyid": 6070331, "player_optauuid": "1hlx5mvl8th7y82gocnuxacd0"},
    {"klub": "Hvidovre IF", "navn": "Frederik Rask Høgh Jensen", "position": "Attacker", "player_wyid": None, "player_optauuid": "9tt9eo9bsff7dp7aqjal1obo4"},
    
    # Kolding IF
    {"klub": "Kolding IF", "navn": "Jeffrey Papayaw Adjei-Broni", "position": "Attacker", "player_wyid": 6123421, "player_optauuid": "cumsropo1r0msfzxxteml1w"},
    {"klub": "Kolding IF", "navn": "Jonas Graabæk Hansen", "position": "Defender", "player_wyid": 11856451, "player_optauuid": "ju0n48qswe2v63ubre4ozt3o"},
    {"klub": "Kolding IF", "navn": "Filip Lesniak", "position": "Midfielder", "player_wyid": 2418543, "player_optauuid": "q6uah3ucqhk39bymyfma9xp1"},
    {"klub": "Kolding IF", "navn": "Adam Danko", "position": "Goalkeeper", "player_wyid": 6329991, "player_optauuid": "lxsyoos06fqbsi6skcm974a2"},
    {"klub": "Kolding IF", "navn": "Hans Høllsberg", "position": "Midfielder", "player_wyid": 5698447, "player_optauuid": "apuo8j6dbzbr264gwsckrr4k"},
    {"klub": "Kolding IF", "navn": "Aksel Emil Halsgaard", "position": "Defender", "player_wyid": 624735, "player_optauuid": "em0yawcqyqwf53hbj0zlz4duc"},
    {"klub": "Kolding IF", "navn": "Abdul Samad Shahzad Arshad", "position": "Midfielder", "player_wyid": 5775773, "player_optauuid": "j4yxqk470udckpmequhkmdjo"},
    {"klub": "Kolding IF", "navn": "Nicolai Bossen", "position": "Midfielder", "player_wyid": 690948, "player_optauuid": "dvnd5025v01tme7xzayw6jhn8"},
    {"klub": "Kolding IF", "navn": "Mikkel Anthoni Lynge", "position": "Midfielder", "player_wyid": 697953, "player_optauuid": "bs5wze64ksftqrh53gh9256hg"},
    {"klub": "Kolding IF", "navn": "Isak Frederik Tånnander", "position": "Midfielder", "player_wyid": 5611536, "player_optauuid": "bajck5osvj7trnwt2a5mc3dg"},
    {"klub": "Kolding IF", "navn": "Niels Henrik Melsæther Morberg", "position": "Midfielder", "player_wyid": 4491365, "player_optauuid": "u9zrgsm6wycfcbk04m64wd1w"},
    {"klub": "Kolding IF", "navn": "Albert Nørager", "position": "Defender", "player_wyid": 4500698, "player_optauuid": "ewvm6ux4yvpwgrzjkc1chqwa"},
    {"klub": "Kolding IF", "navn": "Lasse Bak Laursen", "position": "Defender", "player_wyid": 1090748, "player_optauuid": "cpmf0lnxudnkpgskcw6pzbrbo"},
    {"klub": "Kolding IF", "navn": "Sterling Yatéké", "position": "Attacker", "player_wyid": 5797069, "player_optauuid": "ircna8pbskreztmy1wiqwx9m"},
    {"klub": "Kolding IF", "navn": "Casper Jørgensen", "position": "Midfielder", "player_wyid": 11729159, "player_optauuid": "fvf8z6p8ok0n5vu999ysfywa"},
    {"klub": "Kolding IF", "navn": "Tobias Augustinus-Jensen", "position": "Midfielder", "player_wyid": 678650, "player_optauuid": "a6vduk9b8pcf250he49x1vitw"},
    {"klub": "Kolding IF", "navn": "Magnus Døj", "position": "Defender", "player_wyid": 627720, "player_optauuid": "ditbnaezwo4x10717bf53uwb8"},

    # Vejle Boldklub
    {"klub": "Vejle Boldklub", "navn": "Wahid Faghir", "position": "Attacker", "player_wyid": 543966, "player_optauuid": "e9kq60f4sugjddbxnc0pqo60a"},
    {"klub": "Vejle Boldklub", "navn": "Andrew Hjulsager", "position": "Midfielder", "player_wyid": 1351131, "player_optauuid": "d2fpmtdglpqwyhnc657n77it"},
    {"klub": "Vejle Boldklub", "navn": "Tobias Bach", "position": "Midfielder", "player_wyid": 7661045, "player_optauuid": "lssweodhkyifhj333v6f6r6c"},
    {"klub": "Vejle Boldklub", "navn": "Jelle Duin", "position": "Attacker", "player_wyid": 448662, "player_optauuid": "f1jk2tqumutelh2ym21v5beuh"},
    {"klub": "Vejle Boldklub", "navn": "Abdoulaye Camara", "position": "Attacker", "player_wyid": 12101168, "player_optauuid": "w7eh1ukicd4p0vp7kqqrzu38"},
    {"klub": "Vejle Boldklub", "navn": "Max Birkjær Jensen", "position": "Midfielder", "player_wyid": 12332262, "player_optauuid": "yz7lj68ih2ng9m42r0cb7lzo"},
    {"klub": "Vejle Boldklub", "navn": "Christian Gammelgaard", "position": "Attacker", "player_wyid": 5698431, "player_optauuid": "hbucfyn2l3bxcw5r4zcb1dlg"},
    {"klub": "Vejle Boldklub", "navn": "Gustav Marcussen", "position": "Midfielder", "player_wyid": 347368, "player_optauuid": "ayxi2m0g0pm6rl1ba5pto66z9"},
    {"klub": "Vejle Boldklub", "navn": "Mikkel Duelund", "position": "Midfielder", "player_wyid": 3610965, "player_optauuid": "qvy65ckiigykkowpyco05zv9"},
    {"klub": "Vejle Boldklub", "navn": "Mike Vestergård", "position": "Midfielder", "player_wyid": 562451, "player_optauuid": "f58yr2jmfp8kpgprfxbokt1t6"},
    {"klub": "Vejle Boldklub", "navn": "Thomas Gundelund", "position": "Defender", "player_wyid": 5449321, "player_optauuid": "xjhud4hyekcg08nue1iosmsq"},
    {"klub": "Vejle Boldklub", "navn": "Lundrim Hetemi", "position": "Midfielder", "player_wyid": 5218537, "player_optauuid": "uia9zlz3axnuc6usdn9u4kfe"},
    {"klub": "Vejle Boldklub", "navn": "Tobias Lauritsen", "position": "Midfielder", "player_wyid": 7623052, "player_optauuid": "2zuxw8lez5w4vjd8spzzysyc"},
    {"klub": "Vejle Boldklub", "navn": "Stefan Ivov Velkov", "position": "Defender", "player_wyid": 2392591, "player_optauuid": "ykl08k2c2kwxukw0gvslf6qd"},
    {"klub": "Vejle Boldklub", "navn": "Lasse Nielsen", "position": "Defender", "player_wyid": 12265019, "player_optauuid": "mjzy2s8qv0a5qw9pyhs112ol"},
    {"klub": "Vejle Boldklub", "navn": "Christian Sørensen", "position": "Defender", "player_wyid": 7358148, "player_optauuid": "mcb1hiuk9rzf48cx3vj5i3th"},
    {"klub": "Vejle Boldklub", "navn": "Nicolai Oppen Larsen", "position": "Goalkeeper", "player_wyid": 623781, "player_optauuid": "b2492j7qzdo7g3ysxz6gq4g5x"},
    {"klub": "Vejle Boldklub", "navn": "Giorgi Tabatadze", "position": "Defender", "player_wyid": 771159, "player_optauuid": "d1uqdyoqq6vyafeqbnsi6xo2c"},
    {"klub": "Vejle Boldklub", "navn": "Bismark Edjeodji", "position": "Midfielder", "player_wyid": 9271754, "player_optauuid": "nzauesd85d6utkwdc1s1a1as"},

    # Vendsyssel FF
    {"klub": "Vendsyssel FF", "navn": "Bilal Konteh", "position": "Defender", "player_wyid": 9152663, "player_optauuid": "ylz4gki78fg6jxbbzae0hgk4"},
    {"klub": "Vendsyssel FF", "navn": "Marcus Hannesbo", "position": "Midfielder", "player_wyid": 9851527, "player_optauuid": "ar33yy0wd5ah5o8om1l12pgq"},
    {"klub": "Vendsyssel FF", "navn": "Stephen Fumen Michael", "position": "Midfielder", "player_wyid": 12318425, "player_optauuid": "jhfvec5tqv3sjtzejmu4b47o"},
    {"klub": "Vendsyssel FF", "navn": "Precious Tonye Williams", "position": "Attacker", "player_wyid": 93043261, "player_optauuid": "c83cudouly28512clb83cic3"},
    {"klub": "Vendsyssel FF", "navn": "Andreas Rise Kristiansen", "position": "Midfielder", "player_wyid": "9vbxe5gvruap8h546efz3nx1w", "player_optauuid": "9vbxe5gvruap8h546efz3nx1w"},
    {"klub": "Vendsyssel FF", "navn": "Malthe Holt Nielsen", "position": "Midfielder", "player_wyid": 11429693, "player_optauuid": "rxtektemoyt390x6pq1xreac"},
    {"klub": "Vendsyssel FF", "navn": "Steven Simpson", "position": "Attacker", "player_wyid": 7545507, "player_optauuid": "t811fc39zstqmkqyb56flogk"},
    {"klub": "Vendsyssel FF", "navn": "Ari Olsen", "position": "Defender", "player_wyid": 10994686, "player_optauuid": "282fmbmx8lzirvh1ljkf33rp"},
    {"klub": "Vendsyssel FF", "navn": "Lasse Steffensen", "position": "Attacker", "player_wyid": 5458469, "player_optauuid": "l89n30nejpn2u22ygvchwnze"},
    {"klub": "Vendsyssel FF", "navn": "Rasmus Vilhelm Schüller", "position": "Midfielder", "player_wyid": 354717, "player_optauuid": "pel84swlqfux6obt6lznze1h"},
    {"klub": "Vendsyssel FF", "navn": "Adam Vendelbo", "position": "Attacker", "player_wyid": 5793536, "player_optauuid": "miatayfy07pf4og7qc7c7pqs"},
    {"klub": "Vendsyssel FF", "navn": "Benjamin Clemmensen", "position": "Defender", "player_wyid": 7646208, "player_optauuid": "rn42gm9xm3yunk883yan9vdg"},
    {"klub": "Vendsyssel FF", "navn": "Mads Nyboe Lauritsen", "position": "Defender", "player_wyid": 782048, "player_optauuid": "oywgthoxa153nf48la1j8v10"},
    {"klub": "Vendsyssel FF", "navn": "Sebastian Lodberg", "position": "Attacker", "player_wyid": 678062, "player_optauuid": "b2e6na1kcw3l5tu7n32w1awwk"},
    {"klub": "Vendsyssel FF", "navn": "Emil Grønn Pedersen", "position": "Attacker", "player_wyid": 1114180, "player_optauuid": "d25swlwty2q67c514p61ci7f8"},
    {"klub": "Vendsyssel FF", "navn": "Lasse William Schulz", "position": "Goalkeeper", "player_wyid": 6868916, "player_optauuid": "4vlnkuqfh7rnymg8qku8amwa"},
]

player_mapping = PlayerMapping(PLAYER_MAPPING)

