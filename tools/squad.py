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

    # --- 1. DATAVASK & KONTRAKT-BEREGNING ---
    df_squad = df.copy()
    df_squad.columns = [str(c).strip().upper() for c in df_squad.columns]

    if 'CONTRACT' in df_squad.columns:
        df_squad['CONTRACT'] = pd.to_datetime(df_squad['CONTRACT'], dayfirst=True, errors='coerce')
        idag = datetime.now()
        df_squad['DAYS_LEFT'] = (df_squad['CONTRACT'] - idag).dt.days
    else:
        df_squad['DAYS_LEFT'] = 999

    def get_bg_color(days):
        if pd.isna(days): return '#ffffff'
        if days < 182: return '#ff4b4b'    # Rød
        if days <= 365: return '#fffd8d'   # Gul
        return '#90ee90'                  # Grøn

    # --- 2. FORMATIONER (Horisontal: X=0-120, Y=0-80) ---
    form_valg = st.sidebar.radio("Vælg Formation:", ["4-3-3", "3-5-2", "4-4-2"])

    if form_valg == "4-3-3":
        pos_config = {
            1: (10, 40, 'MM'), 
            5: (35, 72, 'VB'), 4: (30, 48, 'VCB'), 3: (30, 32, 'HCB'), 2: (35, 8, 'HB'),
            6: (55, 40, 'DM'), 8: (75, 55, 'VCM'), 10: (75, 25, 'HCM'),
            11: (105, 72, 'VW'), 9: (112, 40, 'ANG'), 7: (105, 8, 'HW')
        }
    elif form_valg == "3-5-2":
        pos_config = {
            1: (10, 40, 'MM'), 
            4: (32, 55, 'VCB'), 3: (28, 40, 'CB'), 2: (32, 25, 'HCB'),
            5: (55, 75, 'VWB'), 6: (50, 40, 'DM'), 7: (55, 5, 'HWB'), 
            8: (80, 55, 'CM'), 10: (80, 25, 'CM'),
            11: (112, 50, 'ANG'), 9: (112, 30, 'ANG')
        }
    else: # 4-4-2
        pos_config = {
            1: (10, 40, 'MM'), 5: (35, 72, 'VB'), 4: (30, 48, 'VCB'), 3: (30, 32, 'HCB'), 2: (35, 8, 'HB'),
            11: (70, 75, 'VM'), 6: (65, 48, 'CM'), 8: (65, 32, 'CM'), 7: (70, 5, 'HM'),
            9: (112, 50, 'ANG'), 10: (112, 30, 'ANG')
        }

    # --- 3. TEGN BANEN ---
    pitch = Pitch(pitch_type='statsbomb', pitch_color='#1e3d1e', line_color='white', goal_type='box')
    fig, ax = pitch.draw(figsize=(13, 9))

    # --- 4. INDSÆT SPILLERE ---
    for pos_num, coords in pos_config.items():
        x_pos, y_pos, label = coords
        spillere = df_squad[df_squad['POS'] == pos_num].sort_values('PRIOR')
        
        if not spillere.empty:
            # Position Label (Øverst)
            ax.text(x_pos, y_pos + 6, label, size=10, fontweight='black', color="black",
                    va='center', ha='center', 
                    bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=0.2'))
            
            # Spiller-tabel (Stakket under label)
            for i, (_, p) in enumerate(spillere.iterrows()):
                navn = p.get('NAVN', f"{p.get('FIRSTNAME','')} {p.get('LASTNAME','')}")
                bg_color = get_bg_color(p['DAYS_LEFT'])
                y_offset = i * 4.2 
                
                # Venstre-justeret tekst i farvede kasser
                ax.text(x_pos - 5, y_pos + 2 - y_offset, f" {navn} ", 
                        size=8, color="black", va='center', ha='left', fontweight='bold',
                        bbox=dict(facecolor=bg_color, edgecolor='black', linewidth=0.5, boxstyle='square,pad=0.3'))

    # --- 5. LEGEND (Kontraktudløb) ---
    patches = [
        mpatches.Patch(color='#ff4b4b', label='Under 182 dage'),
        mpatches.Patch(color='#fffd8d', label='183-365 dage'),
        mpatches.Patch(color='#90ee90', label='Over 365 dage')
    ]
    ax.legend(handles=patches, loc='lower center', bbox_to_anchor=(0.5, -0.05), 
              ncol=3, fontsize=10, frameon=False)

    st.pyplot(fig)
