def get_role_permissions():
    """Definerer hvad hver rolle som standard har adgang til."""
    return {
        "admin": "ALL",  # Admin har adgang til alt
        
        "Analytiker": [
            "HVIDOVRE IF", "HOLDANALYSE", "SPILLERANALYSE", "TRUPPEN", 
            "HIF ANALYSE", "BETINIA LIGAEN", "SCOUTING", "Opgaver", 
            "Scoutrapport", "Database", "Emnedatabase", "Sammenligning", 
            "Top10-scouting", "Opret emne", "Profil"
        ],
        
        "manager": [
            "HVIDOVRE IF", "HOLDANALYSE", "SPILLERANALYSE", "TRUPPEN", 
            "HIF ANALYSE", "BETINIA LIGAEN", "SCOUTING", "Opgaver", 
            "Scoutrapport", "Database", "Emnedatabase", "Sammenligning", 
            "Top10-scouting", "Opret emne", "Profil"
        ],
        
        "coach": [
            "HVIDOVRE IF", "HOLDANALYSE", "SPILLERANALYSE", "TRUPPEN", 
            "HIF ANALYSE", "BETINIA LIGAEN", "SCOUTING", "Opgaver", 
            "Scoutrapport", "Database", "Sammenligning", "Top10-scouting", "Profil"
            # Bemærk: "Emnedatabase" og "Opret emne" er fjernet her
        ],
        
        "chefscout": [
            "SCOUTING", "Opgaver", "Scoutrapport", "Database", 
            "Emnedatabase", "Sammenligning", "Top10-scouting", "Opret emne", "Profil"
        ],
        
        "scout": [
            "SCOUTING", "Opgaver", "Scoutrapport", "Top10-scouting", "Profil"
            # Kun det mest nødvendige for almindelige scouts
        ]
    }
