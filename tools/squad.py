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

    # --- 2. FORMATIONER (Liggende bane: X=0-120, Y=0-80) ---
    form_valg = st.sidebar.radio("Vælg Formation:", ["4-3-3", "3-5-2", "4-4-2"])

    if form_valg == "4-3-3":
        pos_config = {
            1: (10, 40, 'MM'), 
            5: (35, 72, 'VB'), 4: (30, 48, 'VCB'), 3: (30, 32, 'HCB'), 2: (35, 8, 'HB'),
            6: (55, 40, 'DM'), 8: (75, 55, 'VCM'), 10: (75, 25, 'HCM'),
            11: (100, 72, 'VW'), 9: (108, 40, 'ANG'), 7: (100, 8, 'HW')
        }
    elif form_valg == "3-5-2":
        pos_config = {
            1: (10, 40, 'MM'), 
            4: (30, 55, 'VCB'), 3: (25, 40, 'CB'), 2: (30, 25, 'HCB'),
            5: (55, 72, 'VWB'), 6: (50, 40, 'DM'), 7: (55, 8, 'HWB'), 
            8: (75, 55, 'CM'), 10: (75, 25, 'CM'),
            11: (105, 50, 'ANG'), 9: (105, 30, 'ANG')
        }
    else: # 4-4-2
        pos_config = {
            1: (10, 40, 'MM'), 5: (35, 72, 'VB'), 4: (30, 48, 'VCB'), 3: (30, 32, 'HCB'), 2: (35, 8, 'HB'),
            11: (65, 72, 'VM'), 6: (60, 48, 'CM'), 8: (60, 32, 'CM'), 7: (65, 8, 'HM'),
            9: (105, 50, 'ANG'), 10: (105, 30, 'ANG')
        }

    # --- 3. TEGN BANEN ---
    pitch = Pitch(pitch_type='statsbomb', pitch_color='#224422', line_color='#eeeeee', goal_type='box')
    fig, ax = pitch.draw(figsize=(12, 8))

    # --- 4. INDSÆT SPILLERE ---
    for pos_num, coords in pos_config.items():
        x_pos, y_pos, label = coords
        
        # Filtrer spillere og sorter efter PRIOR (A, B, C)
        spillere_paa_pos = df_squad[df_squad['POS'] == pos_num].sort_values('PRIOR')
        
        if not spillere_paa_pos.empty:
            spiller_liste = []
            for _, p in spillere_paa_pos.iterrows():
                navn = p.get('NAVN', f"{p.get('FIRSTNAME','')} {p.get('LASTNAME','')}")
                prior = p['PRIOR'] if p['PRIOR'] != 'NAN' else '-'
                spiller_liste.append(f"{prior}: {navn}")
            
            samlet_tekst = "\n".join(spiller_liste)
            
            # 1. RØD BOKS MED POSITION (Øverst)
            ax.text(x_pos, y_pos + 4, f" {label} ", size=10, fontweight='bold', color="white",
                    va='bottom', ha='center', 
                    bbox=dict(facecolor='#cc0000', edgecolor='white', boxstyle='round,pad=0.3'))
            
            # 2. HVID BOKS MED NAVNE (Lige nedenunder)
            ax.text(x_pos, y_pos + 3, samlet_tekst, size=8, color="black",
                    va='top', ha='center', fontweight='bold',
                    bbox=dict(facecolor='white', edgecolor='#cc0000', alpha=0.9, boxstyle='round,pad=0.5'))

    st.pyplot(fig)

    if st.button("🖨️ Gem overblik"):
        st.info("Højreklik på billedet og vælg 'Gem billede som...'")
