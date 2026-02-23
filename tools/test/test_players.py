import streamlit as st
import pandas as pd
import os

def vis_side():
    st.markdown("<h3 style='color: #cc0000;'>Test: Spillerstatistik</h3>", unsafe_allow_html=True)
    
    # Præcis sti til din test-data
    csv_path = "data/testdata/players.csv"
    
    if os.path.exists(csv_path):
        # Indlæs data
        df = pd.read_csv(csv_path)
        
        # --- Simple filtre ---
        col1, col2 = st.columns(2)
        
        with col1:
            # Dropdown til hold (hvis kolonnen 'team' findes)
            if 'team' in df.columns:
                hold_liste = ["Alle"] + sorted(df['team'].unique().tolist())
                valgt_hold = st.selectbox("Hold", hold_liste)
            else:
                valgt_hold = "Alle"
            
        with col2:
            # Dropdown til position (hvis kolonnen 'position' findes)
            if 'position' in df.columns:
                pos_liste = ["Alle"] + sorted(df['position'].unique().tolist())
                valgt_pos = st.selectbox("Position", pos_liste)
            else:
                valgt_pos = "Alle"

        # --- Filtrering ---
        filtered_df = df.copy()
        if valgt_hold != "Alle":
            filtered_df = filtered_df[filtered_df['team'] == valgt_hold]
        if valgt_pos != "Alle":
            filtered_df = filtered_df[filtered_df['position'] == valgt_pos]

        st.markdown("---")

        # --- Visning af tabel ---
        st.write(f"Viser {len(filtered_df)} spillere fra test-filen")
        
        st.dataframe(
            filtered_df, 
            use_container_width=True, 
            hide_index=True
        )
        
    else:
        st.error(f"Fejl: Kunne ikke finde filen på {csv_path}")
        st.info("Tjek at filen ligger i mappen: data/testdata/ og hedder players.csv")
