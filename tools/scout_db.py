import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- HJÆLPEFUNKTIONER ---
def rens_metrik_vaerdi(val):
    try:
        if pd.isna(val): return 0
        return int(float(val))
    except:
        return 0

def vis_metrikker(row):
    m_cols = st.columns(4)
    metrics = [
        ("Beslutsomhed", "Beslutsomhed"), ("Fart", "Fart"), 
        ("Aggresivitet", "Aggresivitet"), ("Attitude", "Attitude"),
        ("Udholdenhed", "Udholdenhed"), ("Lederegenskaber", "Lederegenskaber"), 
        ("Teknik", "Teknik"), ("Spilintelligens", "Spilintelligens")
    ]
    for i, (label, col) in enumerate(metrics):
        val = rens_metrik_vaerdi(row.get(col, 0))
        m_cols[i % 4].metric(label, f"{val}")

# --- SELVE HOVEDFUNKTIONEN ---
def vis_side():
    # Hent data fra session_state (som vi indlæste i HIF-dash.py)
    if "main_data" not in st.session_state:
        st.error("Data ikke fundet. Genindlæs siden.")
        return
    
    _, _, hif_avg_map, _, stats_df, df = st.session_state["main_data"]

    st.markdown("<p style='font-size: 14px; font-weight: bold; margin-bottom: 20px;'>Scouting Database</p>", unsafe_allow_html=True)

    # --- FILTRERING ---
    # (Her indsætter du din filtreringslogik fra tidligere...)
    search = st.text_input("Søg", placeholder="Søg spiller eller klub...", label_visibility="collapsed")
    
    # ... Resten af din tabel og vis_profil logik ...
    # SØRG FOR AT vis_profil() ER DEFINERET HERINDE
