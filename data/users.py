# data/users.py

# Format: { "brugernavn": {"pass": "kode", "role": "rolle"} }
USER_DB = {
    "kasper": {"pass": "kasper", "role": "admin"},
    "ceo":    {"pass": "ceo",    "role": "Analytiker"},
    "mr":     {"pass": "mr",     "role": "coach"},
    "kd":     {"pass": "kd",     "role": "coach"},
    "cg":     {"pass": "cg",     "role": "scout"}
}

def get_users():
    return USER_DB
