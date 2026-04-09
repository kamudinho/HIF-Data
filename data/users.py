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
            "restricted": ["ADMIN"] # Alt undtagen admin-panelet
        },
        "mr": {
            "pass": "Retov2650", 
            "role": "manager",
            "restricted": ["ADMIN"] # Alt undtagen admin-panelet
        },
        "kd": {
            "pass": "Daugaard2650", 
            "role": "coach",
            "restricted": ["ADMIN", "Opret emne", "Emnedatabase"] # Ingen adgang til emner
        },
        "cg": {
            "pass": "Gron1234", 
            "role": "scout",
            "restricted": ["ADMIN", "TRUPPEN", "HIF ANALYSE", "BETINIA LIGAEN"] 
            # CG kan se Scouting-menuen (Rapport, Database, Emnedatabase)
        },
        "jeppe": {
            "pass": "Scout1234", 
            "role": "scout",
            "restricted": [
                "ADMIN", "TRUPPEN", "HIF ANALYSE", "BETINIA LIGAEN", "Sammenligning", "Opret emne"
            ] 
            # Jeppe ser kun Scoutrapport, Database og Emnedatabase under Scouting
        }
    }
