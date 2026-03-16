#tools/ligaen/fysisk.py
import streamlit as st
import pandas as pd

def vis_side(dp):
    st.title("Fysisk Data - Rapport")

    # 1. Hent data fra datapakken
    df_fys = dp.get("fysisk_data", pd.DataFrame())
    matches = dp.get("matches", pd.DataFrame())

    # --- DEBUG EXPANDER (Kan fjernes når alt spiller) ---
    with st.expander("🛠 System Check"):
        st.write(f"Antal rækker i fysisk database: {len(df_fys)}")
        if not df_fys.empty:
            st.write("Format eksempel (DB):", df_fys['MATCH_OPTAUUID'].iloc[0])
        st.write(f"Antal kampe i vælger: {len(matches)}")

    if df_fys.empty:
        st.error("🚨 Ingen fysisk data fundet. Prøv at rydde cache (Clear Cache) i Streamlit menuen.")
        return

    # 2. MATCH SELECTOR
    # Vi sorterer kampene efter dato (nyeste først)
    matches = matches.sort_values('MATCH_DATE_FULL', ascending=False)
    
    match_labels = matches.apply(
        lambda row: f"{row['MATCH_DATE_FULL'].strftime('%d/%m')} - {row['CONTESTANTHOME_NAME']} vs {row['CONTESTANTAWAY_NAME']}", 
        axis=1
    )
    
    selected_idx = st.selectbox(
        "Vælg kamp", 
        range(len(match_labels)), 
        format_func=lambda x: match_labels.iloc[x]
    )
    
    selected_match = matches.iloc[selected_idx]
    target_uuid = str(selected_match['MATCH_OPTAUUID']).strip()

    # 3. FILTRERING (Den sikre metode til lange UUIDs)
    # Vi sikrer os at begge sider er strenge og uden whitespace
    df_fys['MATCH_OPTAUUID'] = df_fys['MATCH_OPTAUUID'].astype(str).str.strip()
    current_match_data = df_fys[df_fys['MATCH_OPTAUUID'] == target_uuid].copy()

    # 4. VISNING
    if not current_match_data.empty:
        st.subheader(f"Performance: {match_labels.iloc[selected_idx]}")
        
        # Formatering af visningen
        view_df = current_match_data[['PLAYER_NAME', 'JERSEY', 'DISTANCE', 'TOP_SPEED', 'SPRINTS']].copy()
        
        # Konverter til tal for at sikre korrekt sortering
        view_df['DISTANCE'] = pd.to_numeric(view_df['DISTANCE'], errors='coerce').fillna(0)
        view_df['TOP_SPEED'] = pd.to_numeric(view_df['TOP_SPEED'], errors='coerce').fillna(0)
        view_df['SPRINTS'] = pd.to_numeric(view_df['SPRINTS'], errors='coerce').fillna(0)
        
        view_df.columns = ['Spiller', 'Nr', 'Distance (m)', 'Topfart (km/t)', 'Sprints']
        
        # Style og fremvis
        st.dataframe(
            view_df.sort_values('Distance (m)', ascending=False), 
            use_container_width=True, 
            hide_index=True
        )
        
        # En lille opsummering i bunden
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Distance", f"{int(view_df['Distance (m)'].sum())} m")
        with col2:
            st.metric("Højeste Topfart", f"{view_df['Topfart (km/t)'].max()} km/t")
        with col3:
            st.metric("Total Sprints", int(view_df['Sprints'].sum()))

    else:
        st.warning(f"Ingen match fundet for ID: {target_uuid}")
        st.info("Dette sker typisk hvis kampen endnu ikke er processeret af Second Spectrum.")
        
        # Debug hjælp: Vis hvad vi rent faktisk har af ID'er
        with st.expander("Se tilgængelige ID'er i databasen"):
            st.write(df_fys['MATCH_OPTAUUID'].unique())
