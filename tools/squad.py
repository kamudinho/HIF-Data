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

    # --- 2. FARVE-DEFINITIONER ---
    klub_rod = "#6b0013"  # Din specifikke mørkerøde

    # --- 3. DATA-PROCESSERING ---
    df_squad = df.copy()
    df_squad.columns = [str(c).strip().upper() for c in df_squad.columns]
    df_squad['POS'] = pd.to_numeric(df_squad['POS'], errors='coerce')
    df_squad['PRIOR'] = df_squad.get('PRIOR', '-').astype(str).str.strip().str.upper()

    idag = datetime.now()
    if 'CONTRACT' in df_squad.columns:
        df_squad['CONTRACT'] = pd.to_datetime(df_squad['CONTRACT'], dayfirst=True, errors='coerce')
        df_squad['DAYS_LEFT'] = (df_squad['CONTRACT'] - idag).dt.days

    def get_status_color(row):
        if row['PRIOR'] == 'L': return '#d3d3d3' 
        days = row.get('DAYS_LEFT', 999)
        if pd.isna(days): return 'white'
        if days < 182: return klub_rod  # Bruger den mørkerøde her
        if days <= 365: return '#fffd8d' 
        return 'white'

    # --- 4. HOVED-LAYOUT ---
    col_pitch, col_menu = st.columns([6, 1])

    with col_menu:
        # Styling af knapper via CSS for at ramme den mørkerøde præcis
        st.markdown(f"""
            <style>
            div[st-vertical-layout="true"] > div:first-child {{
                margin-top: 0px;
            }}
            button[kind="primary"] {{
                background-color: {klub_rod} !important;
                border-color: {klub_rod} !important;
                color: white !important;
            }}
            </style>
        """, unsafe_allow_html=True)

        with st.popover("Kontrakter", use_container_width=True):
            df_table = df_squad[['NAVN', 'CONTRACT']].copy()
            df_table['CONTRACT'] = df_table['CONTRACT'].apply(lambda x: x.strftime('%d-%m-%Y') if pd.notnull(x) else "N/A")
            st.dataframe(df_table, hide_index=True, width=550)
        
        st.write("---")
        formations = ["3-4-3", "4-3-3", "3-5-2"]
        for f in formations:
            # Type="primary" vil nu bruge klub_rod pga. CSS'en ovenfor
            if st.button(f, use_container_width=True, type="primary" if st.session_state.formation_valg == f else "secondary"):
                st.session_state.formation_valg = f
                st.rerun()

    with col_pitch:
        pitch = Pitch(pitch_type='statsbomb', pitch_color='#ffffff', line_color='#000000', 
                      pad_top=0, pad_bottom=0, pad_left=1, pad_right=1)
        
        fig, ax = pitch.draw(figsize=(14, 10))
        
        # Legend
        legend_items = [(klub_rod, "< 6 mdr"), ("#fffd8d", "6-12 mdr"), ("#d3d3d3", "Leje")]
        for i, (color, text) in enumerate(legend_items):
            text_color = "white" if color == klub_rod else "black"
            ax.text(1 + (i * 12), 2.5, text, size=11, color=text_color, va='center', ha='left', 
                    fontweight='bold', bbox=dict(facecolor=color, edgecolor='black', boxstyle='square,pad=0.2'))

        # Positions logik
        form_valg = st.session_state.formation_valg
        if form_valg == "3-4-3":
            pos_config = {1: (10, 40, 'MM'), 4: (33, 22, 'VCB'), 3: (33, 40, 'CB'), 2: (33, 58, 'HCB'),
                          5: (60, 10, 'VWB'), 6: (60, 30, 'DM'), 8: (60, 50, 'DM'), 7: (60, 70, 'HWB'), 
                          11: (85, 15, 'VW'), 9: (100, 40, 'ANG'), 10: (85, 65, 'HW')}
        elif form_valg == "4-3-3":
            pos_config = {1: (10, 40, 'MM'), 5: (35, 10, 'VB'), 4: (33, 25, 'VCB'), 3: (33, 55, 'HCB'), 2: (35, 70, 'HB'),
                          6: (50, 40, 'DM'), 8: (68, 25, 'VCM'), 10: (68, 55, 'HCM'),
                          11: (85, 15, 'VW'), 9: (100, 40, 'ANG'), 7: (85, 65, 'HW')}
        else: # 3-5-2
            pos_config = {1: (10, 40, 'MM'), 4: (33, 22, 'VCB'), 3: (33, 40, 'CB'), 2: (33, 58, 'HCB'),
                          5: (60, 10, 'VWB'), 6: (60, 40, 'DM'), 7: (60, 70, 'HWB'), 
                          8: (70, 25, 'CM'), 10: (70, 55, 'CM'), 11: (100, 28, 'ANG'), 9: (100, 52, 'ANG')}

        for pos_num, coords in pos_config.items():
            x_pos, y_pos, label = coords
            spillere_pos = df_squad[df_squad['POS'] == pos_num].sort_values('PRIOR')
            if not spillere_pos.empty:
                # Positionslabel (Mørkerød)
                ax.text(x_pos, y_pos - 5, f" {label} ", size=12, color="white", va='center', ha='center', fontweight='bold',
                        bbox=dict(facecolor=klub_rod, edgecolor='white', boxstyle='round,pad=0.3'))
                
                for i, (_, p) in enumerate(spillere_pos.iterrows()):
                    bg_color = get_status_color(p)
                    # Tekstfarve skifter til hvid hvis baggrunden er mørkerød
                    text_color = "white" if bg_color == klub_rod else "black"
                    
                    visnings_tekst = f" {p['NAVN']} ".ljust(22)
                    ax.text(x_pos, (y_pos - 1.5) + (i * 3.8), visnings_tekst, size=11, 
                            color=text_color, va='top', ha='center', family='monospace', fontweight='bold',
                            bbox=dict(facecolor=bg_color, edgecolor='black', boxstyle='square,pad=0.2', linewidth=1.0))

        plt.subplots_adjust(left=0, right=1, bottom=0, top=1)
        st.pyplot(fig, use_container_width=True)
