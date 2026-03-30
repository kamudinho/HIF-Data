#tools/scouting/emne_db.py
import streamlit as st
import pandas as pd
from mplsoccer import Pitch
from datetime import datetime
import matplotlib.pyplot as plt

def vis_side(df):
    if df is None:
        st.error("Ingen data fundet for truppen.")
        return

    # --- 1. FARVER & KONSTANTER ---
    hif_rod = "#df003b"
    gul_udlob = "#ffffcc"
    leje_gra = "#d3d3d3"
    rod_udlob = "#ffcccc"
    transfer_gron = "#ccffcc" 

    # --- 2. CSS INJECTION (Kompakt dropdown + layout) ---
    st.markdown(f"""
        <style>
            div[data-testid="stSelectbox"] {{ width: 250px !important; }}
            .stSelectbox label p {{ font-size: 14px !important; font-weight: bold; }}
            [data-testid="column"] {{ display: flex !important; flex-direction: column !important; }}
            div.stButton > button {{
                border-radius: 20px !important;
                border: 1px solid #ddd !important;
                background-color: white !important;
                color: #333 !important;
                width: 110px !important;
            }}
            div.stButton > button[kind="primary"] {{
                color: {hif_rod} !important;
                border: 2px solid {hif_rod} !important;
            }}
        </style>
    """, unsafe_allow_html=True)

    # --- 3. DATA PREP ---
    df_squad = df.copy()
    df_squad.columns = [str(c).strip().upper() for c in df_squad.columns]
    df_squad['POS'] = pd.to_numeric(df_squad['POS'], errors='coerce')
    
    idag = datetime.now()
    if 'KONTRAKT' in df_squad.columns:
        df_squad['KONTRAKT_DT'] = pd.to_datetime(df_squad['KONTRAKT'], dayfirst=True, errors='coerce')
        df_squad['DAYS_LEFT'] = (df_squad['KONTRAKT_DT'] - idag).dt.days

    # --- 4. FILTRERING (Her fejlede den sandsynligvis før) ---
    c1, c2 = st.columns([2, 5])
    with c1:
        if 'TRANSFER_VINDUE' in df_squad.columns:
            # Vi finder de unikke vinduer (f.eks. Sommer 26, Sommer 27)
            mulige_vinduer = sorted(df_squad['TRANSFER_VINDUE'].unique().tolist())
            valgt_vindue = st.selectbox("Vis trup for:", mulige_vinduer, key="squad_filter")
            
            # VIGTIGT: Her filtrerer vi den dataframe, der skal tegnes!
            df_display = df_squad[df_squad['TRANSFER_VINDUE'] == valgt_vindue].copy()
        else:
            st.warning("Kolonnen 'TRANSFER_VINDUE' mangler.")
            df_display = df_squad.copy()

    # --- 5. LOGIK TIL FARVER ---
    def get_status_color(row):
        is_transfer = str(row.get('TRANSFER_VINDUE', 'Nu')).strip().upper() != 'NU'
        if is_transfer: return transfer_gron
        if str(row.get('PRIOR', '')).upper() == 'L': return leje_gra
        try:
            days = row.get('DAYS_LEFT')
            if pd.isna(days): return 'white'
            if days < 183: return rod_udlob
            if days <= 365: return gul_udlob
        except: return 'white'
        return 'white'

    # --- 6. FORMATIONER & LAYOUT ---
    if 'formation_valg' not in st.session_state:
        st.session_state.formation_valg = "3-4-3"

    col_pitch, col_menu = st.columns([7, 1])

    with col_menu:
        st.write("")
        for f in ["3-4-3", "4-3-3", "3-5-2"]:
            is_active = st.session_state.formation_valg == f
            if st.button(f, key=f"btn_{f}", use_container_width=True, type="primary" if is_active else "secondary"):
                st.session_state.formation_valg = f
                st.rerun()

    with col_pitch:
        pitch = Pitch(pitch_type='statsbomb', pitch_color='#ffffff', line_color='#333', linewidth=1, pad_top=15, pad_bottom=10)
        fig, ax = pitch.draw(figsize=(13, 9))
        
        # Legends
        ax.text(2, -7, " < 6 mdr (Udløb) ", size=8, fontweight='bold', bbox=dict(facecolor=rod_udlob, edgecolor='#ccc', boxstyle='round,pad=0.2'))
        ax.text(20, -7, " 6-12 mdr (Udløb) ", size=8, fontweight='bold', bbox=dict(facecolor=gul_udlob, edgecolor='#ccc', boxstyle='round,pad=0.2'))
        ax.text(40, -7, " Ny Transfer ", size=8, fontweight='bold', bbox=dict(facecolor=transfer_gron, edgecolor='#ccc', boxstyle='round,pad=0.2'))

        # Positions-config (bevares fuldt ud)
        form = st.session_state.formation_valg
        if form == "3-4-3":
            pos_config = {1: (10, 40, 'MM'), 4: (33, 22, 'VCB'), 3.5: (33, 40, 'CB'), 3: (33, 58, 'HCB'),
                          5: (60, 10, 'VWB'), 6: (60, 30, 'DM'), 8: (60, 50, 'DM'), 2: (60, 70, 'HWB'), 
                          11: (85, 15, 'VW'), 9: (105, 40, 'ANG'), 7: (85, 65, 'HW')}
        elif form == "4-3-3":
            pos_config = {1: (10, 40, 'MM'), 5: (35, 10, 'VB'), 4: (33, 25, 'VCB'), 3: (33, 55, 'HCB'), 2: (35, 70, 'HB'),
                          6: (50, 40, 'DM'), 8: (68, 25, 'VCM'), 10: (68, 55, 'HCM'),
                          11: (85, 15, 'VW'), 9: (105, 40, 'ANG'), 7: (85, 65, 'HW')}
        else: # 3-5-2
            pos_config = {1: (10, 40, 'MM'), 4: (33, 22, 'VCB'), 3.5: (33, 40, 'CB'), 3: (33, 58, 'HCB'),
                          5: (60, 10, 'VWB'), 6: (60, 40, 'DM'), 2: (60, 70, 'HWB'), 
                          8: (70, 25, 'CM'), 10: (70, 55, 'CM'), 9: (105, 28, 'ANG'), 7: (105, 52, 'ANG')}

        for pos_num, (x, y, label) in pos_config.items():
            # Vi bruger df_display (den filtrerede data)
            if form == "4-3-3" and pos_num == 4:
                spillere = df_display[df_display['POS'].isin([4, 3.5])]
            elif form == "3-5-2" and pos_num == 9:
                spillere = df_display[df_display['POS'].isin([9, 11])]
            else:
                spillere = df_display[df_display['POS'] == pos_num]

            spillere = spillere.sort_values('PRIOR')
            
            if not spillere.empty:
                ax.text(x, y - 5, f" {label} ", size=10, color="white", fontweight='bold', ha='center',
                        bbox=dict(facecolor=hif_rod, edgecolor='white', boxstyle='round,pad=0.2'))
                
                for i, (_, p) in enumerate(spillere.iterrows()):
                    ax.text(x, y + (i * 3.5), f" {p['NAVN']} ", size=9, fontweight='bold', ha='center', va='top',
                            bbox=dict(facecolor=get_status_color(p), edgecolor='#333', linewidth=0.5, boxstyle='square,pad=0.2'))

        st.pyplot(fig, use_container_width=True)
