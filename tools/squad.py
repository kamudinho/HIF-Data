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

    # --- 2. DATA-PROCESSERING ---
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
        if days < 182: return '#ff4b4b' 
        if days <= 365: return '#fffd8d' 
        return 'white'

    # --- 3. TOP MENU MED ZOOM-KNAP ---
    # Vi tilføjer col_zoom til rækken
    col1, col2, col3, col_zoom, col_spacer, col_pop = st.columns([0.4, 0.4, 0.4, 0.6, 2.7, 1.0])
    
    formations = ["3-4-3", "4-3-3", "3-5-2"]
    cols = [col1, col2, col3]

    for i, f in enumerate(formations):
        with cols[i]:
            if st.button(f, use_container_width=True, type="primary" if st.session_state.formation_valg == f else "secondary"):
                st.session_state.formation_valg = f
                st.rerun()

    with col_zoom:
        # En toggle-knap til at styre størrelsen
        zoom = st.toggle("🔍 Zoom", value=False)

    with col_pop:
        with st.popover("Kontrakter", use_container_width=True):
            df_table = df_squad[['NAVN', 'CONTRACT']].copy()
            df_table['CONTRACT'] = df_table['CONTRACT'].apply(lambda x: x.strftime('%d-%m-%Y') if pd.notnull(x) else "N/A")
            st.dataframe(df_table, hide_index=True, use_container_width=True)

    # --- 4. DYNAMISK STØRRELSE (Zoom logik) ---
    if zoom:
        # Stor bane: fylder næsten det hele
        _, col_main, _ = st.columns([0.01, 9.98, 0.01])
        fig_size = (14, 7)
        font_size = 6.5
    else:
        # Lille bane: centreret og smal (fylder kun ca. 60% af skærmen)
        _, col_main, _ = st.columns([1.5, 8, 1.5])
        fig_size = (12, 8) # Mere kvadratisk når den er lille
        font_size = 8

    with col_main:
        pitch = Pitch(pitch_type='statsbomb', pitch_color='#ffffff', line_color='#000000', pad_top=0, pad_bottom=0)
        fig, ax = pitch.draw(figsize=fig_size)
        
        # Legend
        legend_items = [("#ff4b4b", "< 6 mdr"), ("#fffd8d", "6-12 mdr"), ("#d3d3d3", "Leje")]
        for i, (color, text) in enumerate(legend_items):
            ax.text(5 + (i * 18), 2, text, size=font_size-1, color="black", va='center', ha='left', 
                    fontweight='bold', bbox=dict(facecolor=color, edgecolor='black', boxstyle='square,pad=0.2'))

        # Formationer (brug eksisterende pos_config logik her...)
        form_valg = st.session_state.formation_valg
        # [Her indsættes pos_config logikken fra tidligere svar]
        if form_valg == "3-4-3":
            pos_config = {1: (10, 40, 'MM'), 4: (33, 22, 'VCB'), 3: (33, 40, 'CB'), 2: (33, 58, 'HCB'),
                          5: (55, 10, 'VWB'), 6: (55, 30, 'DM'), 8: (55, 50, 'DM'), 7: (55, 70, 'HWB'), 
                          11: (85, 15, 'VW'), 9: (108, 40, 'ANG'), 10: (85, 65, 'HW')}
        elif form_valg == "4-3-3":
            pos_config = {1: (10, 40, 'MM'), 5: (35, 10, 'VB'), 4: (33, 25, 'VCB'), 3: (33, 55, 'HCB'), 2: (35, 70, 'HB'),
                          6: (55, 40, 'DM'), 8: (65, 25, 'VCM'), 10: (65, 55, 'HCM'),
                          11: (80, 15, 'VW'), 9: (100, 40, 'ANG'), 7: (80, 65, 'HW')}
        else: # 3-5-2
            pos_config = {1: (10, 40, 'MM'), 4: (33, 22, 'VCB'), 3: (33, 40, 'CB'), 2: (33, 58, 'HCB'),
                          5: (55, 10, 'VWB'), 6: (55, 40, 'DM'), 7: (55, 70, 'HWB'), 
                          8: (65, 25, 'CM'), 10: (65, 55, 'CM'), 11: (100, 25, 'ANG'), 9: (100, 55, 'ANG')}

        for pos_num, coords in pos_config.items():
            x_pos, y_pos, label = coords
            spillere_pos = df_squad[df_squad['POS'] == pos_num].sort_values('PRIOR')
            if not spillere_pos.empty:
                ax.text(x_pos, y_pos - 4, f" {label} ", size=font_size+1, color="white", va='center', ha='center', fontweight='bold',
                        bbox=dict(facecolor='#df003b', edgecolor='white', boxstyle='round,pad=0.2'))
                for i, (_, p) in enumerate(spillere_pos.iterrows()):
                    bg_color = get_status_color(p)
                    ax.text(x_pos, (y_pos - 1.2) + (i * 2.8), f" {p['NAVN']} ".ljust(18), size=font_size, 
                            va='top', ha='center', family='monospace', bbox=dict(facecolor=bg_color, edgecolor='black', boxstyle='square,pad=0.1'))

        plt.subplots_adjust(left=0, right=1, bottom=0, top=1)
        st.pyplot(fig, use_container_width=True)
