import streamlit as st
import pandas as pd

def vis_side(dp):
    st.title("Fysisk Data - Rapport")

    # 1. Hent den færdige data fra pakken
    # 'fysisk_data' er nu den store tabel med data for HELE ligaen
    df_fys = dp.get("fysisk_data", pd.DataFrame())
    matches = dp.get("matches", pd.DataFrame())

    if df_fys.empty:
        st.warning("Ingen fysisk data tilgængelig i datapakken.")
        return

    # 2. Vælg kamp (Vi bruger data der allerede er hentet)
    match_labels = matches.apply(
        lambda row: f"{row['MATCH_DATE_FULL'].strftime('%d/%m')} - {row['CONTESTANTHOME_NAME']} vs {row['CONTESTANTAWAY_NAME']}", 
        axis=1
    )
    
    selected_idx = st.selectbox("Vælg kamp", range(len(match_labels)), format_func=lambda x: match_labels.iloc[x])
    selected_match = matches.iloc[selected_idx]
    
    # Her filtrerer vi bare i den DataFrame vi ALLEREDE har i hukommelsen
    # Ingen nye SQL kald!
    current_match_data = df_fys[df_fys['MATCH_OPTAUUID'] == selected_match['MATCH_OPTAUUID']]

    if not current_match_data.empty:
        st.subheader("Spiller Performance")
        st.dataframe(current_match_data, use_container_width=True, hide_index=True)
    else:
        st.info("Der er ikke matchet fysisk data for denne kamp endnu.")
