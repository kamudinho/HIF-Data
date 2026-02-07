import streamlit as st
import pandas as pd

def vis_side(df):
    st.title("Trupsammensætning & Taktisk Overblik")

    if df is None:
        st.error("Ingen data modtaget.")
        return

    # --- 1. DATAVASK ---
    df_squad = df.copy()
    # Rens overskrifter (fjerner mellemrum og gør store)
    df_squad.columns = [str(c).strip().upper() for c in df_squad.columns]

    # --- TJEK FOR DET NYE NAVN 'POS-TAL' ---
    # Vi tjekker efter 'POS-TAL' (som bliver 'POS-TAL' efter .upper())
    target_col = 'POS-TAL' 
    
    if target_col not in df_squad.columns:
        st.error(f"⚠️ Kunne ikke finde '{target_col}'.")
        st.write("Fundne kolonner lige nu:", list(df_squad.columns))
        return

    # Konverter til tal
    df_squad['POS_CLEAN'] = pd.to_numeric(df_squad[target_col], errors='coerce')
    
    # Håndtering af PRIOR (Hvis den ikke findes, laver vi en tom en så koden ikke dør)
    if 'PRIOR' in df_squad.columns:
        df_squad['PRIOR_CLEAN'] = df_squad['PRIOR'].astype(str).str.strip().str.upper()
    else:
        df_squad['PRIOR_CLEAN'] = 'B' # Default hvis kolonnen mangler

    # --- 2. POSITIONSMAPPING (1-11) ---
    pos_config = {
        1: (4, 2, 'MM'), 2: (3, 4, 'HB'), 3: (3, 3, 'HCB'), 4: (3, 1, 'VCB'),
        5: (3, 0, 'VB'), 6: (2, 2, 'DM'), 8: (1, 1, 'VCM'), 10: (1, 3, 'HCM'),
        7: (0, 4, 'HW'), 9: (0, 2, 'ANG'), 11: (0, 0, 'VW')
    }

    # --- 3. CSS DESIGN ---
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
                grid-template-rows: repeat(5, 140px);
                gap: 10px; padding: 15px;
            }
            .pos-zone { display: flex; flex-direction: column; align-items: center; justify-content: flex-start; }
            .player-card {
                background: white; border-left: 5px solid #0e3255; padding: 4px 8px;
                border-radius: 4px; margin-bottom: 3px; width: 95%; box-shadow: 1px 1px 3px rgba(0,0,0,0.2);
            }
            .prior-tag { font-size: 10px; font-weight: bold; color: #cc0000; margin-right: 5px; }
            .name-text { font-size: 11px; font-weight: 600; color: #333; }
            .label-text { color: white; font-size: 12px; font-weight: bold; text-shadow: 1px 1px 2px black; margin-bottom: 5px; }
        </style>
    """, unsafe_allow_html=True)

    # --- 4. RENDER BANEN ---
    html = '<div class="pitch">'
    for r in range(5):
        for c in range(5):
            pos_num = next((p for p, coords in pos_config.items() if coords[0] == r and coords[1] == c), None)
            
            if pos_num:
                label = pos_config[pos_num][2]
                # Filtrer spillere på denne position
                mask = df_squad['POS_CLEAN'] == pos_num
                spillere = df_squad[mask].sort_values('PRIOR_CLEAN')
                
                html += f'<div class="pos-zone"><div class="label-text">{label}</div>'
                for _, p in spillere.iterrows():
                    navn = p.get('NAVN', f"{p.get('FIRSTNAME','')} {p.get('LASTNAME','')}")
                    prior = p['PRIOR_CLEAN'] if p['PRIOR_CLEAN'] != 'NAN' else '-'
                    html += f'''
                        <div class="player-card">
                            <span class="prior-tag">{prior}</span>
                            <span class="name-text">{navn}</span>
                        </div>
                    '''
                html += '</div>'
            else:
                html += '<div></div>'
    
    html += '</div>'
    st.write(html, unsafe_allow_html=True)
    
    # Print funktion
    if st.button("🖨️ Gem overblik"):
        st.write('<script>window.print();</script>', unsafe_allow_html=True)
