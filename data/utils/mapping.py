# data/utils/mapping.py

# --- 1. SPORTLIG OPTA EVENT TYPE MAPPING ---
# Vi har fjernet alt administrativt støj og beholdt kun det, der sker på banen.
OPTA_EVENT_TYPES = {
    "1": "Pasning",
    "2": "Offside Pass",
    "3": "Dribling",
    "4": "Frispark vundet",
    "6": "Hjørnespark",
    "7": "Tackling",
    "8": "Interception",
    "10": "Redning",
    "11": "Felt-indgreb (Claim)",
    "12": "Clearing",
    "13": "Skud forbi",
    "14": "Stolpeskud",
    "15": "Skud reddet",
    "16": "Mål",
    "17": "Kort",
    "18": "Udskiftet",
    "19": "Indskiftet",
    "41": "Boksning (Keeper)",
    "44": "Luftduel",
    "49": "Erobring",
    "50": "Boldtab",
    "51": "Personlig fejl",
    "58": "Skud imod",
    "60": "Stor chance brændt",
    "72": "Caught Offside",
    "74": "Blokeret aflevering",
    "AS": "Assist",
    "G": "Goal",
    "OG": "Selvmål",
    "RC": "Rødt kort",
    "YC": "Gult kort"
}

# --- 2. DE AFGØRENDE QUALIFIERS ---
# Disse bruges til at give pasninger og skud deres specifikke karakter.
OPTA_QUALIFIERS = {
    "1": "Lang aflevering", "2": "Indlæg", "3": "Aflevering (Hoved)", "4": "Stikning", 
    "9": "Straffespark", "14": "Sidste mand", "15": "Hovedstød", "23": "Kontra",
    "89": "1 mod 1", "101": "Reddet på stregen", "107": "Indkast", "124": "Målspark",
    "138": "Stolpe/Overligger", "154": "Bevidst assist", "155": "Chip", 
    "156": "Lay-off", "168": "Flick-on", "195": "Pull back", "196": "Sideskift",
    "210": "Assist/Key Pass", "214": "Stor chance", "321": "xG"
}

# --- 3. CORE LOGIK & FILTRERING ---
# Liste over ID'er der må passere ind i appen.
CORE_GAME_EVENTS = list(OPTA_EVENT_TYPES.keys())

def get_event_name(event_id):
    """Returnerer det rå navn fra mappingen."""
    return OPTA_EVENT_TYPES.get(str(event_id), f"Ukendt ({event_id})")

def is_offensive_event(event_id):
    """Tjekker om hændelsen er en afslutning (13, 14, 15, 16)."""
    return str(event_id) in ["13", "14", "15", "16"]

def get_action_label(row):
    """
    Hvidovre-appens hjerte: Kategoriserer handlinger baseret på Event + Qualifiers.
    Prioriterer farlighed (Big Chance/Assists) over standardnavne.
    """
    try:
        eid = str(row['EVENT_TYPEID'])
        
        # Filtrér ikke-sportslige hændelser fra
        if eid not in CORE_GAME_EVENTS:
            return None

        # Håndtering af Qualifiers (antager liste eller komma-separeret streng)
        ql = row.get('qual_list', [])
        if isinstance(ql, str):
            ql = ql.split(',')
        ql = [str(q).strip() for q in ql]

        # --- NIVEAU 1: DE AFGØRENDE AKTIONER (Big Chance & Assists) ---
        if "214" in ql:
            return "Stor chance"
        
        # Din vigtige pointe: 210 er en Shot Assist (uanset om der scores)
        if "210" in ql:
            if eid == "16": return "Målgivende assist"
            return "Key Pass (Chance skabt)"

        # --- NIVEAU 2: TAKTISKE DETALJER ---
        if "14" in ql:   return "Afgørende indgreb (Sidste mand)"
        if "4" in ql:    return "Stikning"
        if "195" in ql:  return "Pull back"
        if "196" in ql:  return "Sideskift"
        if "155" in ql:  return "Chippet pasning"

        # --- NIVEAU 3: EVENT SPECIFIK LOGIK ---
        
        # Pasninger
        if eid == "1":
            if "2" in ql:   return "Indlæg"
            if "107" in ql: return "Indkast"
            if "1" in ql:   return "Lang bold"
            return "Pasning"

        # Skudtyper
        if eid in ["13", "14", "15", "16"]:
            suffix = " (Hovedstød)" if "15" in ql else ""
            if eid == "16": return f"MÅL{suffix}"
            if "138" in ql or eid == "14": return f"Skud på stolpe{suffix}"
            if eid == "15": return f"Skud på mål{suffix}"
            return f"Afslutning{suffix}"

        # Defensivt
        if eid == "7":  return "Tackling"
        if eid == "8":  return "Interception"
        if eid == "10": return "Redning"
        if eid == "49": return "Erobring"
        if eid == "12": return "Clearing"
        if eid == "3":  return "Dribling"

        # Fallback
        return OPTA_EVENT_TYPES.get(eid, f"Aktion {eid}")

    except Exception:
        return "Ukendt aktion"

def is_assist(qualifiers_list):
    """Hurtig tjek om en aktion er en assist (ID 210)."""
    return "210" in [str(q) for q in qualifiers_list]
