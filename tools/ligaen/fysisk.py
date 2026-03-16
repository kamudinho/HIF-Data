import streamlit as st
import pandas as pd

def vis_side(dp):
    st.title("⚽ Fysisk Data - Hvidovre IF")
    
    # Hent data fra pakken
    # Vi bruger 'fysisk_data' som vi definerede i Query 10
    df = dp.get("fysisk_data", pd.DataFrame())
    name_map = dp.get("name_map", {})

    if df.empty:
        st.warning("⚠️ Ingen fysisk data fundet for de valgte filtre.")
        st.info("Søgningen er begrænset til NordicBet Liga 2025/26 via din SQL query.")
    else:
        # 1. Konverter navne hvis muligt (valgfrit)
        if name_map:
            # Hvis vi har OptaUUID'er i dataen, kan vi mappe til de pæne navne
            # Men Query 10 returnerer pt. PLAYER_NAME direkte fra Second Spectrum
            pass

        # 2. Key Metrics (Top Scorer af distance/speed)
        col1, col2, col3 = st.columns(3)
        
        top_dist = df.iloc[df['DISTANCE'].idxmax()]
        top_speed = df.iloc[df['TOP_SPEED'].idxmax()]
        
        col1.metric("Mest løbende", f"{top_dist['PLAYER_NAME']}", f"{top_dist['DISTANCE']:.1f} m")
        col2.metric("Højeste Topfart", f"{top_speed['PLAYER_NAME']}", f"{top_speed['TOP_SPEED']:.1f} km/h")
        col3.metric("Antal spillere", len(df))

        st.divider()

        # 3. Interaktiv Tabel
        st.subheader("Spillerstatistik")
        
        # Omdøb kolonner til noget mere læsbart for brugeren
        display_df = df.copy()
        display_df.columns = [c.replace('_', ' ').title() for c in display_df.columns]
        
        st.dataframe(
            display_df, 
            column_config={
                "Distance": st.column_config.NumberColumn("Total Distance (m)", format="%.0f"),
                "Top Speed": st.column_config.NumberColumn("Topfart (km/h)", format="%.1f"),
                "Sprinting": st.column_config.NumberColumn("Sprint (m)", format="%.0f")
            },
            hide_index=True,
            use_container_width=True
        )

        # 4. En lille visualisering
        st.subheader("Distance pr. Spiller")
        st.bar_chart(df.set_index('PLAYER_NAME')['DISTANCE'])

    # Diagnose-sektion gemt i en expander
    with st.expander("🔍 Teknisk Diagnose"):
        st.write("Dataform:", df.shape)
        if not df.empty:
            st.write("Kolonner i dataframe:", list(df.columns))
        st.write("Config fra datapakke:", dp.get("config", {}))
