import streamlit as st
import pandas as pd
from mplsoccer import Pitch
from datetime import datetime
import matplotlib.pyplot as plt

def vis_side(df):
    if df is None:
        st.error("Ingen data fundet for truppen.")
        return

    # --- 1. SESSION STATE ---
    if 'formation_valg' not in st.session_state:
        st.session_state.formation_valg = "3-4-3"

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
        if row['PRIOR'] == 'L': return '#d3d3d3' 
        days = row['DAYS_LEFT']
        if pd.isna(days): return 'white'
        if days < 182: return '#ff4b4b' 
        if days <= 365: return '#fffd8d' 
        return 'white'

    # --- 3. KOMPAKT TOP MENU ---
    # Vi bruger mindre ratios [0.5, 0.5, 0.5] for at gøre formationsknapperne små
    col1, col2, col3, col_spacer, col_pop = st.columns([0.5, 0.5, 0.5, 2.5, 1.2])
    
    formations = ["3-4-3", "4-3-3", "3-5-2"]
    cols = [col1, col2, col3]

    for i, f in enumerate(formations):
        with cols[i]:
            if st.button(f, use_container_width=True, type="primary" if st.session_state.formation_valg == f else "secondary"):
                st.session_state.formation_valg = f
                st.rerun()

    with col_pop:
        # Popover til kontrakter holder banen ren
        with st.popover("Kontrakter", use_container_width=True):
            st.markdown("**Kontraktudløb**")
            df_table = df_squad[['NAVN', 'CONTRACT']].copy()
            df_table['CONTRACT'] = df_table['CONTRACT'].apply(lambda x: x.strftime('%d-%m-%Y') if pd.notnull(x) else "N/A")
            st.dataframe(df_table, hide_index=True, use_container_width=True)

    # --- 4. BANE LAYOUT ---
    form_valg = st.session_state.formation_valg
    
    # Vi bruger en bred midterkolonne for at maksimere banens synlighed
    _, col_main, _ = st.columns([0.05, 5, 0.05])

    with col_main:
        pitch = Pitch(pitch_type='statsbomb', pitch_color='#ffffff', line_color='#000000')
        # Figsize 12x7 giver en god bredde uden at tvinge vertikal scroll
        fig, ax = pitch.draw(figsize=(12, 7), constrained_layout=True)

        # Legend (Mindre tekst for at spare vertikal plads)
        legend_y = -3
        legend_items = [("#ff4b4b", "Udløb < 6 mdr"), ("#fffd8d", "Udløb 6-12 mdr"), ("#d3d3d3", "Leje")]
        for i, (color, text) in enumerate(legend_items):
            x_pos = 5 + (i * 28)
            ax.text(x_pos, legend_y, f"  {text}  ", size=7, color="black",
                    va='center', ha='left', family='monospace', fontweight='bold',
                    bbox=dict(facecolor=color, edgecolor='black', boxstyle='square,pad=0.2', linewidth=0.5))

        # Positions logik
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

        # Tegn spillere
        for pos_num, coords in pos_config.items():
            x_pos, y_pos, label = coords
            spillere_pos = df_squad[df_squad['POS'] == pos_num].sort_values('PRIOR')
            
            if not spillere_pos.empty:
                # Positions-label
                ax.text(x_pos, y_pos - 4, f" {label} ", size=8, color="white",
                        va='center', ha='center', fontweight='bold',
                        bbox=dict(facecolor='#df003b', edgecolor='white', boxstyle='round,pad=0.2', linewidth=1))

                # Spiller-navne
                for i, (_, p) in enumerate(spillere_pos.iterrows()):
                    navn = p.get('NAVN', 'Ukendt')
                    bg_color = get_status_color(p)
                    visnings_tekst = f" {navn} ".ljust(18)
                    y_row = (y_pos - 1.2) + (i * 2.8)
                    
                    ax.text(x_pos, y_row, visnings_tekst, size=7, color="black",
                            va='top', ha='center', family='monospace',
                            bbox=dict(facecolor=bg_color, edgecolor='#000000', 
                                      boxstyle='square,pad=0.1', linewidth=0.5))

        st.pyplot(fig, use_container_width=True)
