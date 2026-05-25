# data/utils/stattype_map.py

STAT_TYPE_MAP = {
    # Offensiv
    "goals": "Mål",
    "goalAssist": "Assists",
    "totalScoringAtt": "Afslutninger",
    "ontargetScoringAtt": "Skud på mål",
    "shotOffTarget": "Skud forbi mål",
    "blockedScoringAtt": "Blokerede afslutninger",
    "expectedGoals": "xG",
    "penaltyWon": "Straffespark fremprovokeret",
    "subsGoals": "Mål af indskiftere", # TILFØJET
    
    # Afleveringer & Spilopbygning
    "totalPass": "Afleveringer",
    "accuratePass": "Succesfulde afleveringer",
    "possessionPercentage": "Boldbesiddelse %",
    "totalThrows": "Indkast",
    "goalKicks": "Målspark",
    "cornerTaken": "Hjørnespark",
    "wonCorners": "Hjørnespark",
    "lostCorners": "Hjørnespark, mod",
    "formationUsed": "Formation", # TILFØJET
    
    # Defensiv
    "totalTackle": "Tacklinger",
    "wonTackle": "Tacklinger vundet",
    "totalClearance": "Clearinger",
    "outfielderBlock": "Blokeringer (markspiller)",
    "totalOffside": "Offside",
    "fkFoulWon": "Frispark vundet",
    "fkFoulLost": "Frispark begået",
    
    # Målmand & Disciplin
    "saves": "Redninger",
    "goalsConceded": "Mål lukket ind",
    "cleanSheet": "Clean sheets", # TILFØJET
    "penaltySave": "Straffespark reddet",
    "penaltyFaced": "Straffespark imod",
    "penaltyConceded": "Straffespark begået",
    "penGoalsConceded": "Mål på straffe imod", # TILFØJET
    "totalYellowCard": "Gule kort",
    "totalRedCard": "Røde kort", # TILFØJET
    "subsMade": "Udskiftninger foretaget"
}
