def get_users():
    return {
        "kasper": {
            "pass": "kasper1234", 
            "role": "admin",
            "restricted": []  # Admin ser alt, inklusive EMNELISTE
        },
        "ceo": {
            "pass": "ceo1234", 
            "role": "Analytiker",
            "restricted": ["ADMIN"] # Kan se alt undtagen ADMIN, herunder EMNELISTE
        },
        "mr": {
            "pass": "Retov2650", 
            "role": "manager",
            "restricted": ["ADMIN"]
        },
        "kd": {
            "pass": "Daugaard2650", 
            "role": "coach",
            "restricted": ["ADMIN", "Opret emne", "Emnedatabase"] # Spærret for Emneliste
        },
        "cg": {
            "pass": "Gron1234", 
            "role": "scout",
            "restricted": ["ADMIN", "Opret emne", "Emnedatabase"] # Spærret for Emneliste
        },
        "jeppe": {
            "pass": "Scout1234", 
            "role": "scout",
            "restricted": [
                "ADMIN", 
                "TRUPPEN", 
                "HIF ANALYSE", 
                "BETINIA LIGAEN", 
                "Opret emne", 
                "Emnedatabase", 
                "Sammenligning",
            ] 
        }
    }
