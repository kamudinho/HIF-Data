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

    # --- 2. FARVER & KONSTANTER ---
    hif_rod = "#df003b"
    gul_udlob = "#ffffcc"
    leje_gra = "#d3d3d3"
    rod_udlob = "#ffcccc"

    # --- 3. CSS INJECTION (Justeret for perfekt balance) ---
    st.markdown("""
        <style>
            [data-testid="column"] {
                display: flex !important;
                flex-direction: column !important;
                justify-content: flex-start !important;
                width: 100% !important;
            }

            /* 2. Ryk banen og menuen moderat OP */
            div[data-testid="stHorizontalBlock"] {
                gap: 0rem !important;
                margin-top: -15px !important; /* Den gyldne middelvej */
            }
            
            div[data-testid="stVerticalBlock"] > div {
                padding-top: 0px !important;
            }

            /* 3. Tving menu-kolonnen helt ud til højre kant */
            div[data-testid="stHorizontalBlock"] > div:last-child {
                flex: 0 1 auto !important;
                min-width: 130px !important;
                padding-left: 0px !important;
                padding-right: 0px !important;
                align-items: flex-end !important;
            }

            /* 4. Pill Button Styling */
            div.stButton {
                text-align: right !important;
                width: 100% !important;
            }

            div.stButton > button {
                border-radius: 20px !important;
                border: 1px solid #ddd !important;
                background-color: white !important;
                color: #333 !important;
                width: 110px !important;
                margin-left: auto !important;
                display: block !important;
            }
            
            div.stButton > button[kind="primary"] {
                color: #df003b !important;
                border: 2px solid #df003b !important;
                font-weight: bold !important;
            }

            div[data-testid="stPopover"] {
                width: 100% !important;
                display: flex !important;
                justify-content: flex-end !important;
            }
            div[data-testid="stPopover"] > button {
                width: 110px !important;
                border-radius: 20px !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # --- 4. TOP BRANDING (Kompakt højde) ---
    st.markdown(f"""
        <div style="background-color:{hif_rod}; padding:10px; border-radius:4px; margin-bottom:10px;">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; text-transform:uppercase; letter-spacing:1px; font-size:1.1rem;">TAKTIK & KONTRAKTER</h3>
        </div>
    """, unsafe_allow_html=True)

    # --- 4. DATA PROCESSERING ---
    df_squad = df.copy()
    df_squad.columns = [str(c).strip().upper() for c in df_squad.columns]
    df_squad['POS'] = pd.to_numeric(df_squad['POS'], errors='coerce')
    
    idag = datetime.now()
    if 'CONTRACT' in df_squad.columns:
        df_squad['CONTRACT_DT'] = pd.to_datetime(df_squad['CONTRACT'], dayfirst=True, errors='coerce')
        df_squad['DAYS_LEFT'] = (df_squad['CONTRACT_DT'] - idag).dt.days

    def get_status_color(row):
        if str(row.get('PRIOR', '')).upper() == 'L': return leje_gra
        days = row.get('DAYS_LEFT', 999)
        if pd.isna(days): return 'white'
        if days < 183: return rod_udlob
        if days <= 365: return gul_udlob
        return 'white'

    # --- 5. HOVEDLAYOUT (Bred bane, smal menu) ---
    col_pitch, col_menu = st.columns([7, 1])

   with col_pitch:
        # 1. Pitch - Vi fjerner 'pad' (standard er 4)
        pitch = Pitch(
            pitch_type='statsbomb', 
            pitch_color='#ffffff', 
            line_color='#333', 
            linewidth=1,
            pad_top=0, pad_bottom=0, pad_left=0, pad_right=0 # Tvinger linjerne til kanten
        )
        
        # 2. Figure - constrained_layout hjælper med at udfylde pladsen
        fig, ax = pitch.draw(figsize=(13, 8), constrained_layout=True)
        
        # 3. Den vigtigste linje: Fjern alt resterende hvidt omkring banen
        fig.subplots_adjust(left=0, right=1, bottom=0, top=1)

        # Legend - Flyttet helt op i hjørnet (nu hvor der ikke er margin)
        # Vi bruger 'va=bottom' og y=pitch_height for at flugte med øverste linje
        ax.text(1, 79, " < 6 mdr ", size=8, fontweight='bold', va='bottom', 
                bbox=dict(facecolor=rod_udlob, edgecolor='#ccc', boxstyle='round,pad=0.2'))
        ax.text(12, 79, " 6-12 mdr ", size=8, fontweight='bold', va='bottom', 
                bbox=dict(facecolor=gul_udlob, edgecolor='#ccc', boxstyle='round,pad=0.2'))
        ax.text(25, 79, " Leje ", size=8, fontweight='bold', va='bottom', 
                bbox=dict(facecolor=leje_gra, edgecolor='#ccc', boxstyle='round,pad=0.2'))

        # ... (Din spiller-rendering her) ...

        # 4. Vis billedet - Streamlit vil nu strække det helt ud til kanterne
        st.pyplot(fig, use_container_width=True)
        
        # Formation Pills
        for f in ["3-4-3", "4-3-3", "3-5-2"]:
            is_active = st.session_state.formation_valg == f
            if st.button(f, use_container_width=True, type="primary" if is_active else "secondary"):
                st.session_state.formation_valg = f
                st.rerun()

    with col_pitch:
        # Pitch Setup
        pitch = Pitch(pitch_type='statsbomb', pitch_color='#ffffff', line_color='#333', linewidth=1)
        fig, ax = pitch.draw(figsize=(13, 8))
        
        # Legend (Kompakt i toppen)
        ax.text(2, 2, " < 6 mdr ", size=8, fontweight='bold', bbox=dict(facecolor=rod_udlob, edgecolor='#ccc', boxstyle='round,pad=0.2'))
        ax.text(14, 2, " 6-12 mdr ", size=8, fontweight='bold', bbox=dict(facecolor=gul_udlob, edgecolor='#ccc', boxstyle='round,pad=0.2'))
        ax.text(28, 2, " Leje ", size=8, fontweight='bold', bbox=dict(facecolor=leje_gra, edgecolor='#ccc', boxstyle='round,pad=0.2'))

        # Positions-logik
        form = st.session_state.formation_valg
        if form == "3-4-3":
            pos_config = {1: (10, 40, 'MM'), 4: (33, 22, 'VCB'), 3: (33, 40, 'CB'), 2: (33, 58, 'HCB'),
                          5: (60, 10, 'VWB'), 6: (60, 30, 'DM'), 8: (60, 50, 'DM'), 7: (60, 70, 'HWB'), 
                          11: (85, 15, 'VW'), 9: (100, 40, 'ANG'), 10: (85, 65, 'HW')}
        elif form == "4-3-3":
            pos_config = {1: (10, 40, 'MM'), 5: (35, 10, 'VB'), 4: (33, 25, 'VCB'), 3: (33, 55, 'HCB'), 2: (35, 70, 'HB'),
                          6: (50, 40, 'DM'), 8: (68, 25, 'VCM'), 10: (68, 55, 'HCM'),
                          11: (85, 15, 'VW'), 9: (100, 40, 'ANG'), 7: (85, 65, 'HW')}
        else: # 3-5-2
            pos_config = {1: (10, 40, 'MM'), 4: (33, 22, 'VCB'), 3: (33, 40, 'CB'), 2: (33, 58, 'HCB'),
                          5: (60, 10, 'VWB'), 6: (60, 40, 'DM'), 7: (60, 70, 'HWB'), 
                          8: (70, 25, 'CM'), 10: (70, 55, 'CM'), 11: (100, 28, 'ANG'), 9: (100, 52, 'ANG')}

        for pos_num, (x, y, label) in pos_config.items():
            spillere = df_squad[df_squad['POS'] == pos_num].sort_values('PRIOR')
            if not spillere.empty:
                ax.text(x, y - 4.5, f" {label} ", size=10, color="white", fontweight='bold', ha='center',
                        bbox=dict(facecolor=hif_rod, edgecolor='white', boxstyle='round,pad=0.2'))
                for i, (_, p) in enumerate(spillere.iterrows()):
                    ax.text(x, (y - 1.5) + (i * 2.3), f" {p['NAVN']} ", size=9, fontweight='bold', ha='center', va='top',
                            bbox=dict(facecolor=get_status_color(p), edgecolor='#333', boxstyle='square,pad=0.2', linewidth=0.5))

        st.pyplot(fig, use_container_width=True)
