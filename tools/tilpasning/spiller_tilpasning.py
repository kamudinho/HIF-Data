import streamlit as st
import pandas as pd
import os

def rens_specialtegn(val):
    """
    Oversætter ødelagte UTF-8/ANSI tegn (danske og baltiske/østlige tegn) 
    til deres rigtige bogstaver.
    """
    if not isinstance(val, str):
        return val
        
    tegn_map = {
        # Danske tegn
        '√∏': 'ø', '√ò': 'Ø',
        '√¶': 'æ', '√Ü': 'Æ',
        '√•': 'å', '√Ö': 'Å',
        '√†': 'å',
        '√∫': 'ú',
        '≈°': 'š', '≈†': 'Š',
        '≈æ': 'ž', '≈Ω': 'Ž',
        '√≥': 'ó',
        '√©': 'é', '√®': 'è', '√¢': 'â', '√º': 'ü', '√∂': 'ö', '√§': 'ä'
    }
    
    for grimt, godt in tegn_map.items():
        val = val.replace(grimt, godt)
        
    if "√∏" in val or "√¶" in val or "√•" in val:
        val = val.replace("√∏", "ø").replace("√¶", "æ").replace("√•", "å")
        
    return val

def vis_side():
    st.caption(
        "Her kan du rette navn, position og klub direkte i tabellen. "
        "De tekniske ID-kolonner (Wyscout, Opta og turneringer) er låst for at beskytte dataforbindelsen."
    )

    # --- 1. FIND OG INDLÆS CSV-FILEN ---
    aktuel_fil_sti = os.path.abspath(__file__)
    projekt_rod = os.path.dirname(os.path.dirname(os.path.dirname(aktuel_fil_sti)))
    overskriv_sti = os.path.join(projekt_rod, 'data', 'players', 'spiller_overskrivning.csv')

    if not os.path.exists(overskriv_sti):
        st.error(f"Kunne ikke finde CSV-filen på stien: {overskriv_sti}")
        return

    try:
        df = pd.read_csv(overskriv_sti, encoding='utf-8-sig')
    except Exception as e:
        st.error(f"Fejl ved indlæsning af CSV: {e}")
        return

    # Sørg for at kolonnenavnene matcher præcis
    for col in ['NAVN', 'POSITION', 'KLUB', 'PLAYER_WYID', 'PLAYER_OPTAUUID', 'COMPETITION_WYID', 'COMPETITION_OPTAUUID']:
        if col not in df.columns:
            df[col] = ""

    # --- AUTOMATISK OPRENSNING AF TEGN ---
    for col in ['NAVN', 'KLUB', 'POSITION']:
        df[col] = df[col].fillna("").astype(str).apply(rens_specialtegn)

    # --- 2. SØGEFELT (Taster live med JavaScript-trigger) ---
    soegning = st.text_input(
        "Søg på navn, position eller klub (søgningen starter efter 2 tegn):", 
        key="live_search_field"
    ).strip().lower()

    # --- JAVASCRIPT TRIGGER (Gør at der søges løbende uden Enter) ---
    st.components.v1.html(
        """
        <script>
        const doc = window.parent.document;
        const inputs = doc.querySelectorAll('input[type="text"]');
        inputs.forEach(input => {
            if (input.getAttribute('aria-label') && input.getAttribute('aria-label').includes('Søg på navn')) {
                if (!input.dataset.hasLiveListener) {
                    input.addEventListener('input', (e) => {
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                    });
                    input.dataset.hasLiveListener = "true";
                }
            }
        });
        </script>
        """,
        height=0,
    )

    # --- 3. FEJLSIKRET FILTRERING ---
    if len(soegning) >= 2:
        navn_match = df['NAVN'].fillna("").astype(str).str.lower().str.contains(soegning)
        pos_match = df['POSITION'].fillna("").astype(str).str.lower().str.contains(soegning)
        klub_match = df['KLUB'].fillna("").astype(str).str.lower().str.contains(soegning)
        
        visnings_df = df[navn_match | pos_match | klub_match].copy()
    else:
        visnings_df = df.copy()

    # --- 4. DEN INTERAKTIVE DATA_EDITOR ---
    redigeret_df = st.data_editor(
        visnings_df,
        height=600,
        num_rows="fixed",
        use_container_width=True,
        hide_index=True,
        disabled=["PLAYER_WYID", "PLAYER_OPTAUUID", "COMPETITION_WYID", "COMPETITION_OPTAUUID"],
        key="spiller_editor",
        column_config={
            "NAVN": st.column_config.TextColumn(
                "Navn",
                help="Rediger spillerens navn",
                required=True
            ),
            "POSITION": st.column_config.SelectboxColumn(
                "Position",
                help="Vælg position",
                options=[
                    "Målmand", "Stopper", "Venstre back", "Højre Back",
                    "Venstre Wingback", "Højre Wingback", "Defensiv midtbane",
                    "Central midtbane", "Offensiv midtbane", "Venstre midtbane",
                    "Højre midtbane", "Angriber", "Venstre kant", "Højre kant",
                    "Forsvarsspiller", "Midtbanespiller"
                ],
                required=True
            ),
            "KLUB": st.column_config.TextColumn(
                "Klub",
                help="Rediger spillerens nuværende klub",
                required=True
            ),
            "PLAYER_WYID": st.column_config.NumberColumn(
                "PLAYER_WYID",
                format="%d"
            ),
            "PLAYER_OPTAUUID": st.column_config.TextColumn(
                "PLAYER-UUID"
            ),
            "COMPETITION_WYID": st.column_config.NumberColumn(
                "Turnering-WYID",
                format="%d"
            ),
            "COMPETITION_OPTAUUID": st.column_config.TextColumn(
                "Turnering-UUID"
            )
        }
    )

    # --- 5. GEM DET REDIGEREDE DATAFRAME ---
    if not redigeret_df.equals(visnings_df):
        try:
            # Opdater det originale dataframe 'df' ud fra ændringerne i 'redigeret_df'
            df.set_index('PLAYER_WYID', inplace=True)
            redigeret_df.set_index('PLAYER_WYID', inplace=True)
            
            df.update(redigeret_df)
            df.reset_index(inplace=True)
            
            # Hold rækkefølgen af kolonnerne fuldstændig intakt
            kolonner_rækkefølge = ['NAVN', 'POSITION', 'KLUB', 'PLAYER_WYID', 'PLAYER_OPTAUUID', 'COMPETITION_WYID', 'COMPETITION_OPTAUUID']
            df = df[kolonner_rækkefølge]

            # Skriv og overskriv CSV-filen direkte på harddisken
            df.to_csv(overskriv_sti, index=False, encoding='utf-8-sig')
            st.success("Ændringer gemt og specialtegn ryddet op! 💾")
            
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Kunne ikke gemme ændringerne: {e}")

if __name__ == "__main__":
    vis_side()
