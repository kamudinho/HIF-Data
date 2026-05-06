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
        # Baltiske, polske og østeuropæiske specialtegn
        '≈°': 'š', '≈†': 'Š',
        '≈æ': 'ž', '≈Ω': 'Ž',
        'ƒÖ': 'ą', 'ƒÜ': 'ć', 'ƒô': 'ę', '≈Ç': 'ł', '≈Ñ': 'ń', '√≥': 'ó', '≈ö': 'ś', '≈∫': 'ź', '≈º': 'ż',
        'ƒÖ': 'Ą', 'ƒÜ': 'Ć', 'ƒò': 'Ę', '≈Detailed': 'Ł', '≈É': 'Ń', '√ì': 'Ó', '≈ö': 'Ś', '≈π': 'Ź', '≈ª': 'Ż',
        'ƒç': 'č', 'ƒé': 'Č',
        'ƒô': 'ē', 'ƒ™': 'ī', '≈´': 'ū', 'ƒÅ': 'ā', 'ƒº': 'ū',
        # Generelle accenter
        '√©': 'é', '√®': 'è', '√¢': 'â', '√º': 'ü', '√∂': 'ö', '√§': 'ä'
    }
    
    for grimt, godt in tegn_map.items():
        val = val.replace(grimt, godt)
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
            df[col] = None

    # --- AUTOMATISK OPRENSNING AF TEGN ---
    for col in ['NAVN', 'KLUB', 'POSITION']:
        df[col] = df[col].apply(rens_specialtegn)

    # --- 2. SØGEFELT (Taster live) ---
    # Vi bruger 'key' direkte. Streamlit vil køre scriptet igen ved hvert tastetryk, når værdien ændres.
    soegning = st.text_input(
        "Søg på navn, position eller klub:", 
        key="live_search_field"
    ).strip().lower()

    # Vi filtrerer dataene til visning
    if len(soegning) >= 2:
        mask = (
            df['NAVN'].astype(str).str.lower().str.contains(soegning) |
            df['POSITION'].astype(str).str.lower().str.contains(soegning) |
            df['KLUB'].astype(str).str.lower().str.contains(soegning)
        )
        visnings_df = df[mask].copy()
    else:
        visnings_df = df.copy()

    # --- 3. DEN INTERAKTIVE DATA_EDITOR ---
    # Vi lader editoren køre på visnings_df og gemmer ændringerne direkte via key-state koblingen
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

    # --- 4. GEM DET REDIGEREDE DATAFRAME ---
    # Hvis der er lavet en ændring i editoren
    if not redigeret_df.equals(visnings_df):
        try:
            # Vi tager det originale fulde dataframe 'df' og opdaterer de rækker, 
            # der har ændret sig i det filtrerede 'redigeret_df', matchet på PLAYER_WYID
            df.set_index('PLAYER_WYID', inplace=True)
            redigeret_df.set_index('PLAYER_WYID', inplace=True)
            
            # Opdaterer værdierne for de matchende spillere
            df.update(redigeret_df)
            
            # Genskab indexet til kolonne før vi gemmer
            df.reset_index(inplace=True)
            
            # Sørg for at holde kolonne-rækkefølgen intakt
            kolonner_rækkefølge = ['NAVN', 'POSITION', 'KLUB', 'PLAYER_WYID', 'PLAYER_OPTAUUID', 'COMPETITION_WYID', 'COMPETITION_OPTAUUID']
            df = df[kolonner_rækkefølge]

            # Gemmer direkte til CSV'en med UTF-8 encoding
            df.to_csv(overskriv_sti, index=False, encoding='utf-8-sig')
            st.success("Ændringer gemt og specialtegn ryddet op! 💾")
            
            # Ryd cache og genindlæs siden helt
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Kunne ikke gemme ændringerne: {e}")

if __name__ == "__main__":
    vis_side()
