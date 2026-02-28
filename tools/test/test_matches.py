import streamlit as st

def vis_side(df):
    st.markdown("### 🏟️ Kampoversigt (Betinia Ligaen)")
    
    if df is None or df.empty:
        st.warning("Ingen data fundet for de valgte filtre.")
        return

    # Vis tabellen
    st.dataframe(
        df, 
        use_container_width=True, 
        hide_index=True,
        # Du kan styre hvilke kolonner du vil se først her:
        column_order=["DATE", "MATCHLABEL", "GOALS", "XG", "SHOTS", "COMPETITION_NAME"]
    )
