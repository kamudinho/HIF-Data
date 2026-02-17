import streamlit as st
import pandas as pd
from mplsoccer import Pitch
from datetime import datetime
import matplotlib.pyplot as plt
import textwrap

def vis_side(df):
    if df is None:
        st.error("Ingen data fundet for truppen.")
        return

    # --- 1. SESSION STATE ---
    if 'formation_valg' not in st.session_state:
        st.session_state.formation_valg = "3-4-3"

    # --- 2. FARVER ---
    hif_rod = "#df003b"
    gul_udlob = "#ffffcc"
    leje_gra = "#d3d3d3"
    rod_udlob = "#ffcccc"

    # --- 3. CSS (Layout & Knapper) ---
    st.markdown(f"""
        <style>
            /* Container setup */
            .block-container {{ padding-top: 1rem !important; max-width: 98% !important; }}
            
            /* Tvinger højre kolonne til at flugte alt mod højre kant */
            [data-testid="column"]:last-child {{
                display: flex !important;
                flex-direction: column !important;
                align-items: flex-end !important;
                justify-content: flex-start !important;
                text-align: right !important;
            }}

            /* Tvinger hver vertikal blok i højre side til at højre-aligne */
            [data-testid="column"]:last-child [data-testid="stVerticalBlock"] {{
                align-items: flex-end !important;
                width: 100% !important;
            }}

            /* Pill Button Styling */
            div.stButton > button {{
                border-radius: 20px !important;
                border: 1px solid #ddd !important;
                background-color: white !important;
                color: #333 !important;
                width: 120px !important;
                margin-left: auto !important; /* Sikrer de skubbes til højre */
            }}
            
            div.stButton > button[kind="primary"] {{
                background-color: white !important;
                color: {hif_rod} !important;
                border: 2px solid {hif_rod} !important;
                font-weight: bold !important;
            }}

            /* Popover Styling */
            [data-testid="stPopover"] {{ width: 120px !important; }}
            [data-testid="stPopoverBody"] {{ width: 400px !important; }}
        </style>
    """, unsafe_allow_html=True)

    # --- 4. BRANDING ---
    st.markdown(f"""
        <div style="background-color:{hif_rod}; padding:10px; border-radius:4px; margin-bottom:20px;">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; text-transform:uppercase;">TAKTIK & KONTRAKTER</h3>
        </div>
    """, unsafe_allow_html=True)

    # --- 5. DATA ---
    df_squad = df.copy()
    df_squad.columns = [str(c).strip().upper() for c in df_squad.columns]
    
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

    # --- 6. LAYOUT (85% Bane, 15% Menu) ---
    col_pitch, col_menu = st.columns([6, 1])

    with col_menu:
        # --- POPOVER ("Trup") ---
        with st.popover("Trup", use_container_width=True):
            tabel_rows = ""
            for _, r in df_squad.sort_values('NAVN').iterrows():
                bg = get_status_color(r)
                kontrakt_str = r['CONTRACT'] if pd.notna(r['CONTRACT']) else "-"
                tabel_rows += f'''
                <tr style="background-color:{bg}; border-bottom: 1px solid #f2f2f2;">
                    <td style="padding: 8px 10px; font-weight:600; color: #222; font-family: sans-serif;">{r['NAVN']}</td>
                    <td style="padding: 8px 10px; text-align:right; color: #222; font-family: sans-serif;">{kontrakt_str}</td>
                </tr>'''

            html_content = f'''
            <table style="width:100%; border-collapse: collapse; margin-top: -10px;">
                <thead>
                    <tr style="background: #fafafa; border-bottom: 2px solid {hif_rod};">
                        <th style="padding: 8px 10px; text-align: left; color: #888; font-size: 10px; font-family: sans-serif; text-transform: uppercase;">Spiller</th>
                        <th style="padding: 8px 10px; text-align: right; color: #888; font-size: 10px; font-family: sans-serif; text-transform: uppercase;">Udløb</th>
                    </tr>
                </thead>
                <tbody>{tabel_rows}</tbody>
            </table>'''
            
            # Vi bruger components for at undgå "Tbody" tekstfejl
            st.components.v1.html(html_content, height=450, scrolling=True)
        
        st.write("") # Spacer
        
        # Formationsknapper
        for f in ["3-4-3", "4-3-3", "3-5-2"]:
            if st.button(f, use_container_width=True, type="primary" if st.session_state.formation_valg == f else "secondary"):
                st.session_state.formation_valg = f
                st.rerun()

    with col_pitch:
        pitch = Pitch(pitch_type='statsbomb', pitch_color='#ffffff', line_color='#333333', linewidth=1)
        fig, ax = pitch.draw(figsize=(13, 8))
        
        # Legend (Lille i øverste venstre hjørne)
        ax.text(1, 2, "< 6 mdr", size=7, fontweight='bold', bbox=dict(facecolor=rod_udlob, edgecolor='#ccc', boxstyle='round,pad=0.2'))
        ax.text(1, 5, "6-12 mdr", size=7, fontweight='bold', bbox=dict(facecolor=gul_udlob, edgecolor='#ccc', boxstyle='round,pad=0.2'))
        ax.text(1, 8, "Leje", size=7, fontweight='bold', bbox=dict(facecolor=leje_gra, edgecolor='#ccc', boxstyle='round,pad=0.2'))

        # (Formation rendering logik her...)
        # ... (Samme position_config som før) ...
        
        st.pyplot(fig, use_container_width=True)
