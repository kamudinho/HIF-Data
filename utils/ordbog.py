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
    try:
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
    except Exception:
        df = pd.read_csv(csv_path, encoding='latin1')

    # --- SØGEFELT ---
    search_query = st.text_input(
        "Søg i begreber eller forklaringer:", 
        placeholder="Indtast søgeord...", 
        key="ordbog_search_v4"
    )

    # Filtrering
    if search_query:
        mask = (
            df['Begreb'].str.contains(search_query, case=False, na=False) | 
            df['Beskrivelse'].str.contains(search_query, case=False, na=False)
        )
        df = df[mask]

    # --- VISNING MED STICKY HEADERS OG TEXT WRAP ---
    if not df.empty:
        # Vi bruger st.dataframe med specifik konfiguration
        st.data_editor(
            df,
            use_container_width=True,
            hide_index=True,
            disabled=True, # Gør at man ikke kan redigere, men kun læse
            height=600,    # Fast højde sikrer at overskriften (header) bliver 'sticky'
            column_config={
                "Begreb": st.column_config.TextColumn(
                    "Begreb",
                    width="small",
                    required=True,
                ),
                "Beskrivelse": st.column_config.TextColumn(
                    "Beskrivelse",
                    width="large", # Tvinger kolonnen til at være bred
                )
            }
        )
        
        # Denne CSS sikrer at teksten inde i Streamlit tabellen ombrydes i stedet for at blive skåret af
        st.markdown("""
            <style>
                div[data-testid="stDataEditor"] div {
                    white-space: normal !important;
                }
            </style>
        """, unsafe_allow_html=True)
    else:
        st.info("Ingen resultater fundet.")

if __name__ == "__main__":
    vis_side()
