import streamlit as st
import pandas as pd

# --- SIDETITEL ---
st.markdown('<div style="font-size: 22px; font-weight: 700; color: #1a1a1a; margin-bottom: 20px;">Holdoversigt & Nøgletal</div>', unsafe_allow_html=True)

# --- 1. SEKTION: KPI NØGLEMETAL ---
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(label="Kampe Spillet", value="18", delta="--")
with col2:
    st.metric(label="Point", value="34", delta="+2")
with col3:
    st.metric(label="Målscore", value="29 - 18", delta="+11")
with col4:
    st.metric(label="Forventede Mål (xG)", value="1.65", delta="pr. kamp")
with col5:
    st.metric(label="Boldbesiddelse", value="52.4%", delta="+1.2%")

st.divider()

# --- 2. SEKTION: SENESTE KAMPVIRKSOMHED & TAKTIK ---
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("#### Seneste kampe")
    recent_matches = pd.DataFrame({
        "Kamp": [
            "Hvidovre - AC Horsens", 
            "Vendsyssel - Hvidovre", 
            "Hvidovre - Esbjerg fB", 
            "Kolding IF - Hvidovre", 
            "Hvidovre - FC Fredericia"
        ],
        "Resultat": ["2 - 1", "1 - 1", "3 - 0", "0 - 2", "1 - 1"],
        "Form": ["V", "U", "V", "T", "U"]
    })
    st.dataframe(recent_matches, use_container_width=True, hide_index=True)

with col_right:
    st.markdown("#### Taktiske Nøgletal")
    tactical_stats = pd.DataFrame({
        "Parameter": [
            "PPDA (Pres-intensitet)", 
            "Afslutninger pr. kamp", 
            "Skud imod pr. kamp", 
            "Dueller vundet", 
            "Succesfulde afleveringer"
        ],
        "Værdi": ["9.4", "13.2", "9.8", "51.8%", "81.5%"]
    })
    st.dataframe(tactical_stats, use_container_width=True, hide_index=True)

st.divider()

# --- 3. SEKTION: TURNERINGSSTILLING ---
st.markdown("#### Stilling i NordicBet Liga (2026/2027)")

standings_data = pd.DataFrame({
    "Nr": [1, 2, 3, 4, 5, 6],
    "Hold": ["Odense Boldklub", "Hvidovre IF", "AC Horsens", "Esbjerg fB", "Vendsyssel FF", "Kolding IF"],
    "K": [18, 18, 18, 18, 18, 18],
    "P": [39, 34, 32, 28, 26, 25]
})

st.dataframe(standings_data, use_container_width=True, hide_index=True)
