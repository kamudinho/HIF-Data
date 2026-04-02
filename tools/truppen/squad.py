import streamlit as st
import pandas as pd
from mplsoccer import Pitch
from datetime import datetime
import matplotlib.pyplot as plt

def vis_side(df):
    if df is None or df.empty:
        st.error("Ingen data fundet for truppen.")
        return

    # --- 1. SESSION STATE ---
    if 'formation_valg' not in st.session_state:
        st.session_state.formation_valg = "3-4-3"

    # --- 2. FARVER & KONSTANTER ---
    hif_rod = "#df003b"
    gul_udlob = "#ffff99" # Justeret til en lidt kraftigere gul for læsbarhed
    leje_gra = "#d3d3d3"
    rod_udlob = "#ffcccc"

    # --- 3. CSS INJECTION (Forbedret knap-styling) ---
    st.markdown("""
        <style>
            div.stButton > button {
                border-radius: 20px !important;
                border: 1px solid #ddd !important;
                transition: all 0.3s ease;
            }
            div.stButton > button:hover {
                border-color: #df003b !important;
                color: #df003b !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # --- 4. DATA PROCESSERING ---
    df_squad = df.copy()
    # Standardiser kolonnenavne
    df_squad.columns = [str(c).strip().upper() for c in df_squad.columns]
    
    # Håndter både 'UDLØB' og 'KONTRAKT' kolonnenavne for fleksibilitet
    udlob_col = 'UDLØB' if 'UDLØB' in df_squad.columns else 'KONTRAKT'
    
    if udlob_col in df_squad.columns:
        df_squad['KONTRAKT_DT'] = pd.to_datetime(df_squad[udlob_col], dayfirst=True, errors='coerce')
        idag = datetime.now()
        df_squad['DAYS_LEFT'] = (df_squad['KONTRAKT_DT'] - idag).dt.days

    def get_status_color(row):
        # Tjek for leje (PRIOR 'L')
        if str(row.get('PRIOR', '')).upper() == 'L': 
            return leje_gra
        
        days = row.get('DAYS_LEFT')
        if pd.isna(days): 
            return 'white'
        
        if days < 183: # Under 6 måneder
            return rod_udlob
        if days <= 365: # 6-12 måneder
            return gul_udlob
        return 'white'

    # --- 5. LAYOUT ---
    col_pitch, col_menu = st.columns([8, 1.2])

    with col_menu:
        st.write("**Indstillinger**")
        # Formation knapper
        for f in ["3-4-3", "4-3-3", "3-5-2"]:
            is_active = st.session_state.formation_valg == f
            if st.button(f, key=f"btn_{f}", use_container_width=True, type="primary" if is_active else "secondary"):
                st.session_state.formation_valg = f
                st.rerun()
        
        st.write("---")
        # Trup-oversigt i popover
        with st.popover("Se hele truppen", use_container_width=True):
            st.dataframe(
                df_squad[['NAVN', udlob_col]].sort_values('NAVN'),
                hide_index=True,
                use_container_width=True
            )

    with col_pitch:
        pitch = Pitch(
            pitch_type='statsbomb', 
            pitch_color='white', 
            line_color='#333', 
            linewidth=1.5
        )
        fig, ax = pitch.draw(figsize=(13, 8))
        
        # --- LEGENDS (Placeret præcist i toppen) ---
        legend_y = -4
        ax.text(2, legend_y, " < 6 mdr ", size=8, weight='bold', bbox=dict(facecolor=rod_udlob, edgecolor='#333', boxstyle='round,pad=0.3'))
        ax.text(18, legend_y, " 6-12 mdr ", size=8, weight='bold', bbox=dict(facecolor=gul_udlob, edgecolor='#333', boxstyle='round,pad=0.3'))
        ax.text(36, legend_y, " Leje ", size=8, weight='bold', bbox=dict(facecolor=leje_gra, edgecolor='#333', boxstyle='round,pad=0.3'))

        # Positions-konfiguration
        form = st.session_state.formation_valg
        if form == "3-4-3":
            pos_config = {1: (10, 40, 'MM'), 4: (33, 22, 'VCB'), 3.5: (33, 40, 'CB'), 3: (33, 58, 'HCB'),
                          5: (58, 10, 'VWB'), 6: (55, 32, 'DM'), 8: (55, 48, 'DM'), 2: (58, 70, 'HWB'), 
                          11: (82, 15, 'VW'), 9: (98, 40, 'ANG'), 7: (82, 65, 'HW')}
        elif form == "4-3-3":
            pos_config = {1: (10, 40, 'MM'), 5: (35, 12, 'VB'), 4: (30, 28, 'VCB'), 3: (30, 52, 'HCB'), 2: (35, 68, 'HB'),
                          6: (55, 40, 'DM'), 8: (72, 25, 'VCM'), 10: (72, 55, 'HCM'),
                          11: (85, 15, 'VW'), 9: (105, 40, 'ANG'), 7: (85, 65, 'HW')}
        else: # 3-5-2
            pos_config = {1: (10, 40, 'MM'), 4: (33, 22, 'VCB'), 3.5: (33, 40, 'CB'), 3: (33, 58, 'HCB'),
                          5: (55, 10, 'VWB'), 6: (55, 40, 'DM'), 2: (55, 70, 'HWB'), 
                          8: (75, 28, 'CM'), 10: (75, 52, 'CM'), 9: (102, 32, 'ANG'), 7: (102, 48, 'ANG')}

        # Tegn spillere
        for pos_num, (x, y, label) in pos_config.items():
            spillere = df_squad[df_squad['POS'].astype(str) == str(pos_num)]
            spillere = spillere.sort_values('PRIOR', ascending=True)

            if not spillere.empty:
                # Positions-label (f.eks. ANG)
                ax.text(x, y - 5, label, size=9, color="white", weight='bold', ha='center',
                        bbox=dict(facecolor=hif_rod, edgecolor='none', boxstyle='round,pad=0.2'))
                
                # Spiller-navne
                for i, (_, p) in enumerate(spillere.iterrows()):
                    ax.text(x, y + (i * 2.8), p['NAVN'], size=8.5, weight='bold', ha='center',
                            bbox=dict(facecolor=get_status_color(p), edgecolor='#333', boxstyle='square,pad=0.2', linewidth=0.5))

        st.pyplot(fig, use_container_width=True)
