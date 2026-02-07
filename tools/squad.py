import streamlit as st
import pandas as pd
from mplsoccer import Pitch
from datetime import datetime
import matplotlib.patches as mpatches

def vis_side(df):
    st.title("Hvidovre IF - Strømlinet Trupoverblik")

    if df is None:
        st.error("Ingen data fundet.")
        return

    # --- 1. DATA-STRUKTURERING & KONTRAKT-LOGIK ---
    df_squad = df.copy()
    df_squad.columns = [str(c).strip().upper() for c in df_squad.columns]

    # Beregn restdage til kontraktudløb
    if 'CONTRACT' in df_squad.columns:
        df_squad['CONTRACT'] = pd.to_datetime(df_squad['CONTRACT'], errors='coerce')
        idag = datetime.now()
        df_squad['DAYS_LEFT'] = (df_squad['CONTRACT'] - idag).dt.days
    else:
        df_squad['DAYS_LEFT'] = 999

    def get_bg_color(days):
        if pd.isna(days): return '#ffffff'
        if days < 182: return '#ff4b4b'    # Rød
        if days <= 365: return '#fffd8d'   # Gul
        return '#90ee90'                  # Grøn

    # --- 2. FASTLÅSTE POSITIONER (Strømlinet Layout) ---
    form_valg = st.sidebar.radio("Vælg Formation:", ["4-3-3", "3-5-2"])

    if form_valg == "4-3-3":
        pos_config = {
            1: (12, 40, 'MM'), 5: (35, 70, 'VB'), 4: (32, 48, 'VCB'), 3: (32, 32, 'HCB'), 2: (35, 10, 'HB'),
            6: (55, 40, 'DM'), 8: (78, 55, 'VCM'), 10: (78, 25, 'HCM'),
            11: (102, 70, 'VW'), 9: (110, 40, 'ANG'), 7: (102, 10, 'HW')
        }
    else: # 3-5-2
        pos_config = {
            1: (12, 40, 'MM'), 4: (32, 55, 'VCB'), 3: (30, 40, 'CB'), 2: (32, 25, 'HCB'),
            5: (58, 72, 'VWB'), 6: (52, 40, 'DM'), 7: (58, 8, 'HWB'), 
            8: (82, 55, 'CM'), 10: (82, 25, 'CM'),
            11: (110, 50, 'ANG'), 9: (110, 30, 'ANG')
        }

    # --- 3. TEGN BANEN ---
    pitch = Pitch(pitch_type='statsbomb', pitch_color='#1a331a', line_color='white', goal_type='box')
    fig, ax = pitch.draw(figsize=(14, 10))

    # --- 4. RENDER SPILLERE (Venstrejusteret & Struktureret) ---
    for pos_num, coords in pos_config.items():
        x_pos, y_pos, label = coords
        
        # Hent og sorter spillere (A-kæden øverst)
        spillere = df_squad[df_squad['POS'] == pos_num].sort_values('PRIOR')
        
        if not spillere.empty:
            # A. Positions-overskrift (Hvid label)
            ax.text(x_pos, y_pos + 6, f" {label} ", size=10, fontweight='black', color="black",
                    va='center', ha='center', 
                    bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=0.2'))
            
            # B. Spiller-kasser (Venstrejusteret stak)
            # Vi låser kasserne til en fast bredde ved at bruge 'fixed' padding eller faste x-ankre
            for i, (_, p) in enumerate(spillere.iterrows()):
                navn = p.get('NAVN', f"{p.get('FIRSTNAME','')} {p.get('LASTNAME','')}")
                bg_color = get_bg_color(p['DAYS_LEFT'])
                
                # Lodret afstand (y-offset)
                y_offset = i * 4.5 
                
                # Vi bruger ha='left' og rykker x lidt til venstre for center-punktet
                ax.text(x_pos - 6, y_pos + 3 - y_offset, f" {navn} ", size=8, color="black",
                        va='center', ha='left', fontweight='bold',
                        bbox=dict(facecolor=bg_color, edgecolor='black', linewidth=0.8, boxstyle='square,pad=0.3'))

    # --- 5. STRØMLINET LEGEND ---
    patches = [
        mpatches.Patch(color='#ff4b4b', label='< 182 dage'),
        mpatches.Patch(color='#fffd8d', label='183-365 dage'),
        mpatches.Patch(color='#90ee90', label='> 365 dage')
    ]
    ax.legend(handles=patches, loc='lower center', bbox_to_anchor=(0.5, -0.05), 
              ncol=3, fontsize=10, frameon=False)

    st.pyplot(fig)
