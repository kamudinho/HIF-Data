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
        key="ordbog_search_v_final"
    )

    if search_query:
        mask = (
            df['Begreb'].str.contains(search_query, case=False, na=False) | 
            df['Beskrivelse'].str.contains(search_query, case=False, na=False)
        )
        df = df[mask]

    # --- VISNING MED HTML/CSS (Garanteret Wrap + Sticky Header) ---
    if not df.empty:
        # Vi bygger vores egen tabel med CSS for at garantere resultatet
        st.markdown("""
            <style>
                .ordbog-container {
                    max-height: 700px;
                    overflow-y: auto;
                    border: 1px solid #e6e9ef;
                    border-radius: 5px;
                }
                .ordbog-table {
                    width: 100%;
                    border-collapse: collapse;
                    font-family: sans-serif;
                }
                .ordbog-table thead th {
                    position: sticky;
                    top: 0;
                    background-color: #f0f2f6;
                    z-index: 1;
                    text-align: left;
                    padding: 12px;
                    border-bottom: 2px solid #e6e9ef;
                }
                .ordbog-table td {
                    padding: 12px;
                    border-bottom: 1px solid #e6e9ef;
                    vertical-align: top;
                    line-height: 1.5;
                    white-space: normal !important; /* Garanterer wrap */
                }
                .col-begreb { width: 20%; font-weight: 600; }
                .col-beskrivelse { width: 80%; }
            </style>
        """, unsafe_allow_html=True)

        # Start tabellen
        html_table = '<div class="ordbog-container"><table class="ordbog-table"><thead><tr>'
        html_table += '<th class="col-begreb">Begreb</th><th class="col-beskrivelse">Beskrivelse</th>'
        html_table += '</tr></thead><tbody>'

        # Tilføj rækker
        for _, row in df.iterrows():
            html_table += f'<tr><td class="col-begreb">{row["Begreb"]}</td>'
            html_table += f'<td class="col-beskrivelse">{row["Beskrivelse"]}</td></tr>'

        html_table += '</tbody></table></div>'
        
        st.write(html_table, unsafe_allow_html=True)
    else:
        st.info("Ingen resultater fundet.")
