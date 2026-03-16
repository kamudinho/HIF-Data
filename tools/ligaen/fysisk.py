import streamlit as st
import pandas as pd

def vis_side(dp):
    # Overskriften er allerede i top-baren, men vi kan tilføje en subheader
    st.markdown("### 🏃‍♂️ Fysisk Overblik")

    df_fys = dp.get("fysisk_data", pd.DataFrame())
    matches = dp.get("matches", pd.DataFrame())

    if df_fys.empty:
        st.warning("Ingen fysisk data tilgængelig i datapakken for denne sæson.")
        return

    # 1. LIGA OVERBLIK (Leaderboard)
    with st.expander("🏆 Top 10 Præstationer i Ligaen", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Distance (m)**")
            # Vi tager de 10 højeste distancer
            st.dataframe(df_fys.nlargest(10, 'DISTANCE')[['PLAYER_NAME', 'DISTANCE']], hide_index=True)
        with col2:
            st.write("**Topfart (km/t)**")
            st.dataframe(df_fys.nlargest(10, 'TOP_SPEED')[['PLAYER_NAME', 'TOP_SPEED']], hide_index=True)

    st.markdown("---")

    # 2. SPECIFIK KAMP (Din eksisterende logik)
    if not matches.empty:
        match_labels = matches.apply(
            lambda row: f"{row['MATCH_DATE_FULL'].strftime('%d/%m')} - {row['CONTESTANTHOME_NAME']} vs {row['CONTESTANTAWAY_NAME']}", 
            axis=1
        )
        
        selected_idx = st.selectbox("Vælg kamp for detaljeret spiller-statistik", range(len(match_labels)), format_func=lambda x: match_labels.iloc[x])
        selected_match = matches.iloc[selected_idx]
        
        # Filtrering i hukommelsen (Lynhurtigt)
        m_uuid = selected_match['MATCH_OPTAUUID']
        current_match_data = df_fys[df_fys['MATCH_OPTAUUID'] == m_uuid]

        if not current_match_data.empty:
            st.subheader(f"Data for: {match_labels.iloc[selected_idx]}")
            # Formatering af visningen
            disp_df = current_match_data[['PLAYER_NAME', 'JERSEY', 'DISTANCE', 'SPRINTS', 'TOP_SPEED']].copy()
            disp_df.columns = ['Spiller', 'Nr', 'Distance (m)', 'Sprints', 'Topfart (km/t)']
            st.dataframe(disp_df.sort_values("Distance (m)", ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("Der er ikke indlæst tracking-data for denne specifikke kamp endnu.")

    st.write(f"Antal rækker i df_fys: {len(df_fys)}")
    st.write("Første 2 rækker af data:", df_fys.head(2))
