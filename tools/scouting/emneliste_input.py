import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- KONFIGURATION ---
CSV_PATH = 'data/emneliste.csv'
COLUMNS = ["Dato", "Navn", "Position", "Klub", "Prioritet", "Forventning", "Kontrakt", "Bemaerkning", "Oprettet_af"]

def vis_side(dp):
    st.caption("Testside")
