import streamlit as st
import pandas as pd

def vis_side(df):
    st.title("Trupsammensætning & Taktisk Overblik")

    if df is None:
        st.error("Ingen data fundet.")
        return

    # --- 1. DATAVASK ---
    df_squad = df.copy()
    df_squad.columns = [str(c).strip().upper() for c in df_squad.columns]

    # Sikr at POS er tal og PRIOR er rensede bogstaver
    df_squad['POS'] = pd.to_numeric(df_squad['POS'], errors='coerce')
    df_squad['PRIOR'] = df_squad['PRIOR'].astype(str).str.strip().str.upper()

    # --- 2. FORMATIONS VÆLGER ---
    form_valg = st.radio("Vælg Formation:", ["4-3-3", "3-5-2"], horizontal=True)

    # Definition af koordinater (Række 0-4, Kolonne 0-4)
    if form_valg == "4-3-3":
        pos_config = {
            1: (4, 2, 'MM'), 5: (3, 0, 'VB'), 4: (3, 1, 'VCB'), 3: (3, 3, 'HCB'), 2: (3, 4, 'HB'),
            6: (2, 2, 'DM'), 8: (1, 1, 'VCM'), 10: (1, 3, 'HCM'), 11: (0, 0, 'VW'), 9: (0, 2, 'ANG'), 7: (0, 4, 'HW')
        }
    else: # 3-5-2
        pos_config = {
            1: (4, 2, 'MM'), 4: (3, 1, 'VCB'), 3: (3, 2, 'CB'), 2: (3, 3, 'HCB'),
            5: (2, 0, 'VWB'), 6: (2, 2, 'DM'), 7: (2, 4, 'HWB'), 8: (1, 1, 'CM'), 10: (1, 3, 'CM'),
            11: (0, 1, 'ANG'), 9: (0, 3, 'ANG')
        }

    # --- 3. CSS DESIGN ---
    st.markdown("""
        <style>
            .pitch {
                background-color: #2e7d32;
                background-image: linear-gradient(white 1px, transparent 1px), linear-gradient(90deg, white 1px, transparent 1px);
                background-size: 100% 20%;
                border: 2px solid white;
                border-radius: 10px;
                display: grid;
                grid-template-columns: repeat(5, 1fr);
                grid-template-rows: repeat(5, 140px);
                gap: 8px; padding: 10px;
            }
            .pos-zone { display: flex; flex-direction: column; align-items: center; justify-content: flex-start; }
            .player-card {
                background: white; border-left: 4px solid #0e3255; padding: 2px 6px;
                border-radius: 3px; margin-bottom: 2px; width: 95%; box-shadow: 0 1px 2px rgba(0,0,0,0.2);
                display: flex; justify-content: space-between;
            }
            .prior-tag { font-size: 9px; font-weight: bold; color: #cc0000; }
            .name-text { font-size: 10px; font-weight: 600; color: #333; }
            .label-text { color: white; font-size: 11px; font-weight: bold; text-shadow: 1px 1px 2px black; margin-bottom: 3px; }
        </style>
    """, unsafe_allow_html=True)

    # --- 4. RENDER BANE ---
    html = '<div class="pitch">'
    for r in range(5):
        for c in range(5):
            pos_num = next((p for p, coords in pos_config.items() if coords[0] == r and coords[1] == c), None)
            
            if pos_num:
                label = pos_config[pos_num][2]
                # Sorterer efter PRIOR (A -> B -> C)
                spillere = df_squad[df_squad['POS'] == pos_num].sort_values('PRIOR')
                
                html += f'<div class="pos-zone"><div class="label-text">{label}</div>'
                for _, p in spillere.iterrows():
                    navn = p.get('NAVN', f"{p.get('FIRSTNAME','')} {p.get('LASTNAME','')}")
                    prior = p['PRIOR'] if p['PRIOR'] != 'NAN' else '-'
                    html += f'<div class="player-card"><span class="name-text">{navn}</span><span class="prior-tag">{prior}</span></div>'
                html += '</div>'
            else:
                html += '<div></div>'
    
    html += '</div>'
    st.write(html, unsafe_allow_html=True)

    # Print-knap
    if st.button("🖨️ Gem som PDF"):
        st.write('<script>window.print();</script>', unsafe_allow_html=True)
