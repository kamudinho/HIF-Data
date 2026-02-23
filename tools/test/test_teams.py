import streamlit as st
import pandas as pd
import os

def vis_side():
    st.markdown("<h3 style='color: #cc0000;'>Test: Holdoversigt</h3>", unsafe_allow_html=True)
    
    csv_path = "data/testdata/teams.csv"
    
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        
        # Enkel filtrering på række/niveau hvis kolonnen findes
        if 'league' in df.columns:
            liga_liste = ["Alle"] + sorted(df['league'].unique().tolist())
            valgt_liga = st.selectbox("Filtrer på liga", liga_liste)
            
            if valgt_liga != "Alle":
                df = df[df['league'] == valgt_liga]

        st.markdown("---")
        
        # Visning af rå data
        st.dataframe(
            df, 
            use_container_width=True, 
            hide_index=True
        )
        
        # Simpel liste over holdnavne hvis man hurtigt skal kopiere dem
        if 'team_name' in df.columns:
            with st.expander("Se liste over alle holdnavne"):
                st.write(", ".join(df['team_name'].tolist()))
                
    else:
        st.error(f"Filen mangler: {csv_path}")
