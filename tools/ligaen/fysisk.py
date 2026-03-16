import streamlit as st
import pandas as pd

def vis_side(dp):
    st.title("⚽ Fysisk Data - 1. Division")
    
    # Vi henter begge potentielle datakilder fra din pakke
    df_fys = dp.get("fysisk_data", pd.DataFrame())  # Query 10 (F53A)
    # Vi henter også Summary data fra pakken (Sørg for at den er i analyse_load.py)
    df_sum = dp.get("opta", {}).get("team_linebreaks", pd.DataFrame()) # Midlertidig placeholder hvis ikke navngivet
    
    # 1. Tjek den primære tabel (F53A_GAME_PLAYER)
    st.subheader("Primær Tracking (F53A)")
    if not df_fys.empty:
        st.success(f"✅ Succes! Fundet {len(df_fys)} rækker i GAME_PLAYER.")
        
        # Mulighed for at vælge kamp hvis data findes
        kampe = df_fys['MATCH_SSIID'].unique()
        valgt_ssiid = st.selectbox("Vælg kamp (SSIID):", kampe)
        
        filtered_df = df_fys[df_fys['MATCH_SSIID'] == valgt_ssiid]
        st.dataframe(filtered_df)
    else:
        st.error("🚨 Ingen data i F53A_GAME_PLAYER for de valgte filtre.")
        st.info("Dette betyder ofte, at de dybe tracking-data ikke er leveret for 1. division endnu.")

    st.divider()

    # 2. Diagnose: Findes forbindelsen overhovedet?
    with st.expander("🔍 Teknisk Diagnose - Hvor knækker forbindelsen?"):
        st.write("Dine indlæste tabeller:")
        
        col1, col2 = st.columns(2)
        with col1:
            match_count = len(dp.get("matches", []))
            st.metric("Kampe i OPTA_MATCHINFO", match_count)
            
        with col2:
            # Vi tjekker her om 'fysisk_data' er None eller bare tom
            if "fysisk_data" in dp:
                st.write("Variablen 'fysisk_data' findes i datapakken.")
            else:
                st.write("⚠️ 'fysisk_data' blev aldrig tilføjet til datapakken i analyse_load.py")

        # Tjekker kolonne-navne hvis der er data
        if not df_fys.empty:
            st.write("Kolonner fundet:", list(df_fys.columns))
