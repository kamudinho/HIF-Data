# data/users.py
def get_users():
    return {
        "kasper": {
            "pass": "kasper1234", 
            "role": "admin",
            "restricted": []  # Admin har ingen restriktioner - ser alt
        },
        "ceo": {
            "pass": "ceo1234", 
            "role": "Analytiker",
            "restricted": ["ADMIN"] # Kan se alt undtagen ADMIN-panelet
        },
        "mr": {
            "pass": "Retov2650", 
            "role": "coach",
            "restricted": ["ADMIN"] # Låst for Admin og Scouting
        },
        "kd": {
            "pass": "Daugaard2650", 
            "role": "coach",
            "restricted": ["ADMIN"] # Låst for Admin og Scouting
        },
        "cg": {
            "pass": "Gron1234", 
            "role": "scout",
            "restricted": ["ADMIN"] # Låst for Admin og Analyse
        }
    }
