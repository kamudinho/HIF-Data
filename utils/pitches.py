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
