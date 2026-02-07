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

    # --- 2. FORMATIONER (Korrekt Y-logik: 0 er Top, 80 er Bund) ---
    form_valg = st.sidebar.radio("Vælg Formation:", ["4-3-3", "3-5-2"])

    if form_valg == "4-3-3":
        pos_config = {
            1: (12, 40, 'MM'), 
            5: (35, 10, 'VB'), 4: (30, 28, 'VCB'), 3: (30, 52, 'HCB'), 2: (35, 74, 'HB'),
            6: (55, 40, 'DM'), 8: (78, 22, 'VCM'), 10: (78, 58, 'HCM'),
            11: (105, 10, 'VW'), 9: (112, 40, 'ANG'), 7: (105, 74, 'HW')
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
    pitch = Pitch(pitch_type='statsbomb', pitch_color='#1e331e', line_color='#eeeeee')
    fig, ax = pitch.draw(figsize=(14, 10))

    # --- 4. INDSÆT POSITIONER OG TABELLER (Linje for linje styring) ---
    for pos_num, coords in pos_config.items():
        x_pos, y_pos, label = coords
        spillere = df_squad[df_squad['POS'] == pos_num].sort_values('PRIOR')
        
        if not spillere.empty:
            # A. POSITION LABEL (Øverst)
            ax.text(x_pos, y_pos - 10, f" {label} ", size=10, color="white",
                    va='center', ha='center', fontweight='bold',
                    bbox=dict(facecolor='#cc0000', edgecolor='white', 
                              boxstyle='round,pad=0.2', linewidth=1))

            # B. SPILLER-TABEL (Hver linje er nu sin egen boks)
            for i, (_, p) in enumerate(spillere.iterrows()):
                navn = p.get('NAVN', f"{p.get('FIRSTNAME','')} {p.get('LASTNAME','')}")
                prior = p['PRIOR']
                
                # Logik for baggrundsfarve på den enkelte linje
                if prior == 'A':
                    bg_color = '#e6ffe6'  # En svag grøn for at markere førsteprioritet
                    edge_color = '#006400'
                else:
                    bg_color = 'white'
                    edge_color = '#cc0000'
                
                # Beregn lodret placering (y_pos - 5 er start, derefter rykker vi 3.5 enheder ned pr spiller)
                y_row = (y_pos - 5) + (i * 3.8)
                
                ax.text(x_pos, y_row, f" {prior}: {navn} ", size=8.5, color="black",
                        va='top', ha='center', fontweight='bold',
                        bbox=dict(facecolor=bg_color, edgecolor=edge_color, 
                                  boxstyle='square,pad=0.3', linewidth=1, alpha=1.0))

    st.pyplot(fig)
