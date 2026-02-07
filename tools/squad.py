import streamlit as st
import pandas as pd
from mplsoccer import Pitch

def vis_side(df):
    st.title("Hvidovre IF - Taktisk Trupoverblik")

    if df is None:
        st.error("Ingen data fundet.")
        return

    # --- 1. DATAVASK ---
    df_squad = df.copy()
    df_squad.columns = [str(c).strip().upper() for c in df_squad.columns]
    df_squad['POS'] = pd.to_numeric(df_squad['POS'], errors='coerce')
    df_squad['PRIOR'] = df_squad.get('PRIOR', '-').astype(str).str.strip().str.upper()

    # --- 2. FORMATIONER (Optimerede X,Y for at give plads til de store bokse) ---
    form_valg = st.sidebar.radio("Vælg Formation:", ["4-3-3", "3-5-2"])

    if form_valg == "4-3-3":
        pos_config = {
            1: (10, 40, 'MM'), 
            5: (35, 75, 'VB'), 4: (30, 50, 'VCB'), 3: (30, 30, 'HCB'), 2: (35, 5, 'HB'),
            6: (55, 40, 'DM'), 8: (75, 60, 'VCM'), 10: (75, 20, 'HCM'),
            11: (100, 75, 'VW'), 9: (112, 40, 'ANG'), 7: (100, 5, 'HW')
        }
    else: # 3-5-2
        pos_config = {
            1: (10, 40, 'MM'), 
            4: (32, 58, 'VCB'), 3: (28, 40, 'CB'), 2: (32, 22, 'HCB'),
            5: (58, 76, 'VWB'), 6: (50, 40, 'DM'), 7: (58, 4, 'HWB'), 
            8: (82, 58, 'CM'), 10: (82, 22, 'CM'),
            11: (110, 55, 'ANG'), 9: (110, 25, 'ANG')
        }

    # --- 3. TEGN BANEN ---
    pitch = Pitch(pitch_type='statsbomb', pitch_color='#1e331e', line_color='#eeeeee')
    fig, ax = pitch.draw(figsize=(14, 10))

    # --- 4. INDSÆT SPILLERE (Design fra image_29c50c.png) ---
    for pos_num, coords in pos_config.items():
        x_pos, y_pos, label = coords
        spillere = df_squad[df_squad['POS'] == pos_num].sort_values('PRIOR')
        
        if not spillere.empty:
            # Saml spillertekst (f.eks. "A: Navn\nB: Navn")
            spiller_liste = [f"{p['PRIOR']}: {p.get('NAVN', f'{p.get('FIRSTNAME','')} {p.get('LASTNAME','')}')}" 
                            for _, p in spillere.iterrows()]
            samlet_tekst = "\n".join(spiller_liste)
            
            # A. DEN HVIDE BOKS (Navne)
            # Vi tegner denne først så den ligger nederst
            t_navne = ax.text(x_pos, y_pos, samlet_tekst, size=8, color="black",
                             va='top', ha='center', fontweight='bold',
                             bbox=dict(facecolor='white', edgecolor='#cc0000', 
                                       boxstyle='round,pad=0.5', linewidth=2))
            
            # B. DEN RØDE BOKS (Position - f.eks. "HWB")
            # Vi placerer den præcis i toppen af den hvide boks
            ax.text(x_pos, y_pos, f"{label}", size=9, color="white",
                    va='center', ha='center', fontweight='bold',
                    bbox=dict(facecolor='#cc0000', edgecolor='white', 
                              boxstyle='round,pad=0.2', linewidth=1))

    st.pyplot(fig)
