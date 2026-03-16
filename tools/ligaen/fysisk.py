import streamlit as st
import pandas as pd

def vis_side(dp):
    st.title("Fysisk Data - Rapport")

    df_fys = dp.get("fysisk_data", pd.DataFrame())
    matches = dp.get("matches", pd.DataFrame())

    if df_fys.empty:
        st.warning("Ingen fysisk data fundet i databasen for denne periode.")
        return

    # 1. MATCH SELECTOR
    match_labels = matches.apply(
        lambda row: f"{row['MATCH_DATE_FULL'].strftime('%d/%m')} - {row['CONTESTANTHOME_NAME']} vs {row['CONTESTANTAWAY_NAME']}", 
        axis=1
    )
    
    selected_idx = st.selectbox("Vælg kamp", range(len(match_labels)), format_func=lambda x: match_labels.iloc[x])
    selected_match = matches.iloc[selected_idx]
    
    # 2. DEN SIKRE FILTRERING (Løser UUID problemet)
    # Vi tager det korte ID fra kampen (f.eks. 2435012)
    m_id = str(selected_match['MATCH_OPTAUUID']).replace('g', '')
    
    # Vi tjekker om det korte ID findes INDE I det lange ID fra Second Spectrum
    current_match_data = df_fys[df_fys['MATCH_OPTAUUID'].str.contains(m_id, na=False)]

    # 3. VISNING
    if not current_match_data.empty:
        st.subheader(f"Spiller Performance: {match_labels.iloc[selected_idx]}")
        
        # Omdøb kolonner så de er pæne
        view_df = current_match_data[['PLAYER_NAME', 'JERSEY', 'DISTANCE', 'TOP_SPEED', 'SPRINTS']].copy()
        view_df.columns = ['Spiller', 'Nr', 'Distance (m)', 'Topfart (km/t)', 'Sprints']
        
        st.dataframe(view_df.sort_values('Distance (m)', ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info(f"Ingen fysisk data matchet for ID: {m_id}. Systemet leder efter dette ID i de lange UUID-strenge.")
        # Debug: Vis hvad vi rent faktisk har i tabellen
        with st.expander("Se rå UUID'er i databasen (Debug)"):
            st.write(df_fys['MATCH_OPTAUUID'].unique()[:5])
