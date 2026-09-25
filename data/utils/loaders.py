# data/utils/loaders.py
import streamlit as st
import random

HIF_CITATER_OG_FAKTA = [
    "Vidste du, at Hvidovre IF vandt deres første mesterskab i 1966.",
]

def load_med_hif_fakta(beskrivelse="Henter data..."):
    """
    Viser en loader med skiftende HIF-citater og fun-facts helt uden ikoner.
    """
    placeholder = st.empty()
    citat_valg = random.choice(HIF_CITATER_OG_FAKTA)
    
    with placeholder.container():
        st.info(f"{beskrivelse}\n\n{citat_valg}")
    
    return placeholder
