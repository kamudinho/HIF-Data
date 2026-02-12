import streamlit as st
import pandas as pd
import uuid

REPO = "Kamudinho/HIF-data"
FILE_PATH = "scouting_db.csv"

def vis_side():
    st.markdown("### 📋 Scouting Database")
    
    try:
        # Hent data med cache-buster for at sikre vi ser det nyeste
        raw_url = f"https://raw.githubusercontent.com/{REPO}/main/{FILE_PATH}?nocache={uuid.uuid4()}"
        db = pd.read_csv(raw_url)
        
        # Gør tabellen pænere
        st.dataframe(
            db, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Rating": st.column_config.NumberColumn(format="%d ⭐"),
                "Dato": st.column_config.DateColumn()
            }
        )
    except Exception as e:
        st.info("Databasen er tom eller kunne ikke hentes.")
