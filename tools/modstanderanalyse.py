import streamlit as st
import pandas as pd
import plotly.express as px

# Vi ændrer input-navnet fra df_teams_csv til hold_map
def vis_side(df_team_matches, hold_map):
    st.caption("Modstanderanalyse (Snowflake Direkte)")
    
    # DEBUG: Se hvad hold_map egentlig indeholder
    with st.expander("Debug: Tjek Hold Map"):
        st.write(f"Antal hold i map: {len(hold_map)}")
        st.write("Er 38331 i map?", "38331" in hold_map)
        st.write("Første 5 hold i map:", list(hold_map.items())[:5])

    # 1. Tjek data
    if df_team_matches is None or df_team_matches.empty:
        st.error("Ingen data modtaget fra Snowflake.")
        return

    # 2. Lav navne-vælger i stedet for ID-vælger
    if 'TEAM_WYID' in df_team_matches.columns:
        tilgaengelige_ids = df_team_matches['TEAM_WYID'].unique()
        
        navne_dict = {}
        for tid in tilgaengelige_ids:
            # Vi tvinger både ID fra Snowflake og opslag i hold_map til at være string
            str_tid = str(int(tid)) if pd.notnull(tid) else "0"
            navn = hold_map.get(str_tid, f"Ukendt ({str_tid})")
            navne_dict[navn] = tid
        
        valgt_navn = st.selectbox(
            "Vælg modstander:",
            options=sorted(navne_dict.keys())
        )
        
        valgt_id = navne_dict[valgt_navn]

        # 3. Filtrer data
        df_filtreret = df_team_matches[df_team_matches['TEAM_WYID'] == valgt_id].copy()
    else:
        st.error("Kolonnen 'TEAM_WYID' mangler.")
        return

    # 4. Vis resultater med Navn
    st.success(f"Viser data for: {valgt_navn}")
    
    col1, col2 = st.columns(2)
    col1.metric("Antal kampe fundet", len(df_filtreret))
    if 'XG' in df_filtreret.columns:
        col2.metric("Gns. xG", round(df_filtreret['XG'].mean(), 2))

    st.subheader(f"Kampdata for {valgt_navn}")
    st.dataframe(df_filtreret, use_container_width=True)
