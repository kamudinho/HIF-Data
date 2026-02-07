import streamlit as st
import pandas as pd
import numpy as np

def vis_side(df):
    st.title("Squad Depth & Taktisk Overblik")

    if df is None or df.empty:
        st.error("Dataframen er tom eller ikke indlæst korrekt.")
        return

    # --- 1. ROBUST RENSNING AF KOLONNER ---
    df_squad = df.copy()
    
    # Vi fjerner alt "støj" fra kolonnenavne (mellemrum, linjeskift) og gør dem store
    df_squad.columns = df_squad.columns.str.strip().str.upper()
    
    # Tjek om 'POS' findes efter rensning
    if 'POS' not in df_squad.columns:
        st.error(f"Kolonnen 'POS' mangler. Fundne kolonner: {list(df_squad.columns)}")
        return

    # Konverter POS og PRIOR til korrekte formater
    df_squad['POS'] = pd.to_numeric(df_squad['POS'], errors='coerce')
    df_squad['PRIOR'] = df_squad['PRIOR'].astype(str).str.strip().str.upper()

    # --- 2. POSITIONSMAPPING (Baseret på dit billede) ---
    # Vi bruger 5x5 grid: (Række, Kolonne)
    # Række 0=Top, 4=Bund | Kolonne 0=Venstre, 4=Højre
    pos_config = {
        5:  (4, 2, 'GKP'), # Tobias Skov
        10: (4, 1, 'GKP'), # Sixten Rasmussen
        11: (3, 0, 'DEF'), # Marius Riis
        9:  (3, 1, 'DEF'), # Frederik Byrrisen
        6:  (3, 3, 'DEF'), # Magnus Carstensen / Andreas Bahne
        2:  (3, 4, 'DEF'), # Semih Sevik (markeret som POS 2)
        1:  (2, 2, 'MID'), # Mads Bonde Haar / Calle Mohr-Pedersen
        3:  (2, 1, 'MID'), # Casper Risbjerg / Jonathan Bisgaard
        7:  (2, 3, 'MID'), # Silas Degn
        4:  (1, 1, 'MID'), # Emil Knoldsborg
        8:  (0, 2, 'FWD')  # Noah Lakman
    }

    # --- 3. CSS DESIGN ---
    st.markdown("""
        <style>
            .pitch {
                background-color: #5d8233;
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
                background: white; border-left: 5px solid #cc0000; padding: 4px 8px;
                border-radius: 4px; margin-bottom: 4px; width: 90%; box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
            }
            .prior-tag { font-size: 10px; font-weight: bold; color: #cc0000; margin-right: 5px; }
            .name-text { font-size: 11px; font-weight: 600; color: #333; }
            .label-text { color: white; font-size: 13px; font-weight: bold; text-shadow: 1px 1px 2px black; margin-bottom: 5px; }
        </style>
    """, unsafe_allow_html=True)

    # --- 4. RENDERING AF BANEN ---
    html = '<div class="pitch">'
    for r in range(5):
        for c in range(5):
            # Find hvilken position (POS nr) der skal være i dette felt
            pos_num = next((p for p, coords in pos_config.items() if coords[0] == r and coords[1] == c), None)
            
            if pos_num:
                label = pos_config[pos_num][2]
                spillere = df_squad[df_squad['POS'] == pos_num].sort_values('PRIOR')
                
                html += f'<div class="pos-zone"><div class="label-text">{label} ({pos_num})</div>'
                for _, p in spillere.iterrows():
                    navn = p['NAVN'] if pd.notnull(p['NAVN']) else f"{p['FIRSTNAME']} {p['LASTNAME']}"
                    html += f'''
                        <div class="player-card">
                            <span class="prior-tag">{p['PRIOR']}</span>
                            <span class="name-text">{navn}</span>
                        </div>
                    '''
                html += '</div>'
            else:
                html += '<div></div>'
    
    html += '</div>'
    st.write(html, unsafe_allow_html=True)
