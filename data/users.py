# data/users.py

# Ordbog over godkendte brugere: { "brugernavn": "adgangskode" }
USER_DB = {
    "kasper": "kasper",
    "ceo": "ceo",
    "mr": "mr",
    "kd": "kd",
    "cg": "cg"
}

def get_users():
    """Returnerer ordbogen med brugere"""
    return USER_DB
