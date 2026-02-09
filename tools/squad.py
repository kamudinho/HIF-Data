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
        df_squad['CONTRACT'] = pd.to_datetime(df_squad['CONTRACT'], dayfirst=True, errors='coerce')
        df_squad['DAYS_LEFT'] = (df_squad['CONTRACT'] - idag).dt.days
    else:
        df_squad['DAYS_LEFT'] = 999 

    def get_status_color(row):
        # Tjek først PRIOR for 'L' (Leje)
        if row['PRIOR'] == 'L':
            return '#d3d3d3'  # Grå
        
        days = row['DAYS_LEFT']
        if pd.isna(days): return 'white'
        if days < 182: return '#ff4b4b'   # Rød (< 6 måneder)
        if days <= 365: return '#fffd8d'  # Gul (6-12 måneder)
        return 'white'                   # Hvid (> 1 år)

    # --- 2. FORMATIONER ---
    form_valg = st.sidebar.radio("Vælg Formation:", ["3-4-3", "4-3-3", "3-5-2"])

    if form_valg == "3-4-3":
        pos_config = {
            1: (10, 43, 'MM'), 
            4: (33, 25, 'VCB'), 3: (33, 43, 'CB'), 2: (33, 65, 'HCB'),
            5: (55, 8, 'VWB'), 6: (55, 33, 'DM'), 8: (55, 53, 'DM'), 7: (55, 78, 'HWB'), 
            11: (85, 15, 'VW'), 9: (90, 43, 'ANG'), 10: (85, 70, 'HW')
        }
    elif form_valg == "4-3-3":
        pos_config = {
            1: (10, 43, 'MM'), 
            5: (35, 10, 'VB'), 4: (33, 30, 'VCB'), 3: (33, 55, 'HCB'), 2: (35, 75, 'HB'),
            6: (55, 43, 'DM'), 8: (65, 30, 'VCM'), 10: (65, 60, 'HCM'),
            11: (80, 15, 'VW'), 9: (90, 44, 'ANG'), 7: (80, 70, 'HW')
        }
    else: # 3-5-2
        pos_config = {
            1: (10, 43, 'MM'), 
            4: (33, 25, 'VCB'), 3: (33, 43, 'CB'), 2: (33, 65, 'HCB'),
            5: (55, 8, 'VWB'), 6: (55, 43, 'DM'), 7: (55, 75, 'HWB'), 
            8: (65, 30, 'CM'), 10: (65, 60, 'CM'),
            11: (95, 30, 'ANG'), 9: (95, 55, 'ANG')
        }

    # --- 3. TEGN BANEN ---
    pitch = Pitch(pitch_type='statsbomb', pitch_color='#ffffff', line_color='#000000')
    fig, ax = pitch.draw(figsize=(12, 8))

    # --- 4. INDSÆT LEGEND ØVERST ---
    legend_y = 2
    legend_items = [
        ("#ff4b4b", "Udløb < 6 mdr"),
        ("#fffd8d", "Udløb 6-12 mdr"),
        ("#d3d3d3", "Leje / Udlejet")
    ]
    
    for i, (color, text) in enumerate(legend_items):
        # Vi spreder dem ud over midten af banen (x fra 25 til 75)
        x_pos = 30 + (i * 20)
        ax.text(x_pos, legend_y, f"  {text}  ", size=8, color="black",
                va='top', ha='center', family='monospace', fontweight='bold',
                bbox=dict(facecolor=color, edgecolor='black', boxstyle='square,pad=0.3', linewidth=0.5))

    # --- 5. INDSÆT POSITIONER OG TABELLER ---
    for pos_num, coords in pos_config.items():
        x_pos, y_pos, label = coords if len(coords) == 3 else (coords[0], coords[1], "N/A")
        
        spillere = df_squad[df_squad['POS'] == pos_num].sort_values('PRIOR')
        
        if not spillere.empty:
            # A. POSITION LABEL
            ax.text(x_pos, y_pos - 4.6, f" {label} ", size=10, color="white",
                    va='center', ha='center', fontweight='bold',
                    bbox=dict(facecolor='#cc0000', edgecolor='white', 
                              boxstyle='round,pad=0.2', linewidth=1))

            # B. SPILLER-TABEL
            for i, (_, p) in enumerate(spillere.iterrows()):
                navn = p.get('NAVN', f"{p.get('FIRSTNAME','')} {p.get('LASTNAME','')}")
                bg_color = get_status_color(p)
                visnings_tekst = f" {navn} ".ljust(25)
                
                y_row = (y_pos - 2.1) + (i * 2.1)
                
                ax.text(x_pos, y_row, visnings_tekst, size=8.5, color="black",
                        va='top', ha='center', fontweight='light', family='monospace',
                        bbox=dict(facecolor=bg_color, edgecolor='#000000', 
                                  boxstyle='square,pad=0.1', linewidth=0.5, alpha=1.0))

    st.pyplot(fig)
