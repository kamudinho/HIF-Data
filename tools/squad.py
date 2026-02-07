import streamlit as st
import pandas as pd
from mplsoccer import Pitch
from datetime import datetime

def vis_side(df):

    if df is None:
        st.error("Ingen data fundet.")
        return

    # --- 1. DATA-PROCESSERING ---
    df_squad = df.copy()
    df_squad.columns = [str(c).strip().upper() for c in df_squad.columns]
    df_squad['POS'] = pd.to_numeric(df_squad['POS'], errors='coerce')
    df_squad['PRIOR'] = df_squad.get('PRIOR', '-').astype(str).str.strip().str.upper()

    # Håndtering af kontrakt-datoer
    idag = datetime.now()
    if 'CONTRACT' in df_squad.columns:
        # Konverterer kontrakt til dato - antager formatet i din CSV er standard
        df_squad['CONTRACT'] = pd.to_datetime(df_squad['CONTRACT'], dayfirst=True, errors='coerce')
        df_squad['DAYS_LEFT'] = (df_squad['CONTRACT'] - idag).dt.days
    else:
        df_squad['DAYS_LEFT'] = 999 

    def get_status_color(days):
        if pd.isna(days): return 'white'
        if days < 182: return '#ff4b4b'   # Rød (< 6 måneder)
        if days <= 365: return '#fffd8d'  # Gul (6-12 måneder)
        return 'white'                   # Hvid (> 1 år)

    # --- 2. FORMATIONER ---
    form_valg = st.sidebar.radio("Vælg Formation:", ["4-3-3", "3-5-2"])

    if form_valg == "4-3-3":
        pos_config = {
            1: (10, 43, 'MM'), 
            5: (35, 10, 'VB'), 4: (30, 30, 'VCB'), 3: (30, 55, 'HCB'), 2: (35, 75, 'HB'),
            6: (50, 43, 'DM'), 8: (60, 30, 'VCM'), 10: (60, 60, 'HCM'),
            11: (80, 15, 'VW'), 9: (90, 44, 'ANG'), 7: (80, 65, 'HW')
        }
    else: # 3-5-2
        pos_config = {
            1: (10, 43, 'MM'), 
            4: (33, 25, 'VCB'), 3: (30, 43, 'CB'), 2: (33, 65, 'HCB'),
            5: (50, 8, 'VWB'), 6: (50, 43, 'DM'), 7: (50, 75, 'HWB'), 
            8: (60, 30, 'CM'), 10: (60, 60, 'CM'),
            11: (90, 30, 'ANG'), 9: (90, 55, 'ANG')
        }

    # --- 3. TEGN BANEN ---
    pitch = Pitch(pitch_type='statsbomb', pitch_color='#ffffff', line_color='#000000')
    fig, ax = pitch.draw(figsize=(12, 8))

    # --- 4. INDSÆT POSITIONER OG TABELLER ---
    for pos_num, coords in pos_config.items():
        x_pos, y_pos, label = coords
        # Sorterer efter PRIOR, men viser det ikke
        spillere = df_squad[df_squad['POS'] == pos_num].sort_values('PRIOR')
        
        if not spillere.empty:
            # A. POSITION LABEL
            ax.text(x_pos, y_pos - 4.6, f" {label} ", size=10, color="white",
                    va='center', ha='center', fontweight='bold',
                    bbox=dict(facecolor='#cc0000', edgecolor='white', 
                              boxstyle='round,pad=0.2', linewidth=1))

            # B. SPILLER-TABEL
            for i, (_, p) in enumerate(spillere.iterrows()):
                # Henter kun navnet
                navn = p.get('NAVN', f"{p.get('FIRSTNAME','')} {p.get('LASTNAME','')}")
                
                # Farvelogik baseret på kontrakt
                bg_color = get_status_color(p['DAYS_LEFT'])
                
                # Tekst justeret til venstre med fast bredde (25 passer til lange navne)
                visnings_tekst = f" {navn} ".ljust(25)
                
                y_row = (y_pos - 2.1) + (i * 2.1)
                
                ax.text(x_pos, y_row, visnings_tekst, size=8.5, color="black",
                        va='top', ha='center', fontweight='light', family='monospace',
                        bbox=dict(facecolor=bg_color, edgecolor='#000000', 
                                  boxstyle='square,pad=0.1', linewidth=0.5, alpha=1.0))

    st.pyplot(fig)
