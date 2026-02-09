import streamlit as st
import pandas as pd
from mplsoccer import Pitch
from datetime import datetime

def vis_side(df):
    if df is None:
        st.error("Ingen data fundet for truppen.")
        return

    # --- 1. HENT FORMATION FRA SIDEBAR (Hovedfil) ---
    form_valg = st.session_state.get("formation_valg", "3-4-3")

    # --- 2. DATA-PROCESSERING ---
    df_squad = df.copy()
    # Standardiser kolonnenavne
    df_squad.columns = [str(c).strip().upper() for c in df_squad.columns]
    
    # Konvertér POS til tal og PRIOR til tekst
    df_squad['POS'] = pd.to_numeric(df_squad['POS'], errors='coerce')
    df_squad['PRIOR'] = df_squad.get('PRIOR', '-').astype(str).str.strip().str.upper()

    # Beregn kontraktudløb
    idag = datetime.now()
    if 'CONTRACT' in df_squad.columns:
        df_squad['CONTRACT'] = pd.to_datetime(df_squad['CONTRACT'], dayfirst=True, errors='coerce')
        df_squad['DAYS_LEFT'] = (df_squad['CONTRACT'] - idag).dt.days
    else:
        df_squad['DAYS_LEFT'] = 999 

    def get_status_color(row):
        if row['PRIOR'] == 'L':
            return '#d3d3d3' # Grå for leje
        days = row['DAYS_LEFT']
        if pd.isna(days): return 'white'
        if days < 182: return '#ff4b4b' # Rød (< 6 mdr)
        if days <= 365: return '#fffd8d' # Gul (6-12 mdr)
        return 'white'

    # --- 3. KONFIGURATION AF BANE ---
    pitch = Pitch(pitch_type='statsbomb', pitch_color='#ffffff', line_color='#000000')
    fig, ax = pitch.draw(figsize=(14, 9), constrained_layout=True)

    # Forklaring (Legend) i bunden af banen
    legend_y = -4 
    legend_items = [
        ("#ff4b4b", "Udløb < 6 mdr"),
        ("#fffd8d", "Udløb 6-12 mdr"),
        ("#d3d3d3", "Leje / Udlejet (L)")
    ]
    
    for i, (color, text) in enumerate(legend_items):
        x_pos = 1 + (i * 22)
        ax.text(x_pos, legend_y, f"  {text}  ", size=11, color="black",
                va='center', ha='left', family='monospace', fontweight='bold',
                bbox=dict(facecolor=color, edgecolor='black', boxstyle='square,pad=0.4', linewidth=0.5))

    # --- 4. FORMATIONS-LOGIK ---
    if form_valg == "3-4-3":
        pos_config = {
            1: (10, 40, 'MM'), 4: (33, 22, 'VCB'), 3: (33, 40, 'CB'), 2: (33, 58, 'HCB'),
            5: (55, 10, 'VWB'), 6: (55, 30, 'DM'), 8: (55, 50, 'DM'), 7: (55, 70, 'HWB'), 
            11: (85, 15, 'VW'), 9: (105, 40, 'ANG'), 10: (85, 65, 'HW')
        }
    elif form_valg == "4-3-3":
        pos_config = {
            1: (10, 40, 'MM'), 5: (35, 10, 'VB'), 4: (33, 25, 'VCB'), 3: (33, 55, 'HCB'), 2: (35, 70, 'HB'),
            6: (55, 40, 'DM'), 8: (65, 25, 'VCM'), 10: (65, 55, 'HCM'),
            11: (80, 15, 'VW'), 9: (95, 40, 'ANG'), 7: (80, 65, 'HW')
        }
    else: # 3-5-2
        pos_config = {
            1: (10, 40, 'MM'), 4: (33, 22, 'VCB'), 3: (33, 40, 'CB'), 2: (33, 58, 'HCB'),
            5: (55, 10, 'VWB'), 6: (55, 40, 'DM'), 7: (55, 70, 'HWB'), 
            8: (65, 25, 'CM'), 10: (65, 55, 'CM'),
            11: (95, 25, 'ANG'), 9: (95, 55, 'ANG')
        }

    # --- 5. TEGN SPILLERE PÅ BANEN ---
    for pos_num, coords in pos_config.items():
        x_pos, y_pos, label = coords
        # Find spillere til denne position
        spillere_pos = df_squad[df_squad['POS'] == pos_num].sort_values('PRIOR')
        
        if not spillere_pos.empty:
            # Positions-mærkat (Rød boks)
            ax.text(x_pos, y_pos - 5, f" {label} ", size=12, color="white",
                    va='center', ha='center', fontweight='bold',
                    bbox=dict(facecolor='#df003b', edgecolor='white', boxstyle='round,pad=0.2', linewidth=1))

            # Spiller-bokse
            for i, (_, p) in enumerate(spillere_pos.iterrows()):
                navn = p.get('NAVN', 'Ukendt')
                bg_color = get_status_color(p)
                # Formaterer teksten så boksene får ens bredde
                visnings_tekst = f" {navn} ".ljust(22)
                y_row = (y_pos - 2.5) + (i * 2.3)
                
                ax.text(x_pos, y_row, visnings_tekst, size=10, color="black",
                        va='top', ha='center', family='monospace',
                        bbox=dict(facecolor=bg_color, edgecolor='#000000', 
                                  boxstyle='square,pad=0.1', linewidth=0.5))

    # --- 6. VISUALISERING ---
    st.pyplot(fig)
