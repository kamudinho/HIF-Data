import streamlit as st
import pandas as pd
import os

def vis_side():
    # Find stien til din CSV-fil
    base_path = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_path, '..', 'data', 'ordbog.csv')

    if not os.path.exists(csv_path):
        st.error(f"Kunne ikke finde ordbogen på stien: {csv_path}")
        return

    # Load data - vi tvinger encoding for at sikre æ, ø, å
    try:
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
    except Exception:
        df = pd.read_csv(csv_path, encoding='latin1')

    # --- SØGEFELT ---
    search_query = st.text_input(
        "Søg i begreber eller forklaringer:", 
        placeholder="Indtast søgeord...", 
        key="ordbog_search_v2"
    )

    # Filtrering
    if search_query:
        mask = (
            df['Begreb'].str.contains(search_query, case=False, na=False) | 
            df['Beskrivelse'].str.contains(search_query, case=False, na=False)
        )
        df = df[mask]

    # --- VISNING MED WRAP ---
    if not df.empty:
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Begreb": st.column_config.TextColumn(
                    "Begreb",
                    width="small",  # Gør denne kolonne smal
                    help="Statistisk udtryk"
                ),
                "Beskrivelse": st.column_config.TextColumn(
                    "Beskrivelse",
                    width="large",  # Gør denne kolonne bred
                    help="Uddybende forklaring"
                )
            }
        )
        
        # Ekstra styling for at tvinge tekst-wrap i Streamlit celler
        st.markdown("""
            <style>
                [data-testid="stTable"] td, [data-testid="stDataFrame"] td {
                    white-space: normal !important;
                    word-wrap: break-word !important;
                }
            </style>
        """, unsafe_allow_html=True)
    else:
        st.info("Ingen resultater fundet.")

if __name__ == "__main__":
    vis_side()
