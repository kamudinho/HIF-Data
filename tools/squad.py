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

    # --- 3. CSS INJECTION (Højrestillet menu & knap-styling) ---
    st.markdown(f"""
        <style>
            .block-container {{ padding-top: 1rem !important; max-width: 98% !important; }}
            
            /* Højrestil indhold i højre kolonne */
            [data-testid="column"]:last-child {{
                display: flex;
                flex-direction: column;
                align-items: flex-end !important;
                text-align: right;
            }}

            /* Pill Button Styling */
            div.stButton > button {{
                border-radius: 20px !important;
                border: 1px solid #ddd !important;
                background-color: white !important;
                color: #333 !important;
                padding: 4px 15px !important;
                width: 100px !important; /* Fast bredde for ensartet look i menuen */
                transition: all 0.2s;
            }}
            
            div.stButton > button[kind="primary"] {{
                background-color: white !important;
                color: {hif_rod} !important;
                border: 2px solid {hif_rod} !important;
                font-weight: bold !important;
            }}

            /* Popover bredde */
            [data-testid="stPopoverBody"] {{ width: 380px !important; }}
        </style>
    """, unsafe_allow_html=True)

    # --- 4. TOP BRANDING ---
    st.markdown(f"""
        <div style="background-color:{hif_rod}; padding:10px; border-radius:4px; margin-bottom:20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; letter-spacing:1px; font-size:1.1rem; text-transform:uppercase;">TAKTIK & KONTRAKTER</h3>
            <p style="color:white; margin:0; text-align:center; font-size:12px; opacity:0.8;">Hvidovre IF | Taktisk Oversigt</p>
        </div>
    """, unsafe_allow_html=True)

    # --- 5. DATA-PROCESSERING ---
    df_squad = df.copy()
    df_squad.columns = [str(c).strip().upper() for c in df_squad.columns]
    df_squad['POS'] = pd.to_numeric(df_squad['POS'], errors='coerce')
    
    idag = datetime.now()
    if 'CONTRACT' in df_squad.columns:
        df_squad['CONTRACT'] = pd.to_datetime(df_squad['CONTRACT'], dayfirst=True, errors='coerce')
        df_squad['DAYS_LEFT'] = (df_squad['CONTRACT'] - idag).dt.days

    def get_status_color(row):
        if str(row.get('PRIOR', '')).upper() == 'L': return leje_gra
        days = row.get('DAYS_LEFT', 999)
        if pd.isna(days): return 'white'
        if days < 183: return "#ffcccc"
        if days <= 365: return "#ffffcc"
        return 'white'

    # --- 6. HOVED-LAYOUT (Bane til venstre, Menu til højre) ---
    col_pitch, col_menu = st.columns([5, 1], gap="medium")

    with col_menu:
        # Popover øverst i menuen
        with st.popover("Kontrakter", use_container_width=True):
            df_display = df_squad[['NAVN', 'CONTRACT']].copy()
            st.dataframe(
                df_display.style.apply(lambda r: [f'background-color: {get_status_color(df_squad.loc[r.name])}']*len(r), axis=1),
                column_config={
                    "NAVN": st.column_config.TextColumn("Navn"),
                    "CONTRACT": st.column_config.DateColumn("Udløb", format="DD.MM.YYYY"),
                },
                hide_index=True, use_container_width=True, height=450
            )
        
        st.write("---")
        st.caption("Formation")
        # Vertikale knapper til højre
        formations = ["3-4-3", "4-3-3", "3-5-2"]
        for f in formations:
            if st.button(f, use_container_width=True, type="primary" if st.session_state.formation_valg == f else "secondary"):
                st.session_state.formation_valg = f
                st.rerun()

    with col_pitch:
        # Pitch Render
        pitch = Pitch(pitch_type='statsbomb', pitch_color='#ffffff', line_color='#333333', linewidth=1)
        fig, ax = pitch.draw(figsize=(12, 9))
        
        # Legend (Lille og diskret i hjørnet)
        legend_items = [("#ffcccc", "< 6 mdr"), ("#ffffcc", "6-12 mdr"), (leje_gra, "Leje")]
        for i, (color, text) in enumerate(legend_items):
            ax.text(1, 2 + (i * 3), text, size=8, color="black", va='center', ha='left', 
                    fontweight='bold', bbox=dict(facecolor=color, edgecolor='#ccc', boxstyle='round,pad=0.2'))

        form_valg = st.session_state.formation_valg
        # Formation defineres her...
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
                    bg_color = get_status_color(p)
                    ax.text(x_pos, (y_pos - 1.5) + (i * 2.2), f" {p['NAVN']} ", size=9, 
                            color="black", va='top', ha='center', fontweight='bold',
                            bbox=dict(facecolor=bg_color, edgecolor='#333', boxstyle='square,pad=0.2', linewidth=0.5))

        plt.subplots_adjust(left=0, right=1, bottom=0, top=1)
        st.pyplot(fig, use_container_width=True)
