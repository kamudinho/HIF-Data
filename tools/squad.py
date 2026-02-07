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

    # --- 2. FORMATIONER (Korrekt placeret på banen) ---
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

    # --- 4. INDSÆT POSITIONER OG TABELLER ---
    for pos_num, coords in pos_config.items():
        x_pos, y_pos, label = coords
        spillere = df_squad[df_squad['POS'] == pos_num].sort_values('PRIOR')
        
        if not spillere.empty:
            spiller_liste = [f"{p['PRIOR']}: {p.get('NAVN', '')}" for _, p in spillere.iterrows()]
            samlet_tekst = "\n".join(spiller_liste)
            
            # A. POSITION LABEL (Øverst - vi trækker fra y for at gå op)
            # y_pos - 8 rykker den op over tabellen
            ax.text(x_pos, y_pos - 8, f" {label} ", size=10, color="white",
                    va='center', ha='center', fontweight='bold',
                    bbox=dict(facecolor='#cc0000', edgecolor='white', 
                              boxstyle='round,pad=0.2', linewidth=1))

            # B. SPILLER-TABEL (Under label - vi bruger va='top' så den vokser nedad)
            # y_pos - 4 giver det ønskede mellemrum på ca. 1 cm
            ax.text(x_pos, y_pos - 4, samlet_tekst, size=8.5, color="black",
                    va='top', ha='center', fontweight='bold',
                    bbox=dict(facecolor='white', edgecolor='#cc0000', 
                              boxstyle='round,pad=0.4', linewidth=1.5, alpha=1.0))

    st.pyplot(fig)
