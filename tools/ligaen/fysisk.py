import streamlit as st
import pandas as pd

def vis_side(dp):
    st.title("Fysisk Data Diagnose")
    
    df = dp.get("fysisk_data", pd.DataFrame())
    
    if df.empty:
        st.warning("Tabellen er tom. Lad os tjekke hvorfor:")
        
        # Tjek om vi overhovedet har fat i de rigtige SSIID'er
        st.write("Søger efter data for 2025 sæsonen...")
        
        # Test: Findes tabellen overhovedet?
        # (Dette kræver at du kører en hurtig query direkte hvis muligt)
    else:
        st.success(f"Fundet {len(df)} rækker!")
        st.dataframe(df.head(20))
