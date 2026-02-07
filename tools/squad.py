import streamlit as st
import pandas as pd
from mplsoccer import Pitch
from datetime import datetime
import matplotlib.patches as mpatches

def vis_side(df):
    st.title("Hvidovre IF - Taktisk Trupoverblik")

    if df is None:
        st.error("Ingen data fundet.")
        return

    # --- 1. DATAVASK & KONTRAKT-FARVER ---
    df_squad = df.copy()
    df_squad.columns = [str(c).strip().upper() for c in df_squad.columns]

    if 'CONTRACT' in df_squad.columns:
        df_squad['CONTRACT'] = pd.to_datetime(df_squad['CONTRACT'], errors='coerce')
        idag = datetime.now()
        df_squad['DAYS_LEFT'] = (df_squad['CONTRACT'] - idag).dt.days
    else:
        df_squad['DAYS_LEFT'] = 999

    def get_bg_color(days):
        if pd.isna(days): return '#ffffff' # Hvid
        if days < 182: return '#ff4b4b'    # Rød
        if days <= 365: return '#fffd8d'   # Gul
        return '#90ee90'                  # Grøn

    # --- 2. FORMATIONER (X=0-120, Y=0-80) ---
    form_valg = st.sidebar.radio("Vælg Formation:", ["4-3-3", "3-5-2", "4-4-2"])

    if form_valg == "4-3-3":
        pos_config = {
            1: (8, 40, 'MM'), 5: (30, 72, 'VB'), 4: (25, 48, 'VCB'), 3: (25, 32, 'HCB'), 2: (30, 8, 'HB'),
            6: (50, 40, 'DM'), 8: (70, 55, 'VCM'), 10: (70, 25, 'HCM'),
            11: (100, 72, 'VW'), 9: (108, 40, 'ANG'), 7: (100, 8, 'HW')
        }
    elif form_valg == "3-5-2":
        pos_config = {
            1: (8, 40, 'MM'), 4: (25, 55, 'VCB'), 3: (22, 40, 'CB'), 2: (25, 25, 'HCB'),
            5: (50, 75, 'VWB'), 6: (45, 40, 'DM'), 7: (50, 5, 'HWB'), 
            8: (75, 55, 'CM'), 10: (75, 25, 'CM'),
            11: (108, 50, 'ANG'), 9: (108, 30, 'ANG')
        }
    else: # 4-4-2
        pos_config = {
            1: (8, 40, 'MM'), 5: (30, 72, 'VB'), 4: (25, 48, 'VCB'), 3: (25, 32, 'HCB'), 2: (30, 8, 'HB'),
            11: (65, 75, 'VM'), 6: (60, 48, 'CM'), 8: (60, 32, 'CM'), 7: (65, 5, 'HM'),
            9: (108, 50, 'ANG'), 10: (108, 30, 'ANG')
        }

    # --- 3. TEGN BANEN ---
    pitch = Pitch(pitch_type='statsbomb', pitch_color='#1e3d1e', line_color='#ffffff', goal_type='box')
    fig, ax = pitch.draw(figsize=(12, 9))

    # --- 4. INDSÆT SPILLERE ---
    for pos_num, coords in pos_config.items():
        x_pos, y_pos, label = coords
        
        spillere_paa_pos = df_squad[df_squad['POS'] == pos_num].sort_values('PRIOR')
        
        if not spillere_paa_pos.empty:
            # 1. Tegn Position Label ØVERST
            ax.text(x_pos, y_pos + 6, label, size=9, fontweight='bold', color="white",
                    va='center', ha='center', bbox=dict(facecolor='#111111', edgecolor='white', boxstyle='round,pad=0.3'))
            
            # 2. Tegn spillere under - VENSTRE-JUSTERET tekst
            offset = 0
            for _, p in spillere_paa_pos.iterrows():
                navn = p.get('NAVN', f"{p.get('FIRSTNAME','')} {p.get('LASTNAME','')}")
                bg_color = get_bg_color(p['DAYS_LEFT'])
                
                # Vi bruger ha='left' for venstre-justering. 
                # x_pos justeres lidt til venstre (-4) så boksen centrerer pænt under label
                ax.text(x_pos - 4, y_pos - offset, f" {navn} ", size=8, color="black",
                        va='center', ha='left', fontweight='bold',
                        bbox=dict(facecolor=bg_color, edgecolor='black', linewidth=0.5, boxstyle='square,pad=0.3'))
                offset += 4.2

    # --- 5. LEGENDS (Manuelt tegnet på figuren) ---
    red_patch = mpatches.Patch(color='#ff4b4b', label='< 182 dage')
    yellow_patch = mpatches.Patch(color='#fffd8d', label='183-365 dage')
    green_patch = mpatches.Patch(color='#90ee90', label='> 365 dage')
    
    ax.legend(handles=[red_patch, yellow_patch, green_patch], 
              loc='lower left', bbox_to_anchor=(0, -0.1), 
              ncol=3, fontsize=9, frameon=False)

    st.pyplot(fig)

    if st.button("🖨️ Gem overblik"):
        st.write("Højreklik på billedet og vælg 'Gem billede som...'")
