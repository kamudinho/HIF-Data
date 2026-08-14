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

    def get_name_by_opta_uuid(self, player_optauuid, conn=None, db_name="KLUB_HVIDOVREIF.AXIS"):
        """
        Henter det korrekte navn ud fra Opta UUID. 
        Hvis det ikke findes i den statiske liste, kan den slå op i databasen via 'conn'.
        """
        if not player_optauuid or str(player_optauuid) == "None":
            return "Ukendt"
            
        uuid_str = str(player_optauuid).strip()
        
        # 1. Tjek den eksisterende cache/liste først
        if uuid_str in self.optauuid_to_name:
            return self.optauuid_to_name[uuid_str]
            
        # 2. Hvis ikke den findes, og der er givet en database-forbindelse med, slå op live
        if conn is not None:
            try:
                sql = f"SELECT PLAYER_NAME FROM {db_name}.OPTA_PLAYERMAPPING WHERE PLAYER_OPTAUUID = '{uuid_str}' LIMIT 1"
                res = conn.query(sql)
                if res is not None and not res.empty:
                    navn = str(res.iloc[0]['PLAYER_NAME']).strip()
                    # Gem den i cachen, så vi ikke slår op flere gange for samme spiller i samme session
                    self.optauuid_to_name[uuid_str] = navn
                    return navn
            except Exception:
                pass
                
        return "Ukendt"

    def get_player_by_name(self, navn):
        return self.players_by_name.get(str(navn).lower(), [])

    def register_players_from_df(self, df, uuid_col='PLAYER_OPTAUUID', name_col='PLAYER_NAME'):
            """Registrerer spillere dynamisk fra en DataFrame, hvis de mangler i den statiske liste."""
            if df is None or df.empty:
                return
                
            if uuid_col not in df.columns or name_col not in df.columns:
                return
    
            for _, row in df.dropna(subset=[uuid_col]).iterrows():
                opta_uuid = str(row[uuid_col]).strip()
                navn = str(row.get(name_col, "")).strip()
    
                if opta_uuid and opta_uuid != "None" and navn and navn != "nan" and navn != "Ukendt":
                    # Hvis spilleren ikke findes i forvejen, tilføj den til cachen
                    if opta_uuid not in self.optauuid_to_name:
                        self.optauuid_to_name[opta_uuid] = navn


