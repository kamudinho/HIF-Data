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

    # --- 3. CSS & BRANDING (Synkroniseret med Players/Statistik) ---
    st.markdown(f"""
        <style>
            .block-container {{ padding-top: 1rem !important; max-width: 98% !important; }}
            
            /* Gør knapperne til "Pills" look */
            div.stButton > button {{
                border-radius: 20px !important;
                border: 1px solid #ddd !important;
                background-color: white !important;
                color: #333 !important;
                padding: 4px 20px !important;
                transition: all 0.3s ease;
            }}
            
            /* Den aktive knap (Primary) */
            div.stButton > button[kind="primary"] {{
                background-color: white !important;
                color: {hif_rod} !important;
                border: 2px solid {hif_rod} !important;
                font-weight: bold !important;
            }}

            div.stButton > button:hover {{
                border-color: {hif_rod} !important;
                color: {hif_rod} !important;
            }}

            [data-testid="stPopoverBody"] {{ width: 380px !important; }}
        </style>
    """, unsafe_allow_html=True)

    # BRANDING HEADER
    st.markdown(f"""
        <div style="background-color:{hif_rod}; padding:10px; border-radius:4px; margin-bottom:20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; letter-spacing:1px; font-size:1.1rem; text-transform:uppercase;">TAKTIK & KONTRAKTER</h3>
            <p style="color:white; margin:0; text-align:center; font-size:12px; opacity:0.8;">Hvidovre IF | Taktisk Oversigt</p>
        </div>
    """, unsafe_allow_html=True)

    # --- 4. DATA-PROCESSERING ---
    df_squad = df.copy()
    df_squad.columns = [str(c).strip().upper() for c in df_squad.columns]
    df_squad['POS'] = pd.to_numeric(df_squad['POS'], errors='coerce')
    df_squad['PRIOR'] = df_squad.get('PRIOR', '-').astype(str).str.strip().str.upper()

    idag = datetime.now()
    if 'CONTRACT' in df_squad.columns:
        df_squad['CONTRACT'] = pd.to_datetime(df_squad['CONTRACT'], dayfirst=True, errors='coerce')
        df_squad['DAYS_LEFT'] = (df_squad['CONTRACT'] - idag).dt.days

    def get_status_color(row):
        if row['PRIOR'] == 'L': return leje_gra
        days = row.get('DAYS_LEFT', 999)
        if pd.isna(days): return 'white'
        if days < 183: return "#ffcccc" # Lys rød (under 6 mdr)
        if days <= 365: return "#ffffcc" # Lys gul (under 1 år)
        return 'white'

    # --- 5. TOP MENU (Knapper og Popover) ---
    c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 2, 1.5])
    
    formations = ["3-4-3", "4-3-3", "3-5-2"]
    for i, f in enumerate(formations):
        with [c1, c2, c3][i]:
            if st.button(f, use_container_width=True, type="primary" if st.session_state.formation_valg == f else "secondary"):
                st.session_state.formation_valg = f
                st.rerun()

    with c5:
        with st.popover("Vis Kontrakter", use_container_width=True):
            df_display = df_squad[['NAVN', 'CONTRACT', 'PRIOR', 'DAYS_LEFT']].copy()
            st.dataframe(
                df_display.style.apply(lambda r: [f'background-color: {get_status_color(r)}']*len(r), axis=1),
                column_order=("NAVN", "CONTRACT"),
                column_config={
                    "NAVN": st.column_config.TextColumn("Navn"),
                    "CONTRACT": st.column_config.DateColumn("Udløb", format="DD.MM.YYYY"),
                },
                hide_index=True, use_container_width=True, height=400
            )

    st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)

    # --- 6. PITCH RENDER ---
    pitch = Pitch(pitch_type='statsbomb', pitch_color='#ffffff', line_color='#333333', linewidth=1)
    fig, ax = pitch.draw(figsize=(14, 10))
    
    # Legend
    legend_items = [("#ffcccc", "< 6 mdr"), ("#ffffcc", "6-12 mdr"), (leje_gra, "Leje")]
    for i, (color, text) in enumerate(legend_items):
        ax.text(1 + (i * 12), 2.5, text, size=10, color="black", va='center', ha='left', 
                fontweight='bold', bbox=dict(facecolor=color, edgecolor='#888', boxstyle='round,pad=0.2'))

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
            # Positions-label
            ax.text(x_pos, y_pos - 4.5, f" {label} ", size=11, color="white", va='center', ha='center', fontweight='bold',
                    bbox=dict(facecolor=hif_rod, edgecolor='white', boxstyle='round,pad=0.2'))
            
            # Spiller-navne
            for i, (_, p) in enumerate(spillere_pos.iterrows()):
                bg_color = get_status_color(p)
                ax.text(x_pos, (y_pos - 1.5) + (i * 2.2), f" {p['NAVN']} ", size=10, 
                        color="black", va='top', ha='center', fontweight='bold',
                        bbox=dict(facecolor=bg_color, edgecolor='#333', boxstyle='square,pad=0.2', linewidth=0.5))

    plt.subplots_adjust(left=0, right=1, bottom=0, top=1)
    st.pyplot(fig, use_container_width=True)
