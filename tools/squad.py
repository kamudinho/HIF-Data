import streamlit as st
import pandas as pd
from mplsoccer import Pitch
from datetime import datetime
import matplotlib.pyplot as plt
import textwrap # Tilføj denne for at fjerne uønsket indrykning

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

    # --- 3. CSS (Sørger for knapper til højre) ---
    st.markdown(f"""
        <style>
            [data-testid="column"]:last-child {{
                display: flex;
                flex-direction: column;
                align-items: flex-end !important;
            }}
            div.stButton > button {{
                border-radius: 20px !important;
                border: 1px solid #ddd !important;
                background-color: white !important;
                width: 120px !important;
            }}
            div.stButton > button[kind="primary"] {{
                color: {hif_rod} !important;
                border: 2px solid {hif_rod} !important;
                font-weight: bold !important;
            }}
            [data-testid="stPopoverBody"] {{ width: 400px !important; }}
        </style>
    """, unsafe_allow_html=True)

    # --- 4. DATA ---
    df_squad = df.copy()
    df_squad.columns = [str(c).strip().upper() for c in df_squad.columns]
    df_squad['POS'] = pd.to_numeric(df_squad['POS'], errors='coerce')
    
    idag = datetime.now()
    if 'CONTRACT' in df_squad.columns:
        df_squad['CONTRACT_DT'] = pd.to_datetime(df_squad['CONTRACT'], dayfirst=True, errors='coerce')
        df_squad['DAYS_LEFT'] = (df_squad['CONTRACT_DT'] - idag).dt.days

    # --- 5. LAYOUT ---
    col_pitch, col_menu = st.columns([5, 1], gap="medium")

    with col_menu:
        # --- POPOVER MED HTML TABEL ---
        with st.popover("Vis Kontrakter", use_container_width=True):
            tabel_rows = ""
            for _, r in df_squad.sort_values('NAVN').iterrows():
                bg = "transparent"
                days = r.get('DAYS_LEFT', 999)
                if str(r.get('PRIOR', '')).upper() == 'L': bg = leje_gra
                elif pd.notna(days):
                    if days < 183: bg = rod_udlob
                    elif days <= 365: bg = gul_udlob
                
                tabel_rows += f'''
                <tr style="background-color:{bg}; border-bottom:1px solid #f2f2f2;">
                    <td style="padding:8px; font-weight:600;">{r['NAVN']}</td>
                    <td style="padding:8px; text-align:right;">{r['CONTRACT'] if pd.notna(r['CONTRACT']) else "-"}</td>
                </tr>'''

            # VIKTIGT: textwrap.dedent fjerner indrykning så det ikke bliver til en kodeblok
            fuld_tabel_html = textwrap.dedent(f'''
                <table style="width:100%; border-collapse:collapse; font-family:sans-serif; font-size:13px;">
                    <thead>
                        <tr style="background:#fafafa; border-bottom:2px solid {hif_rod};">
                            <th style="padding:8px; text-align:left; color:#888; font-size:10px; text-transform:uppercase;">Spiller</th>
                            <th style="padding:8px; text-align:right; color:#888; font-size:10px; text-transform:uppercase;">Udløb</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tabel_rows}
                    </tbody>
                </table>
            ''')
            st.markdown(fuld_tabel_html, unsafe_allow_html=True)
        
        st.write("---")
        for f in ["3-4-3", "4-3-3", "3-5-2"]:
            if st.button(f, use_container_width=True, type="primary" if st.session_state.formation_valg == f else "secondary"):
                st.session_state.formation_valg = f
                st.rerun()

    with col_pitch:
        # Pitch koden herunder (uændret)...
        pitch = Pitch(pitch_type='statsbomb', pitch_color='#ffffff', line_color='#333', linewidth=1)
        fig, ax = pitch.draw(figsize=(12, 9))
        
        # (Resten af din pitch-logik med ax.text for spillere...)
        st.pyplot(fig, use_container_width=True)
