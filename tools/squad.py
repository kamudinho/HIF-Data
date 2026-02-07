import streamlit as st
import pandas as pd
import numpy as np


def vis_taktisk_trup(df):
    st.title("Squad Depth & Formation")

    # --- 1. FORMATIONS DEFINITIONER ---
    formations = {
        "4-3-3": {
            1: (4, 2, 'MM'), 5: (3, 0, 'VB'), 3: (3, 1, 'VCB'), 4: (3, 3, 'HCB'), 2: (3, 4, 'HB'),
            6: (2, 2, 'DM'), 8: (1, 1, 'VCM'), 10: (1, 3, 'HCM'), 11: (0, 0, 'VW'), 9: (0, 2, 'ANG'), 7: (0, 4, 'HW')
        },
        "3-5-2": {
            1: (4, 2, 'MM'), 5: (3, 1, 'VCB'), 3: (3, 2, 'CB'), 4: (3, 3, 'HCB'),
            2: (2, 4, 'HWB'), 6: (2, 2, 'DM'), 8: (1, 1, 'CM'), 10: (1, 3, 'CM'), 11: (2, 0, 'VWB'),
            9: (0, 1, 'V-ANG'), 7: (0, 3, 'H-ANG')
        },
        "3-4-3": {
            1: (4, 2, 'MM'), 5: (3, 1, 'VCB'), 3: (3, 2, 'CB'), 4: (3, 3, 'HCB'),
            2: (2, 4, 'HWB'), 6: (2, 1, 'CM'), 8: (2, 3, 'CM'), 11: (2, 0, 'VWB'),
            9: (0, 2, 'ANG'), 10: (0, 3, 'H-W'), 7: (0, 1, 'V-W')
        }
    }

    # --- 2. UI KONTROL ---
    col_ctrl1, col_ctrl2 = st.columns([2, 1])
    with col_ctrl1:
        valgt_form = st.selectbox("Vælg Formation", list(formations.keys()))
    with col_ctrl2:
        # Knap til at trigge browserens print-dialog (nemmeste måde at gemme som PDF/Billede)
        st.write(" ")  # Spacer
        st.button("🖨️ Gem som PDF",
                  on_click=lambda: st.write('<script>window.print();</script>', unsafe_allow_html=True))

    pos_config = formations[valgt_form]

    # --- 3. CSS (Både til skærm og print) ---
    st.markdown("""
        <style>
            @media print {
                .stApp { background: white !important; }
                .no-print { display: none !important; }
            }
            .pitch {
                background-color: #2e7d32;
                background-image: linear-gradient(white 1px, transparent 1px), linear-gradient(90deg, white 1px, transparent 1px);
                background-size: 100% 20%;
                border: 3px solid white;
                border-radius: 15px;
                display: grid;
                grid-template-columns: repeat(5, 1fr);
                grid-template-rows: repeat(5, 150px);
                gap: 10px;
                padding: 15px;
                width: 100%;
            }
            .pos-zone { display: flex; flex-direction: column; align-items: center; justify-content: flex-start; }
            .player-card {
                background: white; border-left: 4px solid #1e3d59; padding: 2px 6px;
                border-radius: 3px; margin-bottom: 2px; width: 95%; box-shadow: 0 1px 2px rgba(0,0,0,0.2);
            }
            .prior-tag { font-size: 10px; font-weight: bold; color: #d32f2f; margin-right: 5px; }
            .name-text { font-size: 11px; font-weight: 600; color: #333; }
            .label-text { color: white; font-size: 12px; font-weight: bold; text-shadow: 1px 1px 2px black; margin-bottom: 5px; }
        </style>
    """, unsafe_allow_html=True)

    # --- 4. RENDER BANE ---
    html = '<div class="pitch">'
    for r in range(5):
        for c in range(5):
            current_pos = next((p for p, coords in pos_config.items() if coords[0] == r and coords[1] == c), None)

            if current_pos:
                label = pos_config[current_pos][2]
                # Filtrer spillere baseret på POS tallet
                spillere = df[df['POS'] == current_pos].sort_values('PRIOR')

                html += f'<div class="pos-zone"><div class="label-text">{label}</div>'
                for _, p in spillere.iterrows():
                    prior = str(p['PRIOR']) if pd.notnull(p['PRIOR']) else '-'
                    html += f'<div class="player-card"><span class="prior-tag">{prior}</span><span class="name-text">{p["NAVN_FINAL"]}</span></div>'
                html += '</div>'
            else:
                html += '<div></div>'

    html += '</div>'
    st.write(html, unsafe_allow_html=True)

    st.info("💡 Tip: Brug 'Gem som PDF' for at eksportere banen til et dokument eller print.")