import streamlit as st
import pandas as pd

# Eksempel på filtrering i din loader
def process_physical_data(all_phys_df, selected_uuid):
    # Filtrér så vi kun ser på den kamp der er valgt i dashboardet
    match_df = all_phys_df[all_phys_df['MATCH_OPTAUUID'] == selected_uuid]
    return match_df
