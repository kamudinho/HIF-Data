import streamlit as st
import pandas as pd
import numpy as np

def vis_side(df):
    st.title("Squad Depth & Taktisk Overblik")

    # --- 1. DATAVASK ---
    df_squad = df.copy()
    df_squad.columns = [c.upper() for c in df_squad.columns]
    
    # Sørg for at POS og PRIOR er tal/strenge vi kan arbejde med
    df_squad['POS'] = pd.to_numeric(df_squad['POS'], errors='coerce')
    df_squad['PRIOR'] = df_squad['PRIOR'].astype(str).str.upper().replace('NAN', '-')

    # Navne-håndtering
    if 'NAVN' in df_squad.columns:
        df_squad['NAVN_DISPLAY'] = df_squad['NAVN']
    else:
        df_squad['NAVN_DISPLAY'] = (df_squad['FIRSTNAME'].fillna('') + " " + df_squad['LASTNAME'].fillna('')).str.title()

    # --- 2. KLASSISK POSITIONSMAPPING (1-11) ---
    # Her definerer vi hvor på 5x5 griddet tallene lander
    pos_config = {
        1:  (4, 2, 'MM'),    # Målmand
        2:  (3, 4, 'HB'),    # Højre Back
        3:  (3, 3, 'HCB'),   # Højre Centerback
        4:  (3, 1, 'VCB'),   # Venstre Centerback
        5:  (3, 0, 'VB'),    # Venstre Back
        6:  (2, 2, 'DM'),    # Defensiv Midt
        8:  (1, 1, 'VCM'),   # Venstre Central Midt
        10: (1, 3, 'HCM'),   # Højre Central Midt
        7:  (0, 4, 'HW'),    # Højre Wing
        9:  (0, 2, 'ANG'),   # Angriber
        11: (0, 0, 'VW')     # Venstre Wing
    }

    # --- 3. CSS STYLING ---
    st.markdown("""
        <style>
            .pitch {
                background-color: #2e7d32;
                background-image: linear-gradient(rgba(255,255,255,0.05) 2px, transparent 2px), 
                                  linear-gradient(90deg, rgba(255,255,255,0.05) 2px, transparent 2px);
                background-size: 100% 20%;
                border: 2px solid white;
                border-radius: 10px;
                display: grid;
                grid-template-columns: repeat(5, 1fr);
                grid-template-rows: repeat(5, 140px);
                gap: 8px;
                padding: 15px;
            }
            .pos-zone { display: flex; flex-direction: column; align-items: center; justify-content: flex-start; }
            .player-card {
                background: white; border-left: 4px solid #0e3255; padding: 4px 6px;
                border-radius: 4px; margin-bottom: 3px; width: 90%; box-shadow: 0 1px 3px rgba(0,0,0,0.15);
            }
            .prior-tag { font-size: 10px; font-weight: bold; color: #cc0000; margin-right: 6px; }
            .name-text { font-size: 11px; font-weight: 600; color: #1f1f1f; }
            .label-text { color: #ffffff; font-size: 12px; font-weight: 800; text-shadow: 1px 1px 2px #000; margin-bottom: 6px; }
        </style>
    """, unsafe_allow_html=True)

    # --- 4. RENDER BANEN ---
    html = '<div class="pitch">'
    placed_ids = []

    for r in range(5):
        for c in range(5):
            # Find ud af hvilket POS-nummer der skal ligge her
            pos_num = next((p for p, coords in pos_config.items() if coords[0] == r and coords[1] == c), None)
            
            if pos_num:
                label = pos_config[pos_num][2]
                spillere = df_squad[df_squad['POS'] == pos_num].sort_values('PRIOR')
                placed_ids.extend(spillere.index.tolist())
                
                html += f'<div class="pos-zone"><div class="label-text">{label}</div>'
                for _, p in spillere.iterrows():
                    html += f'<div class="player-card"><span class="prior-tag">{p["PRIOR"]}</span><span class="name-text">{p["NAVN_DISPLAY"]}</span></div>'
                html += '</div>'
            else:
                html += '<div></div>'
    
    html += '</div>'
    st.write(html, unsafe_allow_html=True)

    # --- 5. RESERVE-LISTE (Spillere uden gyldig POS) ---
    reserver = df_squad[~df_squad.index.isin(placed_ids)]
    if not reserver.empty:
        st.write("---")
        st.subheader("Øvrige spillere (Uden POS 1-11)")
        cols = st.columns(4)
        for i, (_, p) in enumerate(reserver.iterrows()):
            cols[i % 4].info(f"**{p['NAVN_DISPLAY']}** (Pos: {p['POS'] if pd.notnull(p['POS']) else '?'})")

    # Print knap
    st.button("🖨️ Gem som PDF / Print", on_click=lambda: st.write('<script>window.print();</script>', unsafe_allow_html=True))
