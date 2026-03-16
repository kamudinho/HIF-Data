import streamlit as st
import pandas as pd

def vis_side(dp):
    st.title("Fysisk Data - Rapport")

    # 1. Tjek om data overhovedet findes i datapakken
    df_fys = dp.get("fysisk_data", pd.DataFrame())
    matches = dp.get("matches", pd.DataFrame())

    # --- DEBUG SEKTION ---
    with st.expander("🛠 System Check (Hvorfor virker det ikke?)"):
        st.write(f"Antal rækker i 'fysisk_data': {len(df_fys)}")
        if not df_fys.empty:
            st.write("Eksempel på UUID fra database:", df_fys['MATCH_OPTAUUID'].iloc[0])
        st.write(f"Antal rækker i 'matches': {len(matches)}")
    # ---------------------

    if df_fys.empty:
        st.error("🚨 Ingen data fundet i 'fysisk_data'. Tjek 'analyse_load.py' og Snowflake rettigheder.")
        return

    # 1. MATCH SELECTOR
    match_labels = matches.apply(
        lambda row: f"{row['MATCH_DATE_FULL'].strftime('%d/%m')} - {row['CONTESTANTHOME_NAME']} vs {row['CONTESTANTAWAY_NAME']}", 
        axis=1
    )
    
    selected_idx = st.selectbox("Vælg kamp", range(len(match_labels)), format_func=lambda x: match_labels.iloc[x])
    selected_match = matches.iloc[selected_idx]
    
    # 2. DEN ULTIMATIVE FILTRERING
    # Vi henter det rene Opta ID (fx 2435012)
    m_id = str(selected_match['MATCH_OPTAUUID']).replace('g', '')
    
    # Vi prøver en meget bredere søgning
    # Hvis UUID'en i DB er '62gmple4v7...', tjekker vi om m_id findes deri
    mask = df_fys['MATCH_OPTAUUID'].astype(str).str.contains(m_id, na=False)
    current_match_data = df_fys[mask]

    # 3. VISNING ELLER FEJLFINDING
    if not current_match_data.empty:
        st.subheader(f"Spiller Performance: {match_labels.iloc[selected_idx]}")
        view_df = current_match_data[['PLAYER_NAME', 'JERSEY', 'DISTANCE', 'TOP_SPEED', 'SPRINTS']].copy()
        view_df.columns = ['Spiller', 'Nr', 'Distance (m)', 'Topfart (km/t)', 'Sprints']
        st.dataframe(view_df.sort_values('Distance (m)', ascending=False), use_container_width=True, hide_index=True)
    else:
        st.warning(f"Kunne ikke matche ID: {m_id}")
        st.info("Her er de UUID'er der ligger i din fysiske tabel lige nu:")
        st.write(df_fys['MATCH_OPTAUUID'].unique()[:10])
