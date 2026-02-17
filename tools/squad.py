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
    hif_rod = "#df003b"  # Justeret til din præcise røde farve
    gul_udlob = "#ffffcc" # Matcher din 'players' farve
    leje_gra = "#f2f2f2"  # Matcher din tabel-baggrund

    # --- 3. GLOBAL CSS & BRANDING ---
    st.markdown(f"""
        <style>
            .block-container {{ padding-top: 1rem !important; max-width: 98% !important; }}
            [data-testid="stPopoverBody"] {{ width: 380px !important; }}
            
            /* Pill Button Styling (Ligesom i Top 5) */
            .pill-container {{
                display: flex;
                gap: 8px;
                margin-bottom: 15px;
            }}
            .pill-button {{
                padding: 6px 16px;
                border-radius: 20px;
                border: 1px solid #ddd;
                background-color: white;
                cursor: pointer;
                font-size: 13px;
                transition: all 0.2s;
            }}
            .pill-active {{
                background-color: {hif_rod};
                color: white;
                border-color: {hif_rod};
            }}
        </style>
    """, unsafe_allow_html=True)

    # BRANDING HEADER
    st.markdown(f"""
        <div style="background-color:{hif_rod}; padding:10px; border-radius:4px; margin-bottom:20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; letter-spacing:1px; font-size:1.1rem; text-transform:uppercase;">TAKTIK & KONTRAKTER</h3>
            <p style="color:white; margin:0; text-align:center; font-size:12px; opacity:0.8;">Hvidovre IF | Trupstyring</p>
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
        if row['PRIOR'] == 'L': return "#d3d3d3" # Lys grå til leje
        days = row.get('DAYS_LEFT', 999)
        if pd.isna(days): return 'white'
        if days < 183: return "#ffcccc" # Rød match fra players
        if days <= 365: return "#ffffcc" # Gul match fra players
        return 'white'

    # --- 5. HOVED-LAYOUT ---
    # Vi laver knapperne i en række over banen nu, ligesom på de andre sider
    formations = ["3-4-3", "4-3-3", "3-5-2"]
    
    # Render knapper som Streamlit columns for at de fungerer interaktivt
    cols = st.columns([1, 1, 1, 3, 2])
    for i, f in enumerate(formations):
        with cols[i]:
            is_active = st.session_state.formation_valg == f
            if st.button(f, use_container_width=True, type="primary" if is_active else "secondary"):
                st.session_state.formation_valg = f
                st.rerun()

    with cols[4]:
        with st.popover("Vis Kontrakter", use_container_width=True):
            df_display = df_squad[['NAVN', 'CONTRACT', 'PRIOR', 'DAYS_LEFT']].copy()
            # Styling af rækker til popover
            def style_df(row):
                bg = get_status_color(row)
                return [f'background-color: {bg}'] * len(row) if bg != 'white' else [''] * len(row)
            
            st.dataframe(
                df_display.style.apply(style_df, axis=1),
                column_order=("NAVN", "CONTRACT"),
                column_config={
                    "NAVN": st.column_config.TextColumn("Navn"),
                    "CONTRACT": st.column_config.DateColumn("Udløb", format="DD-MM-YYYY"),
                },
                hide_index=True,
                use_container_width=True,
                height=400
            )

    # --- 6. PITCH RENDER ---
    pitch = Pitch(pitch_type='statsbomb', pitch_color='#ffffff', line_color='#000000', pad_top=0, pad_bottom=0, pad_left=1, pad_right=1)
    fig, ax = pitch.draw(figsize=(14, 10))
    
    # Legend på banen
    legend_items = [("#ffcccc", "< 6 mdr"), ("#ffffcc", "6-12 mdr"), ("#d3d3d3", "Leje")]
    for i, (color, text) in enumerate(legend_items):
        ax.text(1 + (i * 12), 2.5, text, size=11, color="black", va='center', ha='left', 
                fontweight='bold', bbox=dict(facecolor=color, edgecolor='black', boxstyle='square,pad=0.2'))

    form_valg = st.session_state.formation_valg
    # Formation configs (MM, Backs, Midt, Ang)
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
            ax.text(x_pos, y_pos - 5, f" {label} ", size=12, color="white", va='center', ha='center', fontweight='bold',
                    bbox=dict(facecolor=hif_rod, edgecolor='white', boxstyle='round,pad=0.3'))
            
            for i, (_, p) in enumerate(spillere_pos.iterrows()):
                bg_color = get_status_color(p)
                visnings_tekst = f" {p['NAVN']} ".ljust(25)
                ax.text(x_pos, (y_pos - 1.8) + (i * 2.3), visnings_tekst, size=11, 
                        color="black", va='top', ha='center', family='monospace', fontweight='bold',
                        bbox=dict(facecolor=bg_color, edgecolor='black', boxstyle='square,pad=0.2', linewidth=1.0))

    plt.subplots_adjust(left=0, right=1, bottom=0, top=1)
    st.pyplot(fig, use_container_width=True)
