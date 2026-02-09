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

    idag = datetime.now()
    if 'CONTRACT' in df_squad.columns:
        df_squad['CONTRACT'] = pd.to_datetime(df_squad['CONTRACT'], dayfirst=True, errors='coerce')
        df_squad['DAYS_LEFT'] = (df_squad['CONTRACT'] - idag).dt.days
    else:
        df_squad['DAYS_LEFT'] = 999 

    def get_status_color(row):
        if row['PRIOR'] == 'L':
            return '#d3d3d3'  # Grå for leje
        days = row['DAYS_LEFT']
        if pd.isna(days): return 'white'
        if days < 182: return '#ff4b4b'   # Rød
        if days <= 365: return '#fffd8d'  # Gul
        return 'white'

    # --- 2. LEGEND OVENOVER BILLEDET ---
    # Vi bruger kolonner til at lave en pæn række over banen
    st.markdown("### Kontraktstatus & Prioritet")
    l_col1, l_col2, l_col3, l_col4 = st.columns([1, 1, 1, 2])
    
    with l_col1:
        st.markdown('<p style="border-left: 15px solid #ff4b4b; padding-left: 10px;">Udløb < 6 mdr</p>', unsafe_allow_html=True)
    with l_col2:
        st.markdown('<p style="border-left: 15px solid #fffd8d; padding-left: 10px;">Udløb 6-12 mdr</p>', unsafe_allow_html=True)
    with l_col3:
        st.markdown('<p style="border-left: 15px solid #d3d3d3; padding-left: 10px;">Leje / Udlejet (L)</p>', unsafe_allow_html=True)

    # --- 3. FORMATIONER & BANE ---
    form_valg = st.sidebar.radio("Vælg Formation:", ["3-4-3", "4-3-3", "3-5-2"])

    # (Formationer koordinater bibeholdes fra din tidligere kode)
    if form_valg == "3-4-3":
        pos_config = {
            1: (10, 43, 'MM'), 4: (33, 25, 'VCB'), 3: (33, 43, 'CB'), 2: (33, 65, 'HCB'),
            5: (55, 8, 'VWB'), 6: (55, 33, 'DM'), 8: (55, 53, 'DM'), 7: (55, 78, 'HWB'), 
            11: (85, 15, 'VW'), 9: (90, 43, 'ANG'), 10: (85, 70, 'HW')
        }
    elif form_valg == "4-3-3":
        pos_config = {
            1: (10, 43, 'MM'), 5: (35, 10, 'VB'), 4: (33, 30, 'VCB'), 3: (33, 55, 'HCB'), 2: (35, 75, 'HB'),
            6: (55, 43, 'DM'), 8: (65, 30, 'VCM'), 10: (65, 60, 'HCM'),
            11: (80, 15, 'VW'), 9: (90, 44, 'ANG'), 7: (80, 70, 'HW')
        }
    else: # 3-5-2
        pos_config = {
            1: (10, 43, 'MM'), 4: (33, 25, 'VCB'), 3: (33, 43, 'CB'), 2: (33, 65, 'HCB'),
            5: (55, 8, 'VWB'), 6: (55, 43, 'DM'), 7: (55, 75, 'HWB'), 
            8: (65, 30, 'CM'), 10: (65, 60, 'CM'),
            11: (95, 30, 'ANG'), 9: (95, 55, 'ANG')
        }

    pitch = Pitch(pitch_type='statsbomb', pitch_color='#ffffff', line_color='#000000')
    fig, ax = pitch.draw(figsize=(12, 8))

    # --- 4. TEGN SPILLERE ---
    for pos_num, coords in pos_config.items():
        x_pos, y_pos, label = coords
        spillere = df_squad[df_squad['POS'] == pos_num].sort_values('PRIOR')
        
        if not spillere.empty:
            ax.text(x_pos, y_pos - 4.6, f" {label} ", size=10, color="white",
                    va='center', ha='center', fontweight='bold',
                    bbox=dict(facecolor='#cc0000', edgecolor='white', boxstyle='round,pad=0.2', linewidth=1))

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
