import csv
from pathlib import Path

class PlayerMapping:
    def __init__(self, csv_file_path):
        self.wy_to_optauuid = {}
        self.optauuid_to_wy = {}
        self.players_by_name = {}
        self._load_data(csv_file_path)

    def _load_data(self, file_path):
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Kunne ikke finde filen: {file_path}")

        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                klub = row.get("KLUB", "").strip()
                navn = row.get("NAVN", "").strip()
                position = row.get("POSITION", "").strip()
                wy_id = row.get("PLAYER_WYID", "").strip()
                opta_uuid = row.get("PLAYER_OPTAUUID", "").strip()

                player_info = {
                    "klub": klub,
                    "navn": navn,
                    "position": position,
                    "player_wyid": int(wy_id) if wy_id.isdigit() and wy_id != "0" else None,
                    "player_optauuid": opta_uuid if opta_uuid else None
                }

                # Gem i opslagstavler
                if wy_id and wy_id != "0":
                    self.wy_to_optauuid[int(wy_id)] = opta_uuid
                if opta_uuid:
                    self.optauuid_to_wy[opta_uuid] = int(wy_id) if wy_id.isdigit() and wy_id != "0" else None
                
                # Gør det muligt at søge på navn (gemmer i en liste, da navne kan forekomme flere steder)
                self.players_by_name.setdefault(navn.lower(), []).append(player_info)

    def get_opta_uuid(self, player_wyid):
        """Finder Opta UUID ud fra Wyscout ID"""
        return self.wy_to_optauuid.get(int(player_wyid))

    def get_wy_id(self, player_optauuid):
        """Finder Wyscout ID ud fra Opta UUID"""
        return self.optauuid_to_wy.get(player_optauuid)

    def get_player_by_name(self, navn):
        """Finder spillerdetaljer ud fra navn"""
        return self.players_by_name.get(navn.lower(), [])
