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

    if 'POS' not in df_squad.columns:
        st.error("Kunne ikke finde kolonnen 'POS'.")
        return

    df_squad['POS'] = pd.to_numeric(df_squad['POS'], errors='coerce')
    df_squad['PRIOR'] = df_squad.get('PRIOR', '-').astype(str).str.strip().str.upper()

    # --- 2. FORMATIONER (Optimerede koordinater for at undgå overlap) ---
    form_valg = st.sidebar.radio("Vælg Formation:", ["4-3-3", "3-5-2"])

    if form_valg == "4-3-3":
        pos_config = {
            1: (10, 40, 'MM'), 
            5: (35, 74, 'VB'), 4: (28, 52, 'VCB'), 3: (28, 28, 'HCB'), 2: (35, 6, 'HB'),
            6: (55, 40, 'DM'), 8: (80, 58, 'VCM'), 10: (80, 22, 'HCM'),
            11: (108, 74, 'VW'), 9: (112, 40, 'ANG'), 7: (108, 6, 'HW')
        }
    else: # 3-5-2
        pos_config = {
            1: (10, 40, 'MM'), 
            4: (30, 58, 'VCB'), 3: (25, 40, 'CB'), 2: (30, 22, 'HCB'),
            5: (58, 75, 'VWB'), 6: (52, 40, 'DM'), 7: (58, 5, 'HWB'), 
            8: (85, 58, 'CM'), 10: (85, 22, 'CM'),
            11: (112, 55, 'ANG'), 9: (112, 25, 'ANG')
        }

    # --- 3. TEGN BANEN ---
    # Vi bruger den mørkegrønne farve fra dine billeder
    pitch = Pitch(pitch_type='statsbomb', pitch_color='#1e331e', line_color='#eeeeee', goal_type='box')
    fig, ax = pitch.draw(figsize=(14, 10))

    # --- 4. INDSÆT SPILLERE (De to hvide bokse med rød kant) ---
    for pos_num, coords in pos_config.items():
        x_pos, y_pos, label = coords
        
        spillere_paa_pos = df_squad[df_squad['POS'] == pos_num].sort_values('PRIOR')
        
        if not spillere_paa_pos.empty:
            spiller_liste = []
            for _, p in spillere_paa_pos.iterrows():
                navn = p.get('NAVN', f"{p.get('FIRSTNAME','')} {p.get('LASTNAME','')}")
                prior = p['PRIOR'] if p['PRIOR'] != 'NAN' else '-'
                spiller_liste.append(f"{prior}: {navn}")
            
            samlet_tekst = "\n".join(spiller_liste)
            
            # 1. POSITION BOKS (Lille hvid boks med rød kant)
            ax.text(x_pos, y_pos + 4, f" {label} ", size=9, fontweight='bold', color="black",
                    va='bottom', ha='center', 
                    bbox=dict(facecolor='white', edgecolor='#cc0000', boxstyle='round,pad=0.2', linewidth=1.5))
            
            # 2. NAVNE BOKS (Større hvid boks med rød kant)
            ax.text(x_pos, y_pos + 3.5, samlet_tekst, size=8, color="black",
                    va='top', ha='center', fontweight='bold',
                    bbox=dict(facecolor='white', edgecolor='#cc0000', alpha=1.0, boxstyle='round,pad=0.4', linewidth=1.5))

    st.pyplot(fig)
