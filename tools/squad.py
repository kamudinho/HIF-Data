import streamlit as st
import pandas as pd
from mplsoccer import Pitch
from datetime import datetime

def vis_side(df):
    st.title("Hvidovre IF - Taktisk Trupoverblik")

    if df is None:
        st.error("Ingen data fundet.")
        return

    # --- 1. DATAVASK & KONTRAKT-FARVER ---
    df_squad = df.copy()
    df_squad.columns = [str(c).strip().upper() for c in df_squad.columns]

    # Beregn restdage
    if 'CONTRACT' in df_squad.columns:
        df_squad['CONTRACT'] = pd.to_datetime(df_squad['CONTRACT'], errors='coerce')
        idag = datetime.now()
        df_squad['DAYS_LEFT'] = (df_squad['CONTRACT'] - idag).dt.days
    else:
        df_squad['DAYS_LEFT'] = 999 # Default hvis ingen dato

    def get_bg_color(days):
        if pd.isna(days): return '#ffffff' # Hvid (Ingen data)
        if days < 182: return '#ff4b4b'    # Rød
        if days <= 365: return '#fffd8d'   # Gul
        return '#90ee90'                  # Grøn (Over 365 dage)

    # --- 2. FORMATIONER (X=0-120, Y=0-80) ---
    form_valg = st.sidebar.radio("Vælg Formation:", ["4-3-3", "3-5-2", "4-4-2"])

    if form_valg == "4-3-3":
        pos_config = {
            1: (8, 40, 'MM'), 5: (30, 70, 'VB'), 4: (25, 48, 'VCB'), 3: (25, 32, 'HCB'), 2: (30, 10, 'HB'),
            6: (50, 40, 'DM'), 8: (70, 55, 'VCM'), 10: (70, 25, 'HCM'),
            11: (100, 70, 'VW'), 9: (108, 40, 'ANG'), 7: (100, 10, 'HW')
        }
    elif form_valg == "3-5-2":
        pos_config = {
            1: (8, 40, 'MM'), 4: (25, 55, 'VCB'), 3: (22, 40, 'CB'), 2: (25, 25, 'HCB'),
            5: (50, 72, 'VWB'), 6: (45, 40, 'DM'), 7: (50, 8, 'HWB'), 
            8: (75, 55, 'CM'), 10: (75, 25, 'CM'),
            11: (108, 50, 'ANG'), 9: (108, 30, 'ANG')
        }
    else: # 4-4-2
        pos_config = {
            1: (8, 40, 'MM'), 5: (30, 70, 'VB'), 4: (25, 48, 'VCB'), 3: (25, 32, 'HCB'), 2: (30, 10, 'HB'),
            11: (65, 72, 'VM'), 6: (60, 48, 'CM'), 8: (60, 32, 'CM'), 7: (65, 8, 'HM'),
            9: (108, 50, 'ANG'), 10: (108, 30, 'ANG')
        }

    # --- 3. TEGN BANEN ---
    pitch = Pitch(pitch_type='statsbomb', pitch_color='#1e3d1e', line_color='#ffffff', goal_type='box')
    fig, ax = pitch.draw(figsize=(12, 9))

    # --- 4. INDSÆT SPILLERE MED FARVET BAGGRUND ---
    for pos_num, coords in pos_config.items():
        x_pos, y_pos, label = coords
        
        spillere_paa_pos = df_squad[df_squad['POS'] == pos_num].sort_values('PRIOR')
        
        if not spillere_paa_pos.empty:
            # Tegn Position Label (Overskrift)
            ax.text(x_pos, y_pos + 5, label, size=9, fontweight='bold', color="white",
                    va='center', ha='center', bbox=dict(facecolor='#111111', edgecolor='white', boxstyle='round,pad=0.3'))
            
            # Tegn hver spiller for sig for at styre baggrundsfarven
            offset = 0
            for _, p in spillere_paa_pos.iterrows():
                navn = p.get('NAVN', f"{p.get('FIRSTNAME','')} {p.get('LASTNAME','')}")
                bg_color = get_bg_color(p['DAYS_LEFT'])
                
                ax.text(x_pos, y_pos - offset, navn, size=8, color="black",
                        va='center', ha='center', fontweight='bold',
                        bbox=dict(facecolor=bg_color, edgecolor='black', linewidth=0.5, boxstyle='round,pad=0.4'))
                offset += 4.5 # Afstand til næste spiller i rækken

    st.pyplot(fig)

    st.markdown("""
    **Kontraktstatus (Baggrundsfarve):** 🟥 < 182 dage | 🟨 183-365 dage | 🟩 > 365 dage
    """)
