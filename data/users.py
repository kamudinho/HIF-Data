def get_users():
    return {
        "kasper": {
            "pass": "kasper1234", 
            "role": "admin",
            "restricted": []  # Admin ser ALT
        },
        "ceo": {
            "pass": "ceo1234", 
            "role": "Analytiker",
            "restricted": ["TESTSIDE", "ADMIN"] # Alt undtagen admin-panelet
        },
        "mr": {
            "pass": "Retov2650", 
            "role": "manager",
            "restricted": ["TESTSIDE", "TILPASNING", "ADMIN"] # Alt undtagen admin-panelet
        },
        "kd": {
            "pass": "Daugaard2650", 
            "role": "coach",
            "restricted": ["TESTSIDE", "TILPASNING", "ADMIN", "Opret emne", "Emnedatabase"] # Ingen adgang til emner
        },
        "kasper-scout": {
            "pass": "Scout1234", 
            "role": "scout",
            "restricted": [
                "TESTSIDE", "TILPASNING", "ADMIN", "TRUPPEN", "HIF ANALYSE", "BETINIA LIGAEN", "Sammenligning", "Opret emne"
            ] 
            # Jeppe ser kun Scoutrapport, Database og Emnedatabase under Scouting
        }
    }
