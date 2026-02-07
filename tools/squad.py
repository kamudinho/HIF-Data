import streamlit as st
import pandas as pd
import numpy as np

def vis_side(df):
    st.title("Squad Depth & Formation")

    # --- 1. DATAVASK (Vigtigt!) ---
    df_squad = df.copy()
    # Tving kolonnenavne til UPPERCASE
    df_squad.columns = [c.upper() for c in df_squad.columns]
    
    # Tjek om 'POS' findes, ellers tjek 'POS_TAL' eller lignende
    pos_col = 'POS' if 'POS' in df_squad.columns else None
    
    if not pos_col:
        st.error(f"Kunne ikke finde kolonnen 'POS'. Fundne kolonner: {list(df_squad.columns)}")
        return

    # Gør POS-kolonnen til heltal (hvis muligt) for at matche vores mapping
    df_squad[pos_col] = pd.to_numeric(df_squad[pos_col], errors='coerce')
    
    # --- 2. FORMATIONS DEFINITIONER ---
    formations = {
        "4-3-3": {
            1: (4, 2, 'MM'), 5: (3, 0, 'VB'), 3: (3, 1, 'VCB'), 4: (3, 3, 'HCB'), 2: (3, 4, 'HB'),
            6: (2, 2, 'DM'), 8: (1, 1, 'VCM'), 10: (1, 3, 'HCM'), 11: (0, 0, 'VW'), 9: (0, 2, 'ANG'), 7: (0, 4, 'HW')
        },
        "3-5-2": {
            1: (4, 2, 'MM'), 5: (3, 1, 'VCB'), 3: (3, 2, 'CB'), 4: (3, 3, 'HCB'),
            2: (2, 4, 'HWB'), 6: (2, 2, 'DM'), 8: (1, 1, 'CM'), 10: (1, 3, 'CM'), 11: (2, 0, 'VWB'),
            9: (0, 1, 'V-ANG'), 7: (0, 3, 'H-ANG')
        }
    }

    valgt_form = st.selectbox("Vælg Formation", list(formations.keys()))
    pos_config = formations[valgt_form]

    # --- 3. CSS ---
    st.markdown("""
        <style>
            .pitch {
                background-color: #2e7d32;
                background-image: linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), 
                                  linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px);
                background-size: 100% 20%;
                border: 3px solid white;
                border-radius: 15px;
                display: grid;
                grid-template-columns: repeat(5, 1fr);
                grid-template-rows: repeat(5, 150px);
                gap: 10px;
                padding: 15px;
            }
            .pos-zone { display: flex; flex-direction: column; align-items: center; justify-content: flex-start; }
            .player-card {
                background: white; border-left: 4px solid #1e3d59; padding: 4px;
                border-radius: 3px; margin-bottom: 2px; width: 95%; box-shadow: 0 1px 2px rgba(0,0,0,0.2);
            }
            .prior-tag { font-size: 10px; font-weight: bold; color: #d32f2f; margin-right: 5px; }
            .name-text { font-size: 11px; font-weight: 600; color: #333; }
            .label-text { color: white; font-size: 12px; font-weight: bold; text-shadow: 1px 1px 2px black; margin-bottom: 5px; }
        </style>
    """, unsafe_allow_html=True)

    # --- 4. RENDER ---
    html = '<div class="pitch">'
    for r in range(5):
        for c in range(5):
            # Find ud af hvilket POS-nummer der skal ligge på dette grid-felt
            current_pos_num = next((p for p, coords in pos_config.items() if coords[0] == r and coords[1] == c), None)
            
            if current_pos_num:
                label = pos_config[current_pos_num][2]
                # Filtrer spillere der matcher POS tallet
                spillere = df_squad[df_squad[pos_col] == current_pos_num].sort_values('PRIOR')
                
                html += f'<div class="pos-zone"><div class="label-text">{label}</div>'
                for _, p in spillere.iterrows():
                    prior = str(p['PRIOR']) if pd.notnull(p['PRIOR']) else '-'
                    html += f'<div class="player-card"><span class="prior-tag">{prior}</span><span class="name-text">{p["NAVN_FINAL"]}</span></div>'
                html += '</div>'
            else:
                html += '<div></div>'
    
    html += '</div>'
    st.write(html, unsafe_allow_html=True)

    # --- FEJLSØGNING (Kan slettes når det virker) ---
    with st.expander("Tjek data (Fejlsøgning)"):
        st.write("Unikke værdier i din POS kolonne:", df_squad[pos_col].unique())
        st.write("Eksempel på data:", df_squad[[pos_col, 'NAVN_FINAL', 'PRIOR']].head())
