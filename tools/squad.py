import streamlit as st
import pandas as pd
from mplsoccer import Pitch

def vis_side(df):

    if df is None:
        st.error("Ingen data fundet.")
        return

    # --- 1. DATAVASK ---
    df_squad = df.copy()
    df_squad.columns = [str(c).strip().upper() for c in df_squad.columns]
    df_squad['POS'] = pd.to_numeric(df_squad['POS'], errors='coerce')
    df_squad['PRIOR'] = df_squad.get('PRIOR', '-').astype(str).str.strip().str.upper()

    # --- 2. FORMATIONER ---
    form_valg = st.sidebar.radio("Vælg Formation:", ["4-3-3", "3-5-2"])

    if form_valg == "4-3-3":
        pos_config = {
            1: (12, 40, 'MM'), 
            5: (35, 15, 'VB'), 4: (30, 30, 'VCB'), 3: (30, 60, 'HCB'), 2: (35, 75, 'HB'),
            6: (48, 40, 'DM'), 8: (60, 22, 'VCM'), 10: (60, 58, 'HCM'),
            11: (80, 15, 'VW'), 9: (100, 40, 'ANG'), 7: (80, 65, 'HW')
        }
    else: # 3-5-2
        pos_config = {
            1: (12, 40, 'MM'), 
            4: (32, 22, 'VCB'), 3: (28, 40, 'CB'), 2: (32, 58, 'HCB'),
            5: (58, 6, 'VWB'), 6: (50, 40, 'DM'), 7: (58, 74, 'HWB'), 
            8: (82, 22, 'CM'), 10: (82, 58, 'CM'),
            11: (112, 25, 'ANG'), 9: (112, 55, 'ANG')
        }

    # --- 3. TEGN BANEN ---
    pitch = Pitch(pitch_type='statsbomb', pitch_color='#ffffff', line_color='#000000')
    fig, ax = pitch.draw(figsize=(12, 8))

    # --- 4. INDSÆT POSITIONER OG TABELLER ---
    for pos_num, coords in pos_config.items():
        x_pos, y_pos, label = coords
        spillere = df_squad[df_squad['POS'] == pos_num].sort_values('PRIOR')
        
        if not spillere.empty:
            # A. POSITION LABEL (Sænket til den gode højde)
            ax.text(x_pos, y_pos - 6, f" {label} ", size=10, color="white",
                    va='center', ha='center', fontweight='bold',
                    bbox=dict(facecolor='#cc0000', edgecolor='white', 
                              boxstyle='round,pad=0.2', linewidth=1))

            # B. SPILLER-TABEL (Tættere rækker)
            for i, (_, p) in enumerate(spillere.iterrows()):
                navn = p.get('NAVN', f"{p.get('FIRSTNAME','')} {p.get('LASTNAME','')}")
                prior = p['PRIOR']
                
                # Farve-markering af Prior A
                bg_color = '#e6ffe6' if prior == 'A' else 'white'
                edge_color = '#006400' if prior == 'A' else '#cc0000'
                
                # y_row beregning med mindre spring (3.2 i stedet for 3.8)
                # Starter lige under positionen
                y_row = (y_pos - 3) + (i * 2.8)
                
                ax.text(x_pos, y_row, f" {prior}: {navn} ", size=8.5, color="black",
                        va='top', ha='center', fontweight='bold',
                        bbox=dict(facecolor=bg_color, edgecolor=edge_color, 
                                  boxstyle='square,pad=0.2', linewidth=1, alpha=1.0))

    st.pyplot(fig)
