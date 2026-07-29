from mplsoccer import Pitch, VerticalPitch

def get_pitch(type="staaende"):
    """
    Returnerer en matplotlib fig og ax med den ønskede bane-type (tilpasset 105x68 meter):
    - 'staaende' (Vertikal)
    - 'liggende' (Horisontal)
    - 'halv' (Halv bane til f.eks. skud- og afslutningsanalyser)
    """
    if type == "liggende":
        pitch = Pitch(pitch_type='custom', pitch_length=105, pitch_width=68, 
                      pitch_color='#ffffff', line_color='#cccccc', orientation='horizontal')
        fig, ax = pitch.draw(figsize=(10, 7))
        
    elif type == "halv":
        # Lodret halv bane (fokuseret på den sidste tredjedel / modstanderens felt)
        pitch = VerticalPitch(pitch_type='custom', pitch_length=105, pitch_width=68, 
                              pitch_color='#ffffff', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(8, 10))
        ax.set_ylim(55, 105) # Viser fra midterlinjen og op til modstanderens mål
        
    else:
        # Standard stående fuld bane
        pitch = VerticalPitch(pitch_type='custom', pitch_length=105, pitch_width=68, 
                              pitch_color='#ffffff', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(7, 10))
        
    return pitch, fig, ax

def get_boundaries():
    """
    Returnerer standard zone-definitioner (105x68 m banen).
    """
    P_L, P_W = 105.0, 68.0
    X_MID_L, X_MID_R = (P_W - 18.32) / 2, (P_W + 18.32) / 2
    X_INN_L, X_INN_R = (P_W - 40.2) / 2, (P_W + 40.2) / 2
    Y_GOAL, Y_6YD, Y_PK, Y_18YD, Y_MID = 105.0, 99.5, 94.0, 88.5, 75.0

    return {
        "Zone 1": {"y_min": Y_6YD, "y_max": Y_GOAL, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 2": {"y_min": Y_PK, "y_max": Y_6YD, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 3": {"y_min": Y_18YD, "y_max": Y_PK, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 4A": {"y_min": Y_6YD, "y_max": Y_GOAL, "x_min": X_MID_R, "x_max": X_INN_R},
        "Zone 4B": {"y_min": Y_6YD, "y_max": Y_GOAL, "x_min": X_INN_L, "x_max": X_MID_L},
        "Zone 5A": {"y_min": Y_18YD, "y_max": Y_6YD, "x_min": X_MID_R, "x_max": X_INN_R},
        "Zone 5B": {"y_min": Y_18YD, "y_max": Y_6YD, "x_min": X_INN_L, "x_max": X_MID_L},
        "Zone 6A": {"y_min": Y_18YD, "y_max": Y_GOAL, "x_min": X_INN_R, "x_max": P_W},
        "Zone 6B": {"y_min": Y_18YD, "y_max": Y_GOAL, "x_min": 0, "x_max": X_INN_L},
        "Zone 7C": {"y_min": Y_MID, "y_max": Y_18YD, "x_min": 0, "x_max": X_MID_L},
        "Zone 7B": {"y_min": Y_MID, "y_max": Y_18YD, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 7A": {"y_min": Y_MID, "y_max": Y_18YD, "x_min": X_MID_R, "x_max": P_W},
        "Zone 8":  {"y_min": 0, "y_max": Y_MID, "x_min": 0, "x_max": P_W}
    }
