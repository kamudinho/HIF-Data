import streamlit as st
from data.data_load import load_snowflake_query, get_data_package

def vis_hold_detaljer():
    # 1. Hent data
    dp = get_data_package()
    comp_f = dp["comp_filter"]
    seas_f = dp["season_filter"]
    
    df = load_snowflake_query("team_stats_full", comp_f, seas_f)
    
    if df.empty:
        st.error("Kunne ikke hente data.")
        return

    st.title("Hold Analyse")

    # 2. Opret tabs
    tab1, tab2, tab3 = st.tabs(["📊 Generelt", "⚽ Offensivt", "🛡️ Defensivt"])

    with tab1:
        st.subheader("Overblik")
        # Her viser du f.eks. Stilling, Kampe, Point
        cols = ['TEAMNAME', 'MATCHES', 'TOTALPOINTS', 'TOTALWINS', 'TOTALDRAWS', 'TOTALLOSSES']
        st.dataframe(df[cols].sort_values("TOTALPOINTS", ascending=False), hide_index=True)

    with tab2:
        st.subheader("Offensive Stats")
        # Her viser du Mål, xG, Skud
        cols_off = ['TEAMNAME', 'GOALS', 'XGSHOT', 'SHOTS']
        # Vi tilføjer en beregning af effektivitet
        df_off = df.copy()
        df_off['Mål pr. xG'] = (df_off['GOALS'] / df_off['XGSHOT']).round(2)
        st.dataframe(df_off[['TEAMNAME', 'GOALS', 'XGSHOT', 'Mål pr. xG', 'SHOTS']], hide_index=True)

    with tab3:
        st.subheader("Defensive Stats")
        # Her viser du Mål Imod, xG Imod, PPDA
        cols_def = ['TEAMNAME', 'CONCEDEDGOALS', 'XGSHOTAGAINST', 'PPDA']
        st.dataframe(df[cols_def].sort_values("CONCEDEDGOALS", ascending=True), hide_index=True)
