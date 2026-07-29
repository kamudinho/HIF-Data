from mplsoccer import Pitch

def get_pitch(type="stảende"):
    """
    Returnerer en matplotlib fig og ax med den ønskede bane-type:
    - 'staaende' (Standard Opta vertikal)
    - 'liggende' (Horisontal / Landscaped)
    - 'halv' (Halv bane, typisk til nærbilleder / defensive aktioner)
    """
    if type == "liggende":
        # Liggende bane (roteret 90 grader eller med omvendte dimensioner)
        pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD', orientation='horizontal')
        fig, ax = pitch.draw(figsize=(10, 7))
        
    elif type == "halv":
        # Halv bane (fokus på f.eks. egen eller modstanderens banehalvdel, typisk x fra 50 til 100)
        pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD', orientation='horizontal')
        fig, ax = pitch.draw(figsize=(8, 7))
        # Begræns y-aksen/x-aksen til kun at vise den ene halvdel (tilpas evt. efter dine Opta-koordinater)
        ax.set_xlim(50, 100)
        ax.set_ylim(0, 100)
        
    else:
        # Standard stående bane (vertikal)
        pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD', orientation='vertical')
        fig, ax = pitch.draw(figsize=(7, 10))
        
    return pitch, fig, ax
