def vis_side(dp):
    st.title("⚽ Fysisk Data - Hvidovre IF")
    
    df_fys = dp.get("fysisk_data", pd.DataFrame())
    
    # 1. Sikrere filtrering
    if df_fys.empty:
        st.warning("Ingen fysisk data fundet i databasen overhovedet.")
        return

    # Kamp-vælger (Sørg for at vi kun vælger blandt kampe der har data)
    uuids = df_fys['MATCH_OPTAUUID'].unique()
    # ... din kamp-vælger logik her ...
    
    # Lad os sige vi har filtreret til 'df' for den valgte kamp:
    df = df_fys[df_fys['MATCH_OPTAUUID'] == selected_uuid] 

    # 2. DETTE FIXER FEJLEN
    if df.empty:
        st.error(f"🚨 Der er ingen rækker for den valgte kamp i databasen.")
        st.info("Dette sker ofte hvis kampen er lige spillet, og Second Spectrum ikke har uploadet tallene endnu.")
    else:
        # Nu tør vi godt bruge .iloc[0] eller .idxmax()
        col1, col2, col3 = st.columns(3)
        
        idx_dist = df['DISTANCE'].idxmax()
        idx_speed = df['TOP_SPEED'].idxmax()
        
        top_dist = df.loc[idx_dist]
        top_speed = df.loc[idx_speed]
        
        col1.metric("Mest løbende", f"{top_dist['PLAYER_NAME']}", f"{top_dist['DISTANCE']/1000:.2f} km")
        col2.metric("Højeste Topfart", f"{top_speed['PLAYER_NAME']}", f"{top_speed['TOP_SPEED']:.1f} km/h")
        col3.metric("Spillere", len(df))

        st.dataframe(df)
