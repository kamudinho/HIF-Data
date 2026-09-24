import streamlit as st
import pandas as pd

def vis_trup_side(team_wyid, seasonname):
    st.markdown('<div class="main-header">Modstanderanalyse</div>', unsafe_allow_html=True)
    
    st.write(f"Viser trup for Hold ID: {team_wyid} i sæson {seasonname}")
    
    # Eksempel på layout med data-tabel eller spillere
    st.markdown("### Modstanderanalyse")
    
    # Her kan du hente rigtige data ind via dine data-loadere, f.eks.:
    # df_trup = hent_spiller_data(team_wyid, seasonname)
    
    # Midlertidig eksempel-tabel:
    data = {
        "Spiller": ["Spiller 1", "Spiller 2", "Spiller 3"],
        "Position": ["Angriber", "Midtbane", "Forsvar"],
        "Alder": [24, 26, 22]
    }
    df = pd.DataFrame(data)
    
    st.dataframe(df, use_container_width=True)
