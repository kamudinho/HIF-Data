import streamlit as st
import pandas as pd

def vis_side(df_players):
    st.markdown("<h3 style='color: #cc0000;'>Trupoversigt</h3>", unsafe_allow_html=True)
    
    if df_players is None or df_players.empty:
        st.warning("Ingen spillerdata tilgængelig.")
        return

    # --- Filtre (Rene dropdowns) ---
    col1, col2, col3 = st.columns(3)
    
    with col1:
        positioner = ["Alle"] + sorted(df_players['position'].unique().tolist()) if 'position' in df_players.columns else ["Alle"]
        valgt_pos = st.selectbox("Position", positioner)
        
    with col2:
        status = ["Alle"] + sorted(df_players['status'].unique().tolist()) if 'status' in df_players.columns else ["Alle"]
        valgt_status = st.selectbox("Status", status)
        
    with col3:
        # Søgefelt til navn
        soege_tekst = st.text_input("Søg spiller").lower()

    # --- Filtrering ---
    mask = pd.Series([True] * len(df_players))
    
    if valgt_pos != "Alle":
        mask &= (df_players['position'] == valgt_pos)
    if valgt_status != "Alle":
        mask &= (df_players['status'] == valgt_status)
    if soege_tekst:
        mask &= (df_players['name'].str.lower().str.contains(soege_tekst))
        
    df_vis = df_players[mask]

    st.markdown("---")

    # --- Visning af tabel ---
    # Vi vælger de vigtigste kolonner for at holde det stramt
    kolonner = ["name", "position", "age", "contract_end", "status"]
    # Tjekker hvilke af dem der rent faktisk findes i din CSV
    eksisterende_kolonner = [c for c in kolonner if c in df_vis.columns]
    
    st.dataframe(
        df_vis[eksisterende_kolonner],
        use_container_width=True,
        hide_index=True
    )

    # --- Hurtig Info ---
    st.markdown(f"Antal spillere i udvalg: **{len(df_vis)}**")
