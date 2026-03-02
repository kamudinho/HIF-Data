import streamlit as st
import pandas as pd

def vis_side(dp):
    st.title("Kampprogram & Resultater")
    
    # 1. HENT DATA FRA PAKKEN
    df_matches = dp.get("opta_matches", pd.DataFrame())
    logo_map = dp.get("logo_map", {})
    hif_opta_uuid = dp.get("TEAM_OPTA_UUID")
    
    if df_matches.empty:
        st.warning("Ingen kampdata fundet i Opta-feedet.")
        return

    # 2. FILTRERING: KUN HVIDOVRES KAMPE (VALGFRIT)
    show_hif_only = st.checkbox("Vis kun Hvidovre IF kampe", value=True)
    
    if show_hif_only:
        display_df = df_matches[
            (df_matches["CONTESTANTHOME_OPTAUUID"] == hif_opta_uuid) | 
            (df_matches["CONTESTANTAWAY_OPTAUUID"] == hif_opta_uuid)
        ].copy()
    else:
        display_df = df_matches.copy()

    # 3. SORTERING EFTER RUNDE
    rounds = sorted(display_df["MATCHDAY"].unique())
    
    for r in rounds:
        st.markdown(f"### Runde {int(r)}")
        round_matches = display_df[display_df["MATCHDAY"] == r]
        
        for _, match in round_matches.iterrows():
            h_name = match["CONTESTANTHOME_NAME"]
            a_name = match["CONTESTANTAWAY_NAME"]
            h_score = match["TOTAL_HOME_SCORE"]
            a_score = match["TOTAL_AWAY_SCORE"]
            status = match["STATUS"]
            
            # Find logoer i logo_map
            h_logo = logo_map.get(h_name, "")
            a_logo = logo_map.get(a_name, "")
            
            # Layout for hver kamp
            with st.container(border=True):
                col1, col2, col3, col4, col5 = st.columns([1, 3, 1, 3, 1])
                
                with col1:
                    if h_logo: st.image(h_logo, width=40)
                
                with col2:
                    # Gør holdnavnet fedt, hvis det er Hvidovre
                    st.write(f"**{h_name}**" if h_name == "Hvidovre" else h_name)
                
                with col3:
                    if status == "Played":
                        st.markdown(f"**{int(h_score)} - {int(a_score)}**")
                    else:
                        st.write("vs")
                
                with col4:
                    st.write(f"**{a_name}**" if a_name == "Hvidovre" else a_name)
                    
                with col5:
                    if a_logo: st.image(a_logo, width=40)

    # 4. EKSTRA: VIS TABEL-STATS (HVIS RELEVANT)
    if st.sidebar.button("Vis Opta Rådata"):
        st.write(df_matches)
