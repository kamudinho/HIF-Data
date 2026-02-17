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
    hif_rod = "#df003b"
    gul_udlob = "#ffffcc"
    leje_gra = "#d3d3d3"
    rod_udlob = "#ffcccc"

    # --- 3. CSS INJECTION (Højrestillet menu & Tabel-styling fra players.py) ---
    st.markdown(f"""
        <style>
            .block-container {{ padding-top: 1rem !important; max-width: 98% !important; }}
            
            /* Højrestil menu-kolonnen */
            [data-testid="column"]:last-child {{
                display: flex;
                flex-direction: column;
                align-items: flex-end !important;
            }}

            /* Pill Button Styling */
            div.stButton > button {{
                border-radius: 20px !important;
                border: 1px solid #ddd !important;
                background-color: white !important;
                color: #333 !important;
                padding: 4px 15px !important;
                width: 120px !important;
                transition: all 0.2s;
            }}
            div.stButton > button[kind="primary"] {{
                background-color: white !important;
                color: {hif_rod} !important;
                border: 2px solid {hif_rod} !important;
                font-weight: bold !important;
            }}

            /* Popover-vindue styling */
            [data-testid="stPopoverBody"] {{ width: 400px !important; padding: 0px !important; }}
            
            /* Tabel-stil magen til players.py */
            .squad-tabel {{
                width: 100%;
                border-collapse: collapse;
                font-family: sans-serif;
                font-size: 13px;
            }}
            .squad-tabel tr {{ border-bottom: 1px solid #f2f2f2; }}
            .squad-tabel th {{
                background: #fafafa;
                border-bottom: 2px solid {hif_rod};
                color: #888;
                font-size: 10px;
                text-transform: uppercase;
                padding: 8px 10px;
                text-align: left;
            }}
            .squad-tabel td {{ padding: 8px 10px; color: #222; }}
        </style>
    """, unsafe_allow_html=True)

    # --- 4. BRANDING ---
    st.markdown(f"""
        <div style="background-color:{hif_rod}; padding:10px; border-radius:4px; margin-bottom:20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; letter-spacing:1px; font-size:1.1rem; text-transform:uppercase;">TAKTIK & KONTRAKTER</h3>
        </div>
    """, unsafe_allow_html=True)

    # --- 5. DATA-PROCESSERING ---
    df_squad = df.copy()
    df_squad.columns = [str(c).strip().upper() for c in df_squad.columns]
    df_squad['POS'] = pd.to_numeric(df_squad['POS'], errors='coerce')
    
    idag = datetime.now()
    if 'CONTRACT' in df_squad.columns:
        df_squad['CONTRACT_DT'] = pd.to_datetime(df_squad['CONTRACT'], dayfirst=True, errors='coerce')
        df_squad['DAYS_LEFT'] = (df_squad['CONTRACT_DT'] - idag).dt.days

    # --- 6. HOVED-LAYOUT ---
    col_pitch, col_menu = st.columns([5, 1], gap="medium")

    with col_menu:
        # --- HTML TABEL TIL POPOVER (RETTET) ---
        with st.popover("Vis Kontrakter", use_container_width=True):
            # Vi bygger rækkerne først som en samlet streng
            tabel_rows = ""
            for _, r in df_squad.sort_values('NAVN').iterrows():
                bg = "transparent"
                days = r.get('DAYS_LEFT', 999)
                if str(r.get('PRIOR', '')).upper() == 'L': 
                    bg = leje_gra
                elif pd.notna(days):
                    if days < 183: bg = rod_udlob
                    elif days <= 365: bg = gul_udlob
                
                kontrakt_str = r['CONTRACT'] if pd.notna(r['CONTRACT']) else "-"
                
                tabel_rows += f'''
                    <tr style="background-color:{bg}; border-bottom: 1px solid #f2f2f2;">
                        <td style="padding: 8px 10px; font-weight:600; color: #222;">{r['NAVN']}</td>
                        <td style="padding: 8px 10px; text-align:right; color: #222;">{kontrakt_str}</td>
                    </tr>
                '''

            # Saml det hele og send til markdown
            fuld_tabel_html = f'''
                <table style="width:100%; border-collapse: collapse; font-family: sans-serif; font-size: 13px;">
                    <thead>
                        <tr style="background: #fafafa; border-bottom: 2px solid {hif_rod};">
                            <th style="padding: 8px 10px; text-align: left; color: #888; font-size: 10px; text-transform: uppercase;">Spiller</th>
                            <th style="padding: 8px 10px; text-align: right; color: #888; font-size: 10px; text-transform: uppercase;">Udløb</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tabel_rows}
                    </tbody>
                </table>
            '''
            
            st.markdown(fuld_tabel_html, unsafe_allow_html=True)
        
        st.write("---")
        formations = ["3-4-3", "4-3-3", "3-5-2"]
        for f in formations:
            if st.button(f, use_container_width=True, type="primary" if st.session_state.formation_valg == f else "secondary"):
                st.session_state.formation_valg = f
                st.rerun()

    with col_pitch:
        # Pitch Render (Bane-logikken forbliver den samme stærke version)
        pitch = Pitch(pitch_type='statsbomb', pitch_color='#ffffff', line_color='#333333', linewidth=1)
        fig, ax = pitch.draw(figsize=(12, 9))
        
        # Legend
        legend_items = [(rod_udlob, "< 6 mdr"), (gul_udlob, "6-12 mdr"), (leje_gra, "Leje")]
        for i, (color, text) in enumerate(legend_items):
            ax.text(1, 2 + (i * 3), text, size=8, color="black", va='center', ha='left', 
                    fontweight='bold', bbox=dict(facecolor=color, edgecolor='#ccc', boxstyle='round,pad=0.2'))

        # Formation rendering...
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
                ax.text(x_pos, y_pos - 4.5, f" {label} ", size=10, color="white", va='center', ha='center', fontweight='bold',
                        bbox=dict(facecolor=hif_rod, edgecolor='white', boxstyle='round,pad=0.2'))
                for i, (_, p) in enumerate(spillere_pos.iterrows()):
                    # Match farve på banen med tabellen
                    days_p = p.get('DAYS_LEFT', 999)
                    bg_p = "white"
                    if str(p.get('PRIOR', '')).upper() == 'L': bg_p = leje_gra
                    elif pd.notna(days_p):
                        if days_p < 183: bg_p = rod_udlob
                        elif days_p <= 365: bg_p = gul_udlob
                    
                    ax.text(x_pos, (y_pos - 1.5) + (i * 2.2), f" {p['NAVN']} ", size=9, 
                            color="black", va='top', ha='center', fontweight='bold',
                            bbox=dict(facecolor=bg_p, edgecolor='#333', boxstyle='square,pad=0.2', linewidth=0.5))

        st.pyplot(fig, use_container_width=True)
