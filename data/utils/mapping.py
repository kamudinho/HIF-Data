# data/utils/mappings.py

# --- 1. OPTA EVENT TYPES (Fra OPTA_DECODE_EVENTTYPE) ---
OPTA_EVENT_TYPES = {
    "1": "Pass", "2": "Offside Pass", "3": "Take On", "4": "Free kick",
    "5": "Out", "6": "Corner", "7": "Tackle", "8": "Interception",
    "9": "Turnover", "10": "Save", "11": "Claim", "12": "Clearance",
    "13": "Miss", "14": "Post", "15": "Attempt Saved", "16": "Goal",
    "17": "Card", "18": "Player off", "19": "Player on", "20": "Player retired",
    "21": "Player returns", "22": "Player becomes goalkeeper", "23": "Goalkeeper becomes player",
    "24": "Condition change", "25": "Official change", "26": "Possession",
    "27": "Start delay", "28": "End delay", "29": "Temporary stop", "30": "End",
    "32": "Start", "41": "Punch", "42": "Good skill", "44": "Aerial",
    "45": "Challenge", "49": "Ball recovery", "50": "Dispossessed", "51": "Error",
    "52": "Keeper pick-up", "53": "Cross not claimed", "54": "Smother",
    "55": "Offside provoked", "56": "Shield ball oop", "57": "Foul throw in",
    "58": "Shot faced", "59": "Keeper Sweeper", "60": "Chance Missed",
    "61": "Ball touch", "73": "Other Ball Contact", "74": "Blocked Pass",
    "82": "Control", "83": "Attempted tackle", "AS": "Assist", "G": "Goal",
    "OG": "Own Goal", "RC": "Red card", "YC": "Yellow card", "Y2C": "Yellow 2nd/RC",
    "SI": "Substitute in", "SO": "Substitute out", "PG": "Penalty goal",
    "PM": "Penalty missed", "PS": "Penalty save", "VAR": "Video Assistant Referee"
}

# --- 2. OPTA QUALIFIERS (De vigtigste fra din liste på 483) ---
OPTA_QUALIFIERS = {
    "1": "Long ball", "2": "Cross", "3": "Head pass", "4": "Through ball",
    "5": "Free kick taken", "6": "Corner taken", "13": "Foul", "14": "Last line",
    "15": "Head", "20": "Right footed", "72": "Left footed", "21": "Other body part",
    "22": "Regular play", "23": "Fast break", "24": "Set piece", "29": "Assisted",
    "31": "Yellow Card", "33": "Red Card", "56": "Zone", "59": "Jersey Number",
    "73": "Left side", "75": "Right side", "98": "Pitch X", "99": "Pitch Y",
    "102": "Goal Mouth Y", "103": "Goal Mouth Z", "107": "Throw In", "108": "Volley",
    "117": "Lob", "137": "Keeper Saved", "138": "Hit Woodwork", 
    "140": "Pass End X", "141": "Pass End Y", "154": "Intentional Assist",
    "155": "Chipped", "156": "Lay-off", "168": "Flick-on", "195": "Pull back",
    "196": "Switch of play", "210": "Assist", "212": "Length", "213": "Angle",
    "214": "Big chance", "238": "Fair Play", "241": "Indirect", "262": "Back heel",
    "279": "Kick Off", "285": "Defensive", "286": "Offensive", "301": "Shot from cross",
    "318": "Expected Assist (xA)", "321": "Expected Goal (xG)", "322": "xG on Target",
    "326": "Shot Pressure", "386": "Driven cross", "387": "Floated cross",
    "393": "Tactical Foul", "487": "Panenka"
}

# --- 3. HJÆLPEFUNKTIONER TIL STREAMLIT ---
def get_event_name(event_id):
    """Returnerer læsbart navn for et Event ID"""
    return OPTA_EVENT_TYPES.get(str(event_id), f"Unknown ({event_id})")

def get_qualifier_name(qual_id):
    """Returnerer læsbart navn for et Qualifier ID"""
    return OPTA_QUALIFIERS.get(str(qual_id), f"Qual {qual_id}")

def is_offensive_event(event_id):
    """Tjekker om eventet er offensivt (Skud, mål, assist)"""
    offensive_ids = ["13", "14", "15", "16", "AS", "G", "PG"]
    return str(event_id) in offensive_ids
