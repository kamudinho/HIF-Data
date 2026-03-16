import streamlit as st
import pandas as pd

def vis_side(dp):
    st.title("Fysisk Data - Hvidovre IF")

    # 1. Hent data
    df_fys = dp.get("fysisk_data", pd.DataFrame())
    matches = dp.get("matches", pd.DataFrame())
    
    # Vi har brug for metadata til at mappe UUID til SSIID
    # Hvis du ikke har denne i din datapakke endnu, skal vi tilføje den i main
    metadata = dp.get("match_metadata", pd.DataFrame())

    if df_fys.empty:
        st.error("Ingen fysisk data fundet i databasen.")
        return

    # 2. Match Vælger
    matches = matches.sort_values('MATCH_DATE_FULL', ascending=False)
    match_options = matches.apply(
        lambda r: f"{r['MATCH_DATE_FULL'].strftime('%d/%m')} - {r['CONTESTANTHOME_NAME']} vs {r['CONTESTANTAWAY_NAME']}", 
        axis=1
    ).tolist()
    
    selected_match_name = st.selectbox("Vælg kamp", match_options)
    selected_idx = match_options.index(selected_match_name)
    selected_match = matches.iloc[selected_idx]
    
    # 3. Find det rigtige ID til filtrering
    # Vi prøver først at se om vi kan finde SSIID i metadataen
    target_uuid = str(selected_match['MATCH_OPTAUUID']).strip()
    
    # LOGIK: Vi filtrerer df_fys. 
    # Da vi er i tvivl om hvilken kolonne der linker, prøver vi begge
    current_match_data = df_fys[
        (df_fys['MATCH_OPTAUUID'].astype(str).str.contains(target_uuid, na=False)) |
        (df_fys['MATCH_OPTAUUID'].astype(str).isin(metadata[metadata['MATCH_OPTAUUID'] == target_uuid]['MATCH_SSIID']))
    ].copy()

    # --- DEBUG (Fjern når det virker) ---
    with st.expander("System Debug"):
        st.write(f"Valgt Match UUID: {target_uuid}")
        st.write(f"Antal rækker i fysisk tabel: {len(df_fys)}")
        if not df_fys.empty:
            st.write("Eksempel på ID i fysisk tabel:", df_fys['MATCH_OPTAUUID'].iloc[0])

    # 4. Visning
    if not current_match_data.empty:
        st.subheader(f"Fysiske stats for kampen")
        
        # Omdøb og formater
        res = current_match_data[['PLAYER_NAME', 'JERSEY', 'DISTANCE', 'TOP_SPEED', 'SPRINTS']].copy()
        res.columns = ['Spiller', 'Nr', 'Distance (m)', 'Topfart (km/t)', 'Sprints']
        
        st.dataframe(res.sort_values('Distance (m)', ascending=False), use_container_width=True, hide_index=True)
    else:
        st.warning("Ingen fysiske data fundet for denne kamp.")
        st.info("Dette skyldes ofte at Second Spectrum data først lander 24-48 timer efter kampen.")
