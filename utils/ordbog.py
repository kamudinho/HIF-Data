import streamlit as st
import pandas as pd
import os

def vis_side():
    # Find stien til din CSV-fil
    base_path = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_path, '..', 'utils', 'ordbog.csv')

    if not os.path.exists(csv_path):
        st.error(f"Kunne ikke finde ordbogen på stien: {csv_path}")
        return

    # Load data
    df = pd.read_csv(csv_path)

    # --- SØGEFELT ---
    search_query = st.text_input("Søg i ordbogen:", placeholder="Skriv f.eks. 'Z-score' eller 'Løb'...", key="ordbog_search")

    # Filtrering baseret på søgning
    if search_query:
        df = df[
            df['Begreb'].str.contains(search_query, case=False, na=False) | 
            df['Beskrivelse'].str.contains(search_query, case=False, na=False)
        ]

    # --- VISNING ---
    if not df.empty:
        # Vi bruger hide_index for at fjerne rækkenumrene til venstre
        st.dataframe(
            df, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Begreb": st.column_config.TextColumn("Begreb", width="medium", help="Det statistiske eller tekniske udtryk"),
                "Beskrivelse": st.column_config.TextColumn("Beskrivelse", width="large", help="Forklaring af begrebet")
            }
        )
    else:
        st.info("Ingen resultater matchede din søgning.")

# Hvis du vil teste den direkte
if __name__ == "__main__":
    vis_side()
