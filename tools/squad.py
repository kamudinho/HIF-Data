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

    # Beregn alder til bunden
    if 'BIRTHDATE' in df_squad.columns:
        df_squad['BIRTHDATE'] = pd.to_datetime(df_squad['BIRTHDATE'], errors='coerce')
        df_squad['ALDER'] = df_squad['BIRTHDATE'].apply(
            lambda x: idag.year - x.year - ((idag.month, idag.day) < (x.month, x.day)) if pd.notna(x) else None
        )

    def get_status_color(row):
        if row['PRIOR'] == 'L':
            return '#d3d3d3'  # Grå for leje
        days = row['DAYS_LEFT']
        if pd.isna(days): return 'white'
        if days < 182: return '#ff4b4b'   # Rød
        if days <= 365: return '#fffd8d'  # Gul
        return 'white'

    # --- 2. TEGN BANEN ---
    # Vi bruger Pitch men tegner på en akse, hvor vi har plads i toppen
    pitch = Pitch(pitch_type='statsbomb', pitch_color='#ffffff', line_color='#000000')
    fig, ax = pitch.draw(figsize=(12, 9)) # Lidt højere figur for at give plads

    # --- 3. LEGENDS INDE I BILLEDET (Øverst til venstre) ---
    legend_y = -5  # Koordinat ovenover selve kridtstregerne
    legend_items = [
        ("#ff4b4b", "Udløb < 6 mdr"),
        ("#fffd8d", "Udløb 6-12 mdr"),
        ("#d3d3d3", "Leje / Udlejet (L)")
    ]
    
    for i, (color, text) in enumerate(legend_items):
        # x-start på 2 og øget mellemrum (25 enheder)
        x_pos = 2 + (i * 25) 
        ax.text(x_pos, legend_y, f"  {text}  ", size=9, color="black",
                va='center', ha='left', family='monospace', fontweight='bold',
                bbox=dict(facecolor=color, edgecolor='black', boxstyle='square,pad=0.4', linewidth=0.5))

    # --- 4. FORMATIONER ---
    form_valg = st.sidebar.radio("Vælg Formation:", ["3-4-3", "4-3-3", "3-5-2"])

    if form_valg == "3-4-3":
        pos_config = {
            1: (10, 43, 'MM'), 4: (33, 25, 'VCB'), 3: (33, 43, 'CB'), 2: (33, 65, 'HCB'),
            5: (55, 8, 'VWB'), 6: (55, 33, 'DM'), 8: (55, 53, 'DM'), 7: (55, 78, 'HWB'), 
            11: (85, 15, 'VW'), 9: (105, 43, 'ANG'), 10: (85, 71, 'HW')
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

    # --- 5. TEGN SPILLERE ---
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

    # --- 6. STATISTIK I BUNDEN ---
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.caption("ANTAL SPILLERE")
        st.subheader(len(df_squad))
    with c2:
        h_avg = pd.to_numeric(df_squad['HEIGHT'], errors='coerce').mean()
        st.caption("GNS. HØJDE")
        st.subheader(f"{h_avg:.1f} cm" if pd.notna(h_avg) else "-")
    with c3:
        age_avg = df_squad['ALDER'].mean() if 'ALDER' in df_squad.columns else None
        st.caption("GNS. ALDER")
        st.subheader(f"{age_avg:.1f} år" if pd.notna(age_avg) else "-")
