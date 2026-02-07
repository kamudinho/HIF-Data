import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch

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

    # --- 2. FORMATIONER (Koordinater 0-120 vertikal, 0-80 horisontal) ---
    form_valg = st.sidebar.radio("Vælg Formation:", ["4-3-3", "3-5-2", "4-4-2"])

    if form_valg == "4-3-3":
        # Format: { POS_NR: (x, y, Label) }
        pos_config = {
            1: (10, 40, 'MM'), 
            5: (35, 10, 'VB'), 4: (30, 28, 'VCB'), 3: (30, 52, 'HCB'), 2: (35, 70, 'HB'),
            6: (55, 40, 'DM'), 8: (75, 25, 'VCM'), 10: (75, 55, 'HCM'),
            11: (100, 10, 'VW'), 9: (105, 40, 'ANG'), 7: (100, 70, 'HW')
        }
    elif form_valg == "3-5-2":
        pos_config = {
            1: (10, 40, 'MM'), 
            4: (30, 20, 'VCB'), 3: (25, 40, 'CB'), 2: (30, 60, 'HCB'),
            5: (55, 10, 'VWB'), 6: (50, 40, 'DM'), 7: (55, 70, 'HWB'), 
            8: (75, 25, 'CM'), 10: (75, 55, 'CM'),
            11: (105, 30, 'ANG'), 9: (105, 50, 'ANG')
        }
    else: # 4-4-2
        pos_config = {
            1: (10, 40, 'MM'), 
            5: (35, 10, 'VB'), 4: (30, 28, 'VCB'), 3: (30, 52, 'HCB'), 2: (35, 70, 'HB'),
            11: (65, 10, 'VM'), 6: (60, 30, 'CM'), 8: (60, 50, 'CM'), 7: (65, 70, 'HM'),
            9: (105, 30, 'ANG'), 10: (105, 50, 'ANG')
        }

    # --- 3. TEGN BANEN ---
    pitch = VerticalPitch(pitch_type='statsbomb', pitch_color='#224422', line_color='#eeeeee', goal_type='box')
    fig, ax = pitch.draw(figsize=(10, 14))

    # --- 4. INDSÆT SPILLERE ---
    for pos_num, coords in pos_config.items():
        y_pos, x_pos, label = coords
        
        # Filtrer spillere og sorter efter PRIOR (A, B, C)
        spillere_paa_pos = df_squad[df_squad['POS'] == pos_num].sort_values('PRIOR')
        
        # Lav tekst-blok for spillerne
        if not spillere_paa_pos.empty:
            spiller_liste = []
            for _, p in spillere_paa_pos.iterrows():
                navn = p.get('NAVN', f"{p.get('FIRSTNAME','')} {p.get('LASTNAME','')}")
                prior = p['PRIOR'] if p['PRIOR'] != 'NAN' else '-'
                spiller_liste.append(f"{prior}: {navn}")
            
            samlet_tekst = "\n".join(spiller_liste)
            
            # Tegn en boks bag teksten
            ax.text(x_pos, y_pos, f" {label} ", size=12, fontweight='bold', color="white",
                    va='bottom', ha='center', bbox=dict(facecolor='#cc0000', edgecolor='white', boxstyle='round,pad=0.3'))
            
            ax.text(x_pos, y_pos - 2, samlet_tekst, size=9, color="black",
                    va='top', ha='center', fontweight='bold',
                    bbox=dict(facecolor='white', edgecolor='#cc0000', alpha=0.9, boxstyle='round,pad=0.5'))

    st.pyplot(fig)

    if st.button("🖨️ Gem overblik"):
        st.write("Højreklik på billedet og vælg 'Gem billede som...' for at gemme banen.")
