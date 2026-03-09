import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    # 1. HENT DATA (Vi sikrer os, at vi rammer de rigtige nøgler fra dit dict)
    df_lb = dp.get("player_linebreaks", pd.DataFrame())
    df_xg = dp.get("xg_agg", pd.DataFrame())  # eller hvad din xG-tabel hedder i dp
    name_map = dp.get("name_map", {})

    if df_lb.empty:
        st.error("Linebreak-data er tom (df_lb er empty). Tjek om 'player_linebreaks' er den rigtige nøgle i dit dp-dict.")
        return

    # 2. STANDARDISER KOLONNER (Tving alt til STORE BOGSTAVER så de matcher dit dump)
    df_lb.columns = [c.upper() for c in df_lb.columns]
    
    # 3. SPILLERVALG
    # Vi finder alle unikke spillere i din linebreak-tabel
    unique_uuids = df_lb['PLAYER_OPTAUUID'].unique()
    
    # Lav en liste med navne baseret på din name_map
    spiller_liste = {name_map.get(uuid, uuid): uuid for uuid in unique_uuids}
    valgt_navn = st.selectbox("Vælg spiller", options=sorted(spiller_liste.keys()))
    valgt_uuid = spiller_liste[valgt_navn]

    # 4. FILTRER OG VIS DATA FOR ANDREAS SMED (eller den valgte)
    p_data = df_lb[df_lb['PLAYER_OPTAUUID'] == valgt_uuid].copy()

    if not p_data.empty:
        st.subheader(f"Linebreaks for {valgt_navn}")
        
        # Vi fjerner procent-rækkerne for at få en ren graf over antal
        graf_df = p_data[~p_data['STAT_TYPE'].str.contains('percentage', case=False)]
        
        # Lav en hurtig bar-chart
        fig = px.bar(graf_df, 
                     x='STAT_TYPE', 
                     y='STAT_VALUE', 
                     title=f"Statistik for {valgt_navn}",
                     color_discrete_sequence=['#FF4B4B'])
        st.plotly_chart(fig, use_container_width=True)

        # Vis den rå tabel nedenunder så vi kan se tallene
        st.dataframe(p_data[['STAT_TYPE', 'STAT_VALUE', 'STAT_FH', 'STAT_SH']], 
                     use_container_width=True, 
                     hide_index=True)
    else:
        st.warning(f"Ingen data fundet for {valgt_navn} (UUID: {valgt_uuid})")
