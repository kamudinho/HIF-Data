import streamlit as st
import pandas as pd
from mplsoccer import Pitch
from datetime import datetime

def vis_side(df):

    if df is None:
        st.error("Ingen data fundet.")
        return

    # --- 1. FORMATIONSVÆLGER I SIDEBAR ---
    with st.sidebar:
        st.markdown("---") # En lille adskiller
        st.markdown('<p class="sidebar-header">Taktisk opstilling</p>', unsafe_allow_html=True)
        form_valg = st.selectbox(
            "Vælg formation for truppen:",
            ["3-4-3", "4-3-3", "3-5-2"],
            index=0,
            key="squad_formation_sidebar"
        )

    # --- 2. DATA-PROCESSERING ---
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
            return '#d3d3d3' # Grå for leje
        days = row['DAYS_LEFT']
        if pd.isna(days): return 'white'
        if days < 182: return '#ff4b4b' # Rød (< 6 mdr)
        if days <= 365: return '#fffd8d' # Gul (6-12 mdr)
        return 'white'

    # --- 3. KONFIGURATION AF BANE ---
    pitch = Pitch(pitch_type='statsbomb', pitch_color='#ffffff', line_color='#000000')
    fig, ax = pitch.draw(figsize=(16, 10), constrained_layout=True)

    # Legends i bunden
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

    # --- 4. FORMATIONER ---
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
            11: (80, 15, 'VW'), 9: (90, 40, 'ANG'), 7: (80, 65, 'HW')
        }
    else: # 3-5-2
        pos_config = {
            1: (10, 40, 'MM'), 4: (33, 22, 'VCB'), 3: (33, 40, 'CB'), 2: (33, 58, 'HCB'),
            5: (55, 10, 'VWB'), 6: (55, 40, 'DM'), 7: (55, 70, 'HWB'), 
            8: (65, 25, 'CM'), 10: (65, 55, 'CM'),
            11: (95, 25, 'ANG'), 9: (95, 55, 'ANG')
        }

    # --- 5. TEGN SPILLERE ---
    for pos_num, coords in pos_config.items():
        x_pos, y_pos, label = coords
        spillere_pos = df_squad[df_squad['POS'] == pos_num].sort_values('PRIOR')
        
        if not spillere_pos.empty:
            ax.text(x_pos, y_pos - 4.8, f" {label} ", size=12, color="white",
                    va='center', ha='center', fontweight='bold',
                    bbox=dict(facecolor='#cc0000', edgecolor='white', boxstyle='round,pad=0.2', linewidth=1))

            for i, (_, p) in enumerate(spillere_pos.iterrows()):
                navn = p.get('NAVN', f"{p.get('FIRSTNAME','')} {p.get('LASTNAME','')}")
                bg_color = get_status_color(p)
                visnings_tekst = f" {navn} ".ljust(25)
                y_row = (y_pos - 2.2) + (i * 2.2)
                
                ax.text(x_pos, y_row, visnings_tekst, size=10, color="black",
                        va='top', ha='center', fontweight='light', family='monospace',
                        bbox=dict(facecolor=bg_color, edgecolor='#000000', 
                                  boxstyle='square,pad=0.1', linewidth=0.5, alpha=1.0))

    # --- 6. VISUALISERING ---
    st.pyplot(fig)
