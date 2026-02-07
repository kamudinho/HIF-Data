import streamlit as st
import pandas as pd

def vis_side(df):
    st.title("Trupsammensætning & Taktisk Overblik")

    # --- 1. DIAGNOSTIK (Vises kun hvis der er fejl) ---
    if df is None:
        st.error("Ingen data modtaget fra main.py")
        return

    # Lav en kopi og rens kolonnenavne (fjern mellemrum og gør store)
    df_squad = df.copy()
    df_squad.columns = [str(c).strip().upper() for c in df_squad.columns]

    # --- TJEK FOR KOLONNER ---
    if 'POS' not in df_squad.columns:
        st.warning("⚠️ Finder ikke 'POS' kolonnen. Her er hvad Python ser i dit Excel-ark:")
        
        # Vis de første 3 rækker af dit ark, så vi kan se overskrifterne
        st.write(df.head(3))
        
        st.info(f"Fundne kolonner (efter rensning): {list(df_squad.columns)}")
        st.markdown("""
        **Løsningsforslag:**
        1. Sørg for at gemme din Excel-fil helt.
        2. Hvis du lige har tilføjet 'POS', så tjek om den er skrevet i række 1.
        3. Prøv at omdøbe kolonnen i Excel til noget helt andet, f.eks. 'PLADS', og se om den dukker op her.
        """)
        return

    # --- 2. HVIS POS ER FUNDET, FORTSÆT ---
    df_squad['POS'] = pd.to_numeric(df_squad['POS'], errors='coerce')
    df_squad['PRIOR'] = df_squad.get('PRIOR', '-').astype(str).str.upper()

    # Mapping af positioner (1-11) til banen (række, kolonne, label)
    pos_config = {
        1: (4, 2, 'MM'), 2: (3, 4, 'HB'), 3: (3, 3, 'HCB'), 4: (3, 1, 'VCB'),
        5: (3, 0, 'VB'), 6: (2, 2, 'DM'), 8: (1, 1, 'VCM'), 10: (1, 3, 'HCM'),
        7: (0, 4, 'HW'), 9: (0, 2, 'ANG'), 11: (0, 0, 'VW')
    }

    # --- 3. CSS TIL BANEN ---
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
                background: white; border-left: 5px solid #0e3255; padding: 3px 8px;
                border-radius: 4px; margin-bottom: 3px; width: 95%; box-shadow: 1px 1px 3px rgba(0,0,0,0.2);
            }
            .name-text { font-size: 11px; font-weight: 600; color: #333; }
            .label-text { color: white; font-size: 12px; font-weight: bold; text-shadow: 1px 1px 2px black; margin-bottom: 5px; }
        </style>
    """, unsafe_allow_html=True)

    # --- 4. TEGN BANEN ---
    html = '<div class="pitch">'
    for r in range(5):
        for c in range(5):
            pos_num = next((p for p, coords in pos_config.items() if coords[0] == r and coords[1] == c), None)
            if pos_num:
                label = pos_config[pos_num][2]
                spillere = df_squad[df_squad['POS'] == pos_num].sort_values('PRIOR')
                html += f'<div class="pos-zone"><div class="label-text">{label}</div>'
                for _, p in spillere.iterrows():
                    navn = p.get('NAVN', f"{p.get('FIRSTNAME','')} {p.get('LASTNAME','')}")
                    html += f'<div class="player-card"><span class="name-text">{navn}</span></div>'
                html += '</div>'
            else:
                html += '<div></div>'
    html += '</div>'
    
    st.write(html, unsafe_allow_html=True)
