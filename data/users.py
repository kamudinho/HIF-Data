def get_role_permissions():
    """Definerer hvad hver rolle som standard har adgang til."""
    return {
        "admin": "ALL",  # Admin har adgang til alt
        
        "Analytiker": [
            "HVIDOVRE IF", "Forside",
            "HOLDANALYSE", "Modstanderanalyse", "Kampoversigt", "Kampudvikling", "Afslutninger", "Målsekvenser", "Grafer",
            "SPILLERANALYSE": ["SPILLERANALYSE", "Spiller-stats", "Spilleraktioner", "Spiller-profil", "Spilleroversigt", "Spillerprofil"],
            "SCOUTING", "Scoutrapport", "Database", "Emnedatabase", "Sammenligning", "Top10-scouting", "Opret emne",
            "TILPASNING", "Spillerdata", "Spiller-score", "Standardsituationer",
            "PROFIL" 
        ],
        
        "manager": [
            "HVIDOVRE IF", "HOLDANALYSE", "SPILLERANALYSE", "TRUPPEN",  
            "HIF ANALYSE", "BETINIA LIGAEN", "SCOUTING", "Opgaver",  
            "Scoutrapport", "Database", "Emnedatabase", "Sammenligning",  
            "Top10-scouting", "Opret emne", "PROFIL"
        ],
        
        "coach": [
            "HVIDOVRE IF", "HOLDANALYSE", "SPILLERANALYSE", "TRUPPEN",  
            "HIF ANALYSE", "BETINIA LIGAEN", "SCOUTING", "Opgaver",  
            "Scoutrapport", "Database", "Sammenligning", "Top10-scouting", "PROFIL"
            # Bemærk: "Emnedatabase" og "Opret emne" er fjernet her
        ],
        
        "chefscout": [
            "SCOUTING", "Opgaver", "Scoutrapport", "Database",  
            "Emnedatabase", "Sammenligning", "Top10-scouting", "Opret emne", "PROFIL"
        ],
        
        "scout": [
            "SCOUTING", "Opgaver", "Scoutrapport", "Top10-scouting", "PROFIL"
            # Kun det mest nødvendige for almindelige scouts
        ]
    }

def get_users():
    return {
        "kasper": {
            "pass": "kasper1234", 
            "role": "admin"
        },
        "ceo": {
            "pass": "ceo1234", 
            "role": "Analytiker"
        },
        "TA": {
            "pass": "TA5270", 
            "role": "Analytiker"
        },
        "mr": {
            "pass": "Retov2650", 
            "role": "manager"
        },
        "kd": {
            "pass": "Daugaard2650", 
            "role": "coach"
        },
        "kasper-scout": {
            "pass": "Scout1234", 
            "role": "scout"
        },
        "mn": {
            "pass": "MN1234", 
            "role": "scout"
        }
    }
