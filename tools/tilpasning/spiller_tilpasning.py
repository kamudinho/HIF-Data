import streamlit as st
import pandas as pd
import os

def vis_side():
    st.subheader("Rediger Spiller-overskrivninger")
    st.write(
        "Her kan du rette navn, position og klub direkte i tabellen. "
        "De tekniske ID-kolonner (Wyscout, Opta og turneringer) er låst for at beskytte dataforbindelsen."
    )

    # --- 1. FIND OG INDLÆS CSV-FILEN ---
    aktuel_fil_sti = os.path.abspath(__file__)
    # Går 2 niveauer op (tilpas hvis din fil-struktur kræver flere/færre os.path.dirname)
    projekt_rod = os.path.dirname(os.path.dirname(os.path.dirname(aktuel_fil_sti)))
    overskriv_sti = os.path.join(projekt_rod, 'data', 'players', 'spiller_overskrivning.csv')

    if not os.path.exists(overskriv_sti):
        st.error(f"Kunne ikke finde CSV-filen på stien: {overskriv_sti}")
        return

    try:
        # Indlæser med utf-8-sig for at håndtere specialtegn som f.eks. 'æ', 'ø', 'å'
        df = pd.read_csv(overskriv_sti, encoding='utf-8-sig')
    except Exception as e:
        st.error(f"Fejl ved indlæsning af CSV: {e}")
        return

    # Sørg for at kolonnenavnene matcher præcis (så vi ikke får problemer med store/små bogstaver)
    for col in ['NAVN', 'POSITION', 'KLUB', 'PLAYER_WYID', 'PLAYER_OPTAUUID', 'COMPETITION_WYID', 'COMPETITION_OPTAUUID']:
        if col not in df.columns:
            # Hvis filen er tom eller mangler kolonner, opretter vi dem
            df[col] = None

    # --- 2. DEN INTERAKTIVE DATA_EDITOR ---
    # Vi bruger 'disabled' til at låse de sidste 4 kolonner
    redigeret_df = st.data_editor(
        df,
        num_rows="fixed", # Sæt til "dynamic" hvis du vil have mulighed for at tilføje/slette rækker helt
        use_container_width=True,
        hide_index=True,
        disabled=["PLAYER_WYID", "PLAYER_OPTAUUID", "COMPETITION_WYID", "COMPETITION_OPTAUUID"],
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
                    "Goalkeeper", "Center Back", "Left Back", "Right Back",
                    "Left Wing Back", "Right Wing Back", "Defensive Midfielder",
                    "Central Midfielder", "Attacking Midfielder", "Left Midfielder",
                    "Right Midfielder", "Striker", "Left Winger", "Right Winger",
                    "Second Striker", "Defender", "Midfielder", "Forward"
                ],
                required=True
            ),
            "KLUB": st.column_config.TextColumn(
                "Klub",
                help="Rediger spillerens nuværende klub",
                required=True
            ),
            # Låste kolonner formateres pænt som tekst/tal uden tusindtals-separator:
            "PLAYER_WYID": st.column_config.NumberColumn(
                "Wyscout ID",
                format="%d"
            ),
            "PLAYER_OPTAUUID": st.column_config.TextColumn(
                "Opta UUID"
            ),
            "COMPETITION_WYID": st.column_config.NumberColumn(
                "Turnering ID (Wy)",
                format="%d"
            ),
            "COMPETITION_OPTAUUID": st.column_config.TextColumn(
                "Turnering UUID (Opta)"
            )
        }
    )

    # --- 3. GEM DET REDIGEREDE DATAFRAME DIREKTE TIL FILEN ---
    if not redigeret_df.equals(df):
        try:
            # Gemmer direkte til CSV'en med uændret kolonnestruktur og UTF-8 encoding
            redigeret_df.to_csv(overskriv_sti, index=False, encoding='utf-8-sig')
            st.success("Filen blev gemt succesfuldt! 💾")
            
            # Ryd cache og genindlæs siden
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Kunne ikke gemme ændringerne: {e}")

if __name__ == "__main__":
    vis_side()
