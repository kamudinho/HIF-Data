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

    # Load data med fejlhåndtering for danske tegn
    try:
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
    except Exception:
        df = pd.read_csv(csv_path, encoding='latin1')

    # --- SØGEFELT ---
    search_query = st.text_input(
        "Søg i begreber eller forklaringer:", 
        placeholder="Indtast søgeord...", 
        key="ordbog_search_v3"
    )

    # Filtrering baseret på søgning
    if search_query:
        mask = (
            df['Begreb'].str.contains(search_query, case=False, na=False) | 
            df['Beskrivelse'].str.contains(search_query, case=False, na=False)
        )
        df = df[mask]

    # --- VISNING MED TVUNGET WRAP ---
    if not df.empty:
        # Vi bruger st.markdown med CSS til at styre kolonnebredden præcist
        # og sikre at teksten ombrydes (wrap)
        st.markdown("""
            <style>
                table {
                    width: 100%;
                }
                th:first-child, td:first-child {
                    width: 150px !important;
                    min-width: 150px !important;
                    max-width: 150px !important;
                    font-weight: bold;
                }
                td {
                    white-space: normal !important;
                    word-wrap: break-word !important;
                    vertical-align: top !important;
                }
            </style>
        """, unsafe_allow_html=True)
        
        # Vi bruger st.table i stedet for st.dataframe for at få fuld tekstvisning
        st.table(df)
    else:
        st.info("Ingen resultater fundet.")

if __name__ == "__main__":
    vis_side()
