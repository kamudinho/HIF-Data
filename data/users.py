# data/users.py
def get_users():
    return {
        "kasper": {
            "pass": "kasper", 
            "role": "admin",
            "restricted": []  # Admin har ingen restriktioner - ser alt
        },
        "ceo": {
            "pass": "ceo", 
            "role": "Analytiker",
            "restricted": ["ADMIN"] # Kan se alt undtagen ADMIN-panelet
        },
        "mr": {
            "pass": "mr", 
            "role": "coach",
            "restricted": ["ADMIN", "SCOUTING"] # Låst for Admin og Scouting
        },
        "kd": {
            "pass": "kd", 
            "role": "coach",
            "restricted": ["ADMIN", "SCOUTING"] # Låst for Admin og Scouting
        },
        "cg": {
            "pass": "cg", 
            "role": "scout",
            "restricted": ["ADMIN", "ANALYSE"] # Låst for Admin og Analyse
        }
    }
