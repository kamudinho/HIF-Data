# data/users.py
def get_users():
    return {
        "kasper": {
            "pass": "kasper", 
            "role": "admin",
            "access": ["TRUPPEN", "ANALYSE", "SCOUTING", "ADMIN"]
        },
        "ceo": {
            "pass": "ceo", 
            "role": "Analytiker",
            "access": ["TRUPPEN", "ANALYSE", "SCOUTING"]
        },
        "mr": {
            "pass": "mr", 
            "role": "coach",
            "access": ["TRUPPEN", "ANALYSE"]
        },
        "kd": {
            "pass": "kd", 
            "role": "coach",
            "access": ["TRUPPEN", "ANALYSE"]
        },
        "cg": {
            "pass": "cg", 
            "role": "scout",
            "access": ["SCOUTING", "TRUPPEN"]
        }
    }