# --- OVERSIGT OVER SPILLERE ---
SEASONNAME = "2026/2027"
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
    {"klub": "AaB", "navn": "Markus André Kaasa", "position": "Midfielder", "player_optauuid": "e0j0uakuzduvis9wqsocngwrt", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AaB", "navn": "Valdemar Møller Damgaard", "position": "Midfielder", "player_optauuid": "5521epytthhw9afm2r3jn3384", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AaB", "navn": "Jubril Chukwu-Emeka Adedeji", "position": "Attacker", "player_optauuid": "4sgxth7onhb5mu29bgyupby3u", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AaB", "navn": "Marcus Bondee", "position": "Midfielder", "player_optauuid": "7wytawxwiszq1aass5ujio7o", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AaB", "navn": "William Thomsen", "position": "Attacker", "player_optauuid": "14ur60ict5k3l9nv02o7psw0k", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AaB", "navn": "Cornelius Axel Olsson", "position": "Defender", "player_optauuid": "5uo9saax5iqsctxq7w3si8w0k", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AaB", "navn": "Kornelius Normann Hansen", "position": "Attacker", "player_optauuid": "48sqqhgtmfmpqb3602iirspd6", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AaB", "navn": "Marc Nielsen", "position": "Defender", "player_optauuid": "bcdp9e3dezuaybm8ndrsanbx0", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AaB", "navn": "Frederik Lindbøg Børsting", "position": "Midfielder", "player_optauuid": "egwhlgopjtjkop7ozy7ltk1cl", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AaB", "navn": "Alexander Lien Håpnes", "position": "Midfielder", "player_optauuid": "5y2mfgruizah0ylcz7q1abw9g", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AaB", "navn": "Uche Brian Seo Nwadike", "position": "Attacker", "player_optauuid": "91cvtiaq4im9hiydjiualozdg", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AaB", "navn": "Vincent Carsten Maria Müller", "position": "Goalkeeper", "player_optauuid": "a2l4ep71txn2edtjjcgewai5m", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AaB", "navn": "Kelvin Pius John", "position": "Attacker", "player_optauuid": "5vrsflxiv2dgfa8199a2qxsve", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AaB", "navn": "Andres Jasson", "position": "Midfielder", "player_optauuid": "8bi1tlz62rjwyak4pnnzgp562", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AaB", "navn": "Nóel Atli Arnórsson", "position": "Midfielder", "player_optauuid": "brinkgys7026490q3ixx6h9uc", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AaB", "navn": "Elison Makolli", "position": "Defender", "player_optauuid": "697f50qoetodmfe8ybcuey2ac", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AaB", "navn": "Mathias Nordestgaard Kubel", "position": "Attacker", "player_optauuid": "az9olsp7tglzt73awei9a4cgk", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},

    # Aarhus Fremad
    {"klub": "Aarhus Fremad", "navn": "Ólafur Dan Hjaltason", "position": "Defender", "player_optauuid": "a5alop4wg4qwwu812pfskfjtg", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Aarhus Fremad", "navn": "Magnus Kaastrup Refstrup Lauritsen", "position": "Attacker", "player_optauuid": "9nafz0c0x2qvmo5ldm0djmcq1", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Aarhus Fremad", "navn": "Viktor Højbjerg", "position": "Goalkeeper", "player_optauuid": "f2hab1q8nrvah7j2k5ci0edxw", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Aarhus Fremad", "navn": "Marcus Løvenbalk Kirchheiner", "position": "Defender", "player_optauuid": "7zb57r5m7lmvj3xlf9y1ldez8", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Aarhus Fremad", "navn": "Jonas Østergaard", "position": "Attacker", "player_optauuid": "4yfwo1ja5nchmj85dlml95o2c", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Aarhus Fremad", "navn": "Jashar Beluli", "position": "Midfielder", "player_optauuid": "29y19vqfjkvlc8s9gr5v5atqs", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Aarhus Fremad", "navn": "Alexander Ludwig", "position": "Defender", "player_optauuid": "61vr9xr91fr4g6ayzga5vn9w5", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Aarhus Fremad", "navn": "Linus Rönnberg", "position": "Midfielder", "player_optauuid": "cyidz45zw5umg1yd6ahot3ndg", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Aarhus Fremad", "navn": "Carl Carøe Nygaard", "position": "Midfielder", "player_optauuid": "2n8fvjqe4es6a04l4ki18uvbo", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Aarhus Fremad", "navn": "Marcus Ryberg", "position": "Midfielder", "player_optauuid": "df9m624q4gqk35f4y3ohxch04", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Aarhus Fremad", "navn": "Magnus Kirchheiner", "position": "Midfielder", "player_optauuid": "5q7msbcrmtsr3b7tykgb6l05w", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Aarhus Fremad", "navn": "Frederik Grube Andersen", "position": "Midfielder", "player_optauuid": "186mdd3akww1wyxdc9ouw6kno", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Aarhus Fremad", "navn": "Devon Bernasko-Appu", "position": "Attacker", "player_optauuid": "2isfyjd6l2uktg58g3pbazaj8", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Aarhus Fremad", "navn": "Simon Bækgård", "position": "Midfielder", "player_optauuid": "5o1k2hd9rdooxpjgbnabuh94a", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Aarhus Fremad", "navn": "Kasper Lunding Jakobsen", "position": "Midfielder", "player_optauuid": "6zxcmzp7w6esj54g05tvk7ai1", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Aarhus Fremad", "navn": "Elias Caspersen Egerton", "position": "Midfielder", "player_optauuid": "8rqctff92ui8fanzbk6skyyac", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Aarhus Fremad", "navn": "Andreas Pisani Laugesen", "position": "Defender", "player_optauuid": "2lvlyvfvdoz7kyqtib6jm9btg", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    
    # AB
    {"klub": "AB", "navn": "Marco Vesterholm", "position": "Midfielder", "player_optauuid": "4m23g10w898skztiwfiedqcd0", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AB", "navn": "Frederik Lindgaard", "position": "Defender", "player_optauuid": "clf3fgzelbfqh8sya98k5pdlg", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AB", "navn": "Marcus Immersen", "position": "Attacker", "player_optauuid": "afr71rcay1uq4ngti10fvr9xw", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AB", "navn": "Adam Ingi Benediktsson", "position": "Goalkeeper", "player_optauuid": "cnfkqyunacrm7mli650a3l3ze", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AB", "navn": "Noah Engell Christensen", "position": "Attacker", "player_optauuid": "5crdnyx54gw8u104sjprb7das", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AB", "navn": "Serigne Saliou Diop", "position": "Attacker", "player_optauuid": "8gma3ufrjv0hj0k2nulcbodn8", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AB", "navn": "Tobias Damtoft Andersen", "position": "Attacker", "player_optauuid": "ernnq3ugpx34joskjyj373lgq", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AB", "navn": "Gabriel Rodrigues Noga", "position": "Defender", "player_optauuid": "1x74ueydb3hpmz8tkzblt68oa", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AB", "navn": "Jonathan Mathys", "position": "Attacker", "player_optauuid": "zpl7lyln792rt0b2oedamvbo", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AB", "navn": "Marc Dal Hende", "position": "Defender", "player_optauuid": "33sxiwcjeqcop3ukuok86ujmd", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AB", "navn": "Casper Dirch Hagel Grening", "position": "Attacker", "player_optauuid": "6hms8o682fsh33l3hp4qo39ey", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AB", "navn": "O’Vonte Mullings", "position": "Attacker", "player_optauuid": "7pdl6jqfaq1x1trdi5k30wsus", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AB", "navn": "Noah Ibsen", "position": "Defender", "player_optauuid": "2lvkvn7fds2seqd882lv90mc4", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AB", "navn": "Mikkel Clement", "position": "Midfielder", "player_optauuid": "c6s8nbgk1z9xvasi3rh3a82s4", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AB", "navn": "Milan Justin Silva Rasmussen", "position": "Attacker", "player_optauuid": "4po6qfkmrc30lep6z6ka5db10", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AB", "navn": "Søren Ulrik Ilsøe", "position": "Midfielder", "player_optauuid": "8ii8snymcafyrv1x9srwkrtka", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AB", "navn": "Travian Anthony LaMere Sousa", "position": "Defender", "player_optauuid": "7zr3gif60ntltgt3s5yi6qjca", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "AB", "navn": "Aidan Bardina Liu", "position": "Defender", "player_optauuid": "4z0ebjgc0s506zay6ekwf5gmi", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},

    # Esbjerg
    {"klub": "Esbjerg", "navn": "Mikail Maden", "position": "Midfielder", "player_optauuid": "15yli690oxmbr4dl1ksti2p9m", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Esbjerg", "navn": "Noah Oliver Strandby", "position": "Attacker", "player_optauuid": "a3s2lypc1aceu363i78aczx1w", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Esbjerg", "navn": "William Johannes Lykke", "position": "Goalkeeper", "player_optauuid": "9h6c9ue598hllcri39erjitqs", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Esbjerg", "navn": "Patrick Lindholm Tjørnelund", "position": "Defender", "player_optauuid": "37mo55lynu3blqnb8k9ln8k16", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Esbjerg", "navn": "Peter Nicolai Kruse Bjur", "position": "Midfielder", "player_optauuid": "6m4anciafmzc24s44xszymbc9", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Esbjerg", "navn": "Julius Lucena", "position": "Attacker", "player_optauuid": "5sha6xhovfmuzd7rolx1om39w", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Esbjerg", "navn": "Anders Sønderskov", "position": "Defender", "player_optauuid": "ajk0mbprro09pccglih9y740k", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Esbjerg", "navn": "Andreas Kristiansen", "position": "Midfielder", "player_optauuid": "ddbrysgujd87xr0si82kha1as", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Esbjerg", "navn": "Oluwatomiwa John Kolawole", "position": "Midfielder", "player_optauuid": "djm3hebvv79jo679zzd2b71g4", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Esbjerg", "navn": "Sander Eng Strand", "position": "Defender", "player_optauuid": "f5gja2wqjlm60rideia16jpm2", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Esbjerg", "navn": "Oskar Adam Rudkjøbing Boesen", "position": "Midfielder", "player_optauuid": "lmrff8mviimc33yyrpjzr2tw", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Esbjerg", "navn": "Benjamin Steenfeldt Hvidt", "position": "Midfielder", "player_optauuid": "4yyiv4t6irqpeayug5qgvmkmh", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Esbjerg", "navn": "Lucas Skjoldberg From", "position": "Attacker", "player_optauuid": "6hmsrr08cllpl4iumu92zskbt", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Esbjerg", "navn": "Muamer Brajanac", "position": "Attacker", "player_optauuid": "4krwgfspxdgpq1pli11b04iga", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Esbjerg", "navn": "Jonathan Roland Foss", "position": "Defender", "player_optauuid": "cy4iqzsaxd9c9v07s4m93caac", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Esbjerg", "navn": "Marcus Winther Hansen", "position": "Midfielder", "player_optauuid": "cod92jjb3qqrg6n1tu15ciwpg", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},

    # Fredericia
    {"klub": "Fredericia", "navn": "Jeppe Kudsk Pedersen", "position": "Defender", "player_optauuid": "b1kyjkhaaiw32cb4bubbpm7tg", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Fredericia", "navn": "Anders Dahl", "position": "Defender", "player_optauuid": "65g5cfsdr10378yvmkpm19444", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Fredericia", "navn": "Frederik Bunten Kjeldal", "position": "Midfielder", "player_optauuid": "2qo4th9tyx2t7mjws65klutjo", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Fredericia", "navn": "Daniel Bisgaard Haarbo", "position": "Midfielder", "player_optauuid": "2zt1yrfv8m2mhpo720n0uydck", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Fredericia", "navn": "Nemo Thomsen", "position": "Attacker", "player_optauuid": "dqp8e2et9fm9r6zo47u1njq50", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Fredericia", "navn": "Malthe Riis Ladefoged", "position": "Defender", "player_optauuid": "7uw675zanxb576wzfvf0lnpjo", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Fredericia", "navn": "William Madsen", "position": "Midfielder", "player_optauuid": "7ztdirfvd9d0x2yw1v051xzbo", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Fredericia", "navn": "Patrick Hessellund Egelund", "position": "Attacker", "player_optauuid": "6lb4k3g75nzgi8bp1y1mzxkru", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Fredericia", "navn": "Lauritz Dauerhøj", "position": "Defender", "player_optauuid": "42j3pc9y10qfcabdvjwu179qs", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Fredericia", "navn": "Felix Vrede Winther", "position": "Midfielder", "player_optauuid": "7rt4wpc0qphwnvhn8jeazesfe", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Fredericia", "navn": "Svenn Crone", "position": "Defender", "player_optauuid": "1ai0gvdx68lxclbj6m255w72t", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Fredericia", "navn": "Eskild Munk Dall", "position": "Attacker", "player_optauuid": "91xtn2wlot8g8ue89zn4iiyqy", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Fredericia", "navn": "Frederik Thykær Rieper", "position": "Defender", "player_optauuid": "3od63zrf6cay4d6ync9i2iuqc", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Fredericia", "navn": "Casper Jørgensen", "position": "Midfielder", "player_optauuid": "9fvf8z6p8ok0n5vu999ysfywa", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Fredericia", "navn": "Oliver Aare Vest", "position": "Defender", "player_optauuid": "5ok6g9rtqb7bz8gnyjqwo2j9w", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Fredericia", "navn": "Emilio Stuberg Simonsen", "position": "Midfielder", "player_optauuid": "45ssaw51hm80y1tfalyesap9m", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Fredericia", "navn": "Elias Hansborg-Sørensen", "position": "Attacker", "player_optauuid": "ewh6t7yo6clfewu89uznll9uc", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Fredericia", "navn": "Valdemar Birksø Thorsen", "position": "Goalkeeper", "player_optauuid": "eiy7fhqxdx3ypg4dq4454hpbe", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    
    # HB Køge
    {"klub": "#HB Køge", "navn": "Ibrahim Figuigui", "position": "Midfielder", "player_optauuid": "3wu2xz4b1gx81bvn53pktoges", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#HB Køge", "navn": "Lukas Rostgaard Achton", "position": "Defender", "player_optauuid": "czudq621hgfprwetp10ckv9jo", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#HB Køge", "navn": "Mads Schütt Rasmussen", "position": "Midfielder", "player_optauuid": "k43cten7yb6p59yo0firhb84", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#HB Køge", "navn": "Noah Stolshøj", "position": "Attacker", "player_optauuid": "ez43e5jd3aur00h75x99xu49g", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#HB Køge", "navn": "Magnus Warming", "position": "Attacker", "player_optauuid": "diwrq7ulrey4juxk4dafct0q1", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#HB Køge", "navn": "Mattias Jakobsen", "position": "Defender", "player_optauuid": "5nved2kta2hk8103hkyhq33hm", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#HB Køge", "navn": "Gabriel M. Larsen", "position": "Midfielder", "player_optauuid": "3mgrufy83uhzs9liw8pwxi784", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#HB Køge", "navn": "Mads Westergren", "position": "Defender", "player_optauuid": "7al9w77ailhli8g487tkl32tw", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#HB Køge", "navn": "Tobias Bendix Thomsen", "position": "Attacker", "player_optauuid": "43m33adgmas68tl6m34gkuzth", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#HB Køge", "navn": "Laurits Bust Sørensen", "position": "Defender", "player_optauuid": "6gmm4awyvlf9p7jr9dvnmp0tm", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#HB Køge", "navn": "Viktor Løvgren Sørensen", "position": "Midfielder", "player_optauuid": "egxik3guom123v43rthy89c7o", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#HB Køge", "navn": "Silas Hald", "position": "Defender", "player_optauuid": "67p0s4o54xcmiustgy8k5gljo", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#HB Køge", "navn": "Erkan Semovski", "position": "Attacker", "player_optauuid": "8qzac8nxm8nxbckdaisnooutw", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#HB Køge", "navn": "Noah Emil Sømmergaard", "position": "Goalkeeper", "player_optauuid": "bwxxfcjd31gykfbpomwr1od90", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#HB Køge", "navn": "Rasmus Brodersen", "position": "Defender", "player_optauuid": "14mwsmzsrmev2646t2gg22has", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#HB Køge", "navn": "Mike Lindemann Jensen", "position": "Midfielder", "player_optauuid": "619s1phj5bkgkug3aszc1y9cl", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#HB Køge", "navn": "Marcel Ibsen Rømer", "position": "Midfielder", "player_optauuid": "5733iw16239m83syv5dm8huj9", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},

    # Hillerød
    {"klub": "#Hillerød Fodbold", "navn": "Mads Høyer Julø", "position": "Defender", "player_optauuid": "3bf4r3xgrs0ttlhgzb93as5t6", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Hillerød Fodbold", "navn": "Rezan Çorlu", "position": "Midfielder", "player_optauuid": "bqcjd0macjc7hmtz7zx34ym6t", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Hillerød Fodbold", "navn": "Saman Sebastean Jalaei", "position": "Attacker", "player_optauuid": "e0u730to91qqtvvx16uhajz10", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Hillerød Fodbold", "navn": "Jonathan Witt", "position": "Defender", "player_optauuid": "5z7y55t2o577r8ki3i5855as", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Hillerød Fodbold", "navn": "Jakob Gunnar Sigurðsson", "position": "Attacker", "player_optauuid": "cqqkcrvqu2k0tmbtkvtcdk5jo", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Hillerød Fodbold", "navn": "Andreas Frederik Dithmer", "position": "Goalkeeper", "player_optauuid": "ekbi29eljngvxgx9scbzwygwk", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Hillerød Fodbold", "navn": "Magnus Munck Bjørnholm", "position": "Midfielder", "player_optauuid": "9gr9rdahnavv0irjauh5xim8k", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Hillerød Fodbold", "navn": "William Owen Glindtvad", "position": "Defender", "player_optauuid": "559w0q3q2smb3aeotyi724s9g", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Hillerød Fodbold", "navn": "Andreas Høyer", "position": "Defender", "player_optauuid": "c119s9yebqgzdc4qrvvjw5bmc", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Hillerød Fodbold", "navn": "Mikkel Mouritz Jensen", "position": "Midfielder", "player_optauuid": "ezbixgm2km8iapnsl57bn4wkp", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Hillerød Fodbold", "navn": "Rasmus Thelander", "position": "Defender", "player_optauuid": "cw6s5hf1tytvb98vjuosz9r6d", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Hillerød Fodbold", "navn": "Sebastian Larsen", "position": "Defender", "player_optauuid": "4m7gr5z6b40dj02yrmlwgeluc", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Hillerød Fodbold", "navn": "Noah Kretzschmar Nielsen", "position": "Attacker", "player_optauuid": "5x7mnku7nky0ojwfvmmqphl3o", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Hillerød Fodbold", "navn": "Tobias Arndal", "position": "Midfielder", "player_optauuid": "1n4eldqa7h9jvcx1693zqu06i", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Hillerød Fodbold", "navn": "Kasper Enghardt Pedersen", "position": "Defender", "player_optauuid": "khqldwfq14b7giakss24l9t5", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Hillerød Fodbold", "navn": "Nicklas Bjerre Schmidt", "position": "Midfielder", "player_optauuid": "5dlh0fa9yo6z283w9p58xmnoq", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Hillerød Fodbold", "navn": "Berzan Kücükylidiz", "position": "Midfielder", "player_optauuid": "bpldj4qdzfdm1n739atcadbmc", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},

    # --- Hvidovre IF ---
    {"player_wyid": "471964", "klub": "#Hvidovre IF", "navn": "Filip Đukić", "position": "Goalkeeper", "pos": "1", "pos_prioritet": "A - Start-11", "kontrakt": "2027-06-30", "player_optauuid": "d9hh01mit4geyadol3gmzco9", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"player_wyid": "483429", "klub": "#Hvidovre IF", "navn": "Ahmed Iljazovski", "position": "Defender", "pos": "2", "pos_prioritet": "B - Trupspiller", "kontrakt": "2027-06-30", "player_optauuid": "bfvdr7ckiersz26ya2kq9f1g4", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"player_wyid": "764636", "klub": "#Hvidovre IF", "navn": "Alexander Johansen", "position": "Attacker", "pos": "5", "pos_prioritet": "A - Start-11", "kontrakt": "2027-06-30", "player_optauuid": "7ymn0ytcqi6l43nqraxt9s1zo", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"player_wyid": "562692", "klub": "#Hvidovre IF", "navn": "Andreas Smed", "position": "Midfielder", "pos": "11", "pos_prioritet": "A - Start-11", "kontrakt": "2027-06-30", "player_optauuid": "dncrhma6gwcn6pxiu7hfc6qz8", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"player_wyid": "224185", "klub": "#Hvidovre IF", "navn": "Ayo Simon Okosun", "position": "Midfielder", "pos": "6", "pos_prioritet": "A - Start-11", "kontrakt": "2027-06-30", "player_optauuid": "7eramyy1bd8msxmg84ctc8ut", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"player_wyid": "56017", "klub": "#Hvidovre IF", "navn": "Daniel Stenderup", "position": "Defender", "pos": "3", "pos_prioritet": "A - Start-11", "kontrakt": "2027-06-30", "player_optauuid": "a30gduuv9d1s4pkthgu2jhyol", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"player_wyid": "607033", "klub": "#Hvidovre IF", "navn": "Donavan Bagou", "position": "Attacker", "pos": "9", "pos_prioritet": "B - Trupspiller", "kontrakt": "2027-06-30", "player_optauuid": "1hlx5mvl8th7y82gocnuxacd0", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"player_wyid": "748624", "klub": "#Hvidovre IF", "navn": "Emmanuel Aby", "position": "Attacker", "pos": "9", "pos_prioritet": "B - Trupspiller", "kontrakt": "2027-06-30", "player_optauuid": "907vtkod58b7986k7u1619gr8", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"player_wyid": "462085", "klub": "#Hvidovre IF", "navn": "Frederik Rask Høgh Jensen", "position": "Attacker", "pos": "9", "pos_prioritet": "A - Start-11", "kontrakt": "2027-06-30", "player_optauuid": "9tt9eo9bsff7dp7aqjal1obo4", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"player_wyid": "562503", "klub": "#Hvidovre IF", "navn": "Louka Prip", "position": "Attacker", "pos": "7", "pos_prioritet": "A - Start-11", "kontrakt": "2027-06-30", "player_optauuid": "9dnceiwcpsatrdrj2m1uz6pnu", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"player_wyid": "370269", "klub": "#Hvidovre IF", "navn": "Malte Kiilerich Hansen", "position": "Defender", "pos": "3", "pos_prioritet": "A - Start-11", "kontrakt": "2027-06-30", "player_optauuid": "630daj1ef34rczbhng0eoncvd", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"player_wyid": "505392", "klub": "#Hvidovre IF", "navn": "Marius Elvius", "position": "Defender", "pos": "2", "pos_prioritet": "A - Start-11", "kontrakt": "2027-06-30", "player_optauuid": "6c2isptqoy4cq5c8rlr9s1roq", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"player_wyid": "417657", "klub": "#Hvidovre IF", "navn": "Nicolai Clausen", "position": "Defender", "pos": "4", "pos_prioritet": "B - Trupspiller", "kontrakt": "2027-06-30", "player_optauuid": "6dzg820946z4848whaa6ny2nd", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"player_wyid": "579393", "klub": "#Hvidovre IF", "navn": "Nicolaj Jungvig", "position": "Defender", "pos": "3", "pos_prioritet": "B - Trupspiller", "kontrakt": "2027-06-30", "player_optauuid": "3pk6hii2s8tbv2zux8mvbapec", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"player_wyid": "525614", "klub": "#Hvidovre IF", "navn": "Oliver Bjerrum Jensen", "position": "Midfielder", "pos": "8", "pos_prioritet": "B - Trupspiller", "kontrakt": "2027-06-30", "player_optauuid": "4e7sicg0km2z5jq80ptgaxo4q", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"player_wyid": "519715", "klub": "#Hvidovre IF", "navn": "Oliver Juul", "position": "Defender", "pos": "4", "pos_prioritet": "B - Trupspiller", "kontrakt": "2027-06-30", "player_optauuid": "aejgqvdw1jftxaa538kaa15w4", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"player_wyid": "435879", "klub": "#Hvidovre IF", "navn": "Oliver Kjærgaard", "position": "Midfielder", "pos": "6", "pos_prioritet": "A - Start-11", "kontrakt": "2027-06-30", "player_optauuid": "cl4xl80n4gew1ox03r3ooshrd", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"player_wyid": "620821", "klub": "#Hvidovre IF", "navn": "Zamir Aliji", "position": "Midfielder", "pos": "8", "pos_prioritet": "B - Trupspiller", "kontrakt": "2027-06-30", "player_optauuid": "aajgld24isoem1ycoysyxxp1w", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    
    # Kolding
    {"klub": "#Kolding IF", "navn": "Nicolai Bossen", "position": "Midfielder", "player_optauuid": "dvnd5025v01tme7xzayw6jhn8", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Kolding IF", "navn": "Magnus Døj", "position": "Defender", "player_optauuid": "ditbnaezwo4x10717bf53uwb8", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Kolding IF", "navn": "Albert Nørager", "position": "Defender", "player_optauuid": "8ewvm6ux4yvpwgrzjkc1chqwa", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Kolding IF", "navn": "Lasse Laursen", "position": "Defender", "player_optauuid": "cpmf0lnxudnkpgskcw6pzbrbo", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Kolding IF", "navn": "Filip Lesniak", "position": "Midfielder", "player_optauuid": "3q6uah3ucqhk39bymyfma9xp1", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Kolding IF", "navn": "Abdul Samad Shahzad Arshad", "position": "Attacker", "player_optauuid": "3j4yxqk470udckpmequhkmdjo", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Kolding IF", "navn": "Mikkel Anthoni Lynge", "position": "Midfielder", "player_optauuid": "bs5wze64ksftqrh53gh9256hg", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Kolding IF", "navn": "Niels Henrik Melsæther Morberg", "position": "Midfielder", "player_optauuid": "5u9zrgsm6wycfcbk04m64wd1w", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Kolding IF", "navn": "Jeffrey Papayaw Adjei-Broni", "position": "Attacker", "player_optauuid": "1cumsropo1r0msfzxxteml1w", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Kolding IF", "navn": "Sterling Yatéké", "position": "Attacker", "player_optauuid": "9ircna8pbskreztmy1wiqwx9m", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Kolding IF", "navn": "Hans Høllsberg", "position": "Midfielder", "player_optauuid": "7apuo8j6dbzbr264gwsckrr4k", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Kolding IF", "navn": "Aksel Emil Halsgaard", "position": "Defender", "player_optauuid": "em0yawcqyqwf53hbj0zlz4duc", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Kolding IF", "navn": "Tobias Augustinus-Jensen", "position": "Attacker", "player_optauuid": "a6vduk9b8pcf250he49x1vitw", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Kolding IF", "navn": "Isak Tånnander", "position": "Midfielder", "player_optauuid": "6bajck5osvj7trnwt2a5mc3dg", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Kolding IF", "navn": "Jonas Graabæk Hansen", "position": "Defender", "player_optauuid": "1ju0n48qswe2v63ubre4ozt3o", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Kolding IF", "navn": "Adam Danko", "position": "Goalkeeper", "player_optauuid": "1lxsyoos06fqbsi6skcm974a2", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    
    #Vejle
    {"klub": "#Vejle Boldklub", "navn": "Mikkel Duelund", "position": "Midfielder", "player_optauuid": "5qvy65ckiigykkowpyco05zv9", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Vejle Boldklub", "navn": "Tobias Bach", "position": "Midfielder", "player_optauuid": "5lssweodhkyifhj333v6f6r6c", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Vejle Boldklub", "navn": "Lundrim Hetemi", "position": "Midfielder", "player_optauuid": "7uia9zlz3axnuc6usdn9u4kfe", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Vejle Boldklub", "navn": "Gustav Marcussen", "position": "Midfielder", "player_optauuid": "anayxi2m0g0pm6rl1ba5pto66z9", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Vejle Boldklub", "navn": "Jelle Duin", "position": "Attacker", "player_optauuid": "f1jk2tqumutelh2ym21v5beuh", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Vejle Boldklub", "navn": "Nicolai Larsen", "position": "Goalkeeper", "player_optauuid": "b2492j7qzdo7g3ysxz6gq4g5x", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Vejle Boldklub", "navn": "Thomas Gundelund", "position": "Defender", "player_optauuid": "1xjhud4hyekcg08nue1iosmsq", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Vejle Boldklub", "navn": "Wahid Faghir", "position": "Attacker", "player_optauuid": "e9kq60f4sugjddbxnc0pqo60a", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Vejle Boldklub", "navn": "Tobias Lauritsen", "position": "Midfielder", "player_optauuid": "22zuxw8lez5w4vjd8spzzysyc", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Vejle Boldklub", "navn": "Stefan Velkov", "position": "Defender", "player_optauuid": "1ykl08k2c2kwxukw0gvslf6qd", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Vejle Boldklub", "navn": "Abdoulaye Kolev Camara", "position": "Attacker", "player_optauuid": "8w7eh1ukicd4p0vp7kqqrzu38", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Vejle Boldklub", "navn": "Christian Sørensen", "position": "Defender", "player_optauuid": "8mcb1hiuk9rzf48cx3vj5i3th", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Vejle Boldklub", "navn": "Lasse Nielsen", "position": "Defender", "player_optauuid": "9mjzy2s8qv0a5qw9pyhs112ol", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Vejle Boldklub", "navn": "Giorgi Tabatadze", "position": "Defender", "player_optauuid": "d1uqdyoqq6vyafeqbnsi6xo2c", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Vejle Boldklub", "navn": "Mike Vestergård", "position": "Midfielder", "player_optauuid": "f58yr2jmfp8kpgprfxbokt1t6", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Vejle Boldklub", "navn": "Christian Gammelgaard", "position": "Attacker", "player_optauuid": "1hbucfyn2l3bxcw5r4zcb1dlg", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Vejle Boldklub", "navn": "Andrew Hjulsager", "position": "Midfielder", "player_optauuid": "1d2fpmtdglpqwyhnc657n77it", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Vejle Boldklub", "navn": "Bismark Edjeodji", "position": "Midfielder", "player_optauuid": "4nzauesd85d6utkwdc1s1a1as", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "#Vejle Boldklub", "navn": "Max Birkjær Jensen", "position": "Midfielder", "player_optauuid": "2yz7lj68ih2ng9m42r0cb7lzo", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    
    # Vendsyssel FF
    {"klub": "Vendsyssel FF", "navn": "Adam Vendelbo Clement", "position": "Attacker", "player_optauuid": "6miatayfy07pf4og7qc7c7pqs", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Vendsyssel FF", "navn": "Andreas Rise Kristiansen", "position": "Midfielder", "player_optauuid": "9vbxe5gvruap8h546efz3nx1w", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Vendsyssel FF", "navn": "Ari Olsen", "position": "Defender", "player_optauuid": "6282fmbmx8lzirvh1ljkf33rp", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Vendsyssel FF", "navn": "Benjamin Clemmensen", "position": "Defender", "player_optauuid": "8rn42gm9xm3yunk883yan9vdg", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Vendsyssel FF", "navn": "Bilal Konteh Krubally", "position": "Defender", "player_optauuid": "3ylz4gki78fg6jxbbzae0hgk4", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Vendsyssel FF", "navn": "Emil Grønn Pedersen", "position": "Attacker", "player_optauuid": "d25swlwty2q67c514p61ci7f8", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Vendsyssel FF", "navn": "Lasse Steffensen", "position": "Attacker", "player_optauuid": "9l89n30nejpn2u22ygvchwnze", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Vendsyssel FF", "navn": "Lasse William Schulz", "position": "Goalkeeper", "player_optauuid": "64vlnkuqfh7rnymg8qku8amwa", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Vendsyssel FF", "navn": "Mads Nyboe Lauritsen", "position": "Defender", "player_optauuid": "oywgthoxa153nf48la1j8v10", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Vendsyssel FF", "navn": "Malthe Holt Nielsen", "position": "Midfielder", "player_optauuid": "3rxtektemoyt390x6pq1xreac", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Vendsyssel FF", "navn": "Marcus Serup Hannesbo", "position": "Midfielder", "player_optauuid": "7ar33yy0wd5ah5o8om1l12pgq", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Vendsyssel FF", "navn": "Precious Tonye Williams", "position": "Attacker", "player_optauuid": "61c83cudouly28512clb83cic", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Vendsyssel FF", "navn": "Rasmus Vilhelm Schüller", "position": "Midfielder", "player_optauuid": "7pel84swlqfux6obt6lznze1h", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Vendsyssel FF", "navn": "Sebastian Lodberg Oppenhagen", "position": "Attacker", "player_optauuid": "b2e6na1kcw3l5tu7n32w1awwk", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Vendsyssel FF", "navn": "Stephen Fumen Michael", "position": "Midfielder", "player_optauuid": "5jhfvec5tqv3sjtzejmu4b47o", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"},
    {"klub": "Vendsyssel FF", "navn": "Steven Jamal Simpson", "position": "Attacker", "player_optauuid": "7t811fc39zstqmkqyb56flogk", "competition_optauuid": "6ifaeunfdelecgticvxanikzu"}
]

player_mapping = PlayerMapping(PLAYER_MAPPING)

