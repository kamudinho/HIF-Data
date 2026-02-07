import streamlit as st
import pandas as pd

def vis_side(df):
    st.title("Hvidovre IF - Taktisk Trupoverblik")

    if df is None:
        st.error("Ingen data fundet.")
        return

    # --- 1. DATAVASK ---
    df_squad = df.copy()
    df_squad.columns = [str(c).strip().upper() for c in df_squad.columns]

    if 'POS' not in df_squad.columns:
        st.error("Kunne ikke finde kolonnen 'POS'.")
        return

    df_squad['POS'] = pd.to_numeric(df_squad['POS'], errors='coerce')
    df_squad['PRIOR'] = df_squad.get('PRIOR', '-').astype(str).str.strip().str.upper()

    # --- 2. FORMATIONER ---
    form_valg = st.sidebar.radio("Vælg Formation:", ["4-3-3", "3-5-2", "3-4-3"])

    if form_valg == "4-3-3":
        pos_config = {
            1: (4, 2, 'MM'), 5: (3, 0, 'VB'), 4: (3, 1, 'VCB'), 3: (3, 3, 'HCB'), 2: (3, 4, 'HB'),
            6: (2, 2, 'DM'), 8: (1, 1, 'VCM'), 10: (1, 3, 'HCM'), 11: (0, 0, 'VW'), 9: (0, 2, 'ANG'), 7: (0, 4, 'HW')
        }
    elif form_valg == "3-5-2":
        pos_config = {
            1: (4, 2, 'MM'), 4: (3, 1, 'VCB'), 3: (3, 2, 'CB'), 2: (3, 3, 'HCB'),
            5: (2, 0, 'VWB'), 6: (2, 2, 'DM'), 7: (2, 4, 'HWB'), 8: (1, 1, 'CM'), 10: (1, 3, 'CM'),
            11: (0, 1, 'ANG'), 9: (0, 3, 'ANG')
        }
    else: # 3-4-3
        pos_config = {
            1: (4, 2, 'MM'), 4: (3, 1, 'VCB'), 3: (3, 2, 'CB'), 2: (3, 3, 'HCB'),
            5: (2, 0, 'VWB'), 6: (2, 1, 'CM'), 8: (2, 3, 'CM'), 7: (2, 4, 'HWB'),
            11: (0, 0, 'VW'), 9: (0, 2, 'ANG'), 10: (0, 4, 'HW')
        }

    # --- 3. CSS TIL RIGTIG FODBOLDBANE ---
    st.markdown("""
        <style>
            .pitch-container {
                position: relative;
                background-color: #38612e;
                background-image: repeating-linear-gradient(
                    0deg,
                    #38612e,
                    #38612e 40px,
                    #3c6932 40px,
                    #3c6932 80px
                );
                border: 4px solid white;
                border-radius: 5px;
                width: 100%;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                box-sizing: border-box;
                /* Pitch markings */
                overflow: hidden;
            }
            /* Midterlinje og cirkel */
            .pitch-container::before {
                content: "";
                position: absolute;
                top: 50%; left: 0; right: 0;
                height: 2px; background: rgba(255,255,255,0.5);
                z-index: 1;
            }
            .pitch-circle {
                position: absolute;
                top: 50%; left: 50%;
                transform: translate(-50%, -50%);
                width: 120px; height: 120px;
                border: 2px solid rgba(255,255,255,0.5);
                border-radius: 50%;
                z-index: 1;
            }
            /* Straffesparksfelter */
            .box-top {
                position: absolute; top: -2px; left: 25%; width: 50%; height: 80px;
                border: 2px solid rgba(255,255,255,0.5); z-index: 1;
            }
            .box-bottom {
                position: absolute; bottom: -2px; left: 25%; width: 50%; height: 80px;
                border: 2px solid rgba(255,255,255,0.5); z-index: 1;
            }
            
            .grid-layout {
                position: relative;
                display: grid;
                grid-template-columns: repeat(5, 1fr);
                grid-template-rows: repeat(5, 140px);
                gap: 5px;
                z-index: 2; /* Sørg for at spillerne ligger over kridtstregerne */
            }
            .pos-zone { display: flex; flex-direction: column; align-items: center; justify-content: flex-start; }
            .player-card {
                background: rgba(255, 255, 255, 0.95);
                border-left: 4px solid #cc0000;
                padding: 2px 6px;
                border-radius: 3px;
                margin-bottom: 3px;
                width: 90%;
                box-shadow: 0 2px 4px rgba(0,0,0,0.3);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .name-text { font-size: 10px; font-weight: 700; color: #1a1a1a; }
            .prior-tag { font-size: 9px; font-weight: 800; color: #cc0000; }
            .label-text { 
                color: #fff; 
                font-size: 11px; 
                font-weight: bold; 
                background: rgba(0,0,0,0.5);
                padding: 1px 6px;
                border-radius: 10px;
                margin-bottom: 5px;
            }
        </style>
    """, unsafe_allow_html=True)

    # --- 4. RENDER ---
    st.markdown('<div class="pitch-container"><div class="box-top"></div><div class="pitch-circle"></div><div class="box-bottom"></div><div class="grid-layout">', unsafe_allow_html=True)
    
    # Vi bruger samme grid-logik som før
    for r in range(5):
        for c in range(5):
            pos_num = next((p for p, coords in pos_config.items() if coords[0] == r and coords[1] == c), None)
            if pos_num:
                label = pos_config[pos_num][2]
                spillere = df_squad[df_squad['POS'] == pos_num].sort_values('PRIOR')
                
                st.write(f'<div class="pos-zone"><div class="label-text">{label}</div>', unsafe_allow_html=True)
                for _, p in spillere.iterrows():
                    navn = p.get('NAVN', f"{p.get('FIRSTNAME','')} {p.get('LASTNAME','')}")
                    prior = p['PRIOR'] if p['PRIOR'] != 'NAN' else '-'
                    st.write(f'<div class="player-card"><span class="name-text">{navn}</span><span class="prior-tag">{prior}</span></div>', unsafe_allow_html=True)
                st.write('</div>', unsafe_allow_html=True)
            else:
                st.write('<div></div>', unsafe_allow_html=True)
    
    st.markdown('</div></div>', unsafe_allow_html=True)
    
    st.write(" ")
    if st.button("🖨️ Gem / Print overblik"):
        st.write('<script>window.print();</script>', unsafe_allow_html=True)
