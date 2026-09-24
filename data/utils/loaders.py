# data/utils/loaders.py
import streamlit as st
import random

HIF_CITATER_OG_FAKTA = [
    "Vidste du det? Hvidovre IF har spillet i den bedste danske række i flere årtier og taget store skalpe gennem tiden.",
    "Citat: 'Kampen varer i 90 minutter, og bagefter følger statistikken i HIF Data Hub.'",
    "Vidste du det? Systemet henter automatisk live-data fra Snowflake og indsætter fallback-data, hvis der mangler felter.",
    "Klub-ånd: Hvidovre er stolthed, traditionsrige værdier og stærke fællesskaber på Vestegnen.",
    "Statistik-tip: Du kan altid tjekke formkurven for de seneste 10 kampe direkte i toppen af dashboardet."
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
