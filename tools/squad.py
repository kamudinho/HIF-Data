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

    # --- 2. OPTIMEREDE KOORDINATER (Spread for at undgå overlap) ---
    form_valg = st.sidebar.radio("Vælg Formation:", ["4-3-3", "3-5-2"])

    if form_valg == "4-3-3":
        pos_config = {
            1: (10, 40, 'MM'), 
            5: (35, 74, 'VB'), 4: (28, 52, 'VCB'), 3: (28, 28, 'HCB'), 2: (35, 6, 'HB'),
            6: (55, 40, 'DM'), 8: (75, 60, 'VCM'), 10: (75, 20, 'HCM'),
            11: (100, 74, 'VW'), 9: (112, 40, 'ANG'), 7: (100, 6, 'HW')
        }
    else: # 3-5-2
        pos_config = {
            1: (10, 40, 'MM'), 
            4: (30, 60, 'VCB'), 3: (25, 40, 'CB'), 2: (30, 20, 'HCB'),
            5: (58, 75, 'VWB'), 6: (50, 40, 'DM'), 7: (58, 5, 'HWB'), 
            8: (80, 60, 'CM'), 10: (80, 20, 'CM'),
            11: (110, 52, 'ANG'), 9: (110, 28, 'ANG')
        }

    # --- 3. TEGN BANEN ---
    pitch = Pitch(pitch_type='statsbomb', pitch_color='#1e331e', line_color='#eeeeee', goal_type='box')
    fig, ax = pitch.draw(figsize=(14, 10))

    # --- 4. INDSÆT SPILLERE ---
    for pos_num, coords in pos_config.items():
        x_pos, y_pos, label = coords
        
        spillere_paa_pos = df_squad[df_squad['POS'] == pos_num].sort_values('PRIOR')
        
        if not spillere_paa_pos.empty:
            # Vi samler teksten og sikrer, at den ikke er for bred
            spiller_liste = []
            for _, p in spillere_paa_pos.iterrows():
                navn = p.get('NAVN', f"{p.get('FIRSTNAME','')} {p.get('LASTNAME','')}")
                prior = p['PRIOR'] if p['PRIOR'] != 'NAN' else '-'
                spiller_liste.append(f"{prior}: {navn}")
            
            samlet_tekst = "\n".join(spiller_liste)
            
            # POSITION BOKS (Rød top)
            ax.text(x_pos, y_pos + 4.5, f"{label}", size=10, fontweight='bold', color="white",
                    va='bottom', ha='center', zorder=4,
                    bbox=dict(facecolor='#cc0000', edgecolor='white', boxstyle='round,pad=0.3'))
            
            # SPILLER BOKS (Hvid bund)
            # Vi bruger en fast 'va' og 'ha' for at sikre de flugter
            ax.text(x_pos, y_pos + 3.8, samlet_tekst, size=8.5, color="black",
                    va='top', ha='center', fontweight='bold', zorder=3,
                    bbox=dict(facecolor='white', edgecolor='#cc0000', alpha=1.0, 
                              boxstyle='round,pad=0.5', linewidth=1.5))

    st.pyplot(fig)
